import argparse
import json
import shutil
import subprocess
from pathlib import Path

from utils import ensure_dir, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OCR fallback for scanned PDFs.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--language", default="eng")
    parser.add_argument("--force", action="store_true", help="Run OCR even if output already exists")
    args = parser.parse_args()

    if not args.pdf_path.exists() or args.pdf_path.suffix.lower() != ".pdf":
        raise SystemExit("Input must be an existing .pdf file")

    ocr_dir = ensure_dir(args.output_dir / "ocr")
    ocr_pdf = ocr_dir / "ocr_output.pdf"
    meta_path = ocr_dir / "ocr_metadata.json"

    if ocr_pdf.exists() and not args.force:
        result = {
            "ocr_used": True,
            "status": "skipped_existing",
            "language": args.language,
            "ocr_pdf": str(ocr_pdf),
            "note": "OCR output already exists.",
        }
        write_json(meta_path, result)
        print(json.dumps(result, indent=2))
        return

    ocrmypdf = shutil.which("ocrmypdf")
    if ocrmypdf:
        cmd = [ocrmypdf, "--force-ocr", "-l", args.language, str(args.pdf_path), str(ocr_pdf)]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        result = {
            "ocr_used": True,
            "status": "ok" if completed.returncode == 0 else "failed",
            "language": args.language,
            "ocr_pdf": str(ocr_pdf),
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "returncode": completed.returncode,
        }
        if completed.returncode != 0:
            fallback_pdf = ocr_dir / "fallback_copy.pdf"
            shutil.copy2(args.pdf_path, fallback_pdf)
            result["ocr_pdf"] = str(fallback_pdf)
            result["note"] = "OCR failed; using original PDF copy as fallback input."
    else:
        fallback_pdf = ocr_dir / "fallback_copy.pdf"
        shutil.copy2(args.pdf_path, fallback_pdf)
        result = {
            "ocr_used": False,
            "status": "tool_missing",
            "language": args.language,
            "ocr_pdf": str(fallback_pdf),
            "note": "ocrmypdf is not installed; created a fallback copy for downstream extraction.",
        }

    write_json(meta_path, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
