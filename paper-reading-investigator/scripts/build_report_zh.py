import argparse
import re
from pathlib import Path
from typing import Dict

from build_report import render
from utils import EMPTY_VALUE, read_json, write_text

NOT_STATED_ZH = "论文中未明确说明。"

SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
IDENTITY_LINE_RE = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$")

COMMON_REPLACEMENTS = {
    "Not clearly stated in the paper.": NOT_STATED_ZH,
    "The paper presents a compelling idea and useful evidence, but key reproduction details remain partially underspecified.": "论文提出了有价值的思路并给出一定证据，但关键复现细节仍有缺失。",
    "Claim support appears partial unless explicit quantitative comparisons are recoverable from clean tables.": "如果无法从清晰表格中恢复明确的定量对比，当前结论证据强度应视为“部分支持”。",
    "Potential missing details: random seeds, preprocessing defaults, full hyperparameters, and ablation specifics.": "可能缺失的细节包括：随机种子、预处理默认设置、完整超参数与消融实验细节。",
    "Useful and technically meaningful, but reproduce with caution and document assumptions transparently.": "论文具有技术价值，但复现时应保持谨慎，并明确记录所有实现假设。",
}

PREFIX_REPLACEMENTS = {
    "Explain it simply:": "通俗解释：",
    "What problem it solves:": "它解决的问题：",
    "How it works step by step:": "逐步工作机制：",
    "Where confusion usually appears:": "常见困惑点：",
    "What I still cannot verify from the paper:": "仍无法从论文直接验证的点：",
}

RISK_LEVEL_MAP = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

CONFIDENCE_LEVEL_MAP = {
    "low": "低",
    "medium": "中",
    "high": "高",
}


def parse_sections(md_text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    current = None
    buf = []

    for line in md_text.splitlines():
        match = SECTION_HEADING_RE.match(line.strip())
        if match:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = match.group(1).strip()
            buf = []
            continue
        if current is not None:
            buf.append(line)

    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def parse_identity(identity_block: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in identity_block.splitlines():
        line = raw.strip()
        match = IDENTITY_LINE_RE.match(line)
        if match:
            out[match.group(1).strip()] = match.group(2).strip()
    return out


def localize_text(text: str) -> str:
    value = (text or "").strip()
    if not value or value == EMPTY_VALUE:
        return NOT_STATED_ZH

    value = COMMON_REPLACEMENTS.get(value, value)
    for prefix_en, prefix_zh in PREFIX_REPLACEMENTS.items():
        if value.startswith(prefix_en):
            value = value.replace(prefix_en, prefix_zh, 1)
            break

    value = re.sub(r"\bLow\b", "低", value)
    value = re.sub(r"\bMedium\b", "中", value)
    value = re.sub(r"\bHigh\b", "高", value)
    return value


def localize_level(text: str, mapping: Dict[str, str]) -> str:
    raw = (text or "").strip()
    if not raw or raw == EMPTY_VALUE:
        return NOT_STATED_ZH
    return mapping.get(raw.lower(), localize_text(raw))


def pick(analysis: Dict[str, str], identity: Dict[str, str], key: str, identity_key: str) -> str:
    value = (analysis.get(key) or "").strip()
    if value:
        return value
    fallback = (identity.get(identity_key) or "").strip()
    return fallback or EMPTY_VALUE


def build_values(analysis: Dict[str, str], report_path: Path) -> Dict[str, str]:
    final_report_text = report_path.read_text(encoding="utf-8")
    sections = parse_sections(final_report_text)
    identity = parse_identity(sections.get("2. Paper Identity", ""))

    paper_title = pick(analysis, identity, "paper_title", "Paper Title")
    values = {
        "headline_title_zh": f"{paper_title} | 中文精读报告" if paper_title != EMPTY_VALUE else "论文中文精读报告",
        "source_report_path": str(report_path),
        "headline_assessment_zh": localize_text(analysis.get("headline_assessment", "")),
        "paper_title": localize_text(paper_title),
        "authors": localize_text(pick(analysis, identity, "authors", "Authors")),
        "affiliations": localize_text(pick(analysis, identity, "affiliations", "Affiliations")),
        "corresponding_author": localize_text(pick(analysis, identity, "corresponding_author", "Corresponding Author")),
        "corresponding_email": localize_text(pick(analysis, identity, "corresponding_email", "Corresponding Email")),
        "venue": localize_text(pick(analysis, identity, "venue", "Venue / Source")),
        "year": localize_text(pick(analysis, identity, "year", "Year")),
        "doi": localize_text(pick(analysis, identity, "doi", "DOI / Identifier")),
        "code_link": localize_text(pick(analysis, identity, "code_link", "Code / Project Link")),
        "executive_summary_zh": localize_text(analysis.get("executive_summary", "")),
        "research_question_zh": localize_text(analysis.get("research_question", "")),
        "claimed_contributions_zh": localize_text(analysis.get("claimed_contributions", "")),
        "technical_method_zh": localize_text(analysis.get("technical_method", "")),
        "experimental_setup_zh": localize_text(analysis.get("experimental_setup", "")),
        "main_results_zh": localize_text(analysis.get("main_results", "")),
        "evidence_strength_zh": localize_text(analysis.get("evidence_strength", "")),
        "strengths_zh": localize_text(analysis.get("strengths", "")),
        "weaknesses_zh": localize_text(analysis.get("weaknesses", "")),
        "methodological_limitations_zh": localize_text(analysis.get("methodological_limitations", "")),
        "evaluation_risks_zh": localize_text(analysis.get("evaluation_risks", "")),
        "engineering_risks_zh": localize_text(analysis.get("engineering_risks", "")),
        "overclaiming_zh": localize_text(analysis.get("overclaiming_or_underspecification", "")),
        "prerequisites_zh": localize_text(analysis.get("prerequisites", "")),
        "data_requirements_zh": localize_text(analysis.get("data_requirements", "")),
        "environment_and_dependencies_zh": localize_text(analysis.get("environment_and_dependencies", "")),
        "reproduction_workflow_zh": localize_text(analysis.get("reproduction_workflow", "")),
        "missing_details_zh": localize_text(analysis.get("missing_details", "")),
        "reproducibility_risk_zh": localize_level(analysis.get("reproducibility_risk", ""), RISK_LEVEL_MAP),
        "reproducibility_rationale_zh": localize_text(analysis.get("reproducibility_rationale", "")),
        "plain_english_explanation_zh": localize_text(analysis.get("plain_english_explanation", "")),
        "problem_statement_simple_zh": localize_text(analysis.get("problem_statement_simple", "")),
        "step_by_step_mechanism_zh": localize_text(analysis.get("step_by_step_mechanism", "")),
        "analogy_zh": localize_text(analysis.get("analogy", "")),
        "common_confusions_zh": localize_text(analysis.get("common_confusions", "")),
        "unresolved_points_zh": localize_text(analysis.get("unresolved_points", "")),
        "final_verdict_zh": localize_text(analysis.get("final_verdict", "")),
        "author_affiliation_notes_zh": localize_text(analysis.get("author_affiliation_notes", "")),
        "extraction_quality_zh": localize_level(analysis.get("extraction_quality", ""), CONFIDENCE_LEVEL_MAP),
        "ocr_used_zh": localize_text(analysis.get("ocr_used", "")),
        "metadata_confidence_zh": localize_level(analysis.get("metadata_confidence", ""), CONFIDENCE_LEVEL_MAP),
        "interpretation_confidence_zh": localize_level(analysis.get("interpretation_confidence", ""), CONFIDENCE_LEVEL_MAP),
        "confidence_notes_zh": localize_text(analysis.get("confidence_notes", "")),
    }

    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Chinese deep-reading report based on the English final report.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-report", type=Path, default=None, help="Path to English final report markdown.")
    parser.add_argument("--template", type=Path, default=None, help="Optional Chinese template path.")
    parser.add_argument("--output-name", default="final_report_zh.md", help="Output markdown filename.")
    args = parser.parse_args()

    output_dir = args.output_dir
    source_report = args.source_report or (output_dir / "final_report.md")
    analysis_path = output_dir / "analysis.json"

    if not source_report.exists():
        raise SystemExit(f"English report not found: {source_report}")
    if not analysis_path.exists():
        raise SystemExit(f"analysis.json not found: {analysis_path}. Please run analyze_paper.py first.")

    analysis = read_json(analysis_path)
    values = build_values(analysis, source_report)

    if args.template:
        template_path = args.template
    else:
        template_path = Path(__file__).resolve().parent.parent / "templates" / "paper_investigation_report_zh.md"

    template = template_path.read_text(encoding="utf-8")
    report = render(template, values)

    out_path = output_dir / args.output_name
    write_text(out_path, report)
    print(f"Chinese report generated: {out_path}")


if __name__ == "__main__":
    main()
