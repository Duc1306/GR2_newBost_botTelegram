"""Comprehensive model evaluation with baseline comparison.
Đánh giá mô hình đầy đủ với so sánh baseline cho báo cáo đồ án.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.ml_topic_classifier import MLTopicClassifier, TOPIC_LABELS
from src.processing.topic_classifier import TopicClassifier
from src.db.mongo import get_db
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    f1_score, precision_score, recall_score, accuracy_score
)
import numpy as np
import argparse
import json
from datetime import datetime
from typing import List, Tuple, Dict


def fetch_evaluation_data(limit: int = 2000, verified_only: bool = False) -> Tuple[List[str], List[str]]:
    """Fetch data for evaluation."""
    db = get_db()
    collection = db["posts"]
    
    texts = []
    labels = []
    
    # Priority 1: Verified labels
    if verified_only:
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
            if text and manual_labels and manual_labels[0] in TOPIC_LABELS:
                texts.append(text)
                labels.append(manual_labels[0])
    
    # Priority 2: Any labeled data
    if len(texts) < 100:
        cursor = collection.find(
            {"$or": [
                {"topics": {"$exists": True, "$ne": []}},
                {"manual_labels": {"$exists": True, "$ne": []}}
            ]},
            {"text": 1, "topics": 1, "manual_labels": 1}
        ).limit(limit)
        
        for doc in cursor:
            text = doc.get("text", "").strip()
            
            # Prefer manual labels
            label = None
            manual_labels = doc.get("manual_labels", [])
            if manual_labels and manual_labels[0] in TOPIC_LABELS:
                label = manual_labels[0]
            
            if not label:
                topics = doc.get("topics", [])
                if topics and topics[0] in TOPIC_LABELS:
                    label = topics[0]
            
            if text and label:
                texts.append(text)
                labels.append(label)
    
    return texts, labels


class BaselineRuleBasedClassifier:
    """Baseline: Rule-based keyword classifier."""
    
    def __init__(self):
        self.classifier = TopicClassifier()
    
    def fit(self, X, y):
        """Dummy fit (rule-based doesn't need training)."""
        pass
    
    def predict(self, X):
        """Predict using rule-based method."""
        predictions = []
        for text in X:
            topics = self.classifier.classify(text)
            if topics:
                predictions.append(topics[0])
            else:
                # Fallback to most common class
                predictions.append("Chính trị")
        return predictions


class BaselineNaiveBayes:
    """Baseline: Naive Bayes classifier."""
    
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )),
            ('clf', MultinomialNB(alpha=0.1))
        ])
    
    def fit(self, X, y):
        self.pipeline.fit(X, y)
    
    def predict(self, X):
        return self.pipeline.predict(X)


def evaluate_classifier(name: str, classifier, X_train, X_test, y_train, y_test, 
                       preprocess_fn=None) -> Dict:
    """Evaluate a classifier and return metrics."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {name}")
    print(f"{'='*60}")
    
    # Preprocess if needed
    if preprocess_fn:
        X_train_processed = [preprocess_fn(x) for x in X_train]
        X_test_processed = [preprocess_fn(x) for x in X_test]
    else:
        X_train_processed = X_train
        X_test_processed = X_test
    
    # Train
    print(f"Training...")
    classifier.fit(X_train_processed, y_train)
    
    # Predict
    print(f"Predicting...")
    y_pred = classifier.predict(X_test_processed)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    macro_precision = precision_score(y_test, y_pred, average='macro', zero_division=0)
    macro_recall = recall_score(y_test, y_pred, average='macro', zero_division=0)
    
    # Display results
    print(f"\n=== Overall Metrics ===")
    print(f"Accuracy:          {accuracy:.4f} ({accuracy:.2%})")
    print(f"Macro F1-Score:    {macro_f1:.4f}")
    print(f"Weighted F1-Score: {weighted_f1:.4f}")
    print(f"Macro Precision:   {macro_precision:.4f}")
    print(f"Macro Recall:      {macro_recall:.4f}")
    
    print(f"\n=== Classification Report ===")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n=== Confusion Matrix ===")
    print(cm)
    
    # Return metrics as dict
    return {
        'name': name,
        'accuracy': float(accuracy),
        'macro_f1': float(macro_f1),
        'weighted_f1': float(weighted_f1),
        'macro_precision': float(macro_precision),
        'macro_recall': float(macro_recall),
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y_test, y_pred, zero_division=0, output_dict=True)
    }


def compare_models(metrics_list: List[Dict]):
    """Compare multiple models side by side."""
    print(f"\n{'='*80}")
    print(f"MODEL COMPARISON")
    print(f"{'='*80}")
    
    # Table header
    print(f"\n{'Model':<25} {'Accuracy':<12} {'Macro-F1':<12} {'Weighted-F1':<12}")
    print("-" * 80)
    
    # Sort by accuracy (descending)
    sorted_metrics = sorted(metrics_list, key=lambda x: x['accuracy'], reverse=True)
    
    for i, m in enumerate(sorted_metrics):
        marker = "🏆" if i == 0 else "  "
        print(f"{marker} {m['name']:<23} {m['accuracy']:.4f}       {m['macro_f1']:.4f}       {m['weighted_f1']:.4f}")
    
    # Best model
    best = sorted_metrics[0]
    print(f"\n🏆 Best Model: {best['name']}")
    print(f"   Accuracy: {best['accuracy']:.2%}")
    print(f"   Macro F1: {best['macro_f1']:.4f}")
    
    # Improvement over baseline
    if len(sorted_metrics) > 1:
        baseline = sorted_metrics[-1]  # Worst is baseline
        improvement = (best['accuracy'] - baseline['accuracy']) / baseline['accuracy'] * 100
        print(f"\n📈 Improvement over baseline: +{improvement:.1f}%")
        print(f"   Baseline: {baseline['name']} ({baseline['accuracy']:.2%})")
        print(f"   Best: {best['name']} ({best['accuracy']:.2%})")


def save_evaluation_report(metrics_list: List[Dict], output_file: str = "evaluation_report.json"):
    """Save evaluation report to JSON file."""
    report = {
        'evaluation_date': datetime.now().isoformat(),
        'models': metrics_list,
        'summary': {
            'best_model': max(metrics_list, key=lambda x: x['accuracy'])['name'],
            'best_accuracy': max(metrics_list, key=lambda x: x['accuracy'])['accuracy'],
            'best_macro_f1': max(metrics_list, key=lambda x: x['macro_f1'])['macro_f1']
        }
    }
    
    output_path = Path("models") / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Evaluation report saved to: {output_path}")


def main(limit: int = 2000, verified_only: bool = False, test_size: float = 0.2):
    """Main evaluation function."""
    print("="*60)
    print("COMPREHENSIVE MODEL EVALUATION")
    print("="*60)
    
    # 1. Fetch data
    print(f"\nFetching evaluation data (limit={limit}, verified_only={verified_only})...")
    texts, labels = fetch_evaluation_data(limit=limit, verified_only=verified_only)
    
    if len(texts) < 100:
        print(f"\n❌ Not enough data for evaluation: {len(texts)} samples")
        print("Need at least 100 samples. Collect more data first.")
        return
    
    print(f"✓ Loaded {len(texts)} samples")
    
    # Label distribution
    from collections import Counter
    label_counts = Counter(labels)
    print(f"\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")
    
    # 2. Split data
    print(f"\n{'='*60}")
    print(f"Splitting data (test_size={test_size})...")
    print(f"{'='*60}")
    
    # Check if stratification is possible
    min_samples = min(label_counts.values())
    use_stratify = min_samples >= 2
    
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels,
        test_size=test_size,
        random_state=42,
        stratify=labels if use_stratify else None
    )
    
    print(f"Train set: {len(X_train)} samples")
    print(f"Test set:  {len(X_test)} samples")
    
    # 3. Evaluate models
    all_metrics = []
    
    # Baseline 1: Rule-based (keyword matching)
    print(f"\n{'='*60}")
    print(f"BASELINE 1: Rule-Based Keyword Matching")
    print(f"{'='*60}")
    baseline_rule = BaselineRuleBasedClassifier()
    metrics_rule = evaluate_classifier(
        "Baseline: Rule-Based",
        baseline_rule,
        X_train, X_test, y_train, y_test
    )
    all_metrics.append(metrics_rule)
    
    # Baseline 2: Naive Bayes
    print(f"\n{'='*60}")
    print(f"BASELINE 2: Naive Bayes Classifier")
    print(f"{'='*60}")
    baseline_nb = BaselineNaiveBayes()
    
    # Preprocess function for ML models
    def preprocess(text):
        from src.processing.cleaning import clean_text
        cleaned, _ = clean_text(text)
        return cleaned.lower()
    
    metrics_nb = evaluate_classifier(
        "Baseline: Naive Bayes",
        baseline_nb,
        X_train, X_test, y_train, y_test,
        preprocess_fn=preprocess
    )
    all_metrics.append(metrics_nb)
    
    # Main Model: SVM (TF-IDF + LinearSVC)
    print(f"\n{'='*60}")
    print(f"MAIN MODEL: SVM (TF-IDF + LinearSVC)")
    print(f"{'='*60}")
    
    # Train SVM model
    svm_classifier = MLTopicClassifier(model_path="models/topic_classifier_svm_eval.pkl", autoload=False)
    svm_classifier.train(texts, labels, test_size=test_size)
    
    # Get metrics from trained model
    if hasattr(svm_classifier, 'last_metrics'):
        metrics_svm = {
            'name': 'Main: SVM (TF-IDF + LinearSVC)',
            **svm_classifier.last_metrics
        }
        # Clean up confusion matrix for JSON serialization
        if 'confusion_matrix' in metrics_svm and isinstance(metrics_svm['confusion_matrix'], np.ndarray):
            metrics_svm['confusion_matrix'] = metrics_svm['confusion_matrix'].tolist()
        all_metrics.append(metrics_svm)
    
    # 4. Compare models
    compare_models(all_metrics)
    
    # 5. Save report
    save_evaluation_report(all_metrics)
    
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"\n📊 View detailed report: models/evaluation_report.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comprehensive model evaluation with baseline comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate with default settings (2000 samples)
  python scripts/evaluate_model.py
  
  # Evaluate with more data
  python scripts/evaluate_model.py --limit 5000
  
  # Evaluate with only verified labels
  python scripts/evaluate_model.py --verified-only
  
  # Custom test split
  python scripts/evaluate_model.py --test-size 0.3
        """
    )
    parser.add_argument("--limit", type=int, default=2000,
                       help="Maximum samples to use (default: 2000)")
    parser.add_argument("--verified-only", action="store_true",
                       help="Use only manually verified labels")
    parser.add_argument("--test-size", type=float, default=0.2,
                       help="Test set proportion (default: 0.2)")
    
    args = parser.parse_args()
    
    main(
        limit=args.limit,
        verified_only=args.verified_only,
        test_size=args.test_size
    )
