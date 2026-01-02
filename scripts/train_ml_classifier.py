"""Script to train ML topic classifier with real data from MongoDB.
Lấy dữ liệu có label từ DB, train model và save.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.ml_topic_classifier import MLTopicClassifier, TOPIC_LABELS, create_sample_training_data
from src.db.mongo import get_db
from typing import List, Tuple
import argparse


def fetch_labeled_data(limit: int = 10000) -> Tuple[List[str], List[str]]:
    """
    Fetch labeled posts from MongoDB.
    
    Args:
        limit: Maximum number of posts to fetch
        
    Returns:
        Tuple of (texts, labels)
    """
    db = get_db()
    collection = db["posts"]
    
    # Query posts that have topics (labeled data)
    cursor = collection.find(
        {"topics": {"$exists": True, "$ne": []}},
        {"text": 1, "topics": 1}
    ).limit(limit)
    
    texts = []
    labels = []
    
    for doc in cursor:
        text = doc.get("text", "").strip()
        topics = doc.get("topics", [])
        
        if text and topics:
            # Nếu có nhiều topic, lấy topic đầu tiên
            # Hoặc có thể train multi-label classifier
            primary_topic = topics[0]
            
            # Chỉ lấy topic nằm trong TOPIC_LABELS
            if primary_topic in TOPIC_LABELS:
                texts.append(text)
                labels.append(primary_topic)
    
    return texts, labels


def train_from_db(model_path: str = "models/topic_classifier_svm.pkl", 
                  limit: int = 10000,
                  test_size: float = 0.2,
                  use_sample_data: bool = False):
    """
    Train classifier using data from MongoDB.
    
    Args:
        model_path: Path to save trained model
        limit: Maximum training samples
        test_size: Test set proportion
        use_sample_data: If True, use sample data for testing (not recommended for production)
    """
    print("="*60)
    print("Training ML Topic Classifier")
    print("="*60)
    
    # 1. Fetch data
    if use_sample_data:
        print("\n⚠️  Using SAMPLE DATA (only for testing)")
        print("For production, remove --use-sample-data flag\n")
        texts, labels = create_sample_training_data()
        print(f"Loaded {len(texts)} sample training examples")
    else:
        print(f"\nFetching labeled data from MongoDB (limit={limit})...")
        texts, labels = fetch_labeled_data(limit=limit)
        
        if not texts:
            print("\n❌ Không tìm thấy dữ liệu đã label trong database!")
            print("\n📝 Các bước cần làm:")
            print("   1. Thu thập dữ liệu: python -m src.ingestion.telegram_worker --full")
            print("   2. Label dữ liệu bằng rule-based classifier (tự động)")
            print("   3. Hoặc chạy: python scripts/train_ml_classifier.py --use-sample-data (demo)")
            return
    
    print(f"✓ Found {len(texts)} labeled samples")
    
    # Count distribution
    from collections import Counter
    label_counts = Counter(labels)
    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")
    
    # 2. Train
    print("\n" + "="*60)
    print("Training model...")
    print("="*60)
    classifier = MLTopicClassifier(model_path=model_path)
    accuracy = classifier.train(texts, labels, test_size=test_size)
    
    # 3. Save
    print("\nSaving model...")
    classifier.save_model()
    
    print("\n" + "="*60)
    print(f"✓ Training completed! Accuracy: {accuracy:.2%}")
    print(f"✓ Model saved to: {model_path}")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train ML topic classifier with data from MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train với dữ liệu từ DB (KHUYẾN NGHỊ)
  python scripts/train_ml_classifier.py
  
  # Train với nhiều dữ liệu hơn
  python scripts/train_ml_classifier.py --limit 20000
  
  # Train với sample data (chỉ để test)
  python scripts/train_ml_classifier.py --use-sample-data
  
  # Retrain với test size khác
  python scripts/train_ml_classifier.py --test-size 0.3
        """
    )
    parser.add_argument("--model-path", default="models/topic_classifier_svm.pkl",
                       help="Path to save trained model")
    parser.add_argument("--limit", type=int, default=10000,
                       help="Maximum number of training samples from DB")
    parser.add_argument("--test-size", type=float, default=0.2,
                       help="Test set proportion (0.0-1.0)")
    parser.add_argument("--use-sample-data", action="store_true",
                       help="Use sample data instead of DB (only for testing)")
    
    args = parser.parse_args()
    
    train_from_db(
        model_path=args.model_path,
        limit=args.limit,
        test_size=args.test_size,
        use_sample_data=args.use_sample_data
    )
