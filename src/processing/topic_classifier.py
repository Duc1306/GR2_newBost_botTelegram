"""Topic classification using rule-based keywords.
Phân loại bài viết theo chủ đề dựa trên từ khóa.
"""
from typing import List, Set
import re


class TopicClassifier:
    """Rule-based topic classifier using keywords."""
    
    # Định nghĩa keywords cho từng chủ đề (Tiếng Việt + Tiếng Anh)
    TOPIC_KEYWORDS = {
        'Kinh tế': {
            'vi': ['kinh tế', 'tài chính', 'ngân hàng', 'chứng khoán', 'cổ phiếu', 'đầu tư', 
                   'thương mại', 'xuất khẩu', 'nhập khẩu', 'gdp', 'lạm phát', 'lãi suất',
                   'doanh nghiệp', 'startup', 'thị trường', 'tăng trưởng', 'suy thoái',
                   'vnd', 'usd', 'tỷ giá', 'nợ công', 'thuế'],
            'en': ['economy', 'finance', 'banking', 'stock', 'investment', 'trade', 'export',
                   'import', 'market', 'growth', 'recession', 'inflation', 'interest rate',
                   'business', 'startup', 'revenue', 'profit', 'loss', 'tax']
        },
        'Công nghệ': {
            'vi': ['công nghệ', 'ai', 'trí tuệ nhân tạo', 'chatgpt', 'robot', 'điện thoại',
                   'smartphone', 'laptop', 'máy tính', 'phần mềm', 'ứng dụng', 'app',
                   'internet', 'mạng', '5g', '6g', 'wifi', 'chip', 'vi xử lý', 'apple',
                   'samsung', 'google', 'microsoft', 'meta', 'amazon', 'tesla', 'spacex'],
            'en': ['technology', 'tech', 'ai', 'artificial intelligence', 'chatgpt', 'gpt',
                   'llm', 'robot', 'smartphone', 'laptop', 'software', 'app', 'internet',
                   '5g', '6g', 'wifi', 'chip', 'processor', 'apple', 'samsung', 'google',
                   'microsoft', 'meta', 'amazon', 'tesla', 'spacex', 'openai', 'cloud']
        },
        'Crypto': {
            'vi': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'tiền điện tử', 'tiền mã hóa',
                   'blockchain', 'nft', 'defi', 'web3', 'metaverse', 'binance', 'coinbase',
                   'trading', 'altcoin', 'token', 'mining', 'đào coin'],
            'en': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 'blockchain',
                   'nft', 'defi', 'web3', 'metaverse', 'binance', 'coinbase', 'trading',
                   'altcoin', 'token', 'mining', 'hodl', 'bullish', 'bearish', 'pump', 'dump']
        },
        'Chính trị': {
            'vi': ['chính trị', 'chính phủ', 'quốc hội', 'bầu cử', 'tổng thống', 'thủ tướng',
                   'bộ trưởng', 'đảng', 'nghị quyết', 'luật', 'chính sách', 'ngoại giao',
                   'quan hệ quốc tế', 'chiến tranh', 'hòa bình', 'nato', 'liên hợp quốc'],
            'en': ['politics', 'government', 'election', 'president', 'prime minister',
                   'minister', 'party', 'congress', 'senate', 'law', 'policy', 'diplomacy',
                   'international', 'war', 'peace', 'nato', 'united nations', 'un', 'biden',
                   'trump', 'putin', 'xi jinping']
        },
        'Thể thao': {
            'vi': ['thể thao', 'bóng đá', 'football', 'world cup', 'euro', 'sea games',
                   'olympic', 'tennis', 'cầu lông', 'bơi lội', 'điền kinh', 'võ thuật',
                   'boxing', 'messi', 'ronaldo', 'hlv', 'huấn luyện viên', 'vô địch'],
            'en': ['sport', 'football', 'soccer', 'basketball', 'nba', 'world cup', 'euro',
                   'olympic', 'tennis', 'badminton', 'swimming', 'boxing', 'mma', 'ufc',
                   'championship', 'tournament', 'player', 'coach', 'messi', 'ronaldo']
        },
        'Giải trí': {
            'vi': ['giải trí', 'phim', 'movie', 'ca sĩ', 'nhạc', 'âm nhạc', 'nghệ sĩ',
                   'diễn viên', 'sao', 'showbiz', 'hollywood', 'netflix', 'disney',
                   'kpop', 'vpop', 'blackpink', 'bts', 'concert', 'liveshow'],
            'en': ['entertainment', 'movie', 'film', 'music', 'singer', 'artist', 'actor',
                   'actress', 'celebrity', 'hollywood', 'netflix', 'disney', 'marvel',
                   'kpop', 'concert', 'album', 'grammy', 'oscar', 'billboard']
        },
        'Sức khỏe': {
            'vi': ['sức khỏe', 'y tế', 'bệnh viện', 'bác sĩ', 'thuốc', 'vaccine', 'tiêm chủng',
                   'covid', 'corona', 'virus', 'dịch bệnh', 'chữa bệnh', 'dinh dưỡng',
                   'tập luyện', 'gym', 'yoga', 'ung thư', 'tim mạch', 'đái tháo đường'],
            'en': ['health', 'medical', 'hospital', 'doctor', 'medicine', 'vaccine', 'vaccination',
                   'covid', 'corona', 'virus', 'pandemic', 'disease', 'treatment', 'nutrition',
                   'fitness', 'gym', 'yoga', 'cancer', 'diabetes', 'heart', 'mental health']
        },
        'Giáo dục': {
            'vi': ['giáo dục', 'học sinh', 'sinh viên', 'trường học', 'đại học', 'cao đẳng',
                   'thi', 'điểm', 'học bổng', 'du học', 'thầy cô', 'giảng viên', 'giáo viên',
                   'tuyển sinh', 'tốt nghiệp', 'bằng cấp', 'chứng chỉ'],
            'en': ['education', 'student', 'school', 'university', 'college', 'exam', 'test',
                   'scholarship', 'study abroad', 'teacher', 'professor', 'graduation',
                   'degree', 'certificate', 'learning', 'course', 'online learning']
        },
        'Du lịch': {
            'vi': ['du lịch', 'travel', 'khách sạn', 'resort', 'nghỉ dưỡng', 'visa', 'hộ chiếu',
                   'vé máy bay', 'đặt phòng', 'tour', 'điểm đến', 'phượt', 'check in'],
            'en': ['travel', 'tourism', 'hotel', 'resort', 'vacation', 'visa', 'passport',
                   'flight', 'booking', 'destination', 'tourist', 'trip', 'journey']
        },
        'Ẩm thực': {
            'vi': ['ẩm thực', 'món ăn', 'nhà hàng', 'quán', 'đầu bếp', 'nấu ăn', 'công thức',
                   'recipe', 'food', 'ngon', 'michelin', 'street food', 'phở', 'bánh mì'],
            'en': ['food', 'cuisine', 'restaurant', 'chef', 'cooking', 'recipe', 'delicious',
                   'michelin', 'street food', 'dish', 'meal', 'dining']
        }
    }
    
    @classmethod
    def classify(cls, text: str, lang: str = None) -> List[str]:
        """
        Classify text into topics based on keywords.
        
        Args:
            text: Text to classify (cleaned)
            lang: Language hint ('vi' or 'en'), optional
            
        Returns:
            List of topic names, sorted by relevance
        """
        if not text:
            return []
        
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords_dict in cls.TOPIC_KEYWORDS.items():
            score = 0
            
            # Check Vietnamese keywords
            if lang == 'vi' or lang is None:
                for keyword in keywords_dict['vi']:
                    # Use word boundary to avoid partial matches
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    matches = len(re.findall(pattern, text_lower))
                    score += matches
            
            # Check English keywords
            if lang == 'en' or lang is None:
                for keyword in keywords_dict['en']:
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    matches = len(re.findall(pattern, text_lower))
                    score += matches
            
            if score > 0:
                topic_scores[topic] = score
        
        # Sort by score descending
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return topics with score > 0, max 3 topics
        return [topic for topic, score in sorted_topics[:3]]
    
    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get list of all available topics."""
        return list(cls.TOPIC_KEYWORDS.keys())
    
    @classmethod
    def add_keywords(cls, topic: str, vi_keywords: List[str] = None, en_keywords: List[str] = None):
        """
        Add custom keywords to existing topic or create new topic.
        
        Args:
            topic: Topic name
            vi_keywords: Vietnamese keywords to add
            en_keywords: English keywords to add
        """
        if topic not in cls.TOPIC_KEYWORDS:
            cls.TOPIC_KEYWORDS[topic] = {'vi': [], 'en': []}
        
        if vi_keywords:
            cls.TOPIC_KEYWORDS[topic]['vi'].extend(vi_keywords)
        if en_keywords:
            cls.TOPIC_KEYWORDS[topic]['en'].extend(en_keywords)


def classify_post_topics(text: str, lang: str = None) -> List[str]:
    """
    Convenience function to classify post topics.
    
    Args:
        text: Post text (cleaned)
        lang: Language hint
        
    Returns:
        List of topic names
    """
    return TopicClassifier.classify(text, lang)
