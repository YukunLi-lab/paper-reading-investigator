import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

from utils import EMPTY_VALUE, dedupe_keep_order, join_or_default, read_json, safe_excerpt, sentence_split, write_json


def _to_display(value: object) -> str:
    if value is None:
        return EMPTY_VALUE
    if isinstance(value, list):
        return join_or_default([str(item) for item in value], default=EMPTY_VALUE)
    if isinstance(value, dict):
        if not value:
            return EMPTY_VALUE
        pairs = [f"{key}: {join_or_default(map(str, values)) if isinstance(values, list) else values}" for key, values in value.items()]
        return "; ".join(pairs)
    text = str(value).strip()
    return text if text else EMPTY_VALUE


def _sentence_overlap(a: str, b: str) -> float:
    left = set(re.findall(r"[A-Za-z][A-Za-z0-9\-]+", a.lower()))
    right = set(re.findall(r"[A-Za-z][A-Za-z0-9\-]+", b.lower()))
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


def choose_reproducibility_risk(sections: Dict[str, str], metadata: Dict[str, object], alignment_rows: List[Dict[str, object]]) -> Tuple[str, str]:
    missing_sections = sum(
        1
        for key in ["method", "experiments", "results", "limitations"]
        if key not in sections or len((sections.get(key) or "").strip()) < 200
    )
    missing_hardware = 1 if not metadata.get("hardware_details") else 0
    weak_claims = sum(1 for row in alignment_rows if row.get("support_strength") == "weak")

    score = missing_sections + missing_hardware + (1 if weak_claims >= 2 else 0)
    if score >= 4:
        return "High", "Key implementation/evaluation details and claim evidence are too sparse for reliable reproduction."
    if score >= 2:
        return "Medium", "Some reproduction-critical details exist, but hardware or evidence links remain partially underspecified."
    return "Low", "Method setup, evaluation details, and claim support appear adequate for a first implementation attempt."


def extract_core_concepts(sections: Dict[str, str]) -> List[str]:
    source = "\n".join([sections.get("method", ""), sections.get("introduction", ""), sections.get("abstract", "")])
    concepts = []
    for sentence in sentence_split(source):
        lower = sentence.lower()
        if any(token in lower for token in ["framework", "module", "objective", "loss", "pipeline", "architecture", "algorithm"]):
            concepts.append(sentence)
    return dedupe_keep_order(concepts)[:6]


def build_feynman_block(sections: Dict[str, str], concepts: List[str]) -> Dict[str, str]:
    intro = safe_excerpt(sections.get("introduction", ""), 1100)
    method = safe_excerpt(sections.get("method", ""), 1500)
    concept_list = "; ".join(concepts) if concepts else EMPTY_VALUE
    return {
        "plain_english_explanation": f"Explain it simply: {intro}",
        "problem_statement_simple": "What problem it solves: " + safe_excerpt(sections.get("abstract", ""), 750),
        "step_by_step_mechanism": "How it works step by step: " + method,
        "analogy": "Intuitive analogy: the method behaves like a multi-stage lab protocol where each stage removes one uncertainty source.",
        "common_confusions": "Where confusion usually appears: hidden preprocessing choices, training schedules, and benchmark protocol details.",
        "unresolved_points": "What I still cannot verify from the paper: exact defaults for all hyperparameters and unstated engineering constraints.",
        "core_concepts": concept_list,
    }


def _collect_claims(paper: Dict[str, object], sections: Dict[str, str]) -> List[str]:
    claims = list(paper.get("claim_candidates", []))
    if claims:
        return claims[:12]

    source = "\n".join([sections.get("abstract", ""), sections.get("conclusion", ""), sections.get("results", "")])
    claims = []
    for sentence in sentence_split(source):
        lower = sentence.lower()
        if any(
            trigger in lower
            for trigger in ["we propose", "we show", "we achieve", "outperform", "state-of-the-art", "improve", "significantly"]
        ):
            claims.append(sentence)
    return dedupe_keep_order(claims)[:12]


def _collect_evidence_sentences(sections: Dict[str, str], paper: Dict[str, object]) -> List[str]:
    pools = [sections.get("results", ""), sections.get("experiments", ""), sections.get("discussion", "")]
    citations = paper.get("figure_table_citations", {}).get("citations", [])
    for item in citations:
        context = item.get("context", "")
        if context:
            pools.append(context)
    evidence = []
    for sentence in sentence_split("\n".join(pools)):
        if re.search(r"\d", sentence) or any(keyword in sentence.lower() for keyword in ["table", "figure", "ablation", "baseline", "improv"]):
            evidence.append(sentence)
    return dedupe_keep_order(evidence)


def align_claims_to_evidence(claims: List[str], evidence_pool: List[str]) -> List[Dict[str, object]]:
    rows = []
    for claim in claims:
        scored = sorted(
            ((candidate, _sentence_overlap(claim, candidate)) for candidate in evidence_pool),
            key=lambda item: item[1],
            reverse=True,
        )
        top = scored[:2]
        top_score = top[0][1] if top else 0.0
        if top_score >= 0.22:
            strength = "strong"
        elif top_score >= 0.11:
            strength = "partial"
        else:
            strength = "weak"
        rows.append(
            {
                "claim": claim,
                "support_strength": strength,
                "evidence": [item[0] for item in top if item[1] > 0],
                "score": round(top_score, 3),
            }
        )
    return rows


def maybe_refine_alignment_with_openai(
    alignment: List[Dict[str, object]],
    sections: Dict[str, str],
    model: str,
) -> Tuple[List[Dict[str, object]], str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return alignment, "heuristic_only"

    try:
        from openai import OpenAI
    except Exception:
        return alignment, "heuristic_only_openai_pkg_missing"

    prompt = {
        "alignment": alignment,
        "results_excerpt": safe_excerpt(sections.get("results", ""), 2600),
        "experiments_excerpt": safe_excerpt(sections.get("experiments", ""), 2600),
    }
    system = (
        "You are validating claim-evidence alignment for a paper report. "
        "Return strict JSON list with same claim order and fields: claim, support_strength(strong|partial|weak), evidence(list), score(0-1)."
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model,
            temperature=0,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        text = getattr(response, "output_text", "") or ""
        if not text:
            return alignment, "heuristic_only_llm_empty"
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return alignment, "heuristic_only_llm_parse_failed"
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, list) and parsed:
            return parsed, f"heuristic_plus_llm({model})"
    except Exception:
        return alignment, "heuristic_only_llm_error"
    return alignment, "heuristic_only_llm_fallback"


def render_alignment_summary(rows: List[Dict[str, object]]) -> str:
    if not rows:
        return EMPTY_VALUE
    lines = []
    for idx, row in enumerate(rows, start=1):
        evidence = row.get("evidence") or []
        evidence_preview = "; ".join(evidence[:2]) if evidence else "No direct evidence sentence matched."
        lines.append(f"{idx}. Claim: {row['claim']} | Support: {row['support_strength']} | Evidence: {evidence_preview}")
    return "\n".join(lines)


def summarize_entities(metadata: Dict[str, object]) -> Dict[str, str]:
    return {
        "datasets_summary": _to_display(metadata.get("dataset_names")),
        "models_summary": _to_display(metadata.get("model_names")),
        "benchmarks_summary": _to_display(metadata.get("benchmark_names")),
        "metrics_summary": _to_display(metadata.get("metric_names")),
        "hardware_summary": _to_display(metadata.get("hardware_details")),
    }


def build_slide_outline(analysis: Dict[str, object], paper: Dict[str, object]) -> str:
    rows = analysis.get("claim_evidence_matrix", [])
    top_row = rows[0] if rows else {}
    top_evidence = "; ".join((top_row.get("evidence") or [])[:2]) if top_row else EMPTY_VALUE
    return "\n".join(
        [
            "# Group Meeting Brief",
            "",
            "## Slide 1 - Problem and Motivation",
            analysis.get("problem_statement_simple", EMPTY_VALUE),
            "",
            "## Slide 2 - Method Snapshot",
            analysis.get("technical_method", EMPTY_VALUE),
            "",
            "## Slide 3 - Experimental Setup",
            analysis.get("experimental_setup", EMPTY_VALUE),
            "",
            "## Slide 4 - Results",
            analysis.get("main_results", EMPTY_VALUE),
            "",
            "## Slide 5 - Claim-Evidence Highlight",
            f"Top claim support: {top_row.get('support_strength', EMPTY_VALUE)}",
            top_evidence,
            "",
            "## Slide 6 - Reproducibility",
            f"Risk: {analysis.get('reproducibility_risk', EMPTY_VALUE)}",
            analysis.get("reproducibility_rationale", EMPTY_VALUE),
            "",
            "## Slide 7 - Strengths and Risks",
            analysis.get("strengths", EMPTY_VALUE),
            analysis.get("weaknesses", EMPTY_VALUE),
            "",
            "## Slide 8 - Actionable Next Steps",
            "- Verify unresolved implementation details from appendix/code release.",
            "- Re-run key baseline comparisons with matched data preprocessing.",
            "- Prioritize ablation and stress tests before deployment claims.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze extracted paper content into investigation fields.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--enable-llm-alignment", action="store_true", help="Use OpenAI API when OPENAI_API_KEY is set.")
    parser.add_argument("--llm-model", default="gpt-5-mini", help="Model used for claim-evidence alignment refinement.")
    args = parser.parse_args()

    out = args.output_dir
    paper = read_json(out / "paper_content.json")
    metadata = paper.get("metadata", {})
    sections = paper.get("sections", {})
    entities_summary = summarize_entities(metadata)

    claims = _collect_claims(paper, sections)
    evidence_pool = _collect_evidence_sentences(sections, paper)
    alignment = align_claims_to_evidence(claims, evidence_pool)
    alignment_mode = "heuristic_only"
    if args.enable_llm_alignment:
        alignment, alignment_mode = maybe_refine_alignment_with_openai(alignment, sections, model=args.llm_model)

    risk, rationale = choose_reproducibility_risk(sections, metadata, alignment)
    concepts = extract_core_concepts(sections)
    feynman = build_feynman_block(sections, concepts)

    headline_title = "Strong Idea, but Reproduction Depends on Missing Experimental Specifics"
    if risk == "Low":
        headline_title = "Well-Specified Empirical Study with Practical Reproduction Path"
    elif risk == "High":
        headline_title = "Promising Contribution with Significant Reproducibility and Evidence Gaps"

    analysis = {
        "headline_title": headline_title,
        "headline_assessment": "The paper appears valuable, but evidence linkage and implementation completeness should be checked before committing resources.",
        "paper_title": _to_display(metadata.get("paper_title")),
        "authors": _to_display(metadata.get("authors")),
        "affiliations": _to_display(metadata.get("affiliations")),
        "corresponding_author": _to_display(metadata.get("corresponding_author")),
        "corresponding_email": _to_display(metadata.get("corresponding_email")),
        "venue": _to_display(metadata.get("venue")),
        "year": _to_display(metadata.get("year")),
        "doi": _to_display(metadata.get("doi")),
        "code_link": _to_display(metadata.get("code_link")),
        "executive_summary": safe_excerpt(sections.get("abstract", ""), 1800),
        **feynman,
        "research_question": safe_excerpt(sections.get("introduction", ""), 900),
        "claimed_contributions": _to_display(claims) if claims else safe_excerpt(sections.get("abstract", ""), 900),
        "technical_method": safe_excerpt(sections.get("method", ""), 1700),
        "experimental_setup": safe_excerpt(sections.get("experiments", ""), 1700),
        "main_results": safe_excerpt(sections.get("results", ""), 1700),
        "evidence_strength": render_alignment_summary(alignment),
        "prerequisites": "Python 3.10+, parser dependencies, optional OCRmyPDF/Tesseract, and a reproducible environment manager (venv/conda).",
        "data_requirements": f"Datasets: {entities_summary['datasets_summary']}. Benchmarks: {entities_summary['benchmarks_summary']}.",
        "environment_and_dependencies": f"Models: {entities_summary['models_summary']}; Metrics: {entities_summary['metrics_summary']}; Hardware: {entities_summary['hardware_summary']}.",
        "reproduction_workflow": "1) Rebuild preprocessing. 2) Re-implement method with reported defaults. 3) Re-run baselines. 4) Validate tables/figures against claim-evidence matrix.",
        "missing_details": "Check for missing random seeds, scheduler settings, data filtering rules, and exact evaluation scripts.",
        "reproducibility_risk": risk,
        "reproducibility_rationale": rationale,
        "strengths": "Clear motivation, method narrative, and measurable outcomes linked to concrete experiments.",
        "weaknesses": "Some claims may rely on indirect evidence, and implementation-level details can remain implicit.",
        "methodological_limitations": "Potential mismatch between claimed novelty and ablation coverage if component-level controls are limited.",
        "evaluation_risks": "Risk of overfitting to benchmark protocol if dataset splits and metric computation details are incomplete.",
        "engineering_risks": "Deployment feasibility depends on hardware assumptions and preprocessing reproducibility.",
        "overclaiming_or_underspecification": "Treat generalization claims cautiously if cross-domain and failure-case tests are limited.",
        "author_affiliation_notes": paper.get("author_affiliation_notes", EMPTY_VALUE),
        "final_verdict": "Use this paper as a serious candidate for follow-up, but start with a scoped replication pilot and explicit evidence checklist.",
        "extraction_quality": "Medium-High",
        "ocr_used": "See ocr/ocr_metadata.json.",
        "metadata_confidence": "Medium-High",
        "interpretation_confidence": "Medium",
        "confidence_notes": f"Claim-evidence alignment mode: {alignment_mode}. Confidence drops when citation contexts or equations are incomplete.",
        "datasets_summary": entities_summary["datasets_summary"],
        "models_summary": entities_summary["models_summary"],
        "benchmarks_summary": entities_summary["benchmarks_summary"],
        "metrics_summary": entities_summary["metrics_summary"],
        "hardware_summary": entities_summary["hardware_summary"],
        "claim_evidence_alignment_mode": alignment_mode,
        "claim_evidence_matrix": alignment,
        "table_count": len(paper.get("tables", [])),
        "equation_count": len(paper.get("equations", [])),
        "figure_table_citation_count": len(paper.get("figure_table_citations", {}).get("citations", [])),
    }

    write_json(out / "analysis.json", analysis)
    write_json(out / "claim_evidence_alignment.json", {"mode": alignment_mode, "rows": alignment})
    write_json(
        out / "meeting_brief.json",
        {
            "paper_title": analysis["paper_title"],
            "reproducibility_risk": analysis["reproducibility_risk"],
            "top_claims": [row.get("claim", "") for row in alignment[:5]],
            "slide_outline": build_slide_outline(analysis, paper),
        },
    )

    print(json.dumps({"status": "ok", "analysis": str(out / "analysis.json"), "alignment_mode": alignment_mode}, indent=2))


if __name__ == "__main__":
    main()
