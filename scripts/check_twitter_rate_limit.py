"""Check Twitter API rate limit status."""
import sys
from pathlib import Path

# Add parent directory to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

import tweepy
from src.config import TWITTER_BEARER_TOKEN
from datetime import datetime, timedelta

def check_rate_limits():
    """Check current rate limit status for Twitter API."""
    
    if not TWITTER_BEARER_TOKEN:
        print(" TWITTER_BEARER_TOKEN not found in .env")
        return
    
    try:
        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
        
        print("\n" + "="*60)
        print(" TWITTER API RATE LIMIT STATUS")
        print("="*60)
        
        # Try to get rate limit info by making a simple call
        current_time = datetime.now()
        try:
            user = client.get_user(username="Twitter")
            print(" API Connection: OK")
            print(f"   Test user: @{user.data.username}")
        except tweepy.TweepyException as e:
            if "429" in str(e):
                print(" RATE LIMIT EXCEEDED!")
                print("   Status:  Over limit")
                print()
                print(" Thời gian:")
                print(f"   • Hiện tại: {current_time.strftime('%H:%M:%S')}")
                
                # Twitter rate limit resets every 15 minutes
                # Calculate next reset (round up to next 15-min mark)
                minutes = current_time.minute
                next_reset_minute = ((minutes // 15) + 1) * 15
                
                if next_reset_minute >= 60:
                    next_reset = current_time.replace(hour=current_time.hour + 1, minute=next_reset_minute - 60, second=0, microsecond=0)
                else:
                    next_reset = current_time.replace(minute=next_reset_minute, second=0, microsecond=0)
                
                wait_time = (next_reset - current_time).total_seconds() / 60
                
                print(f"   • Reset sau: ~{int(wait_time)} phút")
                print(f"   • Thử lại lúc: {next_reset.strftime('%H:%M:%S')}")
                print()
                print(" Hành động:")
                print("   1. Đợi đến thời gian trên")
                print("   2. Chạy lại: python -m src.ingestion.twitter_worker")
                print()
                print("  Lưu ý:")
                print("   • Đã giảm xuống 10 sources → An toàn hơn")
                print("   • Nếu vẫn bị limit: Tăng interval giữa các lần chạy")
                print("   • Khuyên: Chạy mỗi 2-3 giờ thay vì liên tục")
                print("="*60 + "\n")
                return
            else:
                print(f" API Error: {e}")
                return
        
        print("\ Endpoint Limits (Twitter API v2 Essential):")
        print("-" * 60)
        print("User timeline (get_users_tweets):")
        print("   • Requests: 1,500 per 15 min (100 per min)")
        print("   • Monthly: 500,000 tweets total")
        print()
        print("Search recent (search_recent_tweets):")
        print("   • Requests: 450 per 15 min (30 per min)")
        print("   • Results: 100 tweets per request")
        print()
        
        print(" Tips:")
        print("   • With 10 sources: ~10 requests = safe")
        print("   • With 50 sources: ~50 requests = use carefully")
        print("   • With 87 sources: ~87 requests = likely to hit limit")
        print()
        print("   • If you hit limit: Wait 15 minutes")
        print("   • Recommended: 5-15 sources for safe operation")
        print("   • Run frequency: Every 2-3 hours is ideal")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f" Error checking rate limits: {e}")


if __name__ == "__main__":
    check_rate_limits()
