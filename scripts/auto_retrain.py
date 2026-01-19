"""Script to automatically retrain ML model when new data is available.
Tự động retrain model khi có dữ liệu mới.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.ml_topic_classifier import MLTopicClassifier
from src.db.mongo import get_db
from datetime import datetime, timedelta
import argparse


def check_new_data_available(hours: int = 24) -> tuple[bool, int]:
    """
    Check if new labeled data is available since last train.
    
    Args:
        hours: Check for data in last N hours
        
    Returns:
        Tuple of (has_new_data, new_count)
    """
    db = get_db()
    collection = db["posts"]
    
    # Check posts from last N hours with topics
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    new_count = collection.count_documents({
        "topics": {"$exists": True, "$ne": []},
        "fetched_at": {"$gte": cutoff_time}
    })
    
    return new_count > 0, new_count


def get_model_last_modified() -> datetime | None:
    """Get last modified time of model file."""
    model_path = Path("models/topic_classifier_svm.pkl")
    if model_path.exists():
        timestamp = model_path.stat().st_mtime
        return datetime.fromtimestamp(timestamp)
    return None


def should_retrain(min_new_samples: int = 100, hours_since_last: int = 24) -> tuple[bool, str]:
    """
    Determine if model should be retrained.
    
    Args:
        min_new_samples: Minimum new samples to trigger retrain
        hours_since_last: Hours since last check
        
    Returns:
        Tuple of (should_retrain, reason)
    """
    # Check if model exists
    model_path = Path("models/topic_classifier_svm.pkl")
    if not model_path.exists():
        return True, "Model doesn't exist - initial training required"
    
    # Check model age
    last_modified = get_model_last_modified()
    if last_modified:
        age_hours = (datetime.now() - last_modified).total_seconds() / 3600
        if age_hours > hours_since_last:
            # Check for new data
            has_new, new_count = check_new_data_available(hours=int(age_hours))
            if has_new and new_count >= min_new_samples:
                return True, f"Found {new_count} new labeled samples (minimum: {min_new_samples})"
    
    return False, "No retrain needed"


def auto_retrain(min_new_samples: int = 100,
                 hours_since_last: int = 24,
                 force: bool = False,
                 limit: int = 10000):
    """
    Automatically retrain model if needed.
    
    Args:
        min_new_samples: Minimum new samples to trigger retrain
        hours_since_last: Check for data in last N hours
        force: Force retrain regardless of conditions
        limit: Maximum training samples
    """
    print("="*60)
    print("Auto Retrain ML Topic Classifier")
    print("="*60)
    
    if force:
        print("\n FORCE RETRAIN mode enabled")
        should_train = True
        reason = "Forced retrain by user"
    else:
        should_train, reason = should_retrain(min_new_samples, hours_since_last)
    
    print(f"\nChecking retrain conditions...")
    print(f"  Minimum new samples: {min_new_samples}")
    print(f"  Hours since last train: {hours_since_last}")
    
    model_last_modified = get_model_last_modified()
    if model_last_modified:
        print(f"  Current model age: {(datetime.now() - model_last_modified).total_seconds() / 3600:.1f} hours")
    
    if should_train:
        print(f"\n Retraining: {reason}")
        
        # Import and run training
        from scripts.train_ml_classifier import train_from_db
        
        train_from_db(
            model_path="models/topic_classifier_svm.pkl",
            limit=limit,
            test_size=0.2,
            use_sample_data=False
        )
        
        print("\n" + "="*60)
        print("✓ Retrain completed successfully!")
        print("="*60)
    else:
        print(f"\n  Skipping: {reason}")
        print("\nTo force retrain, use: --force")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automatically retrain ML model when new data is available",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check and retrain if needed
  python scripts/auto_retrain.py
  
  # Force retrain regardless of conditions
  python scripts/auto_retrain.py --force
  
  # Custom thresholds
  python scripts/auto_retrain.py --min-samples 200 --hours 48
  
  # With more training data
  python scripts/auto_retrain.py --limit 20000

Typical usage:
  - Run this script daily via cron/scheduler
  - Set min-samples based on your data collection rate
  - Use --force after major data collection campaigns
        """
    )
    parser.add_argument("--min-samples", type=int, default=100,
                       help="Minimum new samples to trigger retrain (default: 100)")
    parser.add_argument("--hours", type=int, default=24,
                       help="Check for new data in last N hours (default: 24)")
    parser.add_argument("--limit", type=int, default=10000,
                       help="Maximum training samples (default: 10000)")
    parser.add_argument("--force", action="store_true",
                       help="Force retrain regardless of conditions")
    
    args = parser.parse_args()
    
    auto_retrain(
        min_new_samples=args.min_samples,
        hours_since_last=args.hours,
        force=args.force,
        limit=args.limit
    )
