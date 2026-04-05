import sys, json, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
print("START")
sys.path.insert(0, '.')

try:
    from src.processing.ai_topic_detector import summarize_cluster
    result = summarize_cluster([
        {'text': 'Iran de doa tan cong can cu My tai Trung Dong, Bo truong Quoc phong Hoa Ky phan ung.'},
        {'text': 'IRGC canh bao se tan cong co so cong nghe My neu xung dot leo thang.'},
        {'text': 'My dua tau chien toi vinh Persian de ran de Iran sau canh bao cua IRGC.'},
    ], topic_name='Iran - My xung dot')
    print("\n=== RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print("ERROR:", e)
    import traceback; traceback.print_exc()
