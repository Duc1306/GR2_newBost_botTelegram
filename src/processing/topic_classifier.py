"""Topic classification using rule-based keywords.
Phân loại bài viết theo chủ đề dựa trên từ khóa.
"""
from typing import List, Set, Tuple
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
                   'business', 'startup', 'revenue', 'profit', 'loss', 'tax',
                   # Thêm financial institutions
                   'bank', 'federal reserve', 'central bank', 'imf', 'world bank',
                   'goldman sachs', 'jp morgan', 'nasdaq', 'dow jones', 'wall street',
                   'bond', 'treasury', 'yield', 'debt', 'loan', 'credit', 'mortgage']
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
                   'altcoin', 'token', 'mining', 'hodl', 'bullish', 'bearish', 'pump', 'dump',
                   # Thêm keywords cho stablecoin & exchanges
                   'stablecoin', 'usdt', 'usdc', 'dai', 'ripple', 'xrp', 'cardano', 'solana',
                   'polygon', 'polkadot', 'avalanche', 'chainlink', 'uniswap', 'pancakeswap',
                   'gemini', 'kraken', 'ftx', 'webbank', 'mastercard', 'bank of england',
                   'sec', 'regulation', 'etf', 'franklin templeton', 'wallet', 'exchange']
        },
        'Chính trị': {
            'vi': ['chính trị', 'chính phủ', 'quốc hội', 'bầu cử', 'tổng thống', 'thủ tướng',
                   'bộ trưởng', 'đảng cộng sản', 'đảng dân chủ', 'nghị quyết quốc hội', 
                   'ngoại giao', 'ngoại trưởng', 'hội nghị',
                   'tuyên bố chính thức', 'biểu tình', 'cải cách chính trị', 'bỏ phiếu',
                   'ủy ban', 'chủ tịch nước', 'văn phòng chính phủ', 'đảng ủy', 'bí thư'],
            'en': ['politics', 'government', 'parliament', 'election', 'president', 'prime minister',
                   'minister', 'political party', 'congress', 'senate', 'policy', 'diplomacy',
                   'political reform', 'voting', 'protest', 'committee']
        },
        'Thế giới': {
            'vi': ['quốc tế', 'thế giới', 'toàn cầu', 'châu á', 'châu âu', 'châu mỹ',
                   'trung đông', 'đông nam á', 'asean', 'un', 'liên hợp quốc',
                   'nato', 'g7', 'g20', 'eu', 'đại sứ', 'lãnh sự',
                   'hội nghị thượng đỉnh', 'liên minh', 'hiệp định', 'điều ước',
                   'chiến tranh', 'xung đột', 'hòa bình', 'khủng hoảng',
                   'nga', 'ukraine', 'mỹ', 'trung quốc', 'nhật bản', 'hàn quốc',
                   'biden', 'putin', 'xi jinping', 'trump', 'chính sách đối ngoại'],
            'en': ['international', 'world', 'global', 'asia', 'europe', 'america',
                   'middle east', 'asean', 'un', 'united nations', 'nato', 'g7', 'g20', 'eu',
                   'ambassador', 'summit', 'alliance', 'treaty', 'agreement',
                   'war', 'conflict', 'peace', 'crisis', 'foreign policy',
                   'russia', 'ukraine', 'usa', 'china', 'japan', 'korea',
                   'biden', 'putin', 'xi jinping', 'trump',
                   # Thêm keywords cho military & Middle East conflicts
                   'military', 'army', 'navy', 'force', 'general', 'commander', 'soldier',
                   'weapon', 'missile', 'strike', 'attack', 'defense', 'ceasefire',
                   'hamas', 'israel', 'palestine', 'gaza', 'sbu', 'killing', 'defiant',
                   'airstrike', 'bombing', 'invasion', 'occupation', 'refugee',
                   'diplomat', 'diplomatic', 'sanction', 'embargo', 'tension']
        },
        'Pháp luật': {
            'vi': ['luật', 'tòa án', 'tòa', 'phiên tòa', 'xét xử', 'án',
                   'công an', 'cảnh sát', 'kiểm sát', 'viện kiểm sát',
                   'bị cáo', 'bị can', 'nghi phạm', 'tội phạm', 'vi phạm',
                   'bắt giữ', 'khởi tố', 'kết án', 'tuyên án', 'kháng cáo',
                   'luật sư', 'biện hộ', 'hợp đồng', 'tranh chấp',
                   'tham nhũng', 'hối lộ', 'trốn thuế', 'rửa tiền',
                   'ma túy', 'cướp', 'trộm', 'giết người', 'hiếp dâm',
                   'giao thông', 'tai nạn', 'vi phạm giao thông',
                   'quyền lợi', 'khiếu nại', 'tố cáo', 'đơn kiện'],
            'en': ['law', 'court', 'trial', 'judge', 'verdict', 'sentence',
                   'police', 'prosecutor', 'attorney', 'lawyer',
                   'defendant', 'suspect', 'crime', 'criminal', 'violation',
                   'arrest', 'charge', 'conviction', 'appeal',
                   'contract', 'dispute', 'corruption', 'bribery', 'fraud',
                   'drug', 'theft', 'murder', 'rape', 'traffic', 'accident']
        },
        'Ô tô - Xe máy': {
            'vi': ['ô tô', 'xe hơi', 'xe máy', 'xe', 'toyota', 'honda', 'mazda',
                   'vinfast', 'hyundai', 'kia', 'ford', 'bmw', 'mercedes',
                   'suv', 'sedan', 'bán tải', 'crossover', 'hatchback',
                   'xe điện', 'ev', 'hybrid', 'động cơ', 'turbo',
                   'lái xe', 'bằng lái', 'giấy phép', 'đăng kiểm',
                   'giá xe', 'mua xe', 'bán xe', 'thị trường xe',
                   'showroom', 'đại lý', 'ra mắt xe', 'xe mới',
                   'pkl', 'wave', 'vision', 'airblade', 'sirius'],
            'en': ['car', 'automobile', 'motorcycle', 'vehicle', 'toyota', 'honda', 'mazda',
                   'vinfast', 'hyundai', 'kia', 'ford', 'bmw', 'mercedes',
                   'suv', 'sedan', 'pickup', 'crossover', 'hatchback',
                   'electric vehicle', 'ev', 'hybrid', 'engine', 'turbo',
                   'driving', 'license', 'registration',
                   'price', 'buy', 'sell', 'market', 'dealer', 'showroom']
        },
        'Khoa học': {
            'vi': ['khoa học', 'nghiên cứu', 'phát hiện', 'thí nghiệm',
                   'nhà khoa học', 'giáo sư', 'tiến sĩ', 'viện', 'đại học',
                   'sinh học', 'vật lý', 'hóa học', 'toán học', 'thiên văn',
                   'nasa', 'vũ trụ', 'hành tinh', 'mặt trời', 'sao',
                   'tế bào', 'gen', 'dna', 'protein', 'vi khuẩn', 'virus',
                   'khủng long', 'hóa thạch', 'tiến hóa', 'sinh thái',
                   'môi trường', 'biến đổi khí hậu', 'ô nhiễm', 'năng lượng',
                   'năng lượng mặt trời', 'điện gió', 'hydro',
                   'robot', 'trí tuệ nhân tạo', 'học máy', 'dữ liệu'],
            'en': ['science', 'research', 'discovery', 'experiment',
                   'scientist', 'professor', 'doctor', 'institute', 'university',
                   'biology', 'physics', 'chemistry', 'mathematics', 'astronomy',
                   'nasa', 'space', 'planet', 'sun', 'star',
                   'cell', 'gene', 'dna', 'protein', 'bacteria', 'virus',
                   'dinosaur', 'fossil', 'evolution', 'ecology',
                   'environment', 'climate change', 'pollution', 'energy',
                   'solar energy', 'wind power', 'hydrogen',
                   'robot', 'artificial intelligence', 'machine learning', 'data']
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
                   'kpop', 'concert', 'album', 'grammy', 'oscar', 'billboard',
                   'spotify', 'youtube', 'streaming', 'band', 'performance', 'show',
                   'drama', 'series', 'episode', 'season', 'director', 'producer']
        },
        'Sức khỏe': {
            'vi': ['sức khỏe', 'y tế', 'bệnh viện', 'bác sĩ', 'bác sỹ', 'thuốc', 'vaccine', 'tiêm chủng',
                   'covid', 'corona', 'virus', 'vi khuẩn', 'nhiễm trùng', 'nhiễm khuẩn', 'dịch bệnh', 
                   'chữa bệnh', 'khám bệnh', 'xét nghiệm', 'phòng khám', 'điều trị',
                   'dinh dưỡng', 'tập luyện', 'gym', 'yoga', 'ung thư', 'tim mạch', 
                   'đái tháo đường', 'huyết áp', 'tiểu đường', 'sức khoẻ', 'bệnh',
                   'massage', 'xoa bóp', 'châm cứu', 'phẫu thuật', 'nội soi',
                   'tâm lý', 'stress', 'trầm cảm', 'lo âu'],
            'en': ['health', 'medical', 'hospital', 'doctor', 'medicine', 'vaccine', 'vaccination',
                   'covid', 'corona', 'virus', 'bacteria', 'infection', 'pandemic', 'disease', 
                   'treatment', 'diagnosis', 'clinic', 'therapy', 'nutrition',
                   'fitness', 'gym', 'yoga', 'cancer', 'diabetes', 'heart', 'blood pressure',
                   'mental health', 'psychology', 'stress', 'depression', 'anxiety',
                   'massage', 'surgery', 'examination']
        },
        'Giáo dục': {
            'vi': ['giáo dục', 'học sinh', 'sinh viên', 'trường học', 'đại học', 'cao đẳng',
                   'thi', 'điểm', 'học bổng', 'du học', 'thầy cô', 'giảng viên', 'giáo viên',
                   'tuyển sinh', 'tốt nghiệp', 'bằng cấp', 'chứng chỉ'],
            'en': ['education', 'student', 'school', 'university', 'college', 'exam', 'test',
                   'scholarship', 'study abroad', 'teacher', 'professor', 'graduation',
                   'degree', 'certificate', 'learning', 'course', 'online learning']
        },
        'Việc làm': {
            'vi': ['tuyển dụng', 'việc làm', 'công việc', 'nhân viên', 'ứng viên', 'phỏng vấn',
                   'cv', 'hồ sơ', 'lương', 'thu nhập', 'thưởng', 'bảo hiểm', 'hợp đồng',
                   'full-time', 'part-time', 'remote', 'freelance', 'intern', 'thực tập'],
            'en': ['job', 'career', 'hiring', 'recruitment', 'position', 'vacancy', 'opening',
                   'developer', 'engineer', 'designer', 'manager', 'specialist', 'analyst',
                   'full_time', 'part_time', 'remote', 'freelance', 'contract', 'intern',
                   'salary', 'compensation', 'benefits', 'resume', 'cv', 'interview',
                   'full-time', 'part-time', 'full time', 'part time', 'we need', 'we are looking',
                   'apply', 'application', 'candidate', 'experience', 'level', 'junior',
                   'senior', 'lead', 'staff', 'principal', 'company', 'location', 'anywhere']
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
    def classify_with_scores(cls, text: str, lang: str = None) -> List[Tuple[str, int]]:
        """
        Classify text and return (topic, score) pairs sorted by score descending.
        Score = total keyword match count for that topic.
        """
        if not text:
            return []

        text_lower = text.lower()
        topic_scores = {}

        for topic, keywords_dict in cls.TOPIC_KEYWORDS.items():
            score = 0
            if lang == 'vi' or lang is None:
                for keyword in keywords_dict['vi']:
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    score += len(re.findall(pattern, text_lower))
            if lang == 'en' or lang is None:
                for keyword in keywords_dict['en']:
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    score += len(re.findall(pattern, text_lower))
            if score > 0:
                topic_scores[topic] = score

        return sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)

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
