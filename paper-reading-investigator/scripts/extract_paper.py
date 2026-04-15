import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from utils import clean_text, default_metadata, ensure_dir, extract_emails, safe_excerpt, write_json, write_text

CANONICAL_SECTIONS = {
    "abstract": ["abstract"],
    "introduction": ["introduction"],
    "related_work": ["related work", "background"],
    "method": ["method", "approach", "methodology", "proposed method"],
    "experiments": ["experiments", "experimental setup", "experiment"],
    "results": ["results", "findings"],
    "discussion": ["discussion", "analysis"],
    "limitations": ["limitations", "limitation"],
    "conclusion": ["conclusion", "conclusions"],
    "references": ["references", "bibliography"],
    "appendix": ["appendix", "supplementary"],
}


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, List[Dict[str, str]]]:
    try:
        import fitz

        doc = fitz.open(pdf_path)
        pages = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append({"page": i, "text": text})
        full = "\n\n".join([f"[Page {p['page']}]\n{p['text']}" for p in pages])
        return full, pages
    except Exception:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text})
        full = "\n\n".join([f"[Page {p['page']}]\n{p['text']}" for p in pages])
        return full, pages


def infer_title_and_authors(lines: List[str]) -> Tuple[str, str, str]:
    candidate = [ln.strip() for ln in lines if ln.strip()]
    if not candidate:
        return ("Not clearly stated in the paper.",) * 3

    title = candidate[0]
    author_line = "Not clearly stated in the paper."
    affiliation_line = "Not clearly stated in the paper."

    for idx, line in enumerate(candidate[1:12], start=1):
        if any(x in line.lower() for x in ["university", "institute", "laboratory", "lab", "college", "school"]):
            affiliation_line = line
            if idx >= 1:
                author_line = candidate[idx - 1]
            break

    return title, author_line, affiliation_line


def split_sections(text: str) -> Dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines()]
    anchors = []
    for i, line in enumerate(lines):
        low = re.sub(r"^[0-9.]+\s*", "", line.lower())
        for section, aliases in CANONICAL_SECTIONS.items():
            if low in aliases or any(low.startswith(a + " ") for a in aliases):
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

    head_lines = [ln for ln in cleaned.splitlines()[:80] if ln.strip()]
    title, authors, affiliations = infer_title_and_authors(head_lines)
    emails = extract_emails("\n".join(head_lines))

    metadata = default_metadata()
    metadata.update(
        {
            "paper_title": title,
            "authors": authors,
            "affiliations": affiliations,
            "corresponding_email": emails[0] if emails else metadata["corresponding_email"],
            "corresponding_author": "Not clearly stated in the paper.",
        }
    )

    paper_content = {
        "metadata": metadata,
        "sections": sections,
        "page_count": len(pages),
        "sample_pages": pages[:5],
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
    write_json(out / "paper_content.json", paper_content)

    print(json.dumps({"status": "ok", "output_dir": str(out)}, indent=2))


if __name__ == "__main__":
    main()
