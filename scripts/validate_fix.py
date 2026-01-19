"""
Quick validation: Run extraction on a small sample to verify the fix.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_categories_from_urls import extract_categories_from_urls


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 VALIDATION TEST: Extract categories from 50 posts")
    print("="*80 + "\n")
    
    # Run with dry_run=True and small limit
    extract_categories_from_urls(
        batch_size=10,
        limit=50,
        delay=0.3,
        dry_run=True  # Don't save to database yet
    )
    
    print("\n" + "="*80)
    print("✅ Validation complete!")
    print("If you see successful extractions above, run the full script with --apply")
    print("Example: python scripts\\extract_categories_from_urls.py --apply --limit 1000")
    print("="*80 + "\n")
