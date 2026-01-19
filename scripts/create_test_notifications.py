"""
Create test notifications for testing the notification system
"""
import sys
import os
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db.mongo import get_db

def create_test_notifications():
    """Create sample notifications for demo/testing"""
    db = get_db()
    
    notifications = [
        {
            "user": "admin",
            "type": "success",
            "title": "Telegram Fetch Completed",
            "message": "Successfully fetched 150 new posts from 5 channels",
            "link": "/posts",
            "read": False,
            "created_at": datetime.utcnow()
        },
        {
            "user": "admin",
            "type": "info",
            "title": "ML Model Updated",
            "message": "Topic classifier retrained with 95.2% accuracy on 1,000 samples",
            "link": "/analytics",
            "read": False,
            "created_at": datetime.utcnow()
        },
        {
            "user": "admin",
            "type": "warning",
            "title": "Low Confidence Predictions",
            "message": "25 posts classified with confidence below 70%. Review recommended.",
            "link": "/posts?confidence=low",
            "read": False,
            "created_at": datetime.utcnow()
        },
        {
            "user": "admin",
            "type": "error",
            "title": "Twitter API Rate Limit",
            "message": "Twitter fetch paused due to rate limit. Will retry in 15 minutes.",
            "link": None,
            "read": False,
            "created_at": datetime.utcnow()
        },
        {
            "user": "admin",
            "type": "success",
            "title": "Trending Topic Detected",
            "message": "New hot topic: 'Bitcoin Price' with 89 mentions in last hour",
            "link": "/trending",
            "read": True,  # This one is already read
            "created_at": datetime.utcnow()
        }
    ]
    
    # Clear existing test notifications (optional)
    db.notifications.delete_many({"user": "admin"})
    
    # Insert new notifications
    result = db.notifications.insert_many(notifications)
    
    print(f" Created {len(result.inserted_ids)} test notifications:")
    for notif in notifications:
        status = "📖 Read" if notif["read"] else "🔔 Unread"
        print(f"  {status} [{notif['type'].upper()}] {notif['title']}")
    
    # Count unread
    unread_count = db.notifications.count_documents({"user": "admin", "read": False})
    print(f"\n Total unread notifications: {unread_count}")

if __name__ == "__main__":
    create_test_notifications()
