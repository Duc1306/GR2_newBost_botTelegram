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
    "Thế giới",
    "Pháp luật",
    "Ô tô - Xe máy",
    "Khoa học",
    "Thể thao",
    "Giải trí",
    "Sức khỏe",
    "Giáo dục",
    "Việc làm",
    "Du lịch",
    "Ẩm thực",
    "Kinh doanh & Khởi nghiệp",
    "Trò chơi & Ứng dụng",
    "Tin tức & Truyền thông",
    "Khác",
]


class MLTopicClassifier:
    """Machine Learning Topic Classifier using TF-IDF + SVM."""
    
    def __init__(self, model_path: Optional[str] = None, autoload: bool = True):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to saved model file. If None, creates new model.
            autoload: Whether to automatically load model if it exists. Default True.
        """
        self.model_path = model_path or "models/topic_classifier_svm.pkl"
        self.pipeline: Optional[Pipeline] = None
        self.labels = TOPIC_LABELS
        
        # Auto-load model if exists and autoload=True
        if autoload and Path(self.model_path).exists():
            try:
                # Check if file is not empty and valid
                if Path(self.model_path).stat().st_size > 0:
                    self.load_model()
                else:
                    print(f"  Model file exists but is empty: {self.model_path}")
            except (EOFError, pickle.UnpicklingError) as e:
                print(f"  Failed to load model: {e}")
                print("   Will train new model when needed.")
    
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
        
        # Check if we have enough samples for stratified split
        from collections import Counter
        label_counts = Counter(labels)
        min_samples = min(label_counts.values())
        n_classes = len(label_counts)
        
        # For stratified split to work:
        # - Each class needs at least 2 samples
        # - test_size must be >= number of classes
        use_stratify = min_samples >= 2 and len(texts) * test_size >= n_classes
        
        if not use_stratify:
            print(f"  Sample size too small for stratified split. Using random split.")
            print(f"   Classes: {n_classes}, Min samples per class: {min_samples}")
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            cleaned_texts, labels, 
            test_size=test_size, 
            random_state=42,
            stratify=labels if use_stratify else None
        )
        
        print(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Build and train pipeline
        self.pipeline = self.build_pipeline()
        self.pipeline.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = self.pipeline.predict(X_test)
        
        # Import metrics
        from sklearn.metrics import f1_score, precision_score, recall_score
        
        # Calculate all metrics
        accuracy = (y_pred == y_test).sum() / len(y_test)
        macro_f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)
        weighted_f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        macro_precision = precision_score(y_test, y_pred, average='macro', zero_division=0)
        macro_recall = recall_score(y_test, y_pred, average='macro', zero_division=0)
        
        # Display results
        print("\n" + "="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        
        print("\n=== Overall Metrics ===")
        print(f"Accuracy:          {accuracy:.4f} ({accuracy:.2%})")
        print(f"Macro F1-Score:    {macro_f1:.4f}")
        print(f"Weighted F1-Score: {weighted_f1:.4f}")
        print(f"Macro Precision:   {macro_precision:.4f}")
        print(f"Macro Recall:      {macro_recall:.4f}")
        
        print("\n=== Per-Topic Classification Report ===")
        print(classification_report(y_test, y_pred, zero_division=0))
        
        print("\n=== Confusion Matrix ===")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)
        
        # Pretty print confusion matrix with labels
        print("\n=== Confusion Matrix (with labels) ===")
        unique_labels = sorted(list(set(y_test) | set(y_pred)))
        print(f"{'':15s}", end="")
        for label in unique_labels:
            print(f"{label[:12]:>12s}", end=" ")
        print()
        for i, label in enumerate(unique_labels):
            print(f"{label[:15]:15s}", end="")
            for j in range(len(unique_labels)):
                if i < cm.shape[0] and j < cm.shape[1]:
                    print(f"{cm[i][j]:12d}", end=" ")
                else:
                    print(f"{0:12d}", end=" ")
            print()
        
        # Store metrics for later retrieval
        self.last_metrics = {
            'accuracy': accuracy,
            'macro_f1': macro_f1,
            'weighted_f1': weighted_f1,
            'macro_precision': macro_precision,
            'macro_recall': macro_recall,
            'confusion_matrix': cm.tolist(),
            'classification_report': classification_report(y_test, y_pred, zero_division=0, output_dict=True)
        }
        
        print("\n" + "="*60)
        
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
        Tuple of (texts, labels) - Using Vietnamese labels matching TOPIC_LABELS
    """
    samples = [
        # Crypto (5 samples)
        ("Bitcoin tăng vọt lên 50000 USD, nhà đầu tư crypto hào hứng", "Crypto"),
        ("Ethereum ra mắt bản nâng cấp mới, giá ETH tăng 20%", "Crypto"),
        ("Binance công bố giao dịch khối lượng lớn, thị trường sôi động", "Crypto"),
        ("NFT market cap reaches new all-time high", "Crypto"),
        ("DeFi protocol launches new staking rewards", "Crypto"),
        
        # Kinh tế (5 samples)
        ("Chứng khoán Việt Nam giảm điểm, VN-Index mất mốc 1200", "Kinh tế"),
        ("Lãi suất ngân hàng tăng, người vay gặp khó khăn", "Kinh tế"),
        ("GDP Việt Nam tăng trưởng 6.5% trong quý 3", "Kinh tế"),
        ("Xuất khẩu nông sản đạt kỷ lục mới", "Kinh tế"),
        ("Startup Việt gọi vốn thành công 50 triệu USD", "Kinh tế"),
        
        # Công nghệ (5 samples)  
        ("Apple ra mắt iPhone 16 với chip AI mới, camera 200MP", "Công nghệ"),
        ("ChatGPT-5 có khả năng xử lý video, cộng đồng phấn khích", "Công nghệ"),
        ("Samsung phát triển màn hình gập mới, độ bền tăng gấp đôi", "Công nghệ"),
        ("Google công bố AI Gemini 2.0, vượt trội GPT-4", "Công nghệ"),
        ("Tesla ra mắt robot hình người Optimus Gen 3", "Công nghệ"),
        
        # Chính trị (5 samples)
        ("Tổng thống Mỹ công bố chính sách mới về thuế quan", "Chính trị"),
        ("Quốc hội Việt Nam thông qua luật đất đai sửa đổi", "Chính trị"),
        ("Liên hợp quốc họp khẩn cấp về xung đột Trung Đông", "Chính trị"),
        ("Bầu cử tổng thống Pháp: ứng viên cánh tả dẫn đầu", "Chính trị"),
        ("NATO mở rộng thành viên, Thụy Điển chính thức gia nhập", "Chính trị"),
        
        # Thể thao (5 samples)
        ("Messi ghi 3 bàn, Inter Miami thắng đậm 5-0", "Thể thao"),
        ("Ronaldo chuyển đến Al Nassr, lương khủng 200 triệu euro/năm", "Thể thao"),
        ("Đội tuyển Việt Nam thắng Thái Lan 2-1 tại vòng loại World Cup", "Thể thao"),
        ("Novak Djokovic vô địch Wimbledon lần thứ 25", "Thể thao"),
        ("Olympic Paris 2024: Mỹ dẫn đầu bảng xếp hạng huy chương", "Thể thao"),
        
        # Giải trí (5 samples)
        ("BTS comeback với album mới, phá kỷ lục YouTube", "Giải trí"),
        ("Blackpink tổ chức concert tại Việt Nam, vé bán hết trong 5 phút", "Giải trí"),
        ("Phim Avengers mới thu về 1 tỷ USD sau 3 ngày công chiếu", "Giải trí"),
        ("Netflix ra mắt series Squid Game 2, rating phá đảo", "Giải trí"),
        ("Ca sĩ Sơn Tùng MTP phát hành MV mới, trending #1 YouTube", "Giải trí"),
        
        # Sức khỏe (5 samples)
        ("Phát hiện thuốc mới chữa ung thư phổi, hiệu quả 85%", "Sức khỏe"),
        ("WHO cảnh báo biến thể COVID-19 mới lây lan nhanh", "Sức khỏe"),
        ("Vaccine HIV đầu tiên trên thế giới sắp được phê duyệt", "Sức khỏe"),
        ("Tập yoga 30 phút mỗi ngày giảm nguy cơ đau tim 40%", "Sức khỏe"),
        ("Bệnh viện K phát triển kỹ thuật xạ trị ung thư tiên tiến", "Sức khỏe"),
        
        # Giáo dục (5 samples)
        ("ĐH Quốc gia Hà Nội công bố phương án tuyển sinh 2024", "Giáo dục"),
        ("Học bổng toàn phần du học Mỹ dành cho sinh viên Việt Nam", "Giáo dục"),
        ("Thi tốt nghiệp THPT 2024: 1 triệu thí sinh đăng ký", "Giáo dục"),
        ("EdTech startup Việt gọi vốn thành công 10 triệu USD", "Giáo dục"),
        ("Coursera mở khóa học AI miễn phí, 500k người đăng ký", "Giáo dục"),
        
        # Du lịch (10 samples)
        ("Đà Nẵng vào top 10 điểm đến tốt nhất châu Á 2024", "Du lịch"),
        ("Mở cửa trở lại visa du lịch Nhật Bản, tour đầy khách", "Du lịch"),
        ("Khách sạn 5 sao Phú Quốc giảm giá 50% dịp hè", "Du lịch"),
        ("Hội An được UNESCO công nhận di sản văn hóa thế giới", "Du lịch"),
        ("Tour du lịch Sapa giảm giá, khách tăng đột biến", "Du lịch"),
        ("Vịnh Hạ Long đón 10 triệu du khách quốc tế năm 2024", "Du lịch"),
        ("Mở đường bay thẳng Việt Nam - Mỹ, vé rẻ bất ngờ", "Du lịch"),
        ("Phú Quốc xây casino mới, thu hút đầu tư khủng", "Du lịch"),
        ("Du lịch Đà Lạt tăng trưởng 200% trong mùa lễ", "Du lịch"),
        ("Nha Trang khai trương công viên biển lớn nhất VN", "Du lịch"),
        
        # Ẩm thực (10 samples)
        ("Phở Việt Nam được CNN bình chọn món ăn ngon nhất thế giới", "Ẩm thực"),
        ("Nhà hàng Michelin đầu tiên tại Việt Nam khai trương", "Ẩm thực"),
        ("Bánh mì Việt Nam nổi tiếng khắp thế giới", "Ẩm thực"),
        ("Món bún chả Hà Nội được Obama thưởng thức", "Ẩm thực"),
        ("Quán cà phê trứng ở phố cổ Hà Nội đông khách", "Ẩm thực"),
        ("Gỏi cuốn Việt Nam vào top món ăn healthy nhất", "Ẩm thực"),
        ("Masterchef Vietnam mùa 5 tìm kiếm tài năng ẩm thực", "Ẩm thực"),
        ("Street food Sài Gòn thu hút du khách quốc tế", "Ẩm thực"),
        ("Lẩu Thái Tom Yum mở chi nhánh tại Việt Nam", "Ẩm thực"),
        ("Món nem rán Việt Nam chinh phục thực khách Hàn Quốc", "Ẩm thực"),

        # Kinh doanh & Khởi nghiệp (10 samples)
        ("Startup fintech Việt gọi vốn Series A 5 triệu USD từ quỹ Nhật", "Kinh doanh & Khởi nghiệp"),
        ("CEO 28 tuổi xây dựng công ty triệu đô từ tay trắng", "Kinh doanh & Khởi nghiệp"),
        ("Doanh nghiệp vừa và nhỏ vượt khó nhờ chuyển đổi số", "Kinh doanh & Khởi nghiệp"),
        ("VNG ra mắt sản phẩm mới, cạnh tranh thị trường ASEAN", "Kinh doanh & Khởi nghiệp"),
        ("Grab Việt Nam mở rộng dịch vụ tài chính cho tiểu thương", "Kinh doanh & Khởi nghiệp"),
        ("Shopee, Tiki, Lazada: Cuộc chiến thương mại điện tử 2024", "Kinh doanh & Khởi nghiệp"),
        ("Pivot thành công: từ food tech sang logistics, startup 10x doanh thu", "Kinh doanh & Khởi nghiệp"),
        ("Quỹ đầu tư mạo hiểm rót 20 triệu USD vào edtech Việt Nam", "Kinh doanh & Khởi nghiệp"),
        ("Mô hình kinh doanh D2C giúp thương hiệu Việt tăng 300% doanh thu", "Kinh doanh & Khởi nghiệp"),
        ("IPO thành công, startup Việt định giá 1 tỷ USD trên sàn chứng khoán", "Kinh doanh & Khởi nghiệp"),

        # Trò chơi & Ứng dụng (10 samples)
        ("Liên Quân Mobile ra mắt tướng mới mùa 30, fan hào hứng", "Trò chơi & Ứng dụng"),
        ("Steam Summer Sale 2024: hàng nghìn game giảm giá đến 90%", "Trò chơi & Ứng dụng"),
        ("PlayStation 5 Pro ra mắt, giá 700 USD, hiệu năng gấp đôi", "Trò chơi & Ứng dụng"),
        ("Valorant VCT 2024: Team Flash vô địch khu vực Đông Nam Á", "Trò chơi & Ứng dụng"),
        ("Minecraft vượt mốc 200 triệu bản bán ra toàn cầu", "Trò chơi & Ứng dụng"),
        ("App TikTok cập nhật tính năng AI tạo video tự động", "Trò chơi & Ứng dụng"),
        ("Google Play Store xóa 1 triệu ứng dụng vi phạm chính sách", "Trò chơi & Ứng dụng"),
        ("Mobile Legends World Championship: Việt Nam vào top 4", "Trò chơi & Ứng dụng"),
        ("Nintendo Switch 2 lộ diện với màn hình OLED 8 inch", "Trò chơi & Ứng dụng"),
        ("Roblox ra mắt nền tảng game metaverse cho trẻ em", "Trò chơi & Ứng dụng"),

        # Tin tức & Truyền thông (10 samples)
        ("VTV tăng cường phát sóng tin tức 24/7 trên kênh VTV1", "Tin tức & Truyền thông"),
        ("Báo điện tử VnExpress đạt 30 triệu lượt đọc mỗi tháng", "Tin tức & Truyền thông"),
        ("Reuters công bố báo cáo tình hình truyền thông toàn cầu 2024", "Tin tức & Truyền thông"),
        ("Mạng xã hội Threads của Meta đạt 100 triệu người dùng", "Tin tức & Truyền thông"),
        ("Nhà báo điều tra bị đe dọa, Hội Nhà báo lên tiếng bảo vệ", "Tin tức & Truyền thông"),
        ("Tạp chí Forbes Việt Nam phát hành số đặc biệt kỷ niệm 10 năm", "Tin tức & Truyền thông"),
        ("Đài BBC mở văn phòng đại diện mới tại Đông Nam Á", "Tin tức & Truyền thông"),
        ("Podcast tin tức buổi sáng của VTC lọt top 10 châu Á", "Tin tức & Truyền thông"),
        ("Báo Tuổi Trẻ triển khai nền tảng tin tức AI cá nhân hóa", "Tin tức & Truyền thông"),
        ("Luật báo chí mới: quy định rõ trách nhiệm của tòa soạn online", "Tin tức & Truyền thông"),

        # Khác (10 samples)
        ("Thời tiết hôm nay: Hà Nội nắng nóng 40 độ, TP.HCM mưa lớn", "Khác"),
        ("Lịch nghỉ lễ 30/4 và 1/5 năm 2024: nghỉ 5 ngày liên tiếp", "Khác"),
        ("Giá xăng hôm nay điều chỉnh tăng 500 đồng/lít", "Khác"),
        ("Tin nhắn rác, cuộc gọi lừa đảo tăng mạnh dịp cuối năm", "Khác"),
        ("Cộng đồng mạng xôn xao clip hài hước về mèo", "Khác"),
        ("Thông báo lịch cúp điện các quận tại TP.HCM tuần này", "Khác"),
        ("Hướng dẫn gia hạn CCCD gắn chip tại nhà qua VNeID", "Khác"),
        ("Chương trình khuyến mãi siêu thị tháng 11: giảm đến 50%", "Khác"),
        ("Hỏi đáp: Thủ tục xin việc cho người nước ngoài tại Việt Nam", "Khác"),
        ("Những điều thú vị ít biết về thành phố Hội An", "Khác"),
    ]

    texts, labels = zip(*samples)
    return list(texts), list(labels)


# ===========================================
# MAIN: Test model predictions only
# ===========================================
if __name__ == "__main__":
    print("=== ML Topic Classifier - Test Predictions ===")
    print("\n  Để train model với dữ liệu thật, sử dụng:")
    print("   python scripts/train_ml_classifier.py\n")
    
    # Check if model exists
    model_path = Path("models/topic_classifier_svm.pkl")
    if not model_path.exists():
        print(" Model chưa được train!")
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
