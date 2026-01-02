"""Script to predict topics for existing posts in MongoDB.
Chạy ML classifier cho các bài viết chưa có topic.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.ml_topic_classifier import MLTopicClassifier
from src.db.mongo import get_db
import argparse
from tqdm import tqdm


def predict_for_unlabeled_posts(model_path: str = "models/topic_classifier_svm.pkl",
                                 batch_size: int = 100,
                                 confidence_threshold: float = 0.3,
                                 force: bool = False):
    """
    Predict topics for posts that don't have topics yet.
    
    Args:
        model_path: Path to trained model
        batch_size: Number of posts to process in each batch
        confidence_threshold: Minimum confidence to save prediction
        force: If True, overwrite existing topics
    """
    print("="*60)
    print("Predicting Topics for Unlabeled Posts")
    print("="*60)
    
    # Load model
    print(f"\nLoading model from: {model_path}")
    try:
        classifier = MLTopicClassifier(model_path=model_path)
    except FileNotFoundError:
        print(f"❌ Model not found: {model_path}")
        print("Train model first: python scripts/train_ml_classifier.py")
        return
    
    # Get DB
    db = get_db()
    collection = db["posts"]
    
    # Query posts without topics
    query = {"topics": {"$exists": False}} if not force else {}
    if not force:
        # Also include posts with empty topics array
        query = {"$or": [
            {"topics": {"$exists": False}},
            {"topics": []},
            {"topics": None}
        ]}
    
    total = collection.count_documents(query)
    print(f"\nFound {total} posts to process")
    
    if total == 0:
        print("No posts to process. Done!")
        return
    
    # Process in batches
    processed = 0
    updated = 0
    skipped = 0
    
    cursor = collection.find(query, {"_id": 1, "id": 1, "text": 1})
    
    batch = []
    pbar = tqdm(cursor, total=total, desc="Processing")
    
    for doc in pbar:
        text = doc.get("text", "").strip()
        
        if not text:
            skipped += 1
            continue
        
        batch.append(doc)
        
        # Process batch
        if len(batch) >= batch_size:
            updated += process_batch(collection, classifier, batch, confidence_threshold)
            processed += len(batch)
            batch = []
            pbar.set_postfix({"updated": updated, "skipped": skipped})
    
    # Process remaining
    if batch:
        updated += process_batch(collection, classifier, batch, confidence_threshold)
        processed += len(batch)
    
    print("\n" + "="*60)
    print(f"✓ Completed!")
    print(f"  Processed: {processed}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print("="*60)


def process_batch(collection, classifier, batch, confidence_threshold):
    """Process a batch of documents."""
    texts = [doc.get("text", "") for doc in batch]
    
    try:
        predictions = classifier.predict_batch(texts)
    except Exception as e:
        print(f"\n⚠️  Batch prediction error: {e}")
        return 0
    
    updated_count = 0
    for doc, (topic, confidence) in zip(batch, predictions):
        if confidence >= confidence_threshold:
            # Update document
            collection.update_one(
                {"id": doc["id"]},
                {
                    "$set": {
                        "topics": [topic],
                        "score": confidence
                    }
                }
            )
            updated_count += 1
    
    return updated_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict topics for unlabeled posts")
    parser.add_argument("--model-path", default="models/topic_classifier_svm.pkl",
                       help="Path to trained model")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for processing")
    parser.add_argument("--confidence-threshold", type=float, default=0.3,
                       help="Minimum confidence to save prediction (0.0-1.0)")
    parser.add_argument("--force", action="store_true",
                       help="Overwrite existing topics")
    
    args = parser.parse_args()
    
    predict_for_unlabeled_posts(
        model_path=args.model_path,
        batch_size=args.batch_size,
        confidence_threshold=args.confidence_threshold,
        force=args.force
    )
