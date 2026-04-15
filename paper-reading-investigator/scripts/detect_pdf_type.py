import argparse
import json
from pathlib import Path

from utils import ensure_dir, write_json


def detect_with_pymupdf(pdf_path: Path) -> dict:
    import fitz  # pymupdf

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    total_chars = 0
    image_heavy_pages = 0
    page_stats = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        char_count = len(text.strip())
        img_count = len(page.get_images(full=True))
        total_chars += char_count
        if img_count > 0 and char_count < 60:
            image_heavy_pages += 1
        page_stats.append(
            {
                "page": i,
                "char_count": char_count,
                "image_count": img_count,
            }
        )

    image_ratio = image_heavy_pages / total_pages if total_pages else 0.0
    avg_chars = total_chars / total_pages if total_pages else 0.0

    if avg_chars >= 1200 and image_ratio < 0.3:
        pdf_type = "digital"
    elif avg_chars < 250 and image_ratio >= 0.6:
        pdf_type = "scanned"
    elif image_ratio >= 0.3:
        pdf_type = "mixed"
    else:
        pdf_type = "poor_text"

    return {
        "pdf_type": pdf_type,
        "total_pages": total_pages,
        "total_chars": total_chars,
        "avg_chars_per_page": round(avg_chars, 2),
        "image_heavy_ratio": round(image_ratio, 3),
        "page_stats": page_stats,
        "detector": "pymupdf",
    }


def detect_with_pypdf(pdf_path: Path) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    texts = [page.extract_text() or "" for page in reader.pages]
    total_pages = len(texts)
    total_chars = sum(len(t.strip()) for t in texts)
    avg_chars = total_chars / total_pages if total_pages else 0.0

    pdf_type = "digital" if avg_chars >= 800 else "poor_text"
    return {
        "pdf_type": pdf_type,
        "total_pages": total_pages,
        "total_chars": total_chars,
        "avg_chars_per_page": round(avg_chars, 2),
        "image_heavy_ratio": None,
        "page_stats": [{"page": i + 1, "char_count": len(t.strip())} for i, t in enumerate(texts)],
        "detector": "pypdf",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect whether a PDF is digital/scanned/mixed/poor_text.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--output", type=Path, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    if not args.pdf_path.exists() or args.pdf_path.suffix.lower() != ".pdf":
        raise SystemExit("Input must be an existing .pdf file")

    try:
        result = detect_with_pymupdf(args.pdf_path)
    except Exception:
        result = detect_with_pypdf(args.pdf_path)

    if args.output:
        ensure_dir(args.output.parent)
        write_json(args.output, result)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
