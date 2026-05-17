"""Geographic region classifier for news posts.

Phân loại địa lý theo 2 bước:
  1. Rule-based (nguồn kênh + từ khóa) — instant, miễn phí
  2. OpenAI fallback nếu rule-based không chắc chắn — tự động cho bài MỚI

Dùng hàm classify_geo() cho pipeline ingestion (bài mới).
backfill_topics.py gọi trực tiếp classify_geo_with_ai() cho bài CŨ hàng loạt.
"""
from __future__ import annotations
import re

# ── Keyword mapping ───────────────────────────────────────────────────────────
# Mỗi region: danh sách từ khóa (lowercase, regex-safe)
_GEO_KEYWORDS: dict[str, list[str]] = {
    "Việt Nam": [
        "việt nam", "vietnam", "viet nam", "hà nội", "hanoi", "hồ chí minh",
        "tp.hcm", "tphcm", "sài gòn", "saigon", "đà nẵng", "da nang",
        "quốc hội", "chính phủ việt", "bộ ngoại giao việt", "vnđ", "vnd",
        "vingroup", "vietcombank", "vietinbank", "bidv", "agribank",
        "vietnam airlines", "vietjet", "bamboo airways",
        "thủ tướng", "tổng bí thư", "chủ tịch nước", "vnexpress",
        "tuổi trẻ", "thanh niên", "người lao động", "dân trí",
        "petrovietnam", "pvn", "sabeco", "habeco", "vinhomes",
    ],
    "Mỹ": [
        "united states", "usa", "u.s.", "u.s.a", "america", "american",
        "washington", "white house", "congress", "senate", "pentagon",
        "federal reserve", "wall street", "nasdaq", "dow jones", "s&p 500",
        "trump", "biden", "harris", "obama", "democrat", "republican",
        "cia", "fbi", "nsa", "fda", "nasa", "sec ",
        "new york", "los angeles", "california", "texas", "florida",
        "silicon valley", "apple inc", "google llc", "microsoft corp",
        "amazon", "meta platforms", "tesla inc",
    ],
    "Trung Quốc": [
        "trung quốc", "china", "chinese", "beijing", "shanghai", "guangdong",
        "tập cận bình", "xi jinping", "prc", "ccp", "cpcc",
        "nhân dân tệ", "yuan", "rmb", "huawei", "alibaba", "tencent",
        "bytedance", "tiktok", "baidu", "xiaomi", "byd", "weibo",
        "hong kong", "hồng kông", "macau", "taiwan", "đài loan",
        "bri", "belt and road", "made in china",
    ],
    "Nga": [
        "nga", "russia", "russian", "moscow", "kremlin", "putin",
        "ukraine", "ukraina", "kiev", "kyiv", "war in ukraine",
        "nato vs russia", "gazprom", "rosneft", "lukoil",
        "ruble", "rubble", "rubl",
    ],
    "Nhật Bản": [
        "nhật bản", "japan", "japanese", "tokyo", "osaka", "kyoto",
        "nikkei", "yen", "sony", "toyota", "honda", "nissan",
        "softbank", "nintendo", "panasonic", "fujitsu",
        "hiroshima", "nagasaki", "fukushima",
        "kishida", "fumio kishida", "prime minister japan",
    ],
    "Hàn Quốc": [
        "hàn quốc", "south korea", "korea", "korean", "seoul",
        "won krw", "samsung", "lg electronics", "hyundai", "kia",
        "sk hynix", "lotte", "kakao", "naver",
        "kpop", "k-pop", "bts", "blackpink", "kdrama",
        "yoon suk-yeol", "president of south korea",
    ],
    "Châu Âu": [
        "châu âu", "europe", "european", "eu ", "euro zone", "eurozone",
        "brussels", "paris", "berlin", "rome", "madrid", "london",
        "uk ", "britain", "england", "france", "germany", "italy", "spain",
        "macron", "scholz", "draghi", "ursula", "nato",
        "ecb", "european central bank", "eu commission",
        "brexit", "schengen",
    ],
    "Trung Đông": [
        "trung đông", "middle east", "israel", "palestine", "gaza",
        "iran", "iraq", "syria", "lebanon", "saudi arabia",
        "uae", "qatar", "kuwait", "bahrain", "oman", "jordan",
        "tel aviv", "jerusalem", "tehran", "riyadh", "dubai",
        "hamas", "hezbollah", "irgc", "opec",
        "oil price", "crude oil", "persian gulf",
    ],
    "Đông Nam Á": [
        "đông nam á", "southeast asia", "asean",
        "thailand", "thái lan", "bangkok",
        "indonesia", "jakarta", "bali",
        "philippines", "manila",
        "malaysia", "kuala lumpur",
        "singapore",
        "myanmar", "burma",
        "cambodia", "campuchia", "phnom penh",
        "laos", "lào", "vientiane",
        "brunei",
    ],
    "Toàn cầu": [
        "toàn cầu", "global", "worldwide", "world", "international",
        "united nations", "un ", "liên hợp quốc", "who ", "imf ",
        "world bank", "wto", "g7", "g20",
        "climate change", "biến đổi khí hậu",
        "covid", "pandemic", "epidemic",
    ],
}

# ── Source / channel → region mapping ─────────────────────────────────────────
# Nếu biết kênh source → gán region ngay, không cần check text
_SOURCE_REGION: dict[str, str] = {
    # Vietnamese news sites
    "vnexpress": "Việt Nam",
    "tuoitre": "Việt Nam",
    "thanhnien": "Việt Nam",
    "nguoilaodong": "Việt Nam",
    "dantri": "Việt Nam",
    "baomoi": "Việt Nam",
    "cafef": "Việt Nam",
    "vietstock": "Việt Nam",
    "tinnhanhchungkhoan": "Việt Nam",
    "kenh14": "Việt Nam",
    "zingnews": "Việt Nam",
    "laodong": "Việt Nam",
    "nhandan": "Việt Nam",
    "baochinhphu": "Việt Nam",
    # US media
    "reuters": "Toàn cầu",
    "bloomberg": "Mỹ",
    "nytimes": "Mỹ",
    "wsj": "Mỹ",
    "cnbc": "Mỹ",
    "cnn": "Toàn cầu",
    "foxnews": "Mỹ",
    "washingtonpost": "Mỹ",
    "apnews": "Toàn cầu",
    # Crypto
    "coindesk": "Toàn cầu",
    "cointelegraph": "Toàn cầu",
    "decrypt": "Toàn cầu",
    "bitcoinmagazine": "Toàn cầu",
}

# ── Compiled patterns ─────────────────────────────────────────────────────────
_COMPILED: dict[str, list[re.Pattern[str]]] = {
    region: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in kws]
    for region, kws in _GEO_KEYWORDS.items()
}


def classify_geo_rule_based(text: str, source: str = "") -> str | None:
    """Phân loại địa lý dựa trên rule (không cần OpenAI).

    Args:
        text:   Nội dung bài viết (đã clean)
        source: Tên kênh / nguồn (username Telegram, domain tên miền…)

    Returns:
        Tên region từ VALID_GEO_REGIONS, hoặc None nếu không xác định được.
    """
    # 1. Ưu tiên nguồn kênh đã biết
    if source:
        src_lower = source.lower().strip()
        for key, region in _SOURCE_REGION.items():
            if key in src_lower:
                return region

    if not text or not text.strip():
        return None

    text_lower = text.lower()

    # 2. Đếm số keyword match cho từng region
    scores: dict[str, int] = {}
    for region, patterns in _COMPILED.items():
        count = sum(1 for p in patterns if p.search(text_lower))
        if count:
            scores[region] = count

    if not scores:
        return None

    # 3. Region có nhiều match nhất
    best = max(scores, key=lambda r: scores[r])
    # Yêu cầu ít nhất 1 match để gán (tránh gán sai)
    return best if scores[best] >= 1 else None


async def classify_geo(text: str, source: str = "") -> str | None:
    """Phân loại địa lý đầy đủ cho bài MỚI trong ingestion pipeline.

    Bước 1 — Rule-based: nhanh, miễn phí, phủ ~70-80% bài.
    Bước 2 — OpenAI fallback: tự động gọi nếu rule-based không xác định được.

    Args:
        text:   Nội dung bài viết (đã clean)
        source: Tên kênh / nguồn (Telegram username, domain…)

    Returns:
        Tên region (str) hoặc None nếu cả hai bước đều thất bại.
    """
    result = classify_geo_rule_based(text, source=source)
    if result:
        return result

    # Fallback: OpenAI
    from src.processing.ai_topic_detector import classify_geo_with_ai
    return await classify_geo_with_ai(text)
