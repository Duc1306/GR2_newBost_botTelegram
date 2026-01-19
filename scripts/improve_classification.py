#!/usr/bin/env python
"""
Cải thiện classification coverage bằng cách thêm English keywords.
"""

import sys
sys.path.append('.')

from src.db.mongo import get_posts_collection

def analyze_unclassified_posts():
    """Phân tích posts chưa được classify"""
    coll = get_posts_collection()
    
    # Posts không có topics
    no_topics = coll.count_documents({'topics': []})
    
    print(f"\n📊 PHÂN TÍCH {no_topics:,} POSTS CHƯA CÓ TOPICS\n")
    print("="*80)
    
    # Đếm theo ngôn ngữ
    from collections import Counter
    langs = Counter()
    samples = {}
    
    for p in coll.find({'topics': []}, {'lang': 1, 'text': 1, 'id': 1}).limit(no_topics):
        lang = p.get('lang') or 'unknown'
        langs[lang] += 1
        
        if lang not in samples:
            samples[lang] = {
                'id': p.get('id'),
                'text': p.get('text', '')[:100]
            }
    
    print("\n🌐 PHÂN BỐ THEO NGÔN NGỮ:\n")
    for lang, count in langs.most_common(10):
        pct = count / no_topics * 100
        print(f"{lang:10s}: {count:6,} ({pct:5.1f}%)")
        if lang in samples:
            sample = samples[lang]
            print(f"             Sample: {sample['text']}...")
            print()
    
    print("\n" + "="*80)
    print("\n💡 KHUYẾN NGHỊ:")
    print("1. Thêm English keywords vào topic_classifier.py")
    print("2. Giảm min_text_length từ 20 → 10 chars")
    print("3. Train ML model cho fallback")
    print("4. Thêm fuzzy matching cho keywords")
    print()

if __name__ == "__main__":
    analyze_unclassified_posts()
