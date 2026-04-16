import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from utils import (
    EMPTY_VALUE,
    clean_text,
    dedupe_keep_order,
    default_metadata,
    ensure_dir,
    extract_emails,
    join_or_default,
    safe_excerpt,
    sentence_split,
    write_json,
    write_text,
)

CANONICAL_SECTIONS = {
    "abstract": ["abstract"],
    "keywords": ["keywords"],
    "introduction": ["introduction"],
    "related_work": ["related work", "background", "prior work"],
    "method": ["method", "approach", "methodology", "proposed method"],
    "experiments": ["experiments", "experimental setup", "experiment", "implementation details"],
    "results": ["results", "findings"],
    "discussion": ["discussion", "analysis"],
    "limitations": ["limitations", "limitation"],
    "conclusion": ["conclusion", "conclusions"],
    "references": ["references", "bibliography"],
    "appendix": ["appendix", "supplementary"],
}

AFFILIATION_HINTS = [
    "university",
    "institute",
    "laboratory",
    "lab",
    "college",
    "school",
    "department",
    "faculty",
    "centre",
    "center",
    "academy",
    "hospital",
]

KNOWN_DATASETS = [
    "ImageNet",
    "COCO",
    "CIFAR-10",
    "CIFAR-100",
    "MNIST",
    "SQuAD",
    "GLUE",
    "SuperGLUE",
    "WMT14",
    "MS MARCO",
    "LibriSpeech",
    "KITTI",
    "Cityscapes",
]

KNOWN_MODELS = [
    "BERT",
    "RoBERTa",
    "T5",
    "GPT",
    "LLaMA",
    "ViT",
    "ResNet",
    "DenseNet",
    "UNet",
    "Transformer",
    "Swin",
]

KNOWN_METRICS = [
    "accuracy",
    "top-1",
    "top-5",
    "f1",
    "precision",
    "recall",
    "auc",
    "mAP",
    "BLEU",
    "ROUGE",
    "WER",
    "CER",
    "MSE",
    "MAE",
    "IoU",
]

SECTION_LIKE_WORDS = {
    "abstract",
    "introduction",
    "related work",
    "method",
    "approach",
    "experiments",
    "results",
    "conclusion",
    "references",
}


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, List[Dict[str, object]]]:
    try:
        import fitz

        doc = fitz.open(pdf_path)
        pages: List[Dict[str, object]] = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            captions = []
            for line in text.splitlines():
                candidate = line.strip()
                if re.match(r"^(Figure|Fig\.?|Table)\s+\d+[A-Za-z]?\b", candidate, flags=re.I):
                    captions.append(candidate)
            pages.append(
                {
                    "page": i,
                    "text": text,
                    "captions": captions,
                }
            )
        full = "\n\n".join([f"[Page {p['page']}]\n{p['text']}" for p in pages])
        return full, pages
    except Exception:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text, "captions": []})
        full = "\n\n".join([f"[Page {p['page']}]\n{p['text']}" for p in pages])
        return full, pages


def _line_is_author_like(line: str) -> bool:
    if "@" in line:
        return False
    token_count = len(line.split())
    if token_count < 2 or token_count > 20:
        return False
    lowercase_ratio = sum(1 for ch in line if ch.islower()) / max(1, sum(1 for ch in line if ch.isalpha()))
    if lowercase_ratio > 0.85:
        return False
    return any(separator in line for separator in [",", " and ", ";"]) or bool(
        re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", line)
    )


def infer_title_authors_affiliations(lines: List[str]) -> Dict[str, object]:
    cleaned_lines = [ln.strip() for ln in lines if ln.strip()]
    if not cleaned_lines:
        return {
            "paper_title": EMPTY_VALUE,
            "authors": [],
            "affiliations": [],
            "author_affiliation_map": {},
            "corresponding_author": EMPTY_VALUE,
            "corresponding_email": EMPTY_VALUE,
            "author_affiliation_notes": "No front-matter text could be extracted.",
        }

    scored: List[Tuple[float, int, str]] = []
    for idx, line in enumerate(cleaned_lines[:30]):
        lower = line.lower()
        score = 0.0
        if 24 <= len(line) <= 220:
            score += 3.0
        if idx < 6:
            score += 2.0
        if "@" in line or "http" in lower:
            score -= 4.0
        if lower in SECTION_LIKE_WORDS:
            score -= 5.0
        if any(hint in lower for hint in AFFILIATION_HINTS):
            score -= 2.0
        if line.endswith("."):
            score -= 1.0
        score += min(1.5, len(re.findall(r"[A-Z]", line)) * 0.08)
        scored.append((score, idx, line))

    title = max(scored, key=lambda item: item[0])[2] if scored else EMPTY_VALUE
    title_index = next((idx for _, idx, text in scored if text == title), 0)

    author_candidates: List[str] = []
    affiliation_candidates: List[str] = []
    possible_corresponding_author = EMPTY_VALUE
    possible_corresponding_email = EMPTY_VALUE

    search_window = cleaned_lines[title_index + 1 : title_index + 22]
    for line in search_window:
        lower = line.lower()
        if any(hint in lower for hint in AFFILIATION_HINTS):
            affiliation_candidates.append(line)
        if _line_is_author_like(line):
            author_candidates.append(line)
        if "correspond" in lower:
            mail = extract_emails(line)
            if mail:
                possible_corresponding_email = mail[0]
            if ":" in line:
                possible_corresponding_author = line.split(":", maxsplit=1)[-1].strip()
        if "*" in line and not affiliation_candidates and _line_is_author_like(line):
            author_candidates.append(re.sub(r"[*†‡]", "", line))

    parsed_authors: List[str] = []
    for line in author_candidates[:4]:
        candidates = re.split(r",|;|\band\b", line)
        for item in candidates:
            normalized = re.sub(r"\s*\d+$", "", item).strip(" *†‡")
            if re.search(r"\b[A-Z][a-z]+(?: [A-Z][a-z.'-]+)+\b", normalized):
                parsed_authors.append(normalized)

    emails = extract_emails("\n".join(search_window))
    if emails and possible_corresponding_email == EMPTY_VALUE:
        possible_corresponding_email = emails[0]

    authors = dedupe_keep_order(parsed_authors)
    affiliations = dedupe_keep_order(affiliation_candidates)

    author_affiliation_map: Dict[str, List[str]] = {}
    if authors and affiliations:
        if len(affiliations) == 1:
            for author in authors:
                author_affiliation_map[author] = [affiliations[0]]
        else:
            for idx, author in enumerate(authors):
                author_affiliation_map[author] = [affiliations[idx % len(affiliations)]]

    notes = "Affiliation mapping inferred from first-page lines."
    if authors and affiliations and len(affiliations) > 1:
        notes = "Affiliation mapping is partially ambiguous in the source PDF."
    if not authors or not affiliations:
        notes = "Author or affiliation lines were incomplete in the extracted text."

    return {
        "paper_title": title if title else EMPTY_VALUE,
        "authors": authors,
        "affiliations": affiliations,
        "author_affiliation_map": author_affiliation_map,
        "corresponding_author": possible_corresponding_author,
        "corresponding_email": possible_corresponding_email,
        "author_affiliation_notes": notes,
    }


def split_sections(text: str) -> Dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines()]
    anchors = []
    for i, line in enumerate(lines):
        normalized = re.sub(r"^[0-9IVXivx.\-\s]+", "", line).lower().strip(": ")
        for section, aliases in CANONICAL_SECTIONS.items():
            if normalized in aliases or any(normalized.startswith(alias + " ") for alias in aliases):
                anchors.append((i, section))
                break

    anchors = sorted(set(anchors), key=lambda x: x[0])
    if not anchors:
        return {"full_text": text}

    output: Dict[str, str] = {}
    for idx, (start, section) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        if block:
            output[section] = block
    return output


def extract_doi(text: str) -> str:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", text)
    return match.group(0) if match else EMPTY_VALUE


def extract_code_link(text: str) -> str:
    urls = re.findall(r"https?://[^\s)]+", text)
    for url in urls:
        if any(keyword in url.lower() for keyword in ["github", "gitlab", "project", "code"]):
            return url.rstrip(".,")
    return EMPTY_VALUE


def extract_year(text: str) -> str:
    years = re.findall(r"\b(19|20)\d{2}\b", text)
    if not years:
        return EMPTY_VALUE
    candidates = re.findall(r"\b(?:19|20)\d{2}\b", text[:4000])
    return candidates[0] if candidates else years[0]


def extract_entities(cleaned_text: str, sections: Dict[str, str]) -> Dict[str, List[str]]:
    search_space = "\n".join([cleaned_text, sections.get("method", ""), sections.get("experiments", ""), sections.get("results", "")])

    datasets = []
    for term in KNOWN_DATASETS:
        if re.search(rf"\b{re.escape(term)}\b", search_space, flags=re.I):
            datasets.append(term)
    datasets += re.findall(r"\b([A-Z][A-Za-z0-9-]{2,})\s+(?:dataset|benchmark|corpus)\b", search_space)

    models = []
    for term in KNOWN_MODELS:
        if re.search(rf"\b{re.escape(term)}\b", search_space, flags=re.I):
            models.append(term)
    models += re.findall(r"\b([A-Z][A-Za-z0-9-]{2,})\s+(?:model|backbone|architecture)\b", search_space)

    metrics = []
    for metric in KNOWN_METRICS:
        if re.search(rf"\b{re.escape(metric)}\b", search_space, flags=re.I):
            metrics.append(metric.upper() if metric.isupper() else metric)

    hardware = re.findall(
        r"\b(?:NVIDIA\s+)?(?:A100|H100|V100|RTX\s?\d{3,4}|TPU\s?v?\d+|MI\d{3})\b",
        search_space,
        flags=re.I,
    )
    hardware += re.findall(r"\b(?:\d+\s*x\s*)?(?:GPU|CPU)s?\b", search_space, flags=re.I)

    benchmarks = re.findall(r"\b(?:benchmark|leaderboard)\s*(?:on|:)?\s*([A-Z][A-Za-z0-9-]{2,})\b", search_space, flags=re.I)

    return {
        "datasets": dedupe_keep_order(datasets),
        "models": dedupe_keep_order(models),
        "metrics": dedupe_keep_order(metrics),
        "hardware": dedupe_keep_order(hardware),
        "benchmarks": dedupe_keep_order(benchmarks),
    }


def extract_equations(section_text: str) -> List[Dict[str, str]]:
    equations: List[Dict[str, str]] = []
    for line in section_text.splitlines():
        candidate = line.strip()
        if len(candidate) < 8:
            continue
        has_math = bool(re.search(r"[=+\-*/^]|\\sum|\\frac|\\mathbb|\\theta|\\lambda", candidate))
        tagged = bool(re.search(r"\(\d+\)\s*$", candidate))
        if has_math and (tagged or len(re.findall(r"[A-Za-z]", candidate)) > 4):
            equations.append(
                {
                    "equation": candidate[:280],
                    "tag": re.search(r"\((\d+)\)\s*$", candidate).group(1) if re.search(r"\((\d+)\)\s*$", candidate) else "",
                }
            )
    deduped = []
    seen = set()
    for eq in equations:
        key = eq["equation"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(eq)
    return deduped[:50]


def extract_tables_from_pages(pages: List[Dict[str, object]]) -> List[Dict[str, object]]:
    tables = []
    for page in pages:
        page_number = int(page["page"])
        text = str(page["text"])
        captions = page.get("captions") or []
        for caption in captions:
            if re.match(r"^Table\s+\d+", caption, flags=re.I):
                tables.append(
                    {
                        "page": page_number,
                        "caption": caption,
                        "row_estimate": None,
                        "column_estimate": None,
                    }
                )

        for block in text.split("\n\n"):
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            if len(lines) < 3:
                continue
            numeric_dense = sum(1 for ln in lines if len(re.findall(r"\d", ln)) >= 3)
            if numeric_dense >= 2 and any(keyword in block.lower() for keyword in ["acc", "f1", "bleu", "%", "table"]):
                tables.append(
                    {
                        "page": page_number,
                        "caption": lines[0][:180],
                        "row_estimate": len(lines),
                        "column_estimate": max((len(re.split(r"\s{2,}|\t", line)) for line in lines), default=None),
                    }
                )
                break

    unique = []
    seen = set()
    for table in tables:
        key = (table["page"], str(table["caption"]).lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(table)
    return unique[:80]


def extract_figure_table_citations(text: str, table_captions: List[str], figure_captions: List[str]) -> Dict[str, object]:
    citations = []
    for sentence in sentence_split(text):
        for match in re.finditer(r"\b(Figure|Fig\.?|Table)\s*(\d+[A-Za-z]?)\b", sentence, flags=re.I):
            citations.append(
                {
                    "type": "table" if match.group(1).lower().startswith("tab") else "figure",
                    "label": f"{match.group(1)} {match.group(2)}".replace("Fig.", "Figure"),
                    "context": sentence[:280],
                }
            )

    caption_lookup = {caption.lower() for caption in table_captions + figure_captions}
    unresolved = []
    for citation in citations:
        normalized = citation["label"].lower()
        if not any(normalized in caption for caption in caption_lookup):
            unresolved.append(citation["label"])

    by_label = defaultdict(int)
    for citation in citations:
        by_label[citation["label"]] += 1

    return {
        "citations": citations[:200],
        "citation_frequency": dict(sorted(by_label.items(), key=lambda item: item[1], reverse=True)),
        "unresolved_references": dedupe_keep_order(unresolved),
    }


def extract_claim_candidates(sections: Dict[str, str]) -> List[str]:
    source = "\n".join([sections.get("abstract", ""), sections.get("conclusion", ""), sections.get("results", "")])
    claims = []
    for sentence in sentence_split(source):
        lower = sentence.lower()
        if any(
            hint in lower
            for hint in [
                "we propose",
                "we present",
                "we show",
                "our method",
                "outperform",
                "state-of-the-art",
                "improves",
                "significantly",
            ]
        ):
            claims.append(sentence)
    return dedupe_keep_order(claims)[:12]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract metadata and structure from a paper PDF.")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    out = ensure_dir(args.output_dir)

    if args.input_path.suffix.lower() == ".pdf":
        raw_text, pages = extract_text_from_pdf(args.input_path)
    else:
        raw_text = args.input_path.read_text(encoding="utf-8")
        pages = []

    cleaned = clean_text(raw_text)
    sections = split_sections(cleaned)

    head_lines = [ln for ln in cleaned.splitlines()[:140] if ln.strip()]
    front_matter = infer_title_authors_affiliations(head_lines)
    metadata = default_metadata()
    metadata.update(
        {
            "paper_title": front_matter["paper_title"],
            "authors": front_matter["authors"],
            "affiliations": front_matter["affiliations"],
            "author_affiliation_map": front_matter["author_affiliation_map"],
            "corresponding_author": front_matter["corresponding_author"],
            "corresponding_email": front_matter["corresponding_email"],
            "doi": extract_doi(cleaned),
            "code_link": extract_code_link(cleaned),
            "year": extract_year(cleaned),
        }
    )

    entities = extract_entities(cleaned, sections)
    metadata.update(
        {
            "dataset_names": entities["datasets"],
            "model_names": entities["models"],
            "benchmark_names": entities["benchmarks"],
            "metric_names": entities["metrics"],
            "hardware_details": entities["hardware"],
        }
    )

    tables = extract_tables_from_pages(pages)
    figure_captions = []
    table_captions = []
    for page in pages:
        for caption in page.get("captions", []):
            if caption.lower().startswith("table"):
                table_captions.append(caption)
            elif caption.lower().startswith(("figure", "fig.")):
                figure_captions.append(caption)

    equations = extract_equations("\n".join([sections.get("method", ""), sections.get("experiments", ""), sections.get("results", "")]))
    citation_analysis = extract_figure_table_citations(cleaned, table_captions, figure_captions)
    claim_candidates = extract_claim_candidates(sections)

    paper_content = {
        "metadata": metadata,
        "sections": sections,
        "page_count": len(pages),
        "sample_pages": pages[:5],
        "entities": entities,
        "tables": tables,
        "equations": equations,
        "figure_table_citations": citation_analysis,
        "claim_candidates": claim_candidates,
        "author_affiliation_notes": front_matter["author_affiliation_notes"],
        "evidence_notes": {
            "abstract": safe_excerpt(sections.get("abstract", "")),
            "method": safe_excerpt(sections.get("method", "")),
            "results": safe_excerpt(sections.get("results", "")),
            "limitations": safe_excerpt(sections.get("limitations", "")),
        },
    }

    write_text(out / "raw_extracted.txt", raw_text)
    write_text(out / "cleaned_text.txt", cleaned)
    write_json(out / "sectioned_text.json", sections)
    write_json(out / "metadata.json", metadata)
    write_json(out / "entity_catalog.json", entities)
    write_json(out / "table_equation_index.json", {"tables": tables, "equations": equations})
    write_json(out / "figure_table_citations.json", citation_analysis)
    write_json(out / "claim_candidates.json", {"claims": claim_candidates})
    write_json(out / "paper_content.json", paper_content)

    summary = {
        "status": "ok",
        "output_dir": str(out),
        "title": metadata.get("paper_title", EMPTY_VALUE),
        "author_count": len(metadata.get("authors", [])),
        "affiliation_count": len(metadata.get("affiliations", [])),
        "table_count": len(tables),
        "equation_count": len(equations),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
