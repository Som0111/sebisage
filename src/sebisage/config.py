"""All paths, model names, thresholds and numeric settings for SebiSage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Paths ---
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EVAL_DIR = DATA_DIR / "eval"
STORAGE_DIR = ROOT / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
CACHE_DIR = ROOT / ".cache" / "llm"

# --- Models ---
# Chosen at Phase 0.2 after checking live Gemini free-tier availability.
# Alias, not a pinned snapshot: Google repoints it to the current flash-lite
# model, so this stays valid without edits as models are deprecated.
GEMINI_MODEL = "gemini-flash-lite-latest"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# --- Chunking ---
MAX_CHUNK_TOKENS = 400
MIN_CHUNK_TOKENS = 40
FIXED_CHUNK_SIZE = 500
FIXED_CHUNK_OVERLAP = 50

# --- Retrieval ---
K_DENSE = 20
K_SPARSE = 20
RRF_K = 60
K_FUSED = 20
K_FINAL = 5
REFUSE_THRESHOLD = 3.5  # set at Phase 5.3 from dev-set top rerank scores (see HUMAN_GUIDE.md)

# --- Eval ---
EVAL_SPLIT_SEED = 42
EVAL_DEV_FRACTION = 0.6

# --- Generation ---
ANSWER_MAX_WORDS = 150
MAX_WAIT_S = 60
REQUEST_TIMEOUT_S = 90  # hard cap per LLM call; the underlying SDK has none by default

# --- Agent / memory ---
MEMORY_TURNS = 4

# --- API ---
SESSION_TTL_S = 3600
RATE_LIMIT_PER_MIN = 10

# --- Cost estimate (USD per 1K tokens), for display only ---
COST_PER_1K_INPUT = 0.0
COST_PER_1K_OUTPUT = 0.0
