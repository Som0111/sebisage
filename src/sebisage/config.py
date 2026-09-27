"""All paths, model names, thresholds and numeric settings for SebiSage."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_app_version() -> str:
    """Reads the version from pyproject.toml so it never drifts from a
    duplicated constant here."""
    try:
        with (ROOT / "pyproject.toml").open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError):
        return "unknown"


APP_VERSION = _read_app_version()

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
WEB_CACHE_DIR = ROOT / ".cache" / "web"

# --- Models ---
# Chosen at Phase 0.2 after checking live Gemini free-tier availability.
# Alias, not a pinned snapshot: Google repoints it to the current flash-lite
# model, so this stays valid without edits as models are deprecated.
GEMINI_MODEL = "gemini-flash-lite-latest"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Measured on CPU over 20 (query, chunk) pairs (see reports/reranker_latency_experiment.md):
# no explicit batch_size ~6060ms median, batch_size=8 ~2940ms, batch_size=16 ~5360ms.
# 8 is fastest for this candidate-set size; same model/inputs, so retrieval quality is unaffected.
RERANKER_BATCH_SIZE = 8

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

# --- Recent/live web route: fetching official SEBI content instead of snippets only ---
SEBI_ALLOWED_DOMAINS: list[str] = [
    "sebi.gov.in",
    "www.sebi.gov.in",
]
WEB_CACHE_TTL_HOURS = 48
WEB_FETCH_TIMEOUT_S = 10
WEB_FETCH_MAX_BYTES = 512_000
WEB_FETCH_PDF_MAX_PAGES = 20
WEB_FETCH_MAX_CHARS = 6000
WEB_FETCH_USER_AGENT = "SebiSage-research-bot/1.0 (educational project)"

# --- Eval ---
EVAL_SPLIT_SEED = 42
EVAL_DEV_FRACTION = 0.6
GATE_TOLERANCE = 0.05  # CI retrieval gate: allowed MRR@10 drop below reports/retrieval_baseline.json

# --- Generation ---
ANSWER_MAX_WORDS = 150
MAX_WAIT_S = 60
REQUEST_TIMEOUT_S = 90  # hard cap per LLM call; the underlying SDK has none by default

# --- Agent / memory ---
MEMORY_TURNS = 4

# --- API ---
SESSION_TTL_S = 3600
RATE_LIMIT_PER_MIN = 10
MAX_QUESTION_CHARS = 2000
API_KEY_HEADER = "X-API-Key"
API_PORT = 8000  # matches Phase 9's Docker layout (API 8000, UI 7860)
UI_PORT = 7860

# --- UI ---
COVERED_REGULATIONS = ["LODR 2015", "PIT 2015", "SAST 2011", "IA 2013", "RA 2014"]
EXAMPLE_QUESTIONS = [
    "When must a listed company disclose a material event?",
    "What is a 'connected person' under the PIT Regulations?",
    "At what shareholding threshold must an acquirer make an open offer?",
    "What happens if a listed entity fails to pay a fine imposed on it by the stock exchange?",
    "What must a research analyst maintain records of?",
    "What is the current repo rate set by the Reserve Bank of India?",
]

# --- Cost estimate (USD per 1K tokens), for display only ---
# GEMINI_MODEL is an alias ("-latest"), so its exact resolved price varies by
# provider updates; these are Gemini 3.1 Flash-Lite's published per-1M-token
# rates ($0.25 in / $1.50 out) as a representative mid-range estimate, not a
# live-queried price. Always shown to the user/API caller labelled "estimate".
COST_PER_1K_INPUT = 0.00025
COST_PER_1K_OUTPUT = 0.0015
