"""Twitter ingestion using Tweepy (Twitter API v2).
Chạy: python -m src.ingestion.twitter_worker [--full]
--full: Lấy tối đa nhiều tweets từ timeline/hashtags (cho training model)
Yêu cầu: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
hoặc TWITTER_BEARER_TOKEN trong .env
"""
from __future__ import annotations
import sys
from datetime import datetime, UTC
from typing import List, Dict, Any
import tweepy
from pathlib import Path

from src.config import (
    TWITTER_API_KEY, TWITTER_API_SECRET, 
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN, TWITTER_FETCH_LIMIT
)
from src.ingestion.sources import TWITTER_SOURCES
from src.processing.cleaning import clean_text
from src.processing.lang import detect_language
from src.processing.web_scraper import enrich_post_with_article
from src.processing.topic_classifier import classify_post_topics
from src.processing.ml_topic_classifier import MLTopicClassifier
from src.models.post import Post, MediaItem
from src.db.mongo import get_posts_collection

# Chế độ lấy dữ liệu đầy đủ (nhiều hơn nhiều)
FULL_MODE_LIMIT = 500  # Lấy tối đa 500 tweets/source cho training

# ML Classifier (lazy load)
_ml_classifier: MLTopicClassifier | None = None
_ml_classifier_checked: bool = False


def get_ml_classifier() -> MLTopicClassifier | None:
    """Get ML classifier instance (lazy load). Returns None if not available."""
    global _ml_classifier, _ml_classifier_checked
    
    if not _ml_classifier_checked:
        _ml_classifier_checked = True
        model_path = Path("models/topic_classifier_svm.pkl")
        
        if model_path.exists():
            try:
                _ml_classifier = MLTopicClassifier(model_path=str(model_path))
                print("✓ ML Topic Classifier loaded successfully")
            except Exception as e:
                print(f"  Failed to load ML classifier: {e}")
                print("   Falling back to rule-based classifier")
                _ml_classifier = None
        else:
            print("\n  ML model not found!")
            print("   → Using rule-based classifier (fallback)")
            print("   → To train ML model: python scripts/train_ml_classifier.py\n")
            _ml_classifier = None
    
    return _ml_classifier


def build_twitter_client() -> tweepy.Client:
    """Tạo Twitter API client."""
    # Ưu tiên dùng Bearer Token (đơn giản nhất cho read-only)
    if TWITTER_BEARER_TOKEN:
        return tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
    
    # Fallback: OAuth 1.0a User Context
    if all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        return tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
    
    raise RuntimeError(
        "Thiếu Twitter API credentials! Cần có:\n"
        "  - TWITTER_BEARER_TOKEN (đơn giản nhất)\n"
        "  hoặc\n"
        "  - TWITTER_API_KEY + TWITTER_API_SECRET + TWITTER_ACCESS_TOKEN + TWITTER_ACCESS_SECRET"
    )


def fetch_tweets_from_user(client: tweepy.Client, username: str, limit: int) -> List[Dict[str, Any]]:
    """Lấy tweets từ một user Twitter."""
    tweets_data = []
    
    try:
        # Lấy user ID từ username
        user = client.get_user(username=username.lstrip('@'), user_fields=['id', 'username'])
        if not user.data:
            print(f"     Không tìm thấy user: {username}")
            return tweets_data
        
        user_id = user.data.id
        user_handle = user.data.username
        
        # Lấy tweets của user
        tweets = client.get_users_tweets(
            id=user_id,
            max_results=min(limit, 100),  # Twitter API limit per request
            tweet_fields=['created_at', 'public_metrics', 'entities', 'attachments'],
            expansions=['attachments.media_keys'],
            media_fields=['type', 'url', 'preview_image_url']
        )
        
        if not tweets.data:
            print(f"     Không có tweets mới từ @{user_handle}")
            return tweets_data
        
        # Parse media nếu có
        media_dict = {}
        if tweets.includes and 'media' in tweets.includes:
            for media in tweets.includes['media']:
                media_dict[media.media_key] = media
        
        for tweet in tweets.data:
            tweet_data = {
                'id': tweet.id,
                'text': tweet.text,
                'author': user_handle,
                'created_at': tweet.created_at,
                'media': [],
                'links': []
            }
            
            # Extract media
            if hasattr(tweet, 'attachments') and tweet.attachments:
                media_keys = tweet.attachments.get('media_keys', [])
                for media_key in media_keys:
                    if media_key in media_dict:
                        media = media_dict[media_key]
                        tweet_data['media'].append({
                            'type': media.type,
                            'url': getattr(media, 'url', None) or getattr(media, 'preview_image_url', '(embedded)')
                        })
            
            # Extract URLs
            if hasattr(tweet, 'entities') and tweet.entities and 'urls' in tweet.entities:
                for url_entity in tweet.entities['urls']:
                    if 'expanded_url' in url_entity:
                        tweet_data['links'].append(url_entity['expanded_url'])
            
            tweets_data.append(tweet_data)
        
        print(f"    Lấy được {len(tweets_data)} tweets từ @{user_handle}")
        
    except tweepy.TweepyException as e:
        print(f"    Lỗi khi lấy tweets từ {username}: {e}")
    
    return tweets_data


def fetch_tweets_from_hashtag(client: tweepy.Client, hashtag: str, limit: int) -> List[Dict[str, Any]]:
    """Lấy tweets chứa một hashtag."""
    tweets_data = []
    
    try:
        query = hashtag if hashtag.startswith('#') else f'#{hashtag}'
        query = f'{query} -is:retweet'  # Loại bỏ retweets
        
        tweets = client.search_recent_tweets(
            query=query,
            max_results=min(limit, 100),  # Twitter API limit per request
            tweet_fields=['created_at', 'author_id', 'public_metrics', 'entities', 'attachments'],
            expansions=['author_id', 'attachments.media_keys'],
            user_fields=['username'],
            media_fields=['type', 'url', 'preview_image_url']
        )
        
        if not tweets.data:
            print(f"     Không có tweets mới cho {query}")
            return tweets_data
        
        # Parse users
        users_dict = {}
        if tweets.includes and 'users' in tweets.includes:
            for user in tweets.includes['users']:
                users_dict[user.id] = user.username
        
        # Parse media
        media_dict = {}
        if tweets.includes and 'media' in tweets.includes:
            for media in tweets.includes['media']:
                media_dict[media.media_key] = media
        
        for tweet in tweets.data:
            author = users_dict.get(tweet.author_id, 'unknown')
            
            tweet_data = {
                'id': tweet.id,
                'text': tweet.text,
                'author': author,
                'created_at': tweet.created_at,
                'media': [],
                'links': []
            }
            
            # Extract media
            if hasattr(tweet, 'attachments') and tweet.attachments:
                media_keys = tweet.attachments.get('media_keys', [])
                for media_key in media_keys:
                    if media_key in media_dict:
                        media = media_dict[media_key]
                        tweet_data['media'].append({
                            'type': media.type,
                            'url': getattr(media, 'url', None) or getattr(media, 'preview_image_url', '(embedded)')
                        })
            
            # Extract URLs
            if hasattr(tweet, 'entities') and tweet.entities and 'urls' in tweet.entities:
                for url_entity in tweet.entities['urls']:
                    if 'expanded_url' in url_entity:
                        tweet_data['links'].append(url_entity['expanded_url'])
            
            tweets_data.append(tweet_data)
        
        print(f"   ✓ Lấy được {len(tweets_data)} tweets cho {query}")
        
    except tweepy.TweepyException as e:
        print(f"    Lỗi khi search hashtag {hashtag}: {e}")
    
    return tweets_data


def process_tweet(tweet_data: Dict[str, Any]) -> Post:
    """Xử lý một tweet thành Post model."""
    raw_text = tweet_data['text']
    cleaned_text, extracted_links = clean_text(raw_text)
    
    # Combine links từ cleaning và từ entities
    all_links = list(set(extracted_links + tweet_data['links']))
    
    # Media items
    media_items: List[MediaItem] = []
    for media in tweet_data['media']:
        media_items.append(MediaItem(
            type=media['type'],
            url=media['url']
        ))
    
    # Detect language
    lang = detect_language(cleaned_text)
    
    # Create Post
    post = Post.from_raw(
        source="twitter",
        source_id=str(tweet_data['id']),
        author=tweet_data['author'],
        text=cleaned_text,
        links=all_links,
        media=media_items,
        created_at=tweet_data['created_at']
    )
    
    # Set language after creation
    post.lang = lang
    
    return post


def classify_and_enrich_post(post: Post) -> Post:
    """Classify topics và enrich với full article nếu có link."""
    # Try ML classifier first, fallback to rule-based
    ml_clf = get_ml_classifier()
    
    if ml_clf:
        try:
            topics = ml_clf.predict_topics(post.text, return_all=False, min_confidence=0.3)
            if topics:
                post.add_topic_prediction(
                    topic=topics[0]['topic'],
                    confidence=topics[0]['confidence'],
                    model_version=ml_clf.model_version,
                    method="ml"
                )
            else:
                # Fallback to rule-based if ML returns no confident predictions
                rule_topics = classify_post_topics(post)
                if rule_topics:
                    post.add_topic_prediction(
                        topic=rule_topics[0],
                        confidence=0.7,
                        model_version="rule-v1",
                        method="rule-based"
                    )
        except Exception as e:
            print(f"     ML classification failed: {e}, using rule-based")
            rule_topics = classify_post_topics(post)
            if rule_topics:
                post.add_topic_prediction(
                    topic=rule_topics[0],
                    confidence=0.7,
                    model_version="rule-v1",
                    method="rule-based"
                )
    else:
        # Use rule-based classifier
        topics = classify_post_topics(post)
        if topics:
            post.add_topic_prediction(
                topic=topics[0],
                confidence=0.7,
                model_version="rule-v1",
                method="rule-based"
            )
    
    # Enrich with full article if there are links
    if post.links:
        try:
            post = enrich_post_with_article(post)
        except Exception as e:
            print(f"     Failed to enrich tweet {post.source_id}: {e}")
    
    return post


def save_tweet_to_db(post: Post) -> bool:
    """Lưu tweet vào database, return True nếu là mới."""
    collection = get_posts_collection()
    
    # Check if already exists
    existing = collection.find_one({"id": post.id})
    if existing:
        return False
    
    # Insert new post
    collection.insert_one(post.model_dump(mode='json'))
    return True


def main():
    """Main entry point."""
    full_mode = "--full" in sys.argv
    limit = FULL_MODE_LIMIT if full_mode else TWITTER_FETCH_LIMIT
    
    print("\n" + "="*60)
    print(" TWITTER INGESTION WORKER")
    print("="*60)
    print(f"Mode: {'FULL (Training)' if full_mode else 'NORMAL (Incremental)'}")
    print(f"Limit per source: {limit} tweets")
    print(f"Sources to monitor: {len(TWITTER_SOURCES)}")
    print("="*60 + "\n")
    
    if not TWITTER_SOURCES:
        print("  Không có Twitter sources được cấu hình!")
        print("   Thêm vào TWITTER_SOURCES trong .env hoặc sources.py")
        print("   Ví dụ: @BBCBreaking;@Reuters;#technology\n")
        return
    
    # Build Twitter client
    try:
        client = build_twitter_client()
        print("✓ Twitter API client đã được khởi tạo\n")
    except Exception as e:
        print(f" Không thể khởi tạo Twitter client: {e}")
        return
    
    total_fetched = 0
    total_new = 0
    
    # Process each source
    for source in TWITTER_SOURCES:
        print(f"\n Đang xử lý: {source}")
        print("-" * 60)
        
        # Determine if username or hashtag
        if source.startswith('@'):
            tweets_data = fetch_tweets_from_user(client, source, limit)
        elif source.startswith('#'):
            tweets_data = fetch_tweets_from_hashtag(client, source, limit)
        else:
            print(f"     Source không hợp lệ: {source} (cần bắt đầu @ hoặc #)")
            continue
        
        if not tweets_data:
            continue
        
        total_fetched += len(tweets_data)
        new_count = 0
        
        # Process each tweet
        for tweet_data in tweets_data:
            try:
                # Convert to Post model
                post = process_tweet(tweet_data)
                
                # Classify and enrich
                post = classify_and_enrich_post(post)
                
                # Save to DB
                is_new = save_tweet_to_db(post)
                if is_new:
                    new_count += 1
                    
            except Exception as e:
                print(f"    Lỗi xử lý tweet {tweet_data['id']}: {e}")
                continue
        
        total_new += new_count
        print(f"    Đã lưu {new_count} tweets mới từ {source}")
    
    print("\n" + "="*60)
    print(" KẾT QUẢ")
    print("="*60)
    print(f"Tổng tweets đã lấy: {total_fetched}")
    print(f"Tweets mới được lưu: {total_new}")
    print(f"Tweets đã tồn tại: {total_fetched - total_new}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
