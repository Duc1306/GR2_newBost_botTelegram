"""
Database Migration Script
Migrate existing schema to support multi-platform + topic predictions.
"""
import sys
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db
from pymongo import UpdateOne

def create_indexes():
    """Create all required indexes."""
    print("\n" + "=" * 60)
    print("Creating Indexes")
    print("=" * 60)
    
    db = get_db()
    
    # ========== POSTS COLLECTION ==========
    posts = db["posts"]
    print("\n posts collection:")
    
    # Unique constraint - content-based deduplication
    # NOTE: Removed (platform, source, source_id) unique index because:
    # - Old posts use id="telegram:3195" (source includes platform)
    # - New posts use id="telegram:channel:3195" (explicit platform field)
    # - This causes conflicts. Use dedupe_key only for uniqueness.
    
    try:
        posts.create_index(
            [("dedupe_key", 1)],
            unique=True,
            name="idx_dedupe_key_unique"
        )
        print("   idx_dedupe_key_unique (content-based deduplication)")
    except Exception as e:
        print(f"    idx_dedupe_key_unique already exists: {e}")
    
    # Composite index for querying (non-unique)
    posts.create_index(
        [("platform", 1), ("source", 1), ("source_id", 1)],
        name="idx_platform_source_id"
    )
    print("   idx_platform_source_id (query index, non-unique)")
    
    # Query indexes
    posts.create_index([("platform", 1), ("created_at", -1)], name="idx_platform_created")
    print("   idx_platform_created")
    
    posts.create_index([("topics", 1), ("created_at", -1)], name="idx_topics_created")
    print("   idx_topics_created")
    
    posts.create_index([("topic_predictions.topic", 1), ("created_at", -1)], name="idx_topic_predictions_created")
    print("   idx_topic_predictions_created")
    
    posts.create_index([("lang", 1), ("platform", 1)], name="idx_lang_platform")
    print("   idx_lang_platform")
    
    # Text search
    try:
        posts.create_index(
            [("text", "text"), ("text_cleaned", "text")],
            name="idx_fulltext_search"
        )
        print("   idx_fulltext_search")
    except Exception as e:
        print(f"    idx_fulltext_search: {e}")
    
    # Removed idx_topics_predictions_retrain - MongoDB cannot index 2 arrays in compound
    # Use separate indexes instead (already created above)
    
    # ========== SOURCES COLLECTION ==========
    sources = db["sources"]
    print("\n sources collection:")
    
    try:
        sources.create_index(
            [("platform", 1), ("source_id", 1)],
            unique=True,
            name="idx_platform_source_id_unique"
        )
        print("   idx_platform_source_id_unique")
    except Exception as e:
        print(f"    idx_platform_source_id_unique already exists: {e}")
    
    sources.create_index([("is_active", 1), ("platform", 1)], name="idx_active_platform")
    print("   idx_active_platform")
    
    sources.create_index([("source_type", 1), ("platform", 1)], name="idx_type_platform")
    print("   idx_type_platform")
    
    # ========== TOPIC_STATS COLLECTION ==========
    topic_stats = db["topic_stats"]
    print("\n topic_stats collection:")
    
    try:
        topic_stats.create_index(
            [("topic", 1), ("date", 1), ("platform", 1)],
            unique=True,
            name="idx_topic_date_platform_unique"
        )
        print("   idx_topic_date_platform_unique")
    except Exception as e:
        print(f"    idx_topic_date_platform_unique already exists: {e}")
    
    topic_stats.create_index([("date", -1), ("topic", 1)], name="idx_date_topic")
    print("   idx_date_topic")
    
    topic_stats.create_index([("trend_score", -1), ("date", -1)], name="idx_trending")
    print("   idx_trending")
    
    # ========== KEYWORD_TRENDS COLLECTION ==========
    keyword_trends = db["keyword_trends"]
    print("\n keyword_trends collection:")
    
    try:
        keyword_trends.create_index(
            [("keyword_normalized", 1), ("date", 1)],
            unique=True,
            name="idx_keyword_date_unique"
        )
        print("   idx_keyword_date_unique")
    except Exception as e:
        print(f"    idx_keyword_date_unique already exists: {e}")
    
    keyword_trends.create_index([("trend_velocity", -1), ("date", -1)], name="idx_trending_velocity")
    print("   idx_trending_velocity")
    
    keyword_trends.create_index([("date", -1), ("total_count", -1)], name="idx_date_count")
    print("   idx_date_count")
    
    keyword_trends.create_index([("keyword_normalized", 1)], name="idx_keyword")
    print("   idx_keyword")
    
    # ========== ML_MODEL_VERSIONS COLLECTION ==========
    ml_models = db["ml_model_versions"]
    print("\n ml_model_versions collection:")
    
    try:
        ml_models.create_index(
            [("version", 1)],
            unique=True,
            name="idx_version_unique"
        )
        print("   idx_version_unique")
    except Exception as e:
        print(f"    idx_version_unique already exists: {e}")
    
    ml_models.create_index([("is_active", 1), ("trained_at", -1)], name="idx_active_trained")
    print("   idx_active_trained")
    
    print("\n All indexes created successfully!")


def backfill_platform_field():
    """Add platform='telegram' to all existing posts."""
    print("\n" + "=" * 60)
    print("Backfilling platform field")
    print("=" * 60)
    
    db = get_db()
    posts = db["posts"]
    
    result = posts.update_many(
        {"platform": {"$exists": False}},
        {"$set": {"platform": "telegram"}}
    )
    
    print(f" Updated {result.modified_count:,} posts with platform='telegram'")


def backfill_text_cleaned():
    """Add text_cleaned field (copy from text for now)."""
    print("\n" + "=" * 60)
    print("Backfilling text_cleaned field")
    print("=" * 60)
    
    db = get_db()
    posts = db["posts"]
    
    # For existing posts without text_cleaned, copy from text
    # In production, this should use the cleaning.clean_text() function
    result = posts.update_many(
        {"text_cleaned": {"$exists": False}},
        [{"$set": {"text_cleaned": "$text"}}]
    )
    
    print(f" Updated {result.modified_count:,} posts with text_cleaned")
    print("  Note: Using raw text. Run cleaning script for proper preprocessing.")


def migrate_topics_to_predictions():
    """Migrate existing topics array to topic_predictions format."""
    print("\n" + "=" * 60)
    print("Migrating topics to topic_predictions")
    print("=" * 60)
    print("\n  DEPRECATION: 'topics' field is kept for backward compatibility.")
    print("   Use 'topic_predictions' for new code (includes confidence + version).")
    print("   Migration: SKIPPED - MongoDB cannot index 2 arrays simultaneously.\n")
    
    print(" To migrate existing posts:")
    print("   1. Use predict_topics.py to add ML predictions")
    print("   2. Or wait for auto-predict on next ingestion")
    print("   3. Old 'topics' field will remain for backward compatibility\n")
    
    print(" Migration step skipped (safe)")


def generate_sources_from_posts():
    """Extract unique sources from posts and create sources collection."""
    print("\n" + "=" * 60)
    print("Generating sources collection")
    print("=" * 60)
    
    db = get_db()
    posts = db["posts"]
    sources = db["sources"]
    
    # Aggregate unique sources
    pipeline = [
        {"$group": {
            "_id": {
                "platform": "$platform",
                "source": "$source"
            },
            "post_count": {"$sum": 1},
            "first_seen": {"$min": "$created_at"},
            "last_seen": {"$max": "$created_at"}
        }}
    ]
    
    results = list(posts.aggregate(pipeline))
    
    for result in results:
        platform = result["_id"]["platform"]
        source = result["_id"]["source"]
        
        # Parse source (format: "telegram:username")
        if ":" in source:
            _, source_id = source.split(":", 1)
        else:
            source_id = source
        
        source_doc = {
            "platform": platform,
            "source_type": "channel",  # Default to channel
            "source_id": source_id,
            "name": source_id,
            "username": source_id if source_id.startswith("@") else f"@{source_id}",
            "url": f"https://t.me/{source_id.lstrip('@')}" if platform == "telegram" else "",
            "is_active": True,
            "fetch_frequency": "daily",
            "post_count": result["post_count"],
            "created_at": result["first_seen"],
            "updated_at": datetime.now(UTC),
            "last_fetched_at": result["last_seen"]
        }
        
        # Upsert
        sources.update_one(
            {"platform": platform, "source_id": source_id},
            {"$set": source_doc},
            upsert=True
        )
    
    print(f" Created/updated {len(results):,} sources")


def register_current_ml_model():
    """Register the current trained ML model."""
    print("\n" + "=" * 60)
    print("Registering ML model version")
    print("=" * 60)
    
    db = get_db()
    ml_models = db["ml_model_versions"]
    
    # Check if model file exists
    model_path = Path(__file__).parent.parent / "models" / "topic_classifier_svm.pkl"
    
    if not model_path.exists():
        print("  Model file not found. Train model first:")
        print("   scripts\\train_ml_classifier.cmd")
        return
    
    # Try to load model metadata
    try:
        import pickle
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
            # Extract metrics if available
            metrics = model_data.get('metrics', {})
            accuracy = metrics.get('accuracy', 0.0)
            f1_score = metrics.get('f1_score', 0.0)
            training_samples = model_data.get('training_samples', 0)
    except:
        print("  Could not extract metrics from model file. Using placeholders.")
        accuracy = 0.0
        f1_score = 0.0
        training_samples = 0
    
    # Register model
    model_doc = {
        "version": f"svm_v1.0_{datetime.now(UTC).strftime('%Y%m%d')}",
        "model_type": "svm",
        "accuracy": accuracy,
        "f1_score": f1_score,
        "precision": 0.0,  # TODO: Extract from training metrics
        "recall": 0.0,     # TODO: Extract from training metrics
        "training_samples": training_samples,
        "topics": ["Crypto", "Kinh tế", "Công nghệ", "Chính trị", "Thể thao", 
                  "Giải trí", "Sức khỏe", "Giáo dục", "Du lịch", "Ẩm thực"],
        "is_active": True,
        "trained_at": datetime.fromtimestamp(model_path.stat().st_mtime, UTC),
        "model_path": str(model_path),
        "training_config": {
            "test_size": 0.2,
            "max_features": 5000,
            "ngram_range": [1, 2]
        },
        "note": "Run train_ml_classifier.py to update metrics"
    }
    
    # Deactivate old models
    ml_models.update_many(
        {"is_active": True},
        {"$set": {"is_active": False}}
    )
    
    # Insert new model
    ml_models.insert_one(model_doc)
    
    print(f" Registered model: {model_doc['version']}")


def show_stats():
    """Show database statistics after migration."""
    print("\n" + "=" * 60)
    print("Database Statistics")
    print("=" * 60)
    
    db = get_db()
    
    collections = {
        "posts": db["posts"],
        "sources": db["sources"],
        "topic_stats": db["topic_stats"],
        "keyword_trends": db["keyword_trends"],
        "ml_model_versions": db["ml_model_versions"]
    }
    
    for name, collection in collections.items():
        count = collection.count_documents({})
        indexes = collection.index_information()
        print(f"\n {name}:")
        print(f"   Documents: {count:,}")
        print(f"   Indexes: {len(indexes)}")
        for idx_name, idx_info in indexes.items():
            if idx_name != "_id_":
                print(f"     - {idx_name}")


def main():
    """Run all migrations."""
    print("=" * 60)
    print("Database Migration - Multi-Platform Schema")
    print("=" * 60)
    
    try:
        # Step 1: Create indexes
        create_indexes()
        
        # Step 2: Backfill fields
        backfill_platform_field()
        backfill_text_cleaned()
        
        # Step 3: Migrate data
        migrate_topics_to_predictions()
        generate_sources_from_posts()
        
        # Step 4: Register ML model
        register_current_ml_model()
        
        # Step 5: Show stats
        show_stats()
        
        print("\n" + "=" * 60)
        print(" Migration completed successfully!")
        print("=" * 60)
        print("\n Next steps:")
        print("   1. Review docs/database_design.md for schema details")
        print("   2. Update ingestion code to use new schema")
        print("   3. Implement aggregation scripts for topic_stats")
        print("   4. Implement keyword extraction for keyword_trends")
        
    except Exception as e:
        print(f"\n Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
