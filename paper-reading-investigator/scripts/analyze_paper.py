import argparse
import json
from pathlib import Path

from utils import EMPTY_VALUE, read_json, safe_excerpt, write_json


def _or_default(value: str) -> str:
    return value if value and value.strip() else EMPTY_VALUE


def choose_reproducibility_risk(sections: dict) -> tuple[str, str]:
    missing = 0
    for key in ["method", "experiments", "results", "limitations"]:
        if key not in sections or len((sections.get(key) or "").strip()) < 100:
            missing += 1

    if missing >= 3:
        return "High", "Critical implementation or evaluation details are missing or too sparse."
    if missing >= 1:
        return "Medium", "Some implementation details are present, but key settings remain underspecified."
    return "Low", "Method and evaluation sections are sufficiently detailed for a first-pass reproduction."


def build_feynman_block(sections: dict) -> dict:
    intro = safe_excerpt(sections.get("introduction", ""), 1000)
    method = safe_excerpt(sections.get("method", ""), 1200)
    return {
        "plain_english_explanation": f"Explain it simply: {_or_default(intro)}",
        "problem_statement_simple": "What problem it solves: " + _or_default(safe_excerpt(sections.get("abstract", ""), 600)),
        "step_by_step_mechanism": "How it works step by step: " + _or_default(method),
        "analogy": "Think of the method as a recipe: inputs are prepared, transformed, and evaluated against a baseline.",
        "common_confusions": "Where confusion usually appears: training details, data preprocessing, and exact hyperparameter schedules.",
        "unresolved_points": "What I still cannot verify from the paper: exact implementation defaults and hidden engineering constraints.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze extracted paper content into investigation fields.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    out = args.output_dir
    paper = read_json(out / "paper_content.json")
    metadata = paper.get("metadata", {})
    sections = paper.get("sections", {})

    risk, rationale = choose_reproducibility_risk(sections)
    feynman = build_feynman_block(sections)

    analysis = {
        "headline_title": "A Promising Paper with Clear Value and Remaining Reproducibility Gaps",
        "headline_assessment": "The paper presents a compelling idea and useful evidence, but key reproduction details remain partially underspecified.",
        "paper_title": metadata.get("paper_title", EMPTY_VALUE),
        "authors": metadata.get("authors", EMPTY_VALUE),
        "affiliations": metadata.get("affiliations", EMPTY_VALUE),
        "corresponding_author": metadata.get("corresponding_author", EMPTY_VALUE),
        "corresponding_email": metadata.get("corresponding_email", EMPTY_VALUE),
        "venue": metadata.get("venue", EMPTY_VALUE),
        "year": metadata.get("year", EMPTY_VALUE),
        "doi": metadata.get("doi", EMPTY_VALUE),
        "code_link": metadata.get("code_link", EMPTY_VALUE),
        "executive_summary": _or_default(safe_excerpt(sections.get("abstract", ""), 1600)),
        **feynman,
        "research_question": _or_default(safe_excerpt(sections.get("introduction", ""), 900)),
        "claimed_contributions": _or_default(safe_excerpt(sections.get("abstract", ""), 900)),
        "technical_method": _or_default(safe_excerpt(sections.get("method", ""), 1600)),
        "experimental_setup": _or_default(safe_excerpt(sections.get("experiments", ""), 1600)),
        "main_results": _or_default(safe_excerpt(sections.get("results", ""), 1600)),
        "evidence_strength": "Claim support appears partial unless explicit quantitative comparisons are recoverable from clean tables.",
        "prerequisites": "Python environment, paper PDF, and optional OCRmyPDF for scanned pages.",
        "data_requirements": "Use the datasets explicitly named in the paper. If unspecified, treat data setup as a blocker.",
        "environment_and_dependencies": "Install dependencies from requirements.txt and system OCR tooling (Tesseract + OCRmyPDF) if needed.",
        "reproduction_workflow": "1) Detect PDF type. 2) OCR fallback if needed. 3) Extract structure. 4) Recreate method and evaluation protocol.",
        "missing_details": "Potential missing details: random seeds, preprocessing defaults, full hyperparameters, and ablation specifics.",
        "reproducibility_risk": risk,
        "reproducibility_rationale": rationale,
        "strengths": "Structured problem framing, explicit method section, and empirical evaluation intent.",
        "weaknesses": "Potentially incomplete implementation details and ambiguous reporting of some setup choices.",
        "methodological_limitations": "If baselines or ablations are incomplete, causal claims remain less certain.",
        "evaluation_risks": "Metric cherry-picking risk and dataset split uncertainty if protocol details are sparse.",
        "engineering_risks": "Reimplementation can drift without exact training recipe and resource assumptions.",
        "overclaiming_or_underspecification": "Treat broad claims cautiously unless robust cross-setting evidence is clearly documented.",
        "author_affiliation_notes": "Prefer first-page title block and footnotes; report ambiguity explicitly where mapping is uncertain.",
        "final_verdict": "Useful and technically meaningful, but reproduce with caution and document assumptions transparently.",
        "extraction_quality": "Medium",
        "ocr_used": "See ocr/ocr_metadata.json when OCR fallback was executed.",
        "metadata_confidence": "Medium",
        "interpretation_confidence": "Medium",
        "confidence_notes": "Confidence drops if OCR noise is high or section boundaries are incomplete.",
    }

    write_json(out / "analysis.json", analysis)
    print(json.dumps({"status": "ok", "analysis": str(out / "analysis.json")}, indent=2))


if __name__ == "__main__":
    main()
