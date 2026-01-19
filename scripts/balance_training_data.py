"""Balance training data by handling class imbalance.
Cân bằng dữ liệu training để tránh model bị thiên vị.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db
from collections import Counter
from sklearn.utils import resample
import numpy as np
from typing import List, Tuple
import argparse


def fetch_labeled_data_by_topic(limit_per_topic: int = None) -> Tuple[List[str], List[str]]:
    """
    Fetch labeled posts from MongoDB, balanced across topics.
    
    Args:
        limit_per_topic: Maximum samples per topic (None = no limit)
        
    Returns:
        Tuple of (texts, labels)
    """
    db = get_db()
    collection = db["posts"]
    
    # Available topics
    from src.processing.ml_topic_classifier import TOPIC_LABELS
    
    all_texts = []
    all_labels = []
    
    print(f"\n{'='*60}")
    print("Fetching data by topic...")
    print(f"{'='*60}")
    
    for topic in TOPIC_LABELS:
        # Query posts with this topic
        cursor = collection.find(
            {"topics": topic},
            {"text": 1}
        )
        
        texts = []
        for doc in cursor:
            text = doc.get("text", "").strip()
            if text:
                texts.append(text)
                
        if not texts:
            print(f"  {topic}: 0 samples (SKIP)")
            continue
            
        # Limit if specified
        if limit_per_topic and len(texts) > limit_per_topic:
            texts = resample(texts, n_samples=limit_per_topic, random_state=42)
            
        all_texts.extend(texts)
        all_labels.extend([topic] * len(texts))
        
        print(f"✓ {topic}: {len(texts)} samples")
    
    return all_texts, all_labels


def balance_dataset(texts: List[str], labels: List[str], 
                   method: str = 'undersample',
                   target_samples: int = None) -> Tuple[List[str], List[str]]:
    """
    Balance dataset using various methods.
    
    Args:
        texts: Input texts
        labels: Input labels
        method: 'undersample', 'oversample', or 'combined'
        target_samples: Target samples per class (None = auto)
        
    Returns:
        Balanced (texts, labels)
    """
    print(f"\n{'='*60}")
    print(f"Balancing dataset using: {method}")
    print(f"{'='*60}")
    
    # Count original distribution
    label_counts = Counter(labels)
    print("\nOriginal distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")
    
    # Separate by class
    from collections import defaultdict
    class_texts = defaultdict(list)
    for text, label in zip(texts, labels):
        class_texts[label].append(text)
    
    # Determine target size
    if target_samples is None:
        if method == 'undersample':
            # Use minority class size
            target_samples = min(label_counts.values())
        elif method == 'oversample':
            # Use majority class size
            target_samples = max(label_counts.values())
        else:  # combined
            # Use median
            target_samples = int(np.median(list(label_counts.values())))
    
    print(f"\nTarget samples per class: {target_samples}")
    
    # Balance each class
    balanced_texts = []
    balanced_labels = []
    
    for label in class_texts.keys():
        class_samples = class_texts[label]
        n_samples = len(class_samples)
        
        if n_samples > target_samples:
            # Undersample (reduce)
            resampled = resample(class_samples, 
                                n_samples=target_samples, 
                                random_state=42)
        elif n_samples < target_samples:
            # Oversample (duplicate with replacement)
            resampled = resample(class_samples, 
                                n_samples=target_samples, 
                                replace=True,
                                random_state=42)
        else:
            resampled = class_samples
            
        balanced_texts.extend(resampled)
        balanced_labels.extend([label] * len(resampled))
        
        print(f"  {label}: {n_samples} → {len(resampled)}")
    
    # Shuffle
    combined = list(zip(balanced_texts, balanced_labels))
    np.random.seed(42)
    np.random.shuffle(combined)
    balanced_texts, balanced_labels = zip(*combined)
    
    print(f"\n✓ Balanced dataset: {len(balanced_texts)} total samples")
    
    return list(balanced_texts), list(balanced_labels)


def main():
    parser = argparse.ArgumentParser(description="Balance training data")
    parser.add_argument('--method', type=str, default='undersample',
                       choices=['undersample', 'oversample', 'combined'],
                       help='Balancing method')
    parser.add_argument('--limit-per-topic', type=int, default=None,
                       help='Max samples per topic before balancing')
    parser.add_argument('--target-samples', type=int, default=None,
                       help='Target samples per class')
    parser.add_argument('--save', action='store_true',
                       help='Save balanced data to JSON file')
    args = parser.parse_args()
    
    print("="*60)
    print("BALANCE TRAINING DATA")
    print("="*60)
    
    # Fetch data
    texts, labels = fetch_labeled_data_by_topic(limit_per_topic=args.limit_per_topic)
    
    if not texts:
        print("\n No labeled data found!")
        return
    
    # Balance
    balanced_texts, balanced_labels = balance_dataset(
        texts, labels, 
        method=args.method,
        target_samples=args.target_samples
    )
    
    # Show final distribution
    final_counts = Counter(balanced_labels)
    print("\nFinal balanced distribution:")
    for label, count in sorted(final_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(balanced_labels)*100:.1f}%)")
    
    # Save if requested
    if args.save:
        import json
        output_file = "models/balanced_training_data.json"
        data = [{"text": t, "label": l} for t, l in zip(balanced_texts, balanced_labels)]
        
        Path(output_file).parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Saved balanced data to: {output_file}")
        print(f"  Use: python scripts/train_ml_classifier.py --from-file {output_file}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Train with balanced data:")
    print(f"   python scripts/train_ml_classifier.py --balanced --method {args.method}")
    print("\n2. Or improve data collection:")
    print("   - Add more diverse Telegram channels (tech, health, education, etc.)")
    print("   - Add Twitter sources with diverse topics")
    print("   - Use fetch with --full to collect more data")
    print("\n3. Review and improve rule-based keywords:")
    print("   - Check src/processing/topic_classifier.py")
    print("   - Add more specific keywords for minority topics")
    print("="*60)


if __name__ == "__main__":
    main()
