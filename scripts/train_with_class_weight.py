"""Train ML classifier with class_weight='balanced' (RECOMMENDED).
Train với toàn bộ dữ liệu, SVM tự động cân bằng class weights.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.ml_topic_classifier import MLTopicClassifier, TOPIC_LABELS
from src.db.mongo import get_db
from typing import List, Tuple
from collections import Counter


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
            primary_topic = topics[0]
            
            if primary_topic in TOPIC_LABELS:
                texts.append(text)
                labels.append(primary_topic)
    
    return texts, labels


def main():
    print("="*80)
    print("TRAIN ML CLASSIFIER WITH CLASS_WEIGHT='BALANCED'")
    print("="*80)
    print("\n Phương pháp này:")
    print("    Giữ TOÀN BỘ 10,000 mẫu (không bỏ dữ liệu)")
    print("    SVM tự động cân bằng class weights")
    print("    Class nhỏ được coi trọng hơn trong training")
    print("    Model vẫn học được ngôn ngữ từ class lớn")
    print("    KHÔNG bị overfitting như oversample")
    print("    KHÔNG mất data như undersample\n")
    
    # Fetch data
    print(f"Fetching labeled data from MongoDB (limit=10000)...")
    texts, labels = fetch_labeled_data(limit=10000)
    
    if not texts:
        print("\n Không tìm thấy dữ liệu đã label trong database!")
        print("\n Các bước cần làm:")
        print("   1. Thu thập dữ liệu: scripts\\fetch_telegram.cmd --full")
        print("   2. Label dữ liệu bằng rule-based classifier (tự động)")
        return
    
    print(f"✓ Found {len(texts)} labeled samples\n")
    
    # Show distribution
    label_counts = Counter(labels)
    print("="*80)
    print("LABEL DISTRIBUTION (BEFORE TRAINING)")
    print("="*80)
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count:,} ({count/len(labels)*100:.1f}%)")
    
    # Check imbalance
    max_count = max(label_counts.values())
    min_count = min(label_counts.values()) if min(label_counts.values()) > 0 else 1
    imbalance_ratio = max_count / min_count
    
    print(f"\n Imbalance ratio: {imbalance_ratio:.1f}:1")
    print(f"   Most common: {max(label_counts, key=label_counts.get)} ({max_count:,} samples)")
    print(f"   Least common: {min(label_counts, key=label_counts.get)} ({min_count:,} samples)")
    
    if imbalance_ratio > 10:
        print(f"\n  SEVERE CLASS IMBALANCE DETECTED!")
        print(f"    Đang dùng class_weight='balanced' để xử lý")
        print(f"    SVM sẽ tự động tăng weight cho class nhỏ")
    
    # Train
    print("\n" + "="*80)
    print("TRAINING MODEL WITH class_weight='balanced'")
    print("="*80)
    
    model_path = "models/topic_classifier_svm.pkl"
    classifier = MLTopicClassifier(model_path=model_path)
    
    accuracy = classifier.train(texts, labels, test_size=0.2)
    
    # Save
    print("\n" + "="*80)
    print("SAVING MODEL")
    print("="*80)
    classifier.save_model()
    print(f"✓ Model saved to: {model_path}")
    
    # Summary
    print("\n" + "="*80)
    print("TRAINING COMPLETED")
    print("="*80)
    print(f" Accuracy: {accuracy:.2%}")
    print(f" Trained on: {len(texts):,} samples")
    print(f" Class weight: balanced (automatic)")
    print(f" Model saved: {model_path}")
    
    print("\n GIẢI THÍCH:")
    print("   - Accuracy có thể thấp hơn undersample (OK)")
    print("   - Nhưng model học được TẤT CẢ dữ liệu")
    print("   - Class nhỏ được coi trọng hơn tự động")
    print("   - Không bị mất 90% data như undersample")
    print("   - TỐT HƠN cho production!")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
