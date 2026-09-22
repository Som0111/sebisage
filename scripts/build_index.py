"""Builds dense + BM25 indexes from data/processed/. Usage: --chunker structured|fixed|all."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import PROCESSED_DIR, REPORTS_DIR, STORAGE_DIR
from sebisage.index.dense import build_dense
from sebisage.index.sparse import build_bm25
from sebisage.ingest.schema import Chunk

CHUNKERS = ["structured", "fixed"]


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _load_chunks(chunker: str) -> list[Chunk]:
    path = PROCESSED_DIR / f"chunks_{chunker}.jsonl"
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(Chunk(**json.loads(line)))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunker", choices=["structured", "fixed", "all"], default="all")
    args = parser.parse_args()
    targets = CHUNKERS if args.chunker == "all" else [args.chunker]

    stats_path = REPORTS_DIR / "index_stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}

    for chunker in targets:
        chunks = _load_chunks(chunker)

        t0 = time.perf_counter()
        dense_count = build_dense(chunks, chunker)
        dense_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        bm25_count = build_bm25(chunks, chunker)
        bm25_s = time.perf_counter() - t0

        stats[chunker] = {
            "chunk_count": len(chunks),
            "dense_build_seconds": round(dense_s, 2),
            "dense_indexed_count": dense_count,
            "bm25_build_seconds": round(bm25_s, 2),
            "bm25_indexed_count": bm25_count,
            "bm25_pickle_bytes": (STORAGE_DIR / f"bm25_{chunker}.pkl").stat().st_size,
        }
        print(f"{chunker}: {len(chunks)} chunks -> dense {dense_s:.2f}s, bm25 {bm25_s:.2f}s")

    stats["chroma_dir_bytes"] = _dir_size(STORAGE_DIR / "chroma")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
