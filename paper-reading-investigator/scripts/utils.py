import json
import re
from pathlib import Path
from typing import Any, Dict, List

EMPTY_VALUE = "Not clearly stated in the paper."


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_emails(text: str) -> List[str]:
    return sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))


def default_metadata() -> Dict[str, Any]:
    return {
        "paper_title": EMPTY_VALUE,
        "authors": EMPTY_VALUE,
        "affiliations": EMPTY_VALUE,
        "corresponding_author": EMPTY_VALUE,
        "corresponding_email": EMPTY_VALUE,
        "venue": EMPTY_VALUE,
        "year": EMPTY_VALUE,
        "doi": EMPTY_VALUE,
        "code_link": EMPTY_VALUE,
    }


def safe_excerpt(text: str, max_chars: int = 1200) -> str:
    return (text or "").strip()[:max_chars] or EMPTY_VALUE
