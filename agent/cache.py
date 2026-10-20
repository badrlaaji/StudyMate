"""Disk cache for LLM answers: key = sha256(model + prompt), one JSON file per key."""

import hashlib
import json
from pathlib import Path

from config import ROOT

CACHE_DIR = ROOT / ".cache" / "llm"


def cache_key(model: str, prompt: str) -> str:
    """Return the sha256 hex digest of model + prompt."""
    return hashlib.sha256((model + prompt).encode("utf-8")).hexdigest()


def cache_get(key: str, folder: Path = CACHE_DIR) -> dict | None:
    """Return the cached JSON value, or None on a miss."""
    path = folder / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cache_put(key: str, value: dict, folder: Path = CACHE_DIR) -> None:
    """Store a JSON value under its key."""
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False)
    (folder / f"{key}.json").write_text(text, encoding="utf-8")
