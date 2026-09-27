from pathlib import Path


VECTOR_TOP_K = 10
KEYWORD_TOP_K = 10
FINAL_TOP_K = 5
RRF_K = 60
HYBRID_SOURCE_DIVERSITY_SCORE_MARGIN = 0.005

KEYWORD_INDEX_PATH = (
    Path(__file__).resolve().parents[2]
    / "chroma_db"
    / "keyword_index.sqlite3"
)
