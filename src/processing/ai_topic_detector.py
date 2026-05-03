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

# Module-level singleton — created once, reused across all calls.
_openai_client = None


def _get_client():
    """Lazy-import openai and return a cached OpenAI client with a sensible timeout."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    try:
        from openai import OpenAI
        from src.config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set — AI features disabled")
            return None
        _openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=45.0)
        return _openai_client
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


# ─── 5. Arbitrate between conflicting topic predictions ──────────────────────

_ARBITRATE_SYSTEM = """You are a precise Vietnamese/English news topic classifier.
Given a short text and two candidate topic labels, decide which topic best fits the text.
You MUST return exactly one topic from the provided valid topics list.
Return ONLY valid JSON with a single key: {"topic": "TopicName"}"""


def arbitrate_topic(
    text: str,
    svm_topic: str,
    keyword_topic: str,
    valid_topics: list[str] | None = None,
) -> str | None:
    """
    Use OpenAI to decide between conflicting SVM and keyword-based topic predictions.

    Args:
        text: The post text (will be truncated to 500 chars).
        svm_topic: Topic predicted by the SVM/ML model.
        keyword_topic: Topic predicted by the keyword/rule-based classifier.
        valid_topics: Allowed topic names. Defaults to TOPIC_LABELS.

    Returns:
        The chosen topic string, or None if OpenAI is unavailable or fails.
    """
    client = _get_client()
    if not client:
        return None

    from src.processing.ml_topic_classifier import TOPIC_LABELS
    topics_list = valid_topics or TOPIC_LABELS

    user_msg = (
        f"Text (first 500 chars): {text[:500]}\n\n"
        f"Candidate A (SVM model): {svm_topic}\n"
        f"Candidate B (keyword rule): {keyword_topic}\n\n"
        f"Valid topics: {', '.join(topics_list)}\n\n"
        "Which topic is most accurate for this text?"
    )

    try:
        from src.config import OPENAI_MODEL
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _ARBITRATE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        topic = str(parsed.get("topic", "")).strip()

        # Exact match first
        if topic in topics_list:
            return topic
        # Case-insensitive fallback
        topic_lower = topic.lower()
        for t in topics_list:
            if t.lower() == topic_lower:
                return t

        logger.warning("OpenAI arbitrate_topic returned unknown topic: %s", topic)
        return None
    except Exception as exc:
        logger.exception("arbitrate_topic failed: %s", exc)
        return None


# ─── 6. Summarise a cluster of posts about the same topic ────────────────────

_SUMMARISE_SYSTEM = """Bạn là Tổng biên tập của một tờ báo lớn tại Việt Nam. Bạn khắt khe, chính xác và không bao giờ bịa đặt.

NHIỆM VỤ: Nhận danh sách bài báo có đánh số ID, chọn lọc và tổng hợp thành BÀI BÁO HOÀN CHỈNH về đúng 1 sự kiện cụ thể đang được nhắc đến nhiều nhất trong danh sách.

QUY TẮC BẮT BUỘC:
1. GOM NHÓM NGHIÊM NGẶT: Chỉ sử dụng các bài thực sự nói về CÙNG MỘT SỰ KIỆN CỤ THỂ. Bài nào lạc đề → bỏ qua hoàn toàn, KHÔNG được nhắc đến.
2. TIÊU ĐỀ SẮC BÉN: "title" PHẢI là câu tường thuật sự kiện cụ thể, KHÔNG dùng từ ngữ chung chung.
   ❌ Sai: "Các tin tức kinh tế nổi bật", "Thời sự hôm nay", "Tin tức công nghệ"
   ✅ Đúng: "Giá vàng SJC vượt 120 triệu đồng/lượng", "Nga phóng tên lửa đạn đạo vào Kyiv"
3. BẰNG CHỨNG: Trong "used_ids", CHỈ liệt kê ID (chuỗi số) của các bài THỰC SỰ đóng góp nội dung vào bài viết này.
4. KHÔNG bịa thêm sự kiện, số liệu, tên người ngoài dữ liệu được cung cấp.
5. Câu văn rõ ràng, khách quan. Độ dài: lead ~2 câu, body 3-4 đoạn (mỗi đoạn 2-4 câu), conclusion 1-2 câu.

ĐỊNH DẠNG ĐẦU RA (Chỉ trả về JSON, không thêm văn bản nào khác):
{
  "title": "Tiêu đề sự kiện cụ thể, sắc bén",
  "lead": "Đoạn mở đầu 2-3 câu nêu bật sự kiện quan trọng nhất",
  "body": [
    "Đoạn 1: bối cảnh và diễn biến chính",
    "Đoạn 2: chi tiết, số liệu, trích dẫn quan trọng",
    "Đoạn 3: các phản ứng hoặc diễn biến liên quan"
  ],
  "conclusion": "Nhận định xu hướng hoặc tóm lược ý nghĩa sự kiện",
  "key_points": ["Điểm nổi bật 1", "Điểm nổi bật 2", "Điểm nổi bật 3"],
  "sentiment": "neutral|positive|negative|mixed",
  "used_ids": ["1", "3", "5"]
}"""


def summarize_cluster(
    posts: list[dict],
    topic_name: str = "",
    max_posts: int = 15,
) -> dict:
    """
    Summarise a cluster of posts on the same topic using OpenAI.

    Args:
        posts: list of post dicts with at least a ``text`` field.
        topic_name: display name of the topic (used as context for GPT).
        max_posts: maximum number of posts to include in the prompt.

    Returns:
        dict with keys ``summary``, ``key_points``, ``sentiment``.
        Falls back to a plain concatenation summary when OpenAI is unavailable.
    """
    if not posts:
        return {"summary": "", "key_points": [], "sentiment": "neutral"}

    client = _get_client()

    # Use up to max_posts; give each post a stable 1-based ID so GPT can
    # reference back which ones it actually used (used_ids in response).
    sample = posts[:max_posts]

    def _post_excerpt(p: dict) -> str:
        """Return the richest short text available for a post."""
        fa = p.get("full_article") or {}
        title = fa.get("title", "").strip()
        text = (p.get("text") or "").strip()
        if title and text:
            return f"{title} — {text[:300]}"
        return (title or text)[:400]

    excerpts = "\n---\n".join(
        f"[ID:{i+1}] {_post_excerpt(p)}" for i, p in enumerate(sample)
    )

    if not client:
        fa = posts[0].get("full_article") or {}
        fallback_text = fa.get("title") or posts[0].get("text", "")[:200]
        return {
            "title": topic_name,
            "lead": fallback_text,
            "body": [],
            "conclusion": "",
            "key_points": [],
            "sentiment": "neutral",
            "ai": False,
            "_used_posts": sample,
        }

    user_msg = (
        f'Chủ đề gợi ý: "{topic_name}"\n\n'
        f"Dưới đây là {len(sample)} bài báo gần đây (mỗi bài có ID riêng):\n\n"
        f"{excerpts}\n\n"
        "Hãy chọn lọc các bài cùng sự kiện cụ thể nhất, tổng hợp và trả về JSON như yêu cầu. "
        "Đặc biệt chú ý điền đầy đủ mảng used_ids với ID của các bài bạn thực sự sử dụng."
    )

    try:
        from src.config import OPENAI_MODEL
        logger.info("summarize_cluster: calling GPT model=%s posts=%d", OPENAI_MODEL, len(sample))
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SUMMARISE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=1600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        logger.info("summarize_cluster: GPT raw response length=%d", len(raw))
        parsed = json.loads(raw)

        # Map used_ids back to post objects (1-based IDs)
        used_ids_raw = parsed.get("used_ids", [])
        used_id_set = {str(uid).strip() for uid in used_ids_raw if uid}
        if used_id_set:
            used_posts = [sample[i] for i in range(len(sample)) if str(i + 1) in used_id_set]
            if not used_posts:            # safety: GPT returned IDs we can't map
                used_posts = sample
        else:
            used_posts = sample           # GPT omitted used_ids — use all

        result = {
            "title": parsed.get("title", ""),
            "lead": parsed.get("lead", ""),
            "body": parsed.get("body", []),
            "conclusion": parsed.get("conclusion", ""),
            "key_points": parsed.get("key_points", []),
            "sentiment": parsed.get("sentiment", "neutral"),
            "ai": True,
            "_used_posts": used_posts,    # consumed by caller, NOT persisted to cache
        }
        logger.info(
            "summarize_cluster: success title=%r lead_len=%d body_paras=%d used=%d/%d",
            result["title"][:40], len(result["lead"]), len(result["body"]),
            len(used_posts), len(sample),
        )
        return result
    except Exception as exc:
        logger.exception("summarize_cluster FAILED (will use fallback): %s", exc)
        fa = posts[0].get("full_article") or {}
        fallback_text = fa.get("title") or posts[0].get("text", "")[:200]
        return {
            "title": topic_name,
            "lead": fallback_text,
            "body": [],
            "conclusion": "",
            "key_points": [],
            "sentiment": "neutral",
            "ai": False,
            "_used_posts": sample,
        }


# ─── 6b. Two-step Map-Reduce cluster+summarize ───────────────────────────────

_MAP_EVENTS_SYSTEM = """Bạn là Tổng biên tập tin tức AI khắt khe.
Tôi cung cấp danh sách mẩu tin ngắn, mỗi tin có số thứ tự [Bài X].

NHIỆM VỤ:
1. Đọc tất cả và TÌM RA các SỰ KIỆN KHÁC NHAU.
2. Tách thành Hot News riêng biệt. TUYỆT ĐỐI KHÔNG GỘP tin không liên quan vào chung 1 tiêu đề.
3. Tin rác, lẻ tẻ, không quan trọng → BỎ QUA.
4. Tiêu đề phải CỤ THỂ:
   ❌ "Tin tức kinh tế hôm nay"
   ✅ "Giá vải chín sớm chạm mức 200.000 đồng/kg"

Ví dụ đúng: 15 bài hỗn hợp → tách ra:
  Event 1 "Giá vải chín sớm tăng 200.000đ" → related_ids: [0]
  Event 2 "Vingroup lãi 5.610 tỷ Quý I" → related_ids: [4]
  Event 3 "Băng cướp rửa tiền bằng lò nướng" → related_ids: [5, 12]
  (các bài không liên quan → bỏ qua)

Chỉ trả về JSON hợp lệ:
{
  "events": [
    {
      "title": "Tiêu đề sự kiện cụ thể",
      "key_points": ["Ý nổi bật 1", "Ý nổi bật 2"],
      "related_ids": [0, 3]
    }
  ]
}"""


def _word_overlap(a: str, b: str) -> float:
    """Simple word-overlap ratio between two strings (case-insensitive)."""
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / min(len(a_words), len(b_words))


def cluster_and_summarize(
    posts: list[dict],
    topic_name: str = "",
    max_posts: int = 15,
) -> dict:
    """
    Two-step Map-Reduce pipeline that eliminates "lazy evaluation" / off-topic posts.

    Step 1 – MAP: Send all posts as [Bài X] text → GPT identifies separate events
    and returns related_ids per event.  Pick the event matching topic_name.

    Step 2 – REDUCE: Pass only that event's posts to summarize_cluster → full article.

    Returns the same dict shape as summarize_cluster, plus '_filtered_posts' (the
    posts that belong to the chosen event) for the caller to use for link_posts /
    post_count.
    """
    if not posts:
        return {
            "title": topic_name, "lead": "", "body": [], "conclusion": "",
            "key_points": [], "sentiment": "neutral", "ai": False,
            "_filtered_posts": [],
        }

    client = _get_client()
    sample = posts[:max_posts]

    def _post_text(p: dict) -> str:
        fa = p.get("full_article") or {}
        title = fa.get("title", "").strip()
        text = (p.get("text") or "").strip()
        if title and text:
            return f"{title} — {text[:250]}"
        return (title or text)[:300]

    formatted = "\n".join(
        f"[Bài {i}]: {_post_text(p)}" for i, p in enumerate(sample)
    )

    best_posts = sample  # fallback — use all if MAP step fails

    if client:
        try:
            from src.config import OPENAI_MODEL
            user_msg = (
                f'Chủ đề gợi ý: "{topic_name}"\n\n'
                f"Danh sách {len(sample)} mẩu tin:\n\n{formatted}\n\n"
                "Hãy tách thành các sự kiện riêng biệt và trả về JSON."
            )
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _MAP_EVENTS_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=900,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            events = parsed.get("events", []) if isinstance(parsed, dict) else []

            if events:
                # Pick event whose title best matches topic_name; tie-break by most related_ids
                best_event = max(
                    events,
                    key=lambda e: (
                        _word_overlap(e.get("title", ""), topic_name),
                        len(e.get("related_ids", [])),
                    ),
                )
                raw_ids = best_event.get("related_ids", [])
                valid_ids = [int(i) for i in raw_ids
                             if str(i).lstrip("-").isdigit() and 0 <= int(i) < len(sample)]
                if valid_ids:
                    best_posts = [sample[i] for i in valid_ids]
                    logger.info(
                        "cluster_and_summarize MAP: %d events → best=%r (%d/%d posts)",
                        len(events), best_event.get("title", "")[:50],
                        len(best_posts), len(sample),
                    )
        except Exception as exc:
            logger.exception("cluster_and_summarize MAP step failed: %s", exc)
            best_posts = sample  # fallback

    # Step 2: full article generation on focused post set
    result = summarize_cluster(best_posts, topic_name=topic_name, max_posts=len(best_posts))
    result.pop("_used_posts", None)          # already consumed inside summarize_cluster
    result["_filtered_posts"] = best_posts   # expose for caller to build link_posts
    return result


# ─── 7. Filter posts to only those genuinely relevant to a topic ─────────────

_RELEVANCE_THRESHOLD = 0.42  # cosine similarity cut-off (raised from 0.32 to avoid ambiguous-word false positives)


def filter_relevant_posts(
    posts: list[dict],
    topic_name: str,
    topic_description: str = "",
    topic_keywords: list[str] | None = None,
    top_k: int = 15,
    threshold: float | None = None,
) -> list[dict]:
    """
    Use embedding-based semantic scoring to keep only posts that are
    genuinely about *topic_name*.

    Strategy:
    1. Build a rich query string from name + description + top keywords.
    2. Call ``score_posts_by_embedding()`` to rank all candidates.
    3. Keep posts where cosine-similarity >= threshold AND at most *top_k* posts.

    Falls back to returning the original posts unchanged when OpenAI is
    unavailable or numpy is missing.
    """
    if not posts:
        return posts

    cutoff = threshold if threshold is not None else _RELEVANCE_THRESHOLD

    # Build a descriptive query to anchor the embedding
    kw_str = ", ".join((topic_keywords or [])[:12])
    query = f"{topic_name}. {topic_description}. Keywords: {kw_str}".strip(". ")

    scored = score_posts_by_embedding(posts, query_text=query)

    # If scoring didn't add _ai_score it returned posts unchanged — keep as-is
    if not scored or "_ai_score" not in scored[0]:
        return posts[:top_k]

    # Apply threshold filter then take top_k
    relevant = [p for p in scored if p.get("_ai_score", 0) >= cutoff]
    if not relevant:
        # If nothing passes the threshold keep the top-3 as a safety net
        relevant = scored[:3]

    return relevant[:top_k]


# ─── 8. Discover specific hot events from a batch of recent link-posts ────────

_DISCOVER_SYSTEM = """Bạn là chuyên gia phân tích tin tức thời sự.
Từ danh sách bài báo mới nhất (có link, được thu thập trong vài giờ qua), hãy xác định các SỰ KIỆN CỤ THỂ đang nóng nhất, không phải danh mục chung chung.

Ví dụ TỐT: "Real Madrid sa thải Ancelotti", "FED tăng lãi suất 0.5%", "Đại dịch cúm A lan rộng ở miền Bắc"
Ví dụ XẤU: "Thể thao", "Kinh tế", "Sức khỏe" (quá chung chung)

Yêu cầu:
- Tối đa 6 sự kiện, ưu tiên tin có nhiều bài nhất
- Mỗi sự kiện phải có ít nhất 2 bài báo hỗ trợ
- Tên sự kiện ngắn gọn (5-10 từ), bằng tiếng Việt hoặc tên riêng giữ nguyên
- Các chỉ số bài tham chiếu là số thứ tự 1-based trong danh sách đầu vào

Trả về ĐÚNG JSON (không thêm văn bản nào khác):
[
  {
    "name": "Tên sự kiện cụ thể",
    "description": "1-2 câu mô tả sự kiện",
    "post_indices": [1, 3, 5],
    "color": "#hex"
  }
]"""


def discover_hot_events(
    posts: list[dict],
    max_events: int = 6,
) -> list[dict]:
    """
    Keyword-frequency clustering → GPT naming.

    Algorithm:
    1. Extract all significant words/bigrams from recent posts.
    2. Rank by term frequency → top trending keywords.
    3. Cluster posts that share top keywords (posts mentioning the same
       high-freq terms belong together).
    4. Feed cluster representatives to GPT to get a *specific* event name
       (e.g. "Giá vàng SJC vượt 120 triệu" instead of just "Kinh tế").

    Falls back to empty list when OpenAI is unavailable.
    """
    import re
    from collections import Counter, defaultdict

    if not posts:
        return []

    # ── Stopwords (Vietnamese + English common words) ─────────────────────────
    STOPWORDS = {
        "và", "của", "có", "được", "trong", "cho", "từ", "này", "đã", "là",
        "với", "các", "một", "những", "về", "để", "đến", "trên", "theo",
        "như", "khi", "tại", "sau", "vào", "hay", "cũng", "đây", "còn",
        "rằng", "bởi", "nên", "hơn", "đó", "mà", "thì", "không", "sẽ",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "was", "are", "were",
        "be", "has", "have", "had", "that", "this", "it", "he", "she",
        "they", "we", "you", "i", "his", "her", "its", "our", "their",
        "said", "say", "says", "also", "will", "can", "not", "as", "up",
    }

    def _tokenize(text: str) -> list[str]:
        if not text:
            return []
        text = text.lower()
        tokens = re.findall(
            r"[a-zA-Z0-9"
            r"àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩị"
            r"òóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+",
            text,
        )
        return [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]

    # ── Step 1: count unigrams + bigrams across all posts ─────────────────────
    unigram_counter: Counter = Counter()
    bigram_counter: Counter = Counter()
    post_tokens: list[list[str]] = []

    for p in posts:
        toks = _tokenize(p.get("text", ""))
        post_tokens.append(toks)
        unigram_counter.update(toks)
        bigrams = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)]
        bigram_counter.update(bigrams)

    # Top keywords: prefer bigrams (more specific) then fill with unigrams
    n = len(posts)
    # Remove bigrams where either word appears in >70% posts (too generic)
    freq_bigrams = [
        (bg, cnt) for bg, cnt in bigram_counter.most_common(60)
        if cnt >= 3 and cnt / n < 0.7
    ]
    freq_unigrams = [
        (w, cnt) for w, cnt in unigram_counter.most_common(60)
        if cnt >= 3 and cnt / n < 0.7
        and not any(w in bg for bg, _ in freq_bigrams[:20])
    ]

    # Merge into a single ranked keyword list (bigrams weighted x1.5)
    scored: list[tuple[str, float]] = (
        [(bg, cnt * 1.5) for bg, cnt in freq_bigrams[:20]]
        + [(w, float(cnt)) for w, cnt in freq_unigrams[:20]]
    )
    scored.sort(key=lambda x: -x[1])
    top_keywords = [kw for kw, _ in scored[:25]]

    if not top_keywords:
        return []

    # ── Step 1b: GPT filter – keep only newsworthy keywords ──────────────────
    # Remove generic/meaningless terms that passed the stopword filter but
    # still have no news value (e.g. "tháng", "năm", "ngày", "1000", "mới").
    client = _get_client()
    if client:
        try:
            from src.config import OPENAI_MODEL
            filter_prompt = (
                "Bạn là biên tập viên tin tức. Từ danh sách từ khóa dưới đây, "
                "hãy GIỮ LẠI chỉ những từ khóa có GIÁ TRỊ TIN TỨC (tên người, "
                "địa điểm, tổ chức, sự kiện cụ thể, chỉ số giá cả, tên sản phẩm, v.v.).\n"
                "LOẠI BỎ những từ quá chung chung hoặc không mang thông tin: "
                "số tròn, đơn vị thời gian, tính từ mơ hồ, từ mô tả hành động chung.\n"
                "Trả về JSON: {\"keywords\": [\"...\"]}\n\n"
                f"Danh sách: {json.dumps(top_keywords, ensure_ascii=False)}"
            )
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Chỉ trả về JSON hợp lệ."},
                    {"role": "user", "content": filter_prompt},
                ],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            parsed_kw = json.loads(resp.choices[0].message.content.strip())
            filtered_kws = parsed_kw.get("keywords", [])
            if isinstance(filtered_kws, list) and len(filtered_kws) >= 3:
                top_keywords = [kw for kw in top_keywords if kw in filtered_kws]
                logger.info("GPT keyword filter: %d → %d keywords", len(scored), len(top_keywords))
        except Exception as exc:
            logger.warning("GPT keyword filter skipped: %s", exc)

    if not top_keywords:
        return []

    # ── Step 2: assign each post a set of matched top-keywords ───────────────
    post_keyword_sets: list[set[str]] = []
    for toks in post_tokens:
        tok_set = set(toks)
        # check unigrams
        matched = {kw for kw in top_keywords if " " not in kw and kw in tok_set}
        # check bigrams
        text_joined = " ".join(toks)
        matched |= {kw for kw in top_keywords if " " in kw and kw in text_joined}
        post_keyword_sets.append(matched)

    # ── Step 3: greedy clustering by shared top-keywords ─────────────────────
    # Each cluster is seeded by the most frequent keyword; posts sharing ≥1
    # keyword with the cluster's seed join it.
    clusters_raw: list[dict] = []
    used_posts: set[int] = set()

    for seed_kw in top_keywords[:15]:
        members = [
            i for i, kws in enumerate(post_keyword_sets)
            if seed_kw in kws and i not in used_posts
        ]
        if len(members) < 3:
            continue
        for i in members:
            used_posts.add(i)
        cluster_posts = [posts[i] for i in members]
        # Top 5 shared keywords for this cluster
        combined_kws: Counter = Counter()
        for i in members:
            combined_kws.update(post_keyword_sets[i])
        top_cluster_kws = [kw for kw, _ in combined_kws.most_common(5)]
        clusters_raw.append({
            "posts": cluster_posts,
            "keywords": top_cluster_kws,
        })
        if len(clusters_raw) >= max_events + 2:
            break

    if not clusters_raw:
        return []

    # ── Step 4: GPT names each cluster as a specific real-world event ─────────
    client = _get_client()
    if not client:
        # Fallback: use top keyword as name
        results = []
        for cl in clusters_raw[:max_events]:
            name = " & ".join(cl["keywords"][:3]).title()
            results.append({
                "name": name,
                "description": "",
                "color": "#6b7280",
                "posts": cl["posts"],
            })
        return results

    cluster_summaries = []
    for idx, cl in enumerate(clusters_raw[:max_events]):
        sample_texts = "\n".join(
            f"- {p.get('text', '')[:200]}" for p in cl["posts"][:5]
        )
        cluster_summaries.append(
            f"Cluster {idx + 1} [keywords: {', '.join(cl['keywords'])}]:\n{sample_texts}"
        )

    naming_prompt = (
        "Dưới đây là các cụm bài báo được nhóm theo từ khóa trending gần đây.\n"
        "Hãy đặt TÊN SỰ KIỆN CỤ THỂ đang xảy ra cho từng cụm. "
        "KHÔNG dùng tên danh mục như 'Kinh tế', 'Thể thao', 'Chính trị', 'Tin tức'.\n"
        "Tên nên phản ánh ĐÚNG sự kiện: giá cả cụ thể, tên người / địa điểm / quốc gia.\n"
        "Ví dụ tốt:\n"
        "  - 'Giá vàng SJC vượt 120 triệu đồng/lượng'\n"
        "  - 'Giá xăng tăng lần 3 trong tháng 4'\n"
        "  - 'Nga phóng tên lửa đạn đạo vào Kyiv'\n"
        "  - 'Iran cảnh báo tấn công căn cứ Mỹ ở Trung Đông'\n"
        "  - 'Trump áp thuế 145%% lên hàng nhập khẩu Trung Quốc'\n"
        "  - 'NVIDIA Blackwell Ultra ra mắt, AI server bùng nổ'\n"
        "  - 'Cổ phiếu VN-Index bứt phá vượt 1.300 điểm'\n\n"
        + "\n\n".join(cluster_summaries)
        + "\n\nTrả về JSON array (đúng số cluster theo thứ tự):\n"
        '[{"cluster": 1, "name": "Tên sự kiện cụ thể", "description": "1 câu mô tả", "color": "#hexcolor"}]'
    )

    try:
        from src.config import OPENAI_MODEL
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là biên tập viên tin tức. Nhiệm vụ: đặt tên sự kiện cụ thể "
                        "cho từng cụm bài, không dùng tên danh mục chung. "
                        "Chỉ trả về JSON array theo format được yêu cầu."
                    ),
                },
                {"role": "user", "content": naming_prompt},
            ],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        items = parsed if isinstance(parsed, list) else next(
            (v for v in parsed.values() if isinstance(v, list)), []
        )

        results = []
        for item in items:
            idx = int(item.get("cluster", 0)) - 1
            if 0 <= idx < len(clusters_raw):
                results.append({
                    "name": item.get("name", clusters_raw[idx]["keywords"][0]),
                    "description": item.get("description", ""),
                    "color": item.get("color", "#be123c"),
                    "posts": clusters_raw[idx]["posts"],
                })
        return results

    except Exception as exc:
        logger.exception("discover_hot_events GPT naming failed: %s", exc)
        # Return clusters with keyword-based names as fallback
        return [
            {
                "name": " & ".join(cl["keywords"][:3]).title(),
                "description": "",
                "color": "#6b7280",
                "posts": cl["posts"],
            }
            for cl in clusters_raw[:max_events]
        ]


# ─── 6. GPT name a list of ML-velocity clusters ──────────────────────────────

def gpt_name_ml_clusters(clusters: list[dict]) -> list[dict]:
    """
    Given ML-velocity clusters (each has 'topic_name' and 'posts'),
    use GPT to replace the broad topic name (e.g. "Kinh tế") with a
    specific real-world event title (e.g. "Giá vàng SJC vượt 120 triệu").

    Returns the same list with 'name', 'description', 'color' added/updated.
    Falls back to the original topic_name when OpenAI is unavailable.
    """
    if not clusters:
        return clusters

    client = _get_client()
    if not client:
        for cl in clusters:
            cl.setdefault("name", cl.get("topic_name", ""))
            cl.setdefault("description", "")
            cl.setdefault("color", "#6b7280")
        return clusters

    # Build summaries for GPT
    cluster_summaries = []
    for idx, cl in enumerate(clusters):
        sample_posts = cl.get("posts", [])[:5]
        sample_texts = "\n".join(
            f"- {(p.get('full_article') or {}).get('title') or p.get('text', '')[:200]}"
            for p in sample_posts
        )
        broad_name = cl.get("topic_name", "")
        cluster_summaries.append(
            f"Cluster {idx + 1} [chủ đề ML: {broad_name}]:\n{sample_texts}"
        )

    naming_prompt = (
        "Dưới đây là các cụm bài báo được nhóm theo chủ đề ML chung chung. "
        "Hãy đặt TÊN SỰ KIỆN CỤ THỂ ĐANG XẢY RA cho từng cụm, phản ánh đúng "
        "nội dung thực tế đang được bàn luận nhiều nhất trong cụm đó. "
        "KHÔNG dùng tên danh mục chung như 'Kinh tế', 'Thể thao', 'Chính trị'.\n"
        "Ví dụ tốt:\n"
        "  - 'Giá vàng SJC vượt 120 triệu đồng/lượng'\n"
        "  - 'Nga phóng tên lửa đạn đạo vào Kyiv'\n"
        "  - 'Iran cảnh báo tấn công căn cứ Mỹ ở Trung Đông'\n"
        "  - 'Giá xăng tăng lần thứ 3 trong tháng'\n"
        "  - 'Trump áp thuế quan 45%% lên hàng Trung Quốc'\n\n"
        + "\n\n".join(cluster_summaries)
        + "\n\nTrả về JSON array (đúng số lượng cluster, theo thứ tự):\n"
        '[{"cluster": 1, "name": "...", "description": "1 câu mô tả ngắn", "color": "#hexcolor"}]'
    )

    try:
        from src.config import OPENAI_MODEL
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là biên tập viên tin tức. Đặt tên sự kiện cụ thể, "
                        "không dùng tên danh mục chung. Chỉ trả về JSON array."
                    ),
                },
                {"role": "user", "content": naming_prompt},
            ],
            temperature=0.1,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        items = parsed if isinstance(parsed, list) else next(
            (v for v in parsed.values() if isinstance(v, list)), []
        )
        for item in items:
            idx = int(item.get("cluster", 0)) - 1
            if 0 <= idx < len(clusters):
                clusters[idx]["name"] = item.get("name", clusters[idx].get("topic_name", ""))
                clusters[idx]["description"] = item.get("description", "")
                clusters[idx]["color"] = item.get("color", clusters[idx].get("color", "#6b7280"))
        # Fallback: ensure every cluster has 'name' even if GPT omitted some
        for cl in clusters:
            cl.setdefault("name", cl.get("topic_name", ""))
            cl.setdefault("description", "")
            cl.setdefault("color", "#6b7280")
        return clusters
    except Exception as exc:
        logger.exception("gpt_name_ml_clusters failed: %s", exc)
        for cl in clusters:
            cl.setdefault("name", cl.get("topic_name", ""))
            cl.setdefault("description", "")
            cl.setdefault("color", "#6b7280")
        return clusters
