"""Shared settings: project paths and .env loading."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def parse_env(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines, skipping blanks and comments."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_env(path: Path = ENV_FILE) -> None:
    """Load .env into os.environ; variables already set win."""
    if not path.exists():
        return
    for key, value in parse_env(path.read_text(encoding="utf-8")).items():
        os.environ.setdefault(key, value)


def get_env(name: str, default: str | None = None) -> str:
    """Return an environment variable, its default, or fail with a clear message."""
    load_env()
    value = os.environ.get(name, "") or default
    if not value:
        raise RuntimeError(f"Missing {name}: copy .env.example to .env and fill it.")
    return value
