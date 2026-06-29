import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.mongo import get_db
db = get_db()
r1 = db['hotnews_filter_cache'].delete_many({})
r2 = db['hotnews_v2_cache'].delete_many({})
r3 = db['hotnews_summary_cache'].delete_many({})
r4 = db['hotnews_audio_cache'].delete_many({})
print(
    'Cleared: '
    f'filter_cache={r1.deleted_count}, '
    f'v2_cache={r2.deleted_count}, '
    f'summary_cache={r3.deleted_count}, '
    f'audio_cache={r4.deleted_count}'
)
