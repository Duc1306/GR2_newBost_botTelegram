"""Test topic classifier."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.topic_classifier import TopicClassifier

print("=" * 70)
print("TESTING TOPIC CLASSIFIER")
print("=" * 70)

# Test cases
test_cases = [
    {
        "text": "Bitcoin tăng giá mạnh, vượt 100.000 USD. Ethereum cũng tăng theo, các nhà đầu tư cryptocurrency rất lạc quan.",
        "expected": "Crypto & Blockchain"
    },
    {
        "text": "Chứng khoán Việt Nam giảm điểm, VN-Index mất 15 điểm. Các cổ phiếu ngân hàng và bất động sản đều giảm.",
        "expected": "Kinh tế"
    },
    {
        "text": "OpenAI ra mắt GPT-5 với khả năng xử lý ngôn ngữ tự nhiên vượt trội. Công nghệ AI tiếp tục phát triển.",
        "expected": "AI & Machine Learning, Công nghệ"
    },
    {
        "text": "Đội tuyển Việt Nam thắng Thái Lan 2-0 tại SEA Games. HLV Troussier rất hài lòng với màn trình diễn.",
        "expected": "Thể thao"
    },
    {
        "text": "iPhone 16 ra mắt với camera 200MP và chip A18. Apple dự kiến bán được 50 triệu máy trong quý này.",
        "expected": "Công nghệ"
    },
    {
        "text": "Phim Avatar 3 ra rạp, doanh thu mở màn 500 triệu USD. Đạo diễn James Cameron rất vui mừng.",
        "expected": "Giải trí"
    },
]

print("\n" + "="*70)
for i, case in enumerate(test_cases, 1):
    print(f"\n📝 Test {i}: {case['text'][:60]}...")
    topics = TopicClassifier.classify(case['text'])
    print(f"   ✅ Topics found: {', '.join(topics) if topics else 'None'}")
    print(f"   💡 Expected: {case['expected']}")
    
print("\n" + "="*70)
print("✅ ALL TESTS COMPLETED!")
print("="*70)

# Test với post dict
print("\n\n" + "="*70)
print("TESTING WITH POST DICT")
print("="*70)

post = {
    'id': 'test_1',
    'text': 'Bitcoin ETF được phê duyệt, giá BTC tăng vọt lên $100,000',
    'full_article': {
        'title': 'Bitcoin vượt mốc lịch sử',
        'content': 'Cryptocurrency market đang rất lạc quan sau khi SEC phê duyệt Bitcoin ETF...'
    }
}

result = TopicClassifier.classify_post(post)
print(f"\n📊 Post: {post['text']}")
print(f"✅ Topics assigned: {', '.join(result['topics'])}")
print("\n" + "="*70)
