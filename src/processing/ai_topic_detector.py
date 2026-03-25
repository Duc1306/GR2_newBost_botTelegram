"""
AI-assisted hot topic detection using OpenAI.

Two main capabilities:
1. `detect_new_hot_topics(posts)` – GPT-4o-mini analyses a batch of recent posts and
   returns suggested NEW hot topics with keywords. Useful for discovering emerging trends
   without manual intervention.

2. `expand_keywords(topic_name, existing_keywords)` – GPT-4o-mini returns an expanded
   keyword list for an existing hot topic (more synonyms, variants, related terms).

3. `score_posts_by_embedding(posts, query_text)` – Uses text-embedding-3-small to rank
   posts by semantic similarity to a topic description. Much more accurate than keyword
   matching for ambiguous or multilingual content.

All functions return gracefully (empty / original values) when OPENAI_API_KEY is not set.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_client():
    """Lazy-import openai and return an AsyncOpenAI client."""
    try:
        from openai import OpenAI
        from src.config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            return None
        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.warning("openai package not installed. Run: pip install openai")
        return None


# ─── 1. Detect new hot topics from a batch of posts ─────────────────────────

DETECT_SYSTEM_PROMPT = """You are a news intelligence analyst.
Given a list of recent news excerpts (international + Vietnamese), identify the TOP
hot/trending topics that are NOT already covered by the provided list.
For each new topic, output:
- A short English slug (e.g. "iran-nuclear-deal")
- A display name with an emoji (e.g. "☢️ Thỏa thuận hạt nhân Iran")
- A one-sentence Vietnamese description
- 10-15 specific search keywords (mix: proper nouns, place names, key terms) in lowercase
  – include both English AND Vietnamese variants where applicable.
- A hex color code suitable for a chip badge.
- Priority (1=most urgent, 10=least urgent).

Return ONLY valid JSON array. No extra text. Format:
[
  {
    "slug": "...",
    "name": "...",
    "description": "...",
    "keywords": ["...", "..."],
    "color": "#xxxxxx",
    "priority": 1
  }
]"""


def detect_new_hot_topics(
    posts: list[dict],
    existing_slugs: list[str] | None = None,
    max_new_topics: int = 5,
) -> list[dict]:
    """
    Analyse a batch of recent posts (max 80 sampled) with GPT and return
    suggested new hot topic dicts ready to be upserted into `hot_topics`.

    Args:
        posts: list of post dicts (only `text` field is used)
        existing_slugs: slugs of already-tracked hot topics (to avoid duplicates)
        max_new_topics: cap on returned suggestions

    Returns:
        list of hot-topic dicts (may be empty if OpenAI unavailable or no new topics found)
    """
    client = _get_client()
    if not client:
        logger.info("OpenAI not configured – skipping AI hot topic detection")
        return []

    # Sample up to 80 posts, take first 300 chars each to stay within token budget
    sample = posts[:80]
    excerpts = "\n---\n".join(
        f"[{i+1}] {p.get('text', '')[:300]}" for i, p in enumerate(sample)
    )

    existing_note = ""
    if existing_slugs:
        existing_note = (
            f"\n\nAlready tracked topics (do NOT suggest these again): {', '.join(existing_slugs)}"
        )

    user_msg = (
        f"Here are {len(sample)} recent news excerpts:{existing_note}\n\n"
        f"{excerpts}\n\n"
        f"Suggest at most {max_new_topics} NEW hot topics."
    )

    try:
        from src.config import OPENAI_MODEL
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": DETECT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        # GPT sometimes wraps in {"topics": [...]} or returns bare array
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            # Try common wrapper keys
            for key in ("topics", "hot_topics", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            if isinstance(parsed, dict):
                parsed = list(parsed.values())[0] if parsed else []

        if not isinstance(parsed, list):
            logger.error("Unexpected GPT response format: %s", type(parsed))
            return []

        # Normalise & add defaults
        result = []
        for item in parsed[:max_new_topics]:
            if not isinstance(item, dict):
                continue
            if "slug" not in item or "name" not in item:
                continue
            result.append({
                "slug": item["slug"],
                "name": item["name"],
                "description": item.get("description", ""),
                "keywords": [str(k).lower() for k in item.get("keywords", [])],
                "color": item.get("color", "#6b7280"),
                "priority": int(item.get("priority", 99)),
                "active": False,  # Admin must activate manually – safety gate
                "ai_generated": True,
            })
        return result

    except Exception as exc:
        logger.exception("GPT detect_new_hot_topics failed: %s", exc)
        return []


# ─── 2. Expand keywords for an existing topic ────────────────────────────────

EXPAND_SYSTEM_PROMPT = """You are a news keyword analyst.
Given a hot topic name and its current keywords, return an EXPANDED keyword list.
Include:
- More synonyms and alternative spellings
- Related proper nouns (people, places, organisations)
- Both English and Vietnamese variants
Keep all keywords lowercase. Return ONLY valid JSON:
{"keywords": ["...", "..."]}
Limit to 30 keywords total."""


def expand_keywords(topic_name: str, existing_keywords: list[str]) -> list[str]:
    """
    Use GPT to expand the keyword list for a hot topic.

    Returns the expanded list, or the original list if OpenAI is unavailable.
    """
    client = _get_client()
    if not client:
        return existing_keywords

    user_msg = (
        f'Topic: "{topic_name}"\n'
        f"Current keywords: {json.dumps(existing_keywords, ensure_ascii=False)}\n\n"
        "Return an expanded keyword list."
    )

    try:
        from src.config import OPENAI_MODEL
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": EXPAND_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        expanded = parsed.get("keywords", existing_keywords)
        # Merge with existing, deduplicate
        merged = list(dict.fromkeys(existing_keywords + [k.lower() for k in expanded]))
        return merged[:30]
    except Exception as exc:
        logger.exception("GPT expand_keywords failed: %s", exc)
        return existing_keywords


# ─── 3. Semantic post scoring via embeddings ─────────────────────────────────

def score_posts_by_embedding(
    posts: list[dict],
    query_text: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Re-rank `posts` by cosine similarity between each post's text embedding
    and `query_text`'s embedding (e.g. topic name + description + keywords).

    Returns posts sorted by similarity (highest first), each augmented with
    an `_ai_score` float in [0, 1].

    Falls back to returning posts unchanged if embeddings are unavailable.
    """
    client = _get_client()
    if not client or not posts:
        return posts

    try:
        import numpy as np
        from src.config import OPENAI_EMBED_MODEL

        texts = [p.get("text", "")[:512] for p in posts]
        all_texts = [query_text] + texts  # query first

        response = client.embeddings.create(
            model=OPENAI_EMBED_MODEL,
            input=all_texts,
        )
        embeddings = [item.embedding for item in response.data]
        query_emb = np.array(embeddings[0])
        post_embs = np.array(embeddings[1:])

        # Cosine similarity
        query_norm = np.linalg.norm(query_emb)
        post_norms = np.linalg.norm(post_embs, axis=1, keepdims=True)
        similarities = (post_embs @ query_emb) / (post_norms.flatten() * query_norm + 1e-9)

        # Augment and sort
        scored = []
        for post, score in zip(posts, similarities.tolist()):
            scored.append({**post, "_ai_score": round(float(score), 4)})
        scored.sort(key=lambda p: p["_ai_score"], reverse=True)

        return scored[:top_k] if top_k else scored

    except ImportError:
        logger.warning("numpy not installed – embedding scoring unavailable")
        return posts
    except Exception as exc:
        logger.exception("Embedding scoring failed: %s", exc)
        return posts


# ─── 4. Quick health check ───────────────────────────────────────────────────

def check_openai_status() -> dict[str, Any]:
    """Returns a status dict indicating whether OpenAI is configured and reachable."""
    from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBED_MODEL
    if not OPENAI_API_KEY:
        return {"available": False, "reason": "OPENAI_API_KEY not set"}

    client = _get_client()
    if not client:
        return {"available": False, "reason": "openai package not installed"}

    try:
        # Cheapest possible call – list models
        client.models.retrieve(OPENAI_MODEL)
        return {
            "available": True,
            "model": OPENAI_MODEL,
            "embed_model": OPENAI_EMBED_MODEL,
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
