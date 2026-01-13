"""Test Twitter worker functionality."""
import pytest
from datetime import datetime, UTC
from src.ingestion.twitter_worker import process_tweet
from src.models.post import Post


def test_process_tweet_basic():
    """Test basic tweet processing."""
    tweet_data = {
        'id': '1234567890',
        'text': 'Breaking news: New technology breakthrough! #technology https://example.com/article',
        'author': 'TechNews',
        'created_at': datetime.now(UTC),
        'media': [],
        'links': ['https://example.com/article']
    }
    
    post = process_tweet(tweet_data)
    
    assert post.platform == "twitter"
    assert post.source == "twitter"
    assert post.source_id == "1234567890"
    assert post.author == "TechNews"
    assert "technology" in post.text.lower()
    assert len(post.links) >= 1
    assert post.id is not None


def test_process_tweet_with_media():
    """Test tweet with media processing."""
    tweet_data = {
        'id': '9876543210',
        'text': 'Check out this amazing photo! #photography',
        'author': 'PhotoDaily',
        'created_at': datetime.now(UTC),
        'media': [
            {'type': 'photo', 'url': 'https://pbs.twimg.com/media/example.jpg'}
        ],
        'links': []
    }
    
    post = process_tweet(tweet_data)
    
    assert len(post.media) == 1
    assert post.media[0].type == "photo"
    assert "twimg.com" in post.media[0].url


def test_process_tweet_hashtag():
    """Test tweet from hashtag search."""
    tweet_data = {
        'id': '1111111111',
        'text': 'Vietnam tech startup raises $10M #vietnam #startup #funding',
        'author': 'StartupNews',
        'created_at': datetime.now(UTC),
        'media': [],
        'links': []
    }
    
    post = process_tweet(tweet_data)
    
    assert "#vietnam" in post.text.lower() or "#startup" in post.text.lower()
    assert post.author == "StartupNews"


def test_process_tweet_language_detection():
    """Test language detection for tweets."""
    # English tweet
    tweet_en = {
        'id': '2222222222',
        'text': 'Breaking news from the United States about technology and innovation',
        'author': 'NewsEN',
        'created_at': datetime.now(UTC),
        'media': [],
        'links': []
    }
    
    post_en = process_tweet(tweet_en)
    assert post_en.lang == "en"
    
    # Vietnamese tweet
    tweet_vi = {
        'id': '3333333333',
        'text': 'Tin tức mới nhất về công nghệ và khởi nghiệp tại Việt Nam',
        'author': 'NewsVI',
        'created_at': datetime.now(UTC),
        'media': [],
        'links': []
    }
    
    post_vi = process_tweet(tweet_vi)
    assert post_vi.lang == "vi"


def test_process_tweet_cleaning():
    """Test text cleaning for tweets."""
    tweet_data = {
        'id': '4444444444',
        'text': 'Check this out!!! 🔥🔥🔥 https://t.co/abc123 #trending',
        'author': 'BuzzFeed',
        'created_at': datetime.now(UTC),
        'media': [],
        'links': ['https://example.com/full-url']
    }
    
    post = process_tweet(tweet_data)
    
    # Text should be cleaned but preserve basic content
    assert post.text is not None
    assert len(post.text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
