import argparse
import json
import os
from pathlib import Path
from typing import List

from utils import ensure_dir, write_json, write_text

DEFAULT_MODEL = "gpt-5-mini"
MAX_CHARS_PER_CHUNK = 9000


def split_markdown_into_chunks(markdown: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    sections: List[str] = []
    current: List[str] = []
    current_len = 0

    for line in markdown.splitlines(keepends=True):
        is_heading = line.startswith("#")
        if is_heading and current and current_len >= max_chars:
            sections.append("".join(current))
            current = []
            current_len = 0

        if len(line) > max_chars and line.strip():
            if current:
                sections.append("".join(current))
                current = []
                current_len = 0
            for i in range(0, len(line), max_chars):
                sections.append(line[i : i + max_chars])
            continue

        if current_len + len(line) > max_chars and current:
            sections.append("".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        sections.append("".join(current))
    return sections


def translate_chunk(client, model: str, chunk: str, index: int, total: int) -> str:
    system_prompt = (
        "You are a professional technical translator. Translate the markdown content into Simplified Chinese.\n"
        "Hard rules:\n"
        "1) Preserve all markdown structure, headings, lists, numbering, and tables.\n"
        "2) Keep code blocks, inline code, paths, commands, and URLs unchanged unless inside normal prose.\n"
        "3) Translate all natural-language prose completely and faithfully.\n"
        "4) Do not omit content, do not summarize, and do not add commentary.\n"
        "5) Keep technical terms accurate; use Chinese where natural and keep necessary English terms in parentheses.\n"
    )
    user_prompt = f"Chunk {index}/{total}. Translate the following markdown fully:\n\n{chunk}"

    response = client.responses.create(
        model=model,
        temperature=0,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    translated = getattr(response, "output_text", "") or ""
    if not translated.strip():
        raise RuntimeError(f"Empty translation result for chunk {index}/{total}.")
    return translated


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click full Chinese translation for final_report.md using LLM.")
    parser.add_argument("output_dir", type=Path, help="Directory containing final_report.md")
    parser.add_argument("--source-report", type=Path, default=None, help="Custom source markdown path")
    parser.add_argument("--output-name", default="final_report_zh_full.md", help="Output markdown filename")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model for translation")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Please set it before running one-click LLM translation.")

    source_report = args.source_report or (args.output_dir / "final_report.md")
    if not source_report.exists():
        raise SystemExit(f"Source report not found: {source_report}")

    markdown = source_report.read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(markdown)
    if not chunks:
        raise SystemExit("Source report is empty.")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise SystemExit(f"openai package is required. Please install requirements first. Details: {exc}")

    client = OpenAI(api_key=api_key)
    translated_chunks = []
    for idx, chunk in enumerate(chunks, start=1):
        translated_chunks.append(translate_chunk(client, args.model, chunk, idx, len(chunks)))

    translated_report = "\n".join(part.strip() for part in translated_chunks if part.strip()) + "\n"
    out_path = args.output_dir / args.output_name
    write_text(out_path, translated_report)

    metadata = {
        "status": "ok",
        "source_report": str(source_report),
        "translated_report": str(out_path),
        "model": args.model,
        "chunk_count": len(chunks),
    }
    write_json(args.output_dir / "translation_metadata.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
