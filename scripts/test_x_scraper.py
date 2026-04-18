"""Script test nhanh X Worker — chạy trực tiếp bằng:
   python scripts/test_x_scraper.py
"""
from __future__ import annotations
import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.config import APIFY_API_TOKEN, X_KEYWORDS, X_USERNAMES, X_FETCH_LIMIT


def _check_config() -> bool:
    print("\n" + "=" * 55)
    print("  X (Twitter) Scraper — Kiểm tra cấu hình")
    print("=" * 55)

    if not APIFY_API_TOKEN:
        print("\n[LỖI] APIFY_API_TOKEN chưa được đặt trong .env!")
        print("  → Đăng ký tại: https://console.apify.com/sign-up")
        print("  → Lấy token  : Settings → Integrations → Personal API tokens")
        return False

    print(f"\n  APIFY_API_TOKEN : {APIFY_API_TOKEN[:16]}...  ✓")
    print(f"  X_KEYWORDS      : {X_KEYWORDS or '(chưa đặt — xem .env.example)'}")
    print(f"  X_USERNAMES     : {X_USERNAMES or '(chưa đặt — xem .env.example)'}")
    print(f"  X_FETCH_LIMIT   : {X_FETCH_LIMIT} tweets")

    if not X_KEYWORDS and not X_USERNAMES:
        print("\n[CẢNH BÁO] Không có X_KEYWORDS hoặc X_USERNAMES nào trong .env!")
        print("  → Sẽ dùng giá trị mặc định để test: keyword='ReactJS', user='TechCrunch'")

    return True


async def main() -> None:
    if not _check_config():
        return

    from src.ingestion.x_worker import fetch_by_keywords, fetch_by_users, _tweet_to_post, _classify_post

    keywords_to_test  = X_KEYWORDS  or ["ReactJS"]
    usernames_to_test = X_USERNAMES or ["TechCrunch"]

    # ---- Test Actor A: từ khóa ----
    print(f"\n[TEST A] Tweet scraper (keyword)")
    print(f"  Keyword: {keywords_to_test[0]} | Lấy tối đa 5 tweets")
    kw_tweets = fetch_by_keywords([keywords_to_test[0]], max_items=5)

    if kw_tweets:
        tweet = kw_tweets[0]
        print(f"\n  Mẫu tweet đầu tiên:")
        print(f"    Text   : {(tweet.get('text') or '')[:120]}...")
        print(f"    Author : @{(tweet.get('author') or {}).get('userName', '?')}")
        print(f"    Likes  : {tweet.get('likeCount', 0)}")
        print(f"    URL    : {tweet.get('url', '—')}")

        post = _tweet_to_post(tweet)
        if post:
            _classify_post(post)
            print(f"    Topics : {post.topics}")
            print(f"    Score  : {post.score:.2f}")
    else:
        print("  [!] Không có tweet nào — kiểm tra lại token hoặc keyword")

    # ---- Test Actor B: tài khoản ----
    print(f"\n[TEST B] Actor apidojo/twitter-user-scraper")
    print(f"  User: @{usernames_to_test[0]} | Lấy tối đa 5 tweets")
    user_tweets = fetch_by_users([usernames_to_test[0]], max_tweets_per_user=5)

    if user_tweets:
        tweet = user_tweets[0]
        print(f"\n  Mẫu tweet đầu tiên:")
        print(f"    Text   : {(tweet.get('text') or '')[:120]}...")
        print(f"    Author : @{(tweet.get('author') or {}).get('userName', '?')}")
        print(f"    Likes  : {tweet.get('likeCount', 0)}")
    else:
        print("  [!] Không có tweet nào")

    # ---- Chạy full pipeline (lưu vào MongoDB) ----
    print("\n" + "-" * 55)
    print("  Chạy full ingest_once (mode=both, max=5) → MongoDB")
    print("-" * 55)
    from src.ingestion.x_worker import ingest_once
    saved = await ingest_once(mode="both", max_items=5)
    print(f"\n  Kết quả: {saved} bài viết đã lưu vào MongoDB")
    print("\n  Kiểm tra tại MongoDB: db.posts.find({{platform: 'twitter'}})")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
