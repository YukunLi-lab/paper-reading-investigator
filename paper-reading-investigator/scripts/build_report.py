import argparse
import re
from pathlib import Path

from utils import read_json, write_text


def render(template: str, values: dict) -> str:
    try:
        from jinja2 import Template

        return Template(template).render(**values)
    except Exception:
        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            return str(values.get(key, ""))

        return re.sub(r"{{\s*([^}]+)\s*}}", repl, template)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build markdown investigation report from extracted analysis.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--template", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir
    analysis = read_json(output_dir / "analysis.json")

    if args.template:
        template_path = args.template
    else:
        template_path = Path(__file__).resolve().parent.parent / "templates" / "paper_investigation_report.md"

    template = template_path.read_text(encoding="utf-8")
    report = render(template, analysis)

    report_path = output_dir / "final_report.md"
    write_text(report_path, report)
    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    main()
