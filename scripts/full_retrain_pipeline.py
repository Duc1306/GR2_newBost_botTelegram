"""
Script để verify và balance dataset trước khi retrain model.
Thực hiện:
1. Sửa lại labels sai (reclassify với rule-based mới)
2. Cân bằng dataset nếu cần
3. Retrain ML model
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fix_misclassified_topics import fix_misclassified_topics
from scripts.train_ml_classifier import train_from_db
import argparse


def full_retrain_pipeline(
    apply_fixes: bool = True,
    batch_size: int = 100,
    balanced: bool = True,
    target_samples: int = 500,
    limit: int = 10000
):
    """
    Pipeline đầy đủ để retrain model:
    1. Sửa labels sai trong database
    2. Balance dataset
    3. Train ML model mới
    
    Args:
        apply_fixes: Có áp dụng sửa labels không (True để apply, False để dry-run)
        batch_size: Batch size cho việc update database
        balanced: Có cân bằng dataset không
        target_samples: Số samples mục tiêu mỗi class
        limit: Số lượng samples tối đa để train
    """
    print("\n" + "="*80)
    print(" FULL ML MODEL RETRAINING PIPELINE")
    print("="*80)
    print()
    print("Các bước thực hiện:")
    print("  [1] Reclassify posts với rule-based classifier đã cải thiện")
    print("  [2] Cân bằng dataset (nếu cần)")
    print("  [3] Train ML model mới")
    print()
    print("="*80 + "\n")
    
    # Step 1: Fix misclassified topics
    print("\n" + "▶"*40)
    print("BƯỚC 1: RECLASSIFY POSTS")
    print("▶"*40 + "\n")
    
    fix_misclassified_topics(
        batch_size=batch_size,
        dry_run=not apply_fixes
    )
    
    if not apply_fixes:
        print("\n⚠️  Dry run completed. No changes applied to database.")
        print("   To apply changes and proceed with training, use --apply flag")
        return
    
    # Step 2: Train new ML model
    print("\n" + "▶"*40)
    print("BƯỚC 2: TRAIN ML MODEL MỚI")
    print("▶"*40 + "\n")
    
    input("\nPress Enter to continue with model training...")
    
    train_from_db(
        model_path="models/topic_classifier_svm.pkl",
        limit=limit,
        test_size=0.2,
        use_sample_data=False,
        balanced=balanced,
        balance_method='undersample',
        target_samples=target_samples,
        verified_only=False
    )
    
    print("\n" + "="*80)
    print(" HOÀN TẤT PIPELINE")
    print("="*80)
    print("\n✅ Đã hoàn thành toàn bộ quá trình retrain!")
    print("\nCác bước tiếp theo:")
    print("  1. Test model mới: python scripts\\evaluate_model.py")
    print("  2. Chạy predict trên toàn bộ DB: python scripts\\predict_topics.py")
    print("  3. Khởi động lại API để sử dụng model mới")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline đầy đủ để retrain ML model sau khi cải thiện classifier"
    )
    parser.add_argument(
        "--apply", 
        action="store_true",
        help="Áp dụng thay đổi vào database và train model (mặc định là dry run)"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=100,
        help="Batch size cho update database (mặc định: 100)"
    )
    parser.add_argument(
        "--balanced",
        action="store_true",
        default=True,
        help="Cân bằng dataset trước khi train (mặc định: True)"
    )
    parser.add_argument(
        "--target-samples",
        type=int,
        default=500,
        help="Số samples mục tiêu mỗi class khi balance (mặc định: 500)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Số lượng samples tối đa để train (mặc định: 10000)"
    )
    
    args = parser.parse_args()
    
    full_retrain_pipeline(
        apply_fixes=args.apply,
        batch_size=args.batch_size,
        balanced=args.balanced,
        target_samples=args.target_samples,
        limit=args.limit
    )
