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
    
      WARNING: Training data quality is critical!
    
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
        "source_topic_count": 0,  # Ground truth from news URLs
        "verified_count": 0,       # Manually verified
        "pseudo_label_count": 0,   # Auto-generated (lowest quality)
        "total_count": 0,
        "verified_only": verified_only
    }
    
    # Strategy 1: Get source_topic from news URLs (BEST - Ground truth from news sites)
    print("\n🎯 Fetching GROUND TRUTH from news URLs (source_topic)...")
    cursor = collection.find(
        {
            "source_topic": {"$exists": True, "$ne": None},
            "text": {"$exists": True, "$ne": ""}
        },
        {"text": 1, "source_topic": 1}
    ).limit(limit)
    
    for doc in cursor:
        text = doc.get("text", "").strip()
        source_topic = doc.get("source_topic")
        
        if text and source_topic and source_topic in TOPIC_LABELS:
            texts.append(text)
            labels.append(source_topic)
            metadata["source_topic_count"] += 1
    
    print(f"   ✅ Found {metadata['source_topic_count']} posts with ground truth from news URLs")
    
    # Strategy 2: Try to get verified labels (GOOD - Manual verification)
    if not verified_only and len(texts) < limit:
        remaining = limit - len(texts)
        print(f"\n✓ Fetching MANUALLY VERIFIED labels...")
        cursor = collection.find(
            {
                "labels_verified": True,
                "manual_labels": {"$exists": True, "$ne": []},
                "source_topic": {"$exists": False}  # Don't duplicate source_topic entries
            },
            {"text": 1, "manual_labels": 1}
        ).limit(remaining)
        
        for doc in cursor:
            text = doc.get("text", "").strip()
            manual_labels = doc.get("manual_labels", [])
            
            if text and manual_labels:
                primary_label = manual_labels[0]
                if primary_label in TOPIC_LABELS:
                    texts.append(text)
                    labels.append(primary_label)
                    metadata["verified_count"] += 1
        
        print(f"   ✅ Found {metadata['verified_count']} manually verified posts")
    
    # Strategy 3: Fallback to pseudo-labels from rule-based/ML (NOT IDEAL - May contain errors)
    if not verified_only and len(texts) < limit:
        remaining_limit = limit - len(texts)
        print(f"\n⚠️  Fetching PSEUDO-LABELS from auto-classification...")
        print(f"   (These may contain errors - lowest quality!)")
        
        cursor = collection.find(
            {
                "$or": [
                    {"topics": {"$exists": True, "$ne": []}},
                    {"topic_predictions": {"$exists": True, "$ne": []}}
                ],
                "labels_verified": {"$ne": True},
                "source_topic": {"$exists": False}  # Don't duplicate
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
    
      IMPORTANT: Training data quality is CRITICAL for model performance!
    
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
        print("\n  Using SAMPLE DATA (only for testing)")
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
            print("\n Không tìm thấy dữ liệu đã label trong database!")
            print("\n Các bước cần làm:")
            print("   1. Thu thập dữ liệu: python -m src.ingestion.telegram_worker --full")
            print("   2. Label dữ liệu bằng rule-based classifier (tự động)")
            print("   3.   RECOMMENDED: Verify labels manually for high quality training")
            print("   4. Hoặc chạy: python scripts/train_ml_classifier.py --use-sample-data (demo)")
            return
    
    print(f"\n{'='*60}")
    print("DATA QUALITY REPORT")
    print(f"{'='*60}")
    print(f"Total samples: {metadata['total_count']}")
    print(f"🎯 Ground truth from news URLs: {metadata['source_topic_count']} ({metadata['source_topic_count']/max(metadata['total_count'],1)*100:.1f}%)")
    print(f"✅ Manually verified labels: {metadata['verified_count']} ({metadata['verified_count']/max(metadata['total_count'],1)*100:.1f}%)")
    print(f"⚠️  Pseudo-labels (auto-generated): {metadata['pseudo_label_count']} ({metadata['pseudo_label_count']/max(metadata['total_count'],1)*100:.1f}%)")
    
    high_quality_count = metadata['source_topic_count'] + metadata['verified_count']
    high_quality_pct = high_quality_count / max(metadata['total_count'], 1) * 100
    
    print(f"\n📊 High-quality labels (ground truth + verified): {high_quality_count} ({high_quality_pct:.1f}%)")
    
    # Show warning if using mostly pseudo-labels
    if metadata['pseudo_label_count'] > high_quality_count:
        print(f"\n⚠️  WARNING: Training data quality is LOW")
        print(f"   Most labels are auto-generated (may contain errors)")
        print(f"\n💡 RECOMMENDED ACTIONS:")
        print(f"   1. Extract categories from news URLs:")
        print(f"      python scripts\\extract_categories_from_urls.py --apply")
        print(f"   2. Manually verify important samples in dashboard")
        print(f"   3. Retrain with higher quality data")
    elif high_quality_pct >= 80:
        print(f"\n✅ EXCELLENT! Training with high-quality ground truth data!")
    elif high_quality_pct >= 50:
        print(f"\n✓ GOOD! Majority of data is from reliable sources")
    else:
        print(f"\n⚠️  Consider improving data quality (current: {high_quality_pct:.1f}% high-quality)")
    
    print(f"{'='*60}\n")
    
    # Count distribution
    from collections import Counter
    label_counts = Counter(labels)
    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")

    # ── Auto-inject sample data for topics with insufficient samples ──────────
    MIN_SAMPLES_PER_TOPIC = 10
    if not use_sample_data:
        sample_texts_all, sample_labels_all = create_sample_training_data()
        sample_by_topic: dict = {}
        for st, sl in zip(sample_texts_all, sample_labels_all):
            sample_by_topic.setdefault(sl, []).append(st)

        injected: dict = {}
        for topic in TOPIC_LABELS:
            current_count = label_counts.get(topic, 0)
            if current_count < MIN_SAMPLES_PER_TOPIC and topic in sample_by_topic:
                samples_to_add = sample_by_topic[topic]
                texts.extend(samples_to_add)
                labels.extend([topic] * len(samples_to_add))
                injected[topic] = (current_count, current_count + len(samples_to_add))

        if injected:
            print(f"\n💉 Auto-injected sample data for topics with < {MIN_SAMPLES_PER_TOPIC} samples:")
            for topic, (before, after) in injected.items():
                print(f"  {topic}: {before} → {after} samples")
            label_counts = Counter(labels)  # recompute after injection

    # ── Auto-enable balanced when imbalance is severe ─────────────────────────
    if not use_sample_data and len(label_counts) > 0:
        max_count = max(label_counts.values())
        min_count = min(label_counts.values()) if min(label_counts.values()) > 0 else 1
        imbalance_ratio = max_count / min_count

        if imbalance_ratio > 10:
            print(f"\n⚠️  Severe class imbalance detected!")
            print(f"   Imbalance ratio: {imbalance_ratio:.1f}:1")
            print(f"   Most common: {max(label_counts, key=label_counts.get)} ({max_count} samples)")
            print(f"   Least common: {min(label_counts, key=label_counts.get)} ({min_count} samples)")

            if not balanced:
                balanced = True
                balance_method = 'oversample'
                print(f"   → Auto-enabling balanced training (oversample) to fix this.")
    else:
        imbalance_ratio = 1  # no check needed for sample data
    
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
