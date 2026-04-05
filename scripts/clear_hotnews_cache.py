from src.db.mongo import get_db
db = get_db()
r1 = db['hotnews_filter_cache'].delete_many({})
r2 = db['hotnews_v2_cache'].delete_many({})
r3 = db['hotnews_summary_cache'].delete_many({})
print(f'Cleared: filter_cache={r1.deleted_count}, v2_cache={r2.deleted_count}, summary_cache={r3.deleted_count}')
