"""Tests for ML Topic Classifier.
"""
import pytest
from src.processing.ml_topic_classifier import MLTopicClassifier, create_sample_training_data, TOPIC_LABELS
from pathlib import Path
import tempfile


def test_topic_labels():
    """Test topic labels are defined correctly."""
    assert len(TOPIC_LABELS) == 9
    assert "Crypto/Finance" in TOPIC_LABELS
    assert "Technology" in TOPIC_LABELS
    assert "Other" in TOPIC_LABELS


def test_create_sample_data():
    """Test sample training data creation."""
    texts, labels = create_sample_training_data()
    
    assert len(texts) > 0
    assert len(texts) == len(labels)
    
    # Check all labels are valid
    for label in labels:
        assert label in TOPIC_LABELS


def test_preprocess_text():
    """Test text preprocessing."""
    classifier = MLTopicClassifier()
    
    # Test basic cleaning
    text = "Bitcoin TĂNG GIÁ mạnh!!!  https://example.com 😀"
    cleaned = classifier.preprocess_text(text)
    
    assert "bitcoin" in cleaned.lower()
    assert "tăng giá" in cleaned.lower()
    assert "https://" not in cleaned
    assert "😀" not in cleaned


def test_train_and_predict():
    """Test training and prediction pipeline."""
    # Create temp model path
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        model_path = tmp.name
    
    try:
        # Get sample data
        texts, labels = create_sample_training_data()
        
        # Train
        classifier = MLTopicClassifier(model_path=model_path)
        accuracy = classifier.train(texts, labels, test_size=0.2)
        
        # Check training
        assert classifier.pipeline is not None
        assert accuracy > 0.0  # Should have some accuracy
        
        # Test prediction
        test_text = "Bitcoin tăng giá mạnh, nhà đầu tư crypto hào hứng"
        topic, confidence = classifier.predict(test_text)
        
        assert topic in TOPIC_LABELS
        assert 0.0 <= confidence <= 1.0
        
        # Test batch prediction
        test_texts = [
            "Apple ra mắt iPhone mới",
            "Messi ghi bàn thắng đẹp",
            "COVID-19 vaccine phát triển mới"
        ]
        results = classifier.predict_batch(test_texts)
        
        assert len(results) == len(test_texts)
        for topic, conf in results:
            assert topic in TOPIC_LABELS
            assert 0.0 <= conf <= 1.0
        
    finally:
        # Cleanup
        if Path(model_path).exists():
            Path(model_path).unlink()


def test_save_and_load_model():
    """Test model persistence."""
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        model_path = tmp.name
    
    try:
        # Train and save
        texts, labels = create_sample_training_data()
        classifier1 = MLTopicClassifier(model_path=model_path)
        classifier1.train(texts, labels, test_size=0.2)
        classifier1.save_model()
        
        # Load in new instance
        classifier2 = MLTopicClassifier(model_path=model_path)
        
        # Test predictions are consistent
        test_text = "Bitcoin price increases"
        topic1, conf1 = classifier1.predict(test_text)
        topic2, conf2 = classifier2.predict(test_text)
        
        assert topic1 == topic2
        assert abs(conf1 - conf2) < 0.001  # Should be identical
        
    finally:
        if Path(model_path).exists():
            Path(model_path).unlink()


def test_get_feature_importance():
    """Test feature importance extraction."""
    texts, labels = create_sample_training_data()
    
    classifier = MLTopicClassifier()
    classifier.train(texts, labels, test_size=0.2)
    
    importance = classifier.get_feature_importance(top_n=10)
    
    assert isinstance(importance, dict)
    assert len(importance) > 0
    
    # Check structure
    for topic, features in importance.items():
        assert topic in classifier.pipeline.named_steps['clf'].classes_
        assert len(features) <= 10
        
        for word, score in features:
            assert isinstance(word, str)
            assert isinstance(score, (int, float))


def test_predict_without_model():
    """Test prediction without trained model raises error."""
    classifier = MLTopicClassifier()
    
    with pytest.raises(ValueError, match="Model not trained"):
        classifier.predict("test text")


def test_empty_text_prediction():
    """Test prediction with empty text."""
    texts, labels = create_sample_training_data()
    classifier = MLTopicClassifier()
    classifier.train(texts, labels, test_size=0.2)
    
    # Empty text should still return a prediction
    topic, conf = classifier.predict("")
    assert topic in TOPIC_LABELS
    assert 0.0 <= conf <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
