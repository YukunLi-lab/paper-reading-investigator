import argparse
import json
import re
from pathlib import Path
from typing import Dict

from utils import EMPTY_VALUE, read_json, write_text


def render(template: str, values: Dict[str, object]) -> str:
    try:
        from jinja2 import Template

        return Template(template).render(**values)
    except Exception:
        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            value = values.get(key, "")
            return str(value)

        return re.sub(r"{{\s*([^}]+)\s*}}", repl, template)


def _first_claim_line(analysis: Dict[str, object]) -> str:
    rows = analysis.get("claim_evidence_matrix", [])
    if not rows:
        return EMPTY_VALUE
    row = rows[0]
    evidence = row.get("evidence", [])
    evidence_text = "; ".join(evidence[:2]) if evidence else "No aligned evidence sentence."
    return f"Claim: {row.get('claim', EMPTY_VALUE)} | Support: {row.get('support_strength', 'weak')} | Evidence: {evidence_text}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a group-meeting friendly briefing deck in markdown.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--template", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir
    analysis = read_json(output_dir / "analysis.json")

    if args.template:
        template_path = args.template
    else:
        template_path = Path(__file__).resolve().parent.parent / "templates" / "group_meeting_brief.md"

    payload = {
        "paper_title": analysis.get("paper_title", EMPTY_VALUE),
        "headline_assessment": analysis.get("headline_assessment", EMPTY_VALUE),
        "research_question": analysis.get("research_question", EMPTY_VALUE),
        "technical_method": analysis.get("technical_method", EMPTY_VALUE),
        "experimental_setup": analysis.get("experimental_setup", EMPTY_VALUE),
        "main_results": analysis.get("main_results", EMPTY_VALUE),
        "claim_evidence_highlight": _first_claim_line(analysis),
        "reproducibility_risk": analysis.get("reproducibility_risk", EMPTY_VALUE),
        "reproducibility_rationale": analysis.get("reproducibility_rationale", EMPTY_VALUE),
        "strengths": analysis.get("strengths", EMPTY_VALUE),
        "weaknesses": analysis.get("weaknesses", EMPTY_VALUE),
        "next_steps": "1) Verify hidden defaults. 2) Reproduce key table rows. 3) Run one stress-test setting before wider adoption.",
    }

    template = template_path.read_text(encoding="utf-8")
    report = render(template, payload)
    brief_path = output_dir / "meeting_brief.md"
    write_text(brief_path, report)

    print(json.dumps({"status": "ok", "meeting_brief": str(brief_path)}, indent=2))


if __name__ == "__main__":
    main()
