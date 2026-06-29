"""TF-IDF based duplicate detection utilities."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, UTC
from typing import Any, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_CANDIDATE_LIMIT = 500

_NON_WORD_RE = re.compile(r"[^\w\s:/.-]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize_for_dedupe(text: str, links: Optional[Iterable[str]] = None) -> str:
    """Normalize post content before TF-IDF comparison."""
    cleaned = (text or "").lower().strip()
    cleaned = _NON_WORD_RE.sub(" ", cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()

    normalized_links: list[str] = []
    for link in links or []:
        link = (link or "").strip().lower()
        if not link:
            continue
        parsed = urlparse(link)
        host = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/")
        if host or path:
            normalized_links.append(f"{host}/{path}".strip("/"))

    if normalized_links:
        cleaned = f"{cleaned} {' '.join(sorted(set(normalized_links)))}".strip()
    return cleaned


def make_dedupe_key(text: str, links: Optional[List[str]] = None) -> str:
    """Create a readable representative key without cryptographic hashing.

    The key is intentionally not used as the primary duplicate decision. Near
    duplicate detection is handled by TF-IDF + cosine similarity.
    """
    normalized = normalize_for_dedupe(text, links)
    tokens = [tok for tok in normalized.split() if len(tok) > 1]
    if not tokens:
        return "tfidf:empty"
    key = "-".join(tokens[:16])
    return f"tfidf:{key[:160]}"


def similarity_score(text_a: str, text_b: str) -> float:
    """Return cosine similarity between two texts after TF-IDF vectorization."""
    doc_a = normalize_for_dedupe(text_a)
    doc_b = normalize_for_dedupe(text_b)
    if not doc_a or not doc_b:
        return 0.0

    vectors = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform([doc_a, doc_b])
    return float(cosine_similarity(vectors[0], vectors[1])[0][0])


def is_duplicate_text(
    new_text: str,
    existing_texts: Iterable[str],
    *,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Tuple[bool, float]:
    """Check whether new_text is near-duplicate of any existing text."""
    normalized_new = normalize_for_dedupe(new_text)
    normalized_existing = [normalize_for_dedupe(text) for text in existing_texts if text]
    normalized_existing = [text for text in normalized_existing if text]
    if not normalized_new or not normalized_existing:
        return False, 0.0

    corpus = normalized_existing + [normalized_new]
    vectors = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(corpus)
    scores = cosine_similarity(vectors[-1], vectors[:-1])[0]
    best = float(scores.max()) if len(scores) else 0.0
    return best >= threshold, best


def find_similar_post(
    posts_col: Any,
    *,
    text: str,
    links: Optional[List[str]] = None,
    created_at: Optional[datetime] = None,
    exclude_id: Optional[str] = None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> Tuple[Optional[dict], float]:
    """Find a near-duplicate post in MongoDB using TF-IDF + cosine similarity."""
    normalized_new = normalize_for_dedupe(text, links)
    if not normalized_new:
        return None, 0.0

    query: dict[str, Any] = {}
    if created_at:
        dt = created_at
        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        query["created_at"] = {"$gte": dt - timedelta(days=lookback_days)}

    projection = {"id": 1, "source_id": 1, "text": 1, "text_cleaned": 1, "links": 1, "dedupe_key": 1}
    candidates = list(posts_col.find(query, projection).sort("created_at", -1).limit(limit))
    if not candidates and query:
        candidates = list(posts_col.find({}, projection).sort("created_at", -1).limit(limit))

    docs: list[str] = []
    kept: list[dict] = []
    for candidate in candidates:
        if exclude_id and candidate.get("id") == exclude_id:
            continue
        candidate_text = candidate.get("text_cleaned") or candidate.get("text") or ""
        candidate_doc = normalize_for_dedupe(candidate_text, candidate.get("links") or [])
        if candidate_doc:
            kept.append(candidate)
            docs.append(candidate_doc)

    if not docs:
        return None, 0.0

    corpus = docs + [normalized_new]
    vectors = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(corpus)
    scores = cosine_similarity(vectors[-1], vectors[:-1])[0]
    if not len(scores):
        return None, 0.0

    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])
    if best_score >= threshold:
        return kept[best_idx], best_score
    return None, best_score
