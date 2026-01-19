"""Simple CLI tool for manual label verification.
Tool đơn giản để verify/correct labels thủ công.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db
from src.processing.ml_topic_classifier import TOPIC_LABELS
from typing import Optional
import argparse


def verify_labels_interactive(limit: int = 50, username: str = "admin"):
    """
    Interactive label verification tool.
    
    Args:
        limit: Number of posts to verify
        username: Username for verification tracking
    """
    db = get_db()
    collection = db["posts"]
    
    print("="*60)
    print("MANUAL LABEL VERIFICATION TOOL")
    print("="*60)
    print(f"\nUsername: {username}")
    print(f"Posts to verify: {limit}")
    print(f"\nAvailable topics: {', '.join(TOPIC_LABELS)}")
    print("\nCommands:")
    print("  1-10: Select topic by number")
    print("  s: Skip this post")
    print("  q: Quit")
    print("="*60)
    
    # Get unverified posts
    cursor = collection.find(
        {
            "labels_verified": {"$ne": True},
            "$or": [
                {"topics": {"$exists": True, "$ne": []}},
                {"topic_predictions": {"$exists": True, "$ne": []}}
            ]
        },
        {
            "text": 1, 
            "topics": 1, 
            "topic_predictions": 1,
            "platform": 1,
            "source": 1
        }
    ).limit(limit)
    
    verified_count = 0
    skipped_count = 0
    
    for i, doc in enumerate(cursor, 1):
        print(f"\n{'='*60}")
        print(f"Post {i}/{limit}")
        print(f"{'='*60}")
        print(f"Platform: {doc.get('platform', 'unknown')}")
        print(f"Source: {doc.get('source', 'unknown')}")
        
        # Show text
        text = doc.get("text", "")
        if len(text) > 300:
            text = text[:300] + "..."
        print(f"\nText: {text}")
        
        # Show current labels
        current_topics = doc.get("topics", [])
        predictions = doc.get("topic_predictions", [])
        
        print(f"\nCurrent labels:")
        if current_topics:
            print(f"  Rule-based: {', '.join(current_topics)}")
        if predictions:
            best_pred = max(predictions, key=lambda p: p.get("confidence", 0))
            print(f"  ML prediction: {best_pred.get('topic')} (confidence: {best_pred.get('confidence', 0):.2%})")
        
        # Show topic options
        print(f"\nSelect correct topic:")
        for idx, topic in enumerate(TOPIC_LABELS, 1):
            print(f"  {idx}. {topic}")
        
        # Get user input
        while True:
            choice = input(f"\nYour choice (1-{len(TOPIC_LABELS)}/s/q): ").strip().lower()
            
            if choice == 'q':
                print(f"\n\nVerification summary:")
                print(f"  Verified: {verified_count}")
                print(f"  Skipped: {skipped_count}")
                return
            
            if choice == 's':
                skipped_count += 1
                break
            
            try:
                choice_idx = int(choice)
                if 1 <= choice_idx <= len(TOPIC_LABELS):
                    selected_topic = TOPIC_LABELS[choice_idx - 1]
                    
                    # Update in DB
                    from datetime import datetime, UTC
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "manual_labels": [selected_topic],
                                "labels_verified": True,
                                "verified_by": username,
                                "verified_at": datetime.now(UTC)
                            }
                        }
                    )
                    
                    verified_count += 1
                    print(f"✓ Verified as: {selected_topic}")
                    break
                else:
                    print(f"Invalid choice. Please enter 1-{len(TOPIC_LABELS)}, s, or q")
            except ValueError:
                print(f"Invalid input. Please enter a number, s, or q")
    
    print(f"\n\n{'='*60}")
    print("VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f"Verified: {verified_count}/{limit}")
    print(f"Skipped: {skipped_count}/{limit}")
    print(f"\nYou can now train with verified data:")
    print(f"  python scripts/train_ml_classifier.py --verified-only")


def show_verification_stats():
    """Show statistics about verified vs unverified data."""
    db = get_db()
    collection = db["posts"]
    
    total = collection.count_documents({})
    verified = collection.count_documents({"labels_verified": True})
    unverified = total - verified
    
    print("="*60)
    print("LABEL VERIFICATION STATISTICS")
    print("="*60)
    print(f"Total posts: {total}")
    print(f"Verified: {verified} ({verified/max(total,1)*100:.1f}%)")
    print(f"Unverified: {unverified} ({unverified/max(total,1)*100:.1f}%)")
    
    if verified > 0:
        print(f"\nVerified posts by topic:")
        pipeline = [
            {"$match": {"labels_verified": True}},
            {"$unwind": "$manual_labels"},
            {"$group": {"_id": "$manual_labels", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        for result in collection.aggregate(pipeline):
            topic = result["_id"]
            count = result["count"]
            print(f"  {topic}: {count}")
    
    print("="*60)
    
    if verified < 500:
        print(f"\n RECOMMENDATION:")
        print(f"   Verify at least 500 samples for reliable training")
        print(f"   Currently: {verified}/500")
        print(f"\n   Run: python scripts/verify_labels.py --limit 500")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manual label verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show verification statistics
  python scripts/verify_labels.py --stats
  
  # Verify 50 posts
  python scripts/verify_labels.py --limit 50
  
  # Verify with custom username
  python scripts/verify_labels.py --limit 100 --username john
        """
    )
    parser.add_argument("--stats", action="store_true",
                       help="Show verification statistics only")
    parser.add_argument("--limit", type=int, default=50,
                       help="Number of posts to verify (default: 50)")
    parser.add_argument("--username", type=str, default="admin",
                       help="Username for tracking (default: admin)")
    
    args = parser.parse_args()
    
    if args.stats:
        show_verification_stats()
    else:
        verify_labels_interactive(limit=args.limit, username=args.username)
