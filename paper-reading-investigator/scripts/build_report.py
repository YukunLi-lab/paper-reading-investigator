import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

from utils import EMPTY_VALUE, read_json, write_text


def render(template: str, values: Dict[str, object]) -> str:
    try:
        from jinja2 import Template

        return Template(template).render(**values)
    except Exception:
        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            value = values.get(key, "")
            if isinstance(value, list):
                return "; ".join([str(item) for item in value]) if value else ""
            return str(value)

        return re.sub(r"{{\s*([^}]+)\s*}}", repl, template)


def build_alignment_table(rows: List[Dict[str, object]]) -> str:
    if not rows:
        return "Not clearly stated in the paper."
    lines = [
        "| # | Claim | Support | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for idx, row in enumerate(rows, start=1):
        claim = str(row.get("claim", "")).replace("|", "\\|")
        support = str(row.get("support_strength", "weak"))
        evidence = row.get("evidence", [])
        evidence_text = "; ".join([str(item) for item in evidence[:2]]) if evidence else "No aligned evidence sentence."
        evidence_text = evidence_text.replace("|", "\\|")
        lines.append(f"| {idx} | {claim} | {support} | {evidence_text} |")
    return "\n".join(lines)


def append_advanced_sections(report: str, analysis: Dict[str, object]) -> str:
    appendix = [
        "",
        "## 11. Structured Extraction Highlights",
        f"- **Datasets:** {analysis.get('datasets_summary', EMPTY_VALUE)}",
        f"- **Models:** {analysis.get('models_summary', EMPTY_VALUE)}",
        f"- **Benchmarks:** {analysis.get('benchmarks_summary', EMPTY_VALUE)}",
        f"- **Metrics:** {analysis.get('metrics_summary', EMPTY_VALUE)}",
        f"- **Hardware:** {analysis.get('hardware_summary', EMPTY_VALUE)}",
        f"- **Estimated Table Count:** {analysis.get('table_count', 0)}",
        f"- **Estimated Equation Count:** {analysis.get('equation_count', 0)}",
        f"- **Figure/Table Citation Mentions:** {analysis.get('figure_table_citation_count', 0)}",
        "",
        "## 12. Claim-Evidence Alignment Matrix",
        build_alignment_table(analysis.get("claim_evidence_matrix", [])),
        "",
        f"_Alignment mode: {analysis.get('claim_evidence_alignment_mode', 'heuristic_only')}_",
    ]
    return report.rstrip() + "\n" + "\n".join(appendix) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build markdown investigation report from extracted analysis.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--with-appendix", action="store_true", help="Append structured extraction and claim-evidence matrix sections.")
    args = parser.parse_args()

    output_dir = args.output_dir
    analysis = read_json(output_dir / "analysis.json")

    if args.template:
        template_path = args.template
    else:
        template_path = Path(__file__).resolve().parent.parent / "templates" / "paper_investigation_report.md"

    template = template_path.read_text(encoding="utf-8")
    report = render(template, analysis)

    if args.with_appendix:
        report = append_advanced_sections(report, analysis)

    report_path = output_dir / "final_report.md"
    write_text(report_path, report)
    print(json.dumps({"status": "ok", "report": str(report_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
