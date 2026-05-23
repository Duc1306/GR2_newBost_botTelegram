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
    """Lazy-import openai and return a cached AsyncOpenAI client with a sensible timeout."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    try:
        from openai import AsyncOpenAI
        from src.config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set — AI features disabled")
            return None
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=45.0)
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


async def detect_new_hot_topics(
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
        response = await client.chat.completions.create(
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


async def expand_keywords(topic_name: str, existing_keywords: list[str]) -> list[str]:
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
        response = await client.chat.completions.create(
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

async def score_posts_by_embedding(
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

        # ── Fast path: posts have pre-computed normalized embeddings ─────────────
        # embed_and_cluster_posts attaches _emb (unit-normalized row) to each post.
        # Only embed the query text — saves one API call per cluster filter.
        if posts and "_emb" in posts[0]:
            q_resp = await client.embeddings.create(model=OPENAI_EMBED_MODEL, input=[query_text])
            q_emb = np.array(q_resp.data[0].embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_emb) + 1e-9
            scored = []
            for post in posts:
                p_emb = post["_emb"]
                if not isinstance(p_emb, np.ndarray):
                    p_emb = np.array(p_emb, dtype=np.float32)
                sim = float(np.dot(p_emb, q_emb) / (np.linalg.norm(p_emb) * q_norm))
                scored.append({**post, "_ai_score": round(sim, 4)})
            scored.sort(key=lambda p: p["_ai_score"], reverse=True)
            return scored[:top_k] if top_k else scored

        # ── Standard path: embed query + all posts (no pre-computed embeddings) ──
        texts = [p.get("text", "")[:512] for p in posts]
        all_texts = [query_text] + texts  # query first

        response = await client.embeddings.create(
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


# ─── 3b. Embedding-based clustering (replaces unigram/bigram greedy) ─────────

async def embed_and_cluster_posts(
    posts: list[dict],
    max_clusters: int = 8,
    min_cluster_size: int = 2,
    similarity_threshold: float = 0.60,
) -> list[list[dict]]:
    """
    Group posts into semantic clusters using OpenAI embeddings + DBSCAN.

    Replaces the old unigram/bigram greedy approach. Handles cases like:
      "Giá vàng SJC biến động" ↔ "Kim loại quý trong nước tăng phi mã"
    which share no keywords but are semantically identical.

    Algorithm:
    1. Batch-embed all post texts in ONE API call (cheap).
    2. Build cosine similarity matrix (numpy, O(n²)).
    3. Run DBSCAN with metric='precomputed' on (1 - cosine) distance matrix.
    4. Sort clusters by size (largest first), return top max_clusters.

    Falls back to [] when OpenAI or numpy/sklearn unavailable.
    """
    client = _get_client()
    if not client or not posts:
        return []

    try:
        import numpy as np
        from sklearn.cluster import DBSCAN
        from src.config import OPENAI_EMBED_MODEL

        # Use title+text for richer signal; cap at 512 tokens
        def _post_text(p: dict) -> str:
            fa = p.get("full_article") or {}
            title = fa.get("title", "").strip()
            text = (p.get("text") or "").strip()
            return f"{title} {text}"[:512] if title else text[:512]

        texts = [_post_text(p) for p in posts]

        # Single batch embedding call
        response = await client.embeddings.create(
            model=OPENAI_EMBED_MODEL,
            input=texts,
        )
        embs = np.array([item.embedding for item in response.data], dtype=np.float32)

        # Cosine similarity matrix → distance matrix
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs_norm = embs / (norms + 1e-9)
        cosine_sim = embs_norm @ embs_norm.T
        dist_matrix = np.clip(1.0 - cosine_sim, 0.0, 2.0).astype(np.float64)

        # DBSCAN: eps = 1 - similarity_threshold (distance space)
        eps = 1.0 - similarity_threshold
        db = DBSCAN(eps=eps, min_samples=min_cluster_size, metric="precomputed")
        labels = db.fit_predict(dist_matrix)

        # Attach normalized embedding to each post for reuse in filter_relevant_posts.
        # This eliminates one embedding API call per cluster (N fewer calls total).
        # _emb is stripped before caching in _build_cluster.
        for post, emb_row in zip(posts, embs_norm):
            post["_emb"] = emb_row  # numpy array row (already unit-normalized)

        # Group posts by cluster label (-1 = noise/outlier → skip)
        from collections import defaultdict
        cluster_map: dict[int, list[dict]] = defaultdict(list)
        for idx, label in enumerate(labels):
            if label >= 0:
                cluster_map[label].append(posts[idx])

        if not cluster_map:
            logger.info("embed_and_cluster_posts: DBSCAN found no clusters (eps=%.2f, n=%d)", eps, len(posts))
            return []

        # Sort by cluster size descending, return top max_clusters
        sorted_clusters = sorted(cluster_map.values(), key=len, reverse=True)
        result = sorted_clusters[:max_clusters]
        logger.info(
            "embed_and_cluster_posts: %d posts → %d clusters (sizes: %s)",
            len(posts), len(result), [len(c) for c in result],
        )
        return result

    except ImportError as e:
        logger.warning("embed_and_cluster_posts unavailable (%s) – fallback to keyword clustering", e)
        return []
    except Exception as exc:
        logger.exception("embed_and_cluster_posts failed: %s", exc)
        return []


# ─── 4. Quick health check ───────────────────────────────────────────────────

async def check_openai_status() -> dict[str, Any]:
    """Returns a status dict indicating whether OpenAI is configured and reachable."""
    from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBED_MODEL
    if not OPENAI_API_KEY:
        return {"available": False, "reason": "OPENAI_API_KEY not set"}

    client = _get_client()
    if not client:
        return {"available": False, "reason": "openai package not installed"}

    try:
        # Cheapest possible call – list models
        await client.models.retrieve(OPENAI_MODEL)
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


async def arbitrate_topic(
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
        response = await client.chat.completions.create(
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

NHIỆM VỤ: Nhận danh sách bài báo có đánh số ID, chọn lọc và tổng hợp thành BÀI BÁO HOÀN CHỈNH, ĐẦY ĐỦ CHI TIẾT về đúng 1 sự kiện cụ thể đang được nhắc đến nhiều nhất trong danh sách.

QUY TẮC BẮT BUỘC:
1. GOM NHÓM NGHIÊM NGẶT: Chỉ sử dụng các bài thực sự nói về CÙNG MỘT SỰ KIỆN CỤ THỂ. Bài nào lạc đề → bỏ qua hoàn toàn, KHÔNG được nhắc đến.
2. TIÊU ĐỀ SẮC BÉN: "title" PHẢI là câu tường thuật sự kiện cụ thể, KHÔNG dùng từ ngữ chung chung.
   ❌ Sai: "Các tin tức kinh tế nổi bật", "Thời sự hôm nay", "Tin tức công nghệ"
   ✅ Đúng: "Giá vàng SJC vượt 120 triệu đồng/lượng", "Nga phóng tên lửa đạn đạo vào Kyiv"
3. BẰNG CHỨNG: Trong "used_ids", CHỈ liệt kê ID (chuỗi số) của các bài THỰC SỰ đóng góp nội dung vào bài viết này.
4. KHÔNG bịa thêm sự kiện, số liệu, tên người ngoài dữ liệu được cung cấp.
5. Đánh giá "sentiment": positive/negative/neutral/mixed dựa trên nội dung sự kiện.
6. Đánh giá "risk_score" từ 1-10: mức độ rủi ro/tác động tiêu cực của sự kiện đối với xã hội/kinh tế/chính trị. 1=không rủi ro, 10=rủi ro cực kỳ cao.
7. Câu văn rõ ràng, khách quan, súc tích nhưng ĐẦY ĐỦ.
   Độ dài bắt buộc:
   - lead: 3-4 câu, nêu rõ WHO/WHAT/WHEN/WHERE
   - body: 8-9 đoạn (mỗi đoạn 3-5 câu), bao quát toàn bộ diễn biến từ đầu đến cuối
   - conclusion: 2-3 câu nhận định xu hướng và tác động
   - key_points: 5-7 điểm nổi bật, ưu tiên số liệu cụ thể

ĐỊNH DẠNG ĐẦU RA (Chỉ trả về JSON, không thêm văn bản nào khác):
{
  "title": "Tiêu đề sự kiện cụ thể, sắc bén",
  "lead": "3-4 câu mở đầu nêu rõ ai, cái gì, khi nào, ở đâu, và tại sao quan trọng.",
  "body": [
    "Bối cảnh và nguyên nhân dẫn đến sự kiện (3-5 câu).",
    "Diễn biến chính và các mốc thời gian quan trọng (3-5 câu).",
    "Số liệu, thống kê và bằng chứng cụ thể được đề cập trong các bài (3-5 câu).",
    "Trích dẫn phát biểu chính thức từ các bên liên quan (3-5 câu).",
    "Phản ứng dư luận và tác động thực tế (3-5 câu).",
    "So sánh với bối cảnh trước đây hoặc các diễn biến liên quan (3-5 câu).",
    "Phân tích chuyên sâu hoặc nhận định từ chuyên gia (3-5 câu).",
    "Tổng hợp toàn cảnh và những điểm quan trọng nhất của sự kiện (3-5 câu)."
  ],
  "conclusion": "2-3 câu nhận định xu hướng tiếp theo và ý nghĩa của sự kiện.",
  "key_points": ["Điểm 1 (ưu tiên số liệu)", "Điểm 2", "Điểm 3", "Điểm 4", "Điểm 5"],
  "sentiment": "neutral|positive|negative|mixed",
  "risk_score": 5,
  "used_ids": ["1", "3", "5"]
}"""


async def summarize_cluster(
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
        body = fa.get("body") or fa.get("content", "")
        text = (p.get("text") or "").strip()
        # Prefer full_article body if available (richer source)
        rich_text = (body[:600] if body else text[:600]).strip()
        if title and rich_text:
            return f"{title} — {rich_text}"
        return (title or rich_text)[:700]

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
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SUMMARISE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2500,
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
            "risk_score": int(parsed.get("risk_score", 5) or 5),
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


# ─── 6b. cluster_and_summarize (direct summarize — MAP step removed) ─────────

async def cluster_and_summarize(
    posts: list[dict],
    topic_name: str = "",
    max_posts: int = 15,
) -> dict:
    """
    Summarise a cluster of posts that are ALREADY semantically grouped
    (by DBSCAN embedding clustering in discover_hot_events).

    The old Map-Reduce MAP step (GPT re-splitting posts into sub-events) has
    been removed because it was redundant: posts arriving here have already
    been clustered by cosine similarity, so they belong to the same event.

    Calls summarize_cluster() directly → one GPT call, faster, cheaper.
    """
    if not posts:
        return {
            "title": topic_name, "lead": "", "body": [], "conclusion": "",
            "key_points": [], "sentiment": "neutral", "ai": False,
            "_filtered_posts": [],
        }

    sample = posts[:max_posts]
    result = await summarize_cluster(sample, topic_name=topic_name, max_posts=len(sample))
    # Preserve GPT-validated posts (those listed in used_ids by the summarizer).
    # These are the only posts that actually contributed to the generated summary,
    # so they are the ground-truth "on-topic" subset of the cluster.
    used_posts = result.pop("_used_posts", None) or sample
    result["_filtered_posts"] = used_posts
    return result


# ─── 7. Filter posts to only those genuinely relevant to a topic ─────────────

_RELEVANCE_THRESHOLD = 0.50  # cosine similarity cut-off (raised to 0.50 for stricter relevance filtering)


async def filter_relevant_posts(
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

    scored = await score_posts_by_embedding(posts, query_text=query)

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


async def discover_hot_events(
    posts: list[dict],
    max_events: int = 6,
) -> list[dict]:
    """
    Embedding-based clustering → GPT naming (replaces old unigram/bigram greedy).

    Algorithm:
    1. PRIMARY: embed_and_cluster_posts() — batch embed all posts, run DBSCAN
       on cosine distance matrix.  Handles semantic equivalents like
       "Giá vàng SJC" ↔ "Kim loại quý trong nước" which share no keywords.
    2. FALLBACK: if embedding unavailable → keyword-frequency greedy clustering.
    3. GPT names each cluster as a specific real-world event in ONE call.

    Falls back to empty list when OpenAI is unavailable.
    """
    import re
    from collections import Counter

    if not posts:
        return []

    # ── PRIMARY: embedding-based DBSCAN clustering ────────────────────────────
    embed_clusters = await embed_and_cluster_posts(
        posts, max_clusters=max_events + 2, min_cluster_size=2, similarity_threshold=0.62
    )

    if embed_clusters:
        clusters_raw = [{"posts": cl, "keywords": []} for cl in embed_clusters]
        logger.info("discover_hot_events: using embedding clusters (%d)", len(clusters_raw))
    else:
        # ── FALLBACK: keyword-frequency greedy clustering ─────────────────────
        logger.info("discover_hot_events: embedding unavailable, falling back to keyword clustering")

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
            tokens = re.findall(
                r"[a-zA-Z0-9"
                r"àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩị"
                r"òóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+",
                text.lower(),
            )
            return [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]

        unigram_counter: Counter = Counter()
        bigram_counter: Counter = Counter()
        post_tokens: list[list[str]] = []

        for p in posts:
            toks = _tokenize(p.get("text", ""))
            post_tokens.append(toks)
            unigram_counter.update(toks)
            bigrams = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)]
            bigram_counter.update(bigrams)

        n = len(posts)
        freq_bigrams = [(bg, cnt) for bg, cnt in bigram_counter.most_common(60) if cnt >= 3 and cnt / n < 0.7]
        freq_unigrams = [(w, cnt) for w, cnt in unigram_counter.most_common(60) if cnt >= 3 and cnt / n < 0.7 and not any(w in bg for bg, _ in freq_bigrams[:20])]
        kw_scored = sorted([(bg, cnt * 1.5) for bg, cnt in freq_bigrams[:20]] + [(w, float(cnt)) for w, cnt in freq_unigrams[:20]], key=lambda x: -x[1])
        top_keywords = [kw for kw, _ in kw_scored[:25]]

        if not top_keywords:
            return []

        post_keyword_sets: list[set[str]] = []
        for toks in post_tokens:
            tok_set = set(toks)
            matched = {kw for kw in top_keywords if " " not in kw and kw in tok_set}
            text_joined = " ".join(toks)
            matched |= {kw for kw in top_keywords if " " in kw and kw in text_joined}
            post_keyword_sets.append(matched)

        clusters_raw = []
        used_indices: set[int] = set()
        for seed_kw in top_keywords[:15]:
            members = [i for i, kws in enumerate(post_keyword_sets) if seed_kw in kws and i not in used_indices]
            if len(members) < 2:
                continue
            for i in members:
                used_indices.add(i)
            combined_kws: Counter = Counter()
            for i in members:
                combined_kws.update(post_keyword_sets[i])
            clusters_raw.append({"posts": [posts[i] for i in members], "keywords": [kw for kw, _ in combined_kws.most_common(5)]})
            if len(clusters_raw) >= max_events + 2:
                break

        if not clusters_raw:
            return []

    # ── GPT names each cluster as a specific real-world event (1 call) ────────
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
        response = await client.chat.completions.create(
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

async def gpt_name_ml_clusters(clusters: list[dict]) -> list[dict]:
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
        response = await client.chat.completions.create(
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


# ─── 9. Classify a single post's topics using OpenAI ────────────────────────

_TOPIC_CLASSIFY_SYSTEM = """Bạn là chuyên gia phân loại tin tức đa ngôn ngữ (Tiếng Việt + Tiếng Anh).
Hãy phân loại bài viết sau vào 1-3 chủ đề phù hợp nhất từ danh sách dưới đây.

Danh sách chủ đề hợp lệ:
Kinh tế, Công nghệ, Crypto, Chính trị, Thế giới, Pháp luật, Ô tô - Xe máy,
Khoa học, Thể thao, Giải trí, Sức khỏe, Giáo dục, Việc làm, Du lịch,
Ẩm thực, Kinh doanh & Khởi nghiệp, Trò chơi & Ứng dụng, Tin tức & Truyền thông, Khác

Trả về JSON array với đúng tên chủ đề từ danh sách trên. Ví dụ: ["Công nghệ", "Kinh tế"]
Chỉ trả về JSON array, không giải thích thêm."""

VALID_TOPICS = {
    "Kinh tế", "Công nghệ", "Crypto", "Chính trị", "Thế giới", "Pháp luật",
    "Ô tô - Xe máy", "Khoa học", "Thể thao", "Giải trí", "Sức khỏe", "Giáo dục",
    "Việc làm", "Du lịch", "Ẩm thực", "Kinh doanh & Khởi nghiệp",
    "Trò chơi & Ứng dụng", "Tin tức & Truyền thông", "Khác",
}


_RPD_EXHAUSTED = False  # module-level flag: True khi daily limit hết


def _parse_retry_after(msg: str) -> float:
    """Lấy số giây cần chờ từ thông báo lỗi 429 của OpenAI."""
    import re
    m = re.search(r"try again in (\d+\.?\d*)s", str(msg))
    return float(m.group(1)) + 0.5 if m else 10.0


async def classify_post_topic_with_ai(text: str, max_topics: int = 2) -> list[str]:
    """Use OpenAI to classify a news post into topics when rule-based fails.

    Args:
        text: Post text (will be trimmed to 800 chars)
        max_topics: Maximum number of topics to return (1-3)

    Returns:
        List of topic name strings from VALID_TOPICS. Empty list on failure.
    """
    global _RPD_EXHAUSTED
    client = _get_client()
    if not client or not text or len(text.strip()) < 20:
        return []
    if _RPD_EXHAUSTED:
        return []

    from src.config import OPENAI_MODEL
    for attempt in range(4):  # tối đa 4 lần thử
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _TOPIC_CLASSIFY_SYSTEM},
                    {"role": "user", "content": text[:800]},
                ],
                temperature=0.1,
                max_tokens=80,
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [t for t in parsed[:max_topics] if isinstance(t, str) and t in VALID_TOPICS]
            return []
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate_limit_exceeded" in msg:
                if "requests per day" in msg or "RPD" in msg:
                    # Daily limit hết — dừng hẳn, không retry vô ích
                    logger.error("[AI] Daily RPD limit exhausted — dừng gọi AI hôm nay.")
                    _RPD_EXHAUSTED = True
                    return []
                wait = _parse_retry_after(msg)
                logger.info("[AI/topic] 429 rate limit, chờ %.1fs (lần %d/4)…", wait, attempt + 1)
                import asyncio as _aio
                await _aio.sleep(wait)
                continue
            logger.warning("classify_post_topic_with_ai failed: %s", exc)
            return []
    return []


# ─── 10. Classify geographic focus of a post using OpenAI ───────────────────

_GEO_CLASSIFY_SYSTEM = """Bạn là chuyên gia địa lý và phân tích tin tức quốc tế.
Xác định khu vực địa lý CHÍNH mà bài viết đề cập đến.

Chọn MỘT trong các khu vực sau (đúng tên, không thay đổi):
- Việt Nam
- Mỹ
- Trung Quốc
- Nga
- Nhật Bản
- Hàn Quốc
- Châu Âu
- Trung Đông
- Đông Nam Á
- Toàn cầu
- Khác

Trả về JSON object: {"region": "tên khu vực"}
Chỉ trả về JSON, không giải thích."""

VALID_GEO_REGIONS = {
    "Việt Nam", "Mỹ", "Trung Quốc", "Nga", "Nhật Bản", "Hàn Quốc",
    "Châu Âu", "Trung Đông", "Đông Nam Á", "Toàn cầu", "Khác",
}

_GEO_REGION_EMOJI = {
    "Việt Nam": "🇻🇳",
    "Mỹ": "🇺🇸",
    "Trung Quốc": "🇨🇳",
    "Nga": "🇷🇺",
    "Nhật Bản": "🇯🇵",
    "Hàn Quốc": "🇰🇷",
    "Châu Âu": "🇪🇺",
    "Trung Đông": "🌙",
    "Đông Nam Á": "🌏",
    "Toàn cầu": "🌍",
    "Khác": "📍",
}


async def classify_geo_with_ai(text: str) -> str | None:
    """Classify the geographic focus of a news post using OpenAI.

    Args:
        text: Post text (trimmed to 600 chars)

    Returns:
        Region string from VALID_GEO_REGIONS, or None on failure.
    """
    global _RPD_EXHAUSTED
    client = _get_client()
    if not client or not text or len(text.strip()) < 20:
        return None
    if _RPD_EXHAUSTED:
        return None

    from src.config import OPENAI_MODEL
    for attempt in range(4):  # tối đa 4 lần thử
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _GEO_CLASSIFY_SYSTEM},
                    {"role": "user", "content": text[:600]},
                ],
                temperature=0.1,
                max_tokens=40,
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            region = parsed.get("region") if isinstance(parsed, dict) else None
            return region if region in VALID_GEO_REGIONS else None
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate_limit_exceeded" in msg:
                if "requests per day" in msg or "RPD" in msg:
                    logger.error("[AI] Daily RPD limit exhausted — dừng gọi AI hôm nay.")
                    _RPD_EXHAUSTED = True
                    return None
                wait = _parse_retry_after(msg)
                logger.info("[AI/geo] 429 rate limit, chờ %.1fs (lần %d/4)…", wait, attempt + 1)
                import asyncio as _aio
                await _aio.sleep(wait)
                continue
            logger.warning("classify_geo_with_ai failed: %s", exc)
            return None
    return None


# ─── 11. Batch classify geo & topics (cost-saving: N posts → 1 API call) ────

_GEO_BATCH_SYSTEM = """Bạn là chuyên gia địa lý. Phân loại địa lý CHÍNH cho nhiều bài báo cùng lúc.

Khu vực hợp lệ: Việt Nam, Mỹ, Trung Quốc, Nga, Nhật Bản, Hàn Quốc, Châu Âu, Trung Đông, Đông Nam Á, Toàn cầu, Khác

Input: danh sách bài theo định dạng [idx] text
Output: JSON array theo đúng thứ tự: [{"idx": 0, "region": "tên khu vực"}, ...]
Chỉ trả về JSON array, không giải thích."""

_TOPIC_BATCH_SYSTEM = """Bạn là chuyên gia phân loại tin tức đa ngôn ngữ.

Chủ đề hợp lệ: Kinh tế, Công nghệ, Crypto, Chính trị, Thế giới, Pháp luật, Ô tô - Xe máy, Khoa học, Thể thao, Giải trí, Sức khỏe, Giáo dục, Việc làm, Du lịch, Ẩm thực, Kinh doanh & Khởi nghiệp, Trò chơi & Ứng dụng, Tin tức & Truyền thông, Khác

Input: danh sách bài theo định dạng [idx] text
Output: JSON array theo đúng thứ tự: [{"idx": 0, "topics": ["Chủ đề1"]}, ...]
Chỉ trả về JSON array, không giải thích."""


async def batch_classify_geo_with_ai(
    texts: list[str],
    batch_size: int = 30,
) -> list[str | None]:
    """Phân loại địa lý cho nhiều bài trong một lần gọi API.

    Tiết kiệm ~60% token so với gọi từng bài riêng lẻ (system prompt overhead
    chỉ trả một lần thay vì N lần).

    Args:
        texts:      Danh sách text cần phân loại.
        batch_size: Số bài mỗi lần gọi API (mặc định 30).

    Returns:
        List kết quả cùng độ dài với ``texts``. None nếu thất bại hoặc
        bài quá ngắn / không xác định được.
    """
    global _RPD_EXHAUSTED
    if not texts:
        return []

    client = _get_client()
    if not client or _RPD_EXHAUSTED:
        return [None] * len(texts)

    from src.config import OPENAI_MODEL
    import asyncio as _aio

    results: list[str | None] = [None] * len(texts)

    for start in range(0, len(texts), batch_size):
        chunk = texts[start: start + batch_size]

        # Build numbered prompt; skip texts that are too short
        lines: list[str] = []
        valid_indices: list[int] = []
        for local_i, text in enumerate(chunk):
            if text and len(text.strip()) >= 20:
                lines.append(f"[{local_i}] {text[:400]}")
                valid_indices.append(local_i)

        if not lines:
            continue

        user_msg = "\n".join(lines)

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": _GEO_BATCH_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=len(valid_indices) * 25 + 20,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                # Response may be {"results": [...]} or just [...]
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    parsed = parsed.get("results", parsed.get("data", list(parsed.values())[0] if parsed else []))
                if not isinstance(parsed, list):
                    break
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    local_i = item.get("idx")
                    region = item.get("region")
                    if isinstance(local_i, int) and region in VALID_GEO_REGIONS:
                        results[start + local_i] = region
                break
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "rate_limit_exceeded" in msg:
                    if "requests per day" in msg or "RPD" in msg:
                        logger.error("[AI] Daily RPD limit exhausted — dừng gọi AI hôm nay.")
                        _RPD_EXHAUSTED = True
                        return results
                    wait = _parse_retry_after(msg)
                    logger.info("[AI/geo-batch] 429, chờ %.1fs (lần %d/3)…", wait, attempt + 1)
                    await _aio.sleep(wait)
                    continue
                logger.warning("batch_classify_geo_with_ai failed: %s", exc)
                break

    return results


async def batch_classify_post_topic_with_ai(
    texts: list[str],
    batch_size: int = 25,
    max_topics: int = 2,
) -> list[list[str]]:
    """Phân loại chủ đề cho nhiều bài trong một lần gọi API.

    Tiết kiệm ~60-70% token so với gọi từng bài riêng lẻ.

    Args:
        texts:      Danh sách text cần phân loại.
        batch_size: Số bài mỗi lần gọi API (mặc định 25).
        max_topics: Số chủ đề tối đa trả về mỗi bài.

    Returns:
        List kết quả cùng độ dài với ``texts``. List rỗng nếu thất bại.
    """
    global _RPD_EXHAUSTED
    if not texts:
        return []

    client = _get_client()
    if not client or _RPD_EXHAUSTED:
        return [[] for _ in texts]

    from src.config import OPENAI_MODEL
    import asyncio as _aio

    results: list[list[str]] = [[] for _ in texts]

    for start in range(0, len(texts), batch_size):
        chunk = texts[start: start + batch_size]

        lines: list[str] = []
        valid_indices: list[int] = []
        for local_i, text in enumerate(chunk):
            if text and len(text.strip()) >= 20:
                lines.append(f"[{local_i}] {text[:500]}")
                valid_indices.append(local_i)

        if not lines:
            continue

        user_msg = "\n".join(lines)

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": _TOPIC_BATCH_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=len(valid_indices) * 40 + 20,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    parsed = parsed.get("results", parsed.get("data", list(parsed.values())[0] if parsed else []))
                if not isinstance(parsed, list):
                    break
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    local_i = item.get("idx")
                    topics = item.get("topics", [])
                    if isinstance(local_i, int) and isinstance(topics, list):
                        valid = [t for t in topics[:max_topics] if isinstance(t, str) and t in VALID_TOPICS]
                        if valid:
                            results[start + local_i] = valid
                break
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "rate_limit_exceeded" in msg:
                    if "requests per day" in msg or "RPD" in msg:
                        logger.error("[AI] Daily RPD limit exhausted — dừng gọi AI hôm nay.")
                        _RPD_EXHAUSTED = True
                        return results
                    wait = _parse_retry_after(msg)
                    logger.info("[AI/topic-batch] 429, chờ %.1fs (lần %d/3)…", wait, attempt + 1)
                    await _aio.sleep(wait)
                    continue
                logger.warning("batch_classify_post_topic_with_ai failed: %s", exc)
                break

    return results
