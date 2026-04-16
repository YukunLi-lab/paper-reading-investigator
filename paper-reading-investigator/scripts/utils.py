import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

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
        "authors": [],
        "affiliations": [],
        "author_affiliation_map": {},
        "corresponding_author": EMPTY_VALUE,
        "corresponding_email": EMPTY_VALUE,
        "venue": EMPTY_VALUE,
        "year": EMPTY_VALUE,
        "doi": EMPTY_VALUE,
        "code_link": EMPTY_VALUE,
        "dataset_names": [],
        "model_names": [],
        "benchmark_names": [],
        "metric_names": [],
        "hardware_details": [],
    }


def safe_excerpt(text: str, max_chars: int = 1200) -> str:
    return (text or "").strip()[:max_chars] or EMPTY_VALUE


def dedupe_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def join_or_default(values: Iterable[str], default: str = EMPTY_VALUE) -> str:
    items = dedupe_keep_order(values)
    return "; ".join(items) if items else default


def sentence_split(text: str) -> List[str]:
    if not text:
        return []
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
