import argparse
import json
from pathlib import Path
from typing import Dict, List

from utils import EMPTY_VALUE, ensure_dir, join_or_default, read_json, write_json, write_text


def _load_paper_bundle(output_dir: Path) -> Dict[str, object]:
    analysis_path = output_dir / "analysis.json"
    paper_content_path = output_dir / "paper_content.json"
    if not analysis_path.exists() or not paper_content_path.exists():
        raise FileNotFoundError(f"Missing analysis.json or paper_content.json in {output_dir}")
    analysis = read_json(analysis_path)
    paper_content = read_json(paper_content_path)
    metadata = paper_content.get("metadata", {})
    return {
        "output_dir": str(output_dir),
        "title": analysis.get("paper_title", metadata.get("paper_title", EMPTY_VALUE)),
        "headline": analysis.get("headline_assessment", EMPTY_VALUE),
        "risk": analysis.get("reproducibility_risk", EMPTY_VALUE),
        "datasets": metadata.get("dataset_names", []),
        "models": metadata.get("model_names", []),
        "metrics": metadata.get("metric_names", []),
        "hardware": metadata.get("hardware_details", []),
        "alignment_rows": analysis.get("claim_evidence_matrix", []),
    }


def _risk_rank(value: str) -> int:
    order = {"Low": 0, "Medium": 1, "High": 2}
    return order.get(value, 3)


def _alignment_score(rows: List[Dict[str, object]]) -> float:
    if not rows:
        return 0.0
    score = 0.0
    for row in rows:
        strength = row.get("support_strength")
        if strength == "strong":
            score += 1.0
        elif strength == "partial":
            score += 0.5
        else:
            score += 0.1
    return round(score / len(rows), 3)


def build_comparison(rows: List[Dict[str, object]]) -> Dict[str, object]:
    for row in rows:
        row["alignment_score"] = _alignment_score(row.get("alignment_rows", []))

    sorted_rows = sorted(rows, key=lambda item: (_risk_rank(item.get("risk", "")), -item["alignment_score"]))
    return {
        "papers": sorted_rows,
        "recommendation": sorted_rows[0]["title"] if sorted_rows else EMPTY_VALUE,
    }


def render_markdown(summary: Dict[str, object]) -> str:
    lines = [
        "# Multi-paper Comparison Report",
        "",
        "| Paper | Reproducibility Risk | Claim-Evidence Score | Datasets | Models | Metrics | Hardware |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for paper in summary["papers"]:
        lines.append(
            "| {title} | {risk} | {score} | {datasets} | {models} | {metrics} | {hardware} |".format(
                title=str(paper.get("title", EMPTY_VALUE)).replace("|", "\\|"),
                risk=paper.get("risk", EMPTY_VALUE),
                score=paper.get("alignment_score", 0),
                datasets=join_or_default(paper.get("datasets", [])),
                models=join_or_default(paper.get("models", [])),
                metrics=join_or_default(paper.get("metrics", [])),
                hardware=join_or_default(paper.get("hardware", [])),
            )
        )

    lines.extend(
        [
            "",
            f"## Recommended First Replication Target",
            summary.get("recommendation", EMPTY_VALUE),
            "",
            "## Notes",
            "- Lower reproducibility risk and higher claim-evidence score are ranked first.",
            "- Use this matrix as triage, then manually validate critical assumptions before resource allocation.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare multiple paper analysis outputs side-by-side.")
    parser.add_argument("paper_dirs", nargs="+", type=Path, help="One or more output directories that contain analysis.json.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to save comparison artifacts.")
    args = parser.parse_args()

    records = [_load_paper_bundle(path) for path in args.paper_dirs]
    summary = build_comparison(records)

    out_dir = ensure_dir(args.output_dir)
    write_json(out_dir / "comparison.json", summary)
    write_text(out_dir / "comparison_report.md", render_markdown(summary))

    print(json.dumps({"status": "ok", "papers_compared": len(records), "output_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
