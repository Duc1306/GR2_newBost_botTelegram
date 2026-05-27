"""Dedupe utilities."""
from __future__ import annotations
import hashlib
from typing import List
 
 
def make_dedupe_key(text: str, links: List[str]) -> str:
    base = (text or "").strip().lower() + "|" + "|".join(sorted([l.strip() for l in links or []]))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]