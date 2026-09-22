"""BM25 build/load (pickled)."""

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from sebisage.config import STORAGE_DIR
from sebisage.ingest.schema import Chunk

# Keeps tokens like "30(6)" and "kmp" intact instead of splitting on
# parentheses/digits, since legal text search depends on exact identifiers.
_TOKEN_RE = re.compile(r"[a-z0-9()]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _path(chunker: str) -> Path:
    return STORAGE_DIR / f"bm25_{chunker}.pkl"


def build_bm25(chunks: list[Chunk], chunker: str) -> int:
    """Rebuild the BM25 index for `chunker` from scratch. Returns count indexed."""
    ids = [c.id for c in chunks]
    corpus = [tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with _path(chunker).open("wb") as f:
        pickle.dump({"ids": ids, "bm25": bm25}, f)
    return len(chunks)


def load_bm25(chunker: str) -> tuple[BM25Okapi, list[str]]:
    with _path(chunker).open("rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["ids"]


def query_bm25(query: str, chunker: str, k: int) -> list[tuple[str, float]]:
    bm25, ids = load_bm25(chunker)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(zip(ids, scores, strict=True), key=lambda x: x[1], reverse=True)
    return ranked[:k]
