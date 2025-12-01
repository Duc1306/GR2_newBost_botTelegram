"""Language detection wrapper (langdetect)."""
from __future__ import annotations
from typing import Optional

try:
    from langdetect import detect
except Exception:  # pragma: no cover
    detect = None  # type: ignore


def detect_language(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    if detect is None:
        return None
    try:
        code = detect(text)
        return code
    except Exception:
        return None
