"""
Category Mapper - Chuyển đổi category từ tiếng Anh sang tiếng Việt
Map các category từ channel.json (tiếng Anh) sang các topic chuẩn tiếng Việt
"""

# Mapping từ category tiếng Anh sang topic tiếng Việt chuẩn
CATEGORY_TO_TOPIC = {
    # Auto & Moto
    'Auto & Moto': 'Ô tô - Xe máy',
    'auto': 'Ô tô - Xe máy',
    'moto': 'Ô tô - Xe máy',
    'automotive': 'Ô tô - Xe máy',
    'cars': 'Ô tô - Xe máy',
    'vehicles': 'Ô tô - Xe máy',
    
    # Movies / Phim ảnh
    'movies': 'Giải trí',
    'movie': 'Giải trí',
    'films': 'Giải trí',
    'cinema': 'Giải trí',
    
    # Books & Magazine
    'Books & Magazine': 'Giáo dục',
    'Books & Magazine ': 'Giáo dục',  # Có khoảng trắng thừa trong channel.json
    'books': 'Giáo dục',
    'magazine': 'Giáo dục',
    'reading': 'Giáo dục',
    
    # Business & Startups
    'Business & Startups': 'Kinh doanh & Khởi nghiệp',
    'business': 'Kinh doanh & Khởi nghiệp',
    'startups': 'Kinh doanh & Khởi nghiệp',
    'startup': 'Kinh doanh & Khởi nghiệp',
    'entrepreneurship': 'Kinh doanh & Khởi nghiệp',
    
    # Crypto
    'Crypto': 'Crypto',
    'crypto': 'Crypto',
    'cryptocurrency': 'Crypto',
    'bitcoin': 'Crypto',
    'blockchain': 'Crypto',
    'defi': 'Crypto',
    'nft': 'Crypto',
    
    # Economics & Finance
    'Economics & Finance': 'Kinh tế',
    'economics': 'Kinh tế',
    'finance': 'Kinh tế',
    'financial': 'Kinh tế',
    'economy': 'Kinh tế',
    'markets': 'Kinh tế',
    'investing': 'Kinh tế',
    'investment': 'Kinh tế',
    
    # Education
    'Education': 'Giáo dục',
    'education': 'Giáo dục',
    'learning': 'Giáo dục',
    'academic': 'Giáo dục',
    'school': 'Giáo dục',
    
    # Entertainment
    'Entertainment': 'Giải trí',
    'entertainment': 'Giải trí',
    'fun': 'Giải trí',
    'showbiz': 'Giải trí',
    'celebrity': 'Giải trí',
    'music': 'Giải trí',
    
    # Food
    'Food': 'Ẩm thực',
    'food': 'Ẩm thực',
    'cooking': 'Ẩm thực',
    'recipes': 'Ẩm thực',
    'dining': 'Ẩm thực',
    'restaurant': 'Ẩm thực',
    
    # Games & Apps
    'Games & Apps': 'Trò chơi & Ứng dụng',
    'games': 'Trò chơi & Ứng dụng',
    'gaming': 'Trò chơi & Ứng dụng',
    'apps': 'Trò chơi & Ứng dụng',
    'applications': 'Trò chơi & Ứng dụng',
    
    # Health
    'Health': 'Sức khỏe',
    'health': 'Sức khỏe',
    'medical': 'Sức khỏe',
    'healthcare': 'Sức khỏe',
    'wellness': 'Sức khỏe',
    'fitness': 'Sức khỏe',
    
    # News & Media
    'News & Media': 'Tin tức & Truyền thông',
    'news': 'Tin tức & Truyền thông',
    'media': 'Tin tức & Truyền thông',
    'journalism': 'Tin tức & Truyền thông',
    
    # Other / Khác
    'Other': 'Khác',
    'other': 'Khác',
    'misc': 'Khác',
    'miscellaneous': 'Khác',
    
    # Political / Chính trị
    'Political': 'Chính trị',
    'politics': 'Chính trị',
    'government': 'Chính trị',
    'policy': 'Chính trị',
    
    # Science
    'Science': 'Khoa học',
    'science': 'Khoa học',
    'scientific': 'Khoa học',
    'research': 'Khoa học',
    
    # Sports
    'Sports': 'Thể thao',
    'sport': 'Thể thao',
    'sports': 'Thể thao',
    'football': 'Thể thao',
    'soccer': 'Thể thao',
    'basketball': 'Thể thao',
    
    # Technology
    'Technology': 'Công nghệ',
    'technology': 'Công nghệ',
    'tech': 'Công nghệ',
    'IT': 'Công nghệ',
    'software': 'Công nghệ',
    'hardware': 'Công nghệ',
    
    # Travel
    'Travel': 'Du lịch',
    'travel': 'Du lịch',
    'tourism': 'Du lịch',
    'destinations': 'Du lịch',
    'vacation': 'Du lịch',
}


def map_category_to_topic(category: str) -> str:
    """
    Chuyển đổi category từ tiếng Anh sang topic tiếng Việt
    
    Args:
        category: Category từ channel.json (tiếng Anh)
    
    Returns:
        Topic tiếng Việt tương ứng, hoặc 'Khác' nếu không tìm thấy
    """
    if not category:
        return 'Khác'
    
    # Chuẩn hóa: loại bỏ khoảng trắng thừa, chuyển về lowercase để so sánh
    category_normalized = category.strip()
    
    # Thử match chính xác trước
    if category_normalized in CATEGORY_TO_TOPIC:
        return CATEGORY_TO_TOPIC[category_normalized]
    
    # Thử match lowercase
    category_lower = category_normalized.lower()
    if category_lower in CATEGORY_TO_TOPIC:
        return CATEGORY_TO_TOPIC[category_lower]
    
    # Không tìm thấy -> trả về 'Khác'
    print(f"⚠️ Không tìm thấy mapping cho category: '{category}' -> sử dụng 'Khác'")
    return 'Khác'


def get_all_vietnamese_topics() -> list[str]:
    """Lấy danh sách tất cả các topic tiếng Việt (unique)"""
    return sorted(list(set(CATEGORY_TO_TOPIC.values())))


if __name__ == "__main__":
    # Test mapping
    print("=== Test Category Mapping ===")
    test_categories = [
        "Auto & Moto",
        "movies",
        "Books & Magazine ",
        "Business & Startups",
        "Crypto",
        "Economics & Finance",
        "Education",
        "Entertainment",
        "Food",
        "Games & Apps",
        "Health",
        "News & Media",
        "Other",
        "Political",
        "Science",
        "Sports",
        "Technology",
        "Travel",
    ]
    
    for cat in test_categories:
        topic = map_category_to_topic(cat)
        print(f"{cat:25} → {topic}")
    
    print("\n=== Danh sách Topic tiếng Việt ===")
    for topic in get_all_vietnamese_topics():
        print(f"  • {topic}")
