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


def fetch_labeled_data(limit: int = 10000, verified_only: bool = False) -> Tuple[List[str], List[str], dict]:
    """
    Fetch labeled posts from MongoDB.
    
    ⚠️  WARNING: Training data quality is critical!
    
    Args:
        limit: Maximum number of posts to fetch
        verified_only: If True, only fetch manually verified labels (RECOMMENDED)
        
    Returns:
        Tuple of (texts, labels, metadata)
        - texts: List of post texts
        - labels: List of topic labels
        - metadata: Dict with data quality info
    """
    db = get_db()
    collection = db["posts"]
    
    texts = []
    labels = []
    metadata = {
        "verified_count": 0,
        "pseudo_label_count": 0,
        "total_count": 0,
        "verified_only": verified_only
    }
    
    # Strategy 1: Try to get verified labels first (GROUND TRUTH)
    if verified_only:
        print("\n🎯 Fetching VERIFIED labels only (ground truth)...")
        cursor = collection.find(
            {
                "labels_verified": True,
                "manual_labels": {"$exists": True, "$ne": []}
            },
            {"text": 1, "manual_labels": 1}
        ).limit(limit)
        
        for doc in cursor:
            text = doc.get("text", "").strip()
            manual_labels = doc.get("manual_labels", [])
            
            if text and manual_labels:
                primary_label = manual_labels[0]
                if primary_label in TOPIC_LABELS:
                    texts.append(text)
                    labels.append(primary_label)
                    metadata["verified_count"] += 1
    
    # Strategy 2: Fallback to pseudo-labels from rule-based/ML (NOT IDEAL)
    if not verified_only or len(texts) < 100:
        remaining_limit = limit - len(texts)
        print(f"\n⚠️  Fetching PSEUDO-LABELS from rule-based/ML predictions...")
        print(f"   (These are NOT manually verified - may contain errors!)")
        
        cursor = collection.find(
            {
                "$or": [
                    {"topics": {"$exists": True, "$ne": []}},
                    {"topic_predictions": {"$exists": True, "$ne": []}}
                ],
                "labels_verified": {"$ne": True}  # Exclude already verified
            },
            {"text": 1, "topics": 1, "topic_predictions": 1, "manual_labels": 1}
        ).limit(remaining_limit)
        
        for doc in cursor:
            text = doc.get("text", "").strip()
            
            # Try manual_labels first (even if not verified)
            label = None
            manual_labels = doc.get("manual_labels", [])
            if manual_labels and manual_labels[0] in TOPIC_LABELS:
                label = manual_labels[0]
            
            # Fallback to topics (rule-based)
            if not label:
                topics = doc.get("topics", [])
                if topics and topics[0] in TOPIC_LABELS:
                    label = topics[0]
            
            # Last resort: topic_predictions (ML)
            if not label:
                predictions = doc.get("topic_predictions", [])
                if predictions:
                    # Get highest confidence prediction
                    best_pred = max(predictions, key=lambda p: p.get("confidence", 0))
                    topic = best_pred.get("topic")
                    if topic in TOPIC_LABELS:
                        label = topic
            
            if label:
                texts.append(text)
                labels.append(label)
                metadata["pseudo_label_count"] += 1
    
    metadata["total_count"] = len(texts)
    return texts, labels, metadata


def train_from_db(model_path: str = "models/topic_classifier_svm.pkl", 
                  limit: int = 10000,
                  test_size: float = 0.2,
                  use_sample_data: bool = False,
                  balanced: bool = False,
                  balance_method: str = 'undersample',
                  target_samples: int = None,
                  verified_only: bool = False):
    """
    Train classifier using data from MongoDB.
    
    ⚠️  IMPORTANT: Training data quality is CRITICAL for model performance!
    
    Pseudo-labels (from rule-based/old ML) are NOT ground truth and may contain errors.
    For production, use manually verified labels (--verified-only flag).
    
    Args:
        model_path: Path to save trained model
        limit: Maximum training samples
        test_size: Test set proportion
        use_sample_data: If True, use sample data for testing (not recommended for production)
        balanced: If True, balance dataset to fix class imbalance
        balance_method: Method to balance ('undersample', 'oversample', 'combined')
        target_samples: Target samples per class for balancing
        verified_only: If True, only use manually verified labels (RECOMMENDED)
    """
    print("="*60)
    print("Training ML Topic Classifier")
    print("="*60)
    
    # 1. Fetch data
    metadata = {"verified_count": 0, "pseudo_label_count": 0, "total_count": 0}
    
    if use_sample_data:
        print("\n⚠️  Using SAMPLE DATA (only for testing)")
        print("For production, remove --use-sample-data flag\n")
        texts, labels = create_sample_training_data()
        print(f"Loaded {len(texts)} sample training examples")
        metadata["total_count"] = len(texts)
    else:
        print(f"\n{'='*60}")
        print("DATA COLLECTION")
        print(f"{'='*60}")
        print(f"Fetching labeled data from MongoDB (limit={limit})...")
        
        # Try verified_only first, fallback if not enough
        verified_only = False  # Can be changed via command line
        texts, labels, metadata = fetch_labeled_data(limit=limit, verified_only=verified_only)
        
        if not texts:
            print("\n❌ Không tìm thấy dữ liệu đã label trong database!")
            print("\n📝 Các bước cần làm:")
            print("   1. Thu thập dữ liệu: python -m src.ingestion.telegram_worker --full")
            print("   2. Label dữ liệu bằng rule-based classifier (tự động)")
            print("   3. ⚠️  RECOMMENDED: Verify labels manually for high quality training")
            print("   4. Hoặc chạy: python scripts/train_ml_classifier.py --use-sample-data (demo)")
            return
    
    print(f"\n{'='*60}")
    print("DATA QUALITY REPORT")
    print(f"{'='*60}")
    print(f"Total samples: {metadata['total_count']}")
    print(f"Verified labels (ground truth): {metadata['verified_count']} ({metadata['verified_count']/max(metadata['total_count'],1)*100:.1f}%)")
    print(f"Pseudo-labels (auto-generated): {metadata['pseudo_label_count']} ({metadata['pseudo_label_count']/max(metadata['total_count'],1)*100:.1f}%)")
    
    # Show warning if using mostly pseudo-labels
    if metadata['pseudo_label_count'] > metadata['verified_count'] * 5:
        print(f"\n⚠️  ⚠️  ⚠️  CRITICAL WARNING ⚠️  ⚠️  ⚠️")
        print(f"Training data contains mostly PSEUDO-LABELS (not verified)!")
        print(f"This may result in:")
        print(f"  - Model learning from noisy/incorrect labels")
        print(f"  - Poor generalization to real data")
        print(f"  - Propagating errors from rule-based classifier")
        print(f"\n💡 RECOMMENDATION:")
        print(f"  1. Create manual labeling tool in dashboard")
        print(f"  2. Manually verify at least 500-1000 samples")
        print(f"  3. Retrain with verified data only")
        print(f"  4. Use --verified-only flag for high-quality training")
    elif metadata['verified_count'] > 0:
        print(f"\n✅ Good! Using some verified labels.")
        print(f"💡 TIP: More verified labels = better model quality")
    
    print(f"{'='*60}\n")
    
    # Count distribution
    from collections import Counter
    label_counts = Counter(labels)
    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")
    
    # Check for severe imbalance
    if not use_sample_data:
        max_count = max(label_counts.values())
        min_count = min(label_counts.values()) if min(label_counts.values()) > 0 else 1
        imbalance_ratio = max_count / min_count
        
        if imbalance_ratio > 10:
            print(f"\n⚠️  WARNING: Severe class imbalance detected!")
            print(f"   Imbalance ratio: {imbalance_ratio:.1f}:1")
            print(f"   Most common: {max(label_counts, key=label_counts.get)} ({max_count} samples)")
            print(f"   Least common: {min(label_counts, key=label_counts.get)} ({min_count} samples)")
            
            if not balanced:
                print(f"\n💡 RECOMMENDATION: Use --balanced flag to fix this:")
                print(f"   python scripts/train_ml_classifier.py --balanced --method undersample")
                print(f"\n   Or run: python scripts/balance_training_data.py")
    
    # Balance dataset if requested
    if balanced and not use_sample_data:
        print(f"\n{'='*60}")
        print(f"Balancing dataset using: {balance_method}")
        print(f"{'='*60}")
        
        from sklearn.utils import resample
        import numpy as np
        
        # Separate by class
        from collections import defaultdict
        class_texts = defaultdict(list)
        for text, label in zip(texts, labels):
            class_texts[label].append(text)
        
        # Determine target size
        if target_samples is None:
            if balance_method == 'undersample':
                target_samples = min(label_counts.values())
            elif balance_method == 'oversample':
                target_samples = max(label_counts.values())
            else:  # combined
                target_samples = int(np.median(list(label_counts.values())))
        
        print(f"Target samples per class: {target_samples}")
        
        # Balance each class
        balanced_texts = []
        balanced_labels = []
        
        for label in class_texts.keys():
            class_samples = class_texts[label]
            n_samples = len(class_samples)
            
            if n_samples > target_samples:
                resampled = resample(class_samples, n_samples=target_samples, random_state=42)
            elif n_samples < target_samples:
                resampled = resample(class_samples, n_samples=target_samples, replace=True, random_state=42)
            else:
                resampled = class_samples
                
            balanced_texts.extend(resampled)
            balanced_labels.extend([label] * len(resampled))
            
            print(f"  {label}: {n_samples} → {len(resampled)}")
        
        # Shuffle
        combined = list(zip(balanced_texts, balanced_labels))
        np.random.seed(42)
        np.random.shuffle(combined)
        texts, labels = zip(*combined)
        texts, labels = list(texts), list(labels)
        
        print(f"\n✓ Balanced dataset: {len(texts)} total samples")
        
        # Show new distribution
        balanced_counts = Counter(labels)
        print("\nBalanced distribution:")
        for label, count in sorted(balanced_counts.items(), key=lambda x: -x[1]):
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
    parser.add_argument("--balanced", action="store_true",
                       help="Balance dataset to fix class imbalance")
    parser.add_argument("--method", type=str, default='undersample',
                       choices=['undersample', 'oversample', 'combined'],
                       help="Balancing method (default: undersample)")
    parser.add_argument("--target-samples", type=int, default=None,
                       help="Target samples per class for balancing")
    parser.add_argument("--verified-only", action="store_true",
                       help="Use only manually verified labels (RECOMMENDED for production)")
    
    args = parser.parse_args()
    
    train_from_db(
        model_path=args.model_path,
        limit=args.limit,
        test_size=args.test_size,
        use_sample_data=args.use_sample_data,
        balanced=args.balanced,
        balance_method=args.method,
        target_samples=args.target_samples,
        verified_only=args.verified_only
    )
