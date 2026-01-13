"""ML-based Topic Classifier using TF-IDF + SVM."""
from __future__ import annotations
import pickle
import sys
from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
sys.path.insert(0, str(Path(__file__).parent.parent))
from processing.cleaning import clean_text


# Topic labels (Vietnamese - matching rule-based classifier)
TOPIC_LABELS = [
    "Crypto",
    "Kinh tế",
    "Công nghệ", 
    "Chính trị",
    "Thể thao",
    "Giải trí",
    "Sức khỏe",
    "Giáo dục",
    "Du lịch",
    "Ẩm thực"
]


class MLTopicClassifier:
    """Machine Learning Topic Classifier using TF-IDF + SVM."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to saved model file. If None, creates new model.
        """
        self.model_path = model_path or "models/topic_classifier_svm.pkl"
        self.pipeline: Optional[Pipeline] = None
        self.labels = TOPIC_LABELS
        
        if Path(self.model_path).exists():
            self.load_model()
    
    def build_pipeline(self) -> Pipeline:
        """
        Build TF-IDF + SVM pipeline.
        
        Returns:
            sklearn Pipeline object
        """
        return Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),  # unigram + bigram
                min_df=2,
                max_df=0.8,
                sublinear_tf=True,
                strip_accents=None  # giữ nguyên tiếng Việt
            )),
            ('clf', LinearSVC(
                C=1.0,
                max_iter=2000,
                random_state=42,
                dual='auto',
                class_weight='balanced'  # Tự động cân bằng class weights
            ))
        ])
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess text before training/prediction.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        cleaned, _ = clean_text(text)
        return cleaned.lower()  # lowercase để chuẩn hóa
    
    def train(self, texts: List[str], labels: List[str], test_size: float = 0.2):
        """
        Train the classifier.
        
        Args:
            texts: List of training texts
            labels: List of corresponding labels
            test_size: Proportion of data for testing
        """
        print(f"Training with {len(texts)} samples...")
        
        # Preprocess all texts
        cleaned_texts = [self.preprocess_text(t) for t in texts]
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            cleaned_texts, labels, 
            test_size=test_size, 
            random_state=42,
            stratify=labels  # đảm bảo tỷ lệ label đều
        )
        
        print(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Build and train pipeline
        self.pipeline = self.build_pipeline()
        self.pipeline.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = self.pipeline.predict(X_test)
        
        print("\n=== Classification Report ===")
        print(classification_report(y_test, y_pred, zero_division=0))
        
        print("\n=== Confusion Matrix ===")
        print(confusion_matrix(y_test, y_pred))
        
        # Calculate accuracy
        accuracy = (y_pred == y_test).sum() / len(y_test)
        print(f"\nTest Accuracy: {accuracy:.2%}")
        
        return accuracy
    
    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict topic for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (predicted_topic, confidence_score)
        """
        if self.pipeline is None:
            raise ValueError("Model not trained or loaded. Train or load model first.")
        
        # Preprocess
        cleaned = self.preprocess_text(text)
        
        # Predict
        predicted_label = self.pipeline.predict([cleaned])[0]
        
        # Get confidence score (distance from decision boundary)
        decision = self.pipeline.decision_function([cleaned])[0]
        
        # Convert decision values to confidence (using softmax-like normalization)
        exp_scores = np.exp(decision - np.max(decision))
        probabilities = exp_scores / exp_scores.sum()
        confidence = float(np.max(probabilities))
        
        return predicted_label, confidence
    
    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Predict topics for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of (predicted_topic, confidence) tuples
        """
        if self.pipeline is None:
            raise ValueError("Model not trained or loaded.")
        
        # Preprocess all
        cleaned_texts = [self.preprocess_text(t) for t in texts]
        
        # Predict
        predicted_labels = self.pipeline.predict(cleaned_texts)
        
        # Get confidence scores
        decisions = self.pipeline.decision_function(cleaned_texts)
        
        results = []
        for label, decision in zip(predicted_labels, decisions):
            exp_scores = np.exp(decision - np.max(decision))
            probabilities = exp_scores / exp_scores.sum()
            confidence = float(np.max(probabilities))
            results.append((label, confidence))
        
        return results
    
    def save_model(self, path: Optional[str] = None):
        """
        Save trained model to disk.
        
        Args:
            path: Path to save model. If None, uses self.model_path
        """
        if self.pipeline is None:
            raise ValueError("No model to save. Train model first.")
        
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            pickle.dump(self.pipeline, f)
        
        print(f"Model saved to: {save_path}")
    
    def load_model(self, path: Optional[str] = None):
        """
        Load trained model from disk.
        
        Args:
            path: Path to load model from. If None, uses self.model_path
        """
        load_path = path or self.model_path
        
        if not Path(load_path).exists():
            raise FileNotFoundError(f"Model file not found: {load_path}")
        
        with open(load_path, 'rb') as f:
            self.pipeline = pickle.load(f)
        
        print(f"Model loaded from: {load_path}")
    
    def get_feature_importance(self, top_n: int = 20) -> dict:
        """
        Get top N important features (words) for each class.
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            Dictionary mapping class -> list of (word, importance) tuples
        """
        if self.pipeline is None:
            raise ValueError("Model not trained or loaded.")
        
        vectorizer = self.pipeline.named_steps['tfidf']
        classifier = self.pipeline.named_steps['clf']
        
        feature_names = vectorizer.get_feature_names_out()
        
        importance_dict = {}
        for idx, label in enumerate(classifier.classes_):
            # Get coefficient weights for this class
            coef = classifier.coef_[idx]
            
            # Get top N features
            top_indices = np.argsort(coef)[-top_n:][::-1]
            top_features = [(feature_names[i], coef[i]) for i in top_indices]
            
            importance_dict[label] = top_features
        
        return importance_dict


def create_sample_training_data() -> Tuple[List[str], List[str]]:
    """
    Create sample training data for demonstration.
    You should replace this with real labeled data.
    
    Returns:
        Tuple of (texts, labels)
    """
    samples = [
        # Crypto/Finance
        ("Bitcoin tăng vọt lên 50000 USD, nhà đầu tư crypto hào hứng", "Crypto/Finance"),
        ("Ethereum ra mắt bản nâng cấp mới, giá ETH tăng 20%", "Crypto/Finance"),
        ("Chứng khoán Việt Nam giảm điểm, VN-Index mất mốc 1200", "Crypto/Finance"),
        ("Lãi suất ngân hàng tăng, người vay gặp khó khăn", "Crypto/Finance"),
        ("Binance công bố giao dịch khối lượng lớn, thị trường sôi động", "Crypto/Finance"),
        
        # Technology  
        ("Apple ra mắt iPhone 16 với chip AI mới, camera 200MP", "Technology"),
        ("ChatGPT-5 có khả năng xử lý video, cộng đồng phấn khích", "Technology"),
        ("Samsung phát triển màn hình gập mới, độ bền tăng gấp đôi", "Technology"),
        ("Google công bố AI Gemini 2.0, vượt trội GPT-4", "Technology"),
        ("Tesla ra mắt robot hình người Optimus Gen 3", "Technology"),
        
        # Politics
        ("Tổng thống Mỹ công bố chính sách mới về thuế quan", "Politics"),
        ("Quốc hội Việt Nam thông qua luật đất đai sửa đổi", "Politics"),
        ("Liên hợp quốc họp khẩn cấp về xung đột Trung Đông", "Politics"),
        ("Bầu cử tổng thống Pháp: ứng viên cánh tả dẫn đầu", "Politics"),
        ("NATO mở rộng thành viên, Thụy Điển chính thức gia nhập", "Politics"),
        
        # Sports
        ("Messi ghi 3 bàn, Inter Miami thắng đậm 5-0", "Sports"),
        ("Ronaldo chuyển đến Al Nassr, lương khủng 200 triệu euro/năm", "Sports"),
        ("Đội tuyển Việt Nam thắng Thái Lan 2-1 tại vòng loại World Cup", "Sports"),
        ("Novak Djokovic vô địch Wimbledon lần thứ 25", "Sports"),
        ("Olympic Paris 2024: Mỹ dẫn đầu bảng xếp hạng huy chương", "Sports"),
        
        # Entertainment
        ("BTS comeback với album mới, phá kỷ lục YouTube", "Entertainment"),
        ("Blackpink tổ chức concert tại Việt Nam, vé bán hết trong 5 phút", "Entertainment"),
        ("Phim Avengers mới thu về 1 tỷ USD sau 3 ngày công chiếu", "Entertainment"),
        ("Netflix ra mắt series Squid Game 2, rating phá đảo", "Entertainment"),
        ("Ca sĩ Sơn Tùng MTP phát hành MV mới, trending #1 YouTube", "Entertainment"),
        
        # Health
        ("Phát hiện thuốc mới chữa ung thư phổi, hiệu quả 85%", "Health"),
        ("WHO cảnh báo biến thể COVID-19 mới lây lan nhanh", "Health"),
        ("Vaccine HIV đầu tiên trên thế giới sắp được phê duyệt", "Health"),
        ("Tập yoga 30 phút mỗi ngày giảm nguy cơ đau tim 40%", "Health"),
        ("Bệnh viện K phát triển kỹ thuật xạ trị ung thư tiên tiến", "Health"),
        
        # Education
        ("ĐH Quốc gia Hà Nội công bố phương án tuyển sinh 2024", "Education"),
        ("Học bổng toàn phần du học Mỹ dành cho sinh viên Việt Nam", "Education"),
        ("Thi tốt nghiệp THPT 2024: 1 triệu thí sinh đăng ký", "Education"),
        ("EdTech startup Việt gọi vốn thành công 10 triệu USD", "Education"),
        ("Coursera mở khóa học AI miễn phí, 500k người đăng ký", "Education"),
        
        # Travel/Food
        ("Đà Nẵng vào top 10 điểm đến tốt nhất châu Á 2024", "Travel/Food"),
        ("Mở cửa trở lại visa du lịch Nhật Bản, tour đầy khách", "Travel/Food"),
        ("Phở Việt Nam được CNN bình chọn món ăn ngon nhất thế giới", "Travel/Food"),
        ("Khách sạn 5 sao Phú Quốc giảm giá 50% dịp hè", "Travel/Food"),
        ("Nhà hàng Michelin đầu tiên tại Việt Nam khai trương", "Travel/Food"),
        
        # Other
        ("Dự báo thời tiết: Bão số 5 đổ bộ miền Trung trong 24h", "Other"),
        ("Giá xăng tăng 2000đ/lít, người dân bức xúc", "Other"),
        ("Triển lãm nghệ thuật đương đại tại Hà Nội thu hút đông đảo khán giả", "Other"),
        ("Động đất 5.5 độ Richter tại Nhật Bản, không có thiệt hại", "Other"),
    ]
    
    texts, labels = zip(*samples)
    return list(texts), list(labels)


# ===========================================
# MAIN: Test model predictions only
# ===========================================
if __name__ == "__main__":
    print("=== ML Topic Classifier - Test Predictions ===")
    print("\n⚠️  Để train model với dữ liệu thật, sử dụng:")
    print("   python scripts/train_ml_classifier.py\n")
    
    # Check if model exists
    model_path = Path("models/topic_classifier_svm.pkl")
    if not model_path.exists():
        print("❌ Model chưa được train!")
        print("\nChạy lệnh sau để train model:")
        print("   python scripts/train_ml_classifier.py")
        print("\nHoặc để test với sample data:")
        print("   python scripts/train_ml_classifier.py --use-sample-data")
        sys.exit(1)
    
    # Load existing model
    print(f"Loading model from: {model_path}")
    classifier = MLTopicClassifier(model_path=str(model_path))
    
    # Test prediction
    print("\n" + "="*60)
    print("Testing predictions...")
    print("="*60)
    
    test_texts = [
        "Bitcoin tăng giá mạnh, nhiều nhà đầu tư kiếm lời",
        "Apple ra mắt MacBook M4 với hiệu năng vượt trội",
        "Quốc hội thông qua luật mới về môi trường",
        "Ronaldo ghi bàn thứ 900 trong sự nghiệp",
        "Phim mới của Marvel thu về 500 triệu USD",
    ]
    
    for text in test_texts:
        topic, confidence = classifier.predict(text)
        print(f"\nText: {text}")
        print(f"→ Predicted: {topic} (confidence: {confidence:.2%})")
    
    # Show feature importance
    print("\n" + "="*60)
    print("Top keywords for each topic")
    print("="*60)
    importance = classifier.get_feature_importance(top_n=10)
    for topic, features in importance.items():
        print(f"\n{topic}:")
        for word, score in features[:10]:
            print(f"  - {word}: {score:.3f}")
