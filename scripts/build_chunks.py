"""Runs the chunkers and writes data/processed/chunks_*.jsonl and reports/chunk_stats.json."""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import PROCESSED_DIR, RAW_DIR, REPORTS_DIR
from sebisage.ingest.chunk import count_tokens, fixed_chunks, structured_chunks
from sebisage.ingest.parse_pdf import parse
from sebisage.ingest.schema import Chunk

SOURCE_FILES = ["lodr_2015.pdf", "pit_2015.pdf", "sast_2011.pdf", "ia_2013.pdf", "ra_2014.pdf"]


def _chunk_to_dict(c: Chunk) -> dict:
    return {
        "id": c.id,
        "text": c.text,
        "regulation": c.regulation,
        "reg_no": c.reg_no,
        "sub_reg": c.sub_reg,
        "chapter": c.chapter,
        "page_start": c.page_start,
        "page_end": c.page_end,
        "source_file": c.source_file,
        "chunker": c.chunker,
    }


def _write_jsonl(path: Path, chunks: list[Chunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(_chunk_to_dict(c), ensure_ascii=False) + "\n")


def _stats_for(chunks: list[Chunk], per_file: dict) -> None:
    for c in chunks:
        per_file.setdefault(c.source_file, {"count": 0, "tokens": [], "with_reg_no": 0})
        entry = per_file[c.source_file]
        entry["count"] += 1
        entry["tokens"].append(count_tokens(c.text))
        if c.reg_no:
            entry["with_reg_no"] += 1


def main() -> None:
    structured_all: list[Chunk] = []
    fixed_all: list[Chunk] = []
    structured_stats: dict = {}

    for source_file in SOURCE_FILES:
        regulation = source_file.removesuffix(".pdf")
        pages = parse(RAW_DIR / source_file)
        structured = structured_chunks(pages, source_file, regulation)
        fixed = fixed_chunks(pages, source_file, regulation)
        structured_all.extend(structured)
        fixed_all.extend(fixed)
        _stats_for(structured, structured_stats)

    _write_jsonl(PROCESSED_DIR / "chunks_structured.jsonl", structured_all)
    _write_jsonl(PROCESSED_DIR / "chunks_fixed.jsonl", fixed_all)

    report = {"files": {}, "totals": {}}
    total_count = 0
    total_with_reg_no = 0
    all_tokens: list[int] = []
    for source_file, entry in structured_stats.items():
        tokens = entry["tokens"]
        report["files"][source_file] = {
            "count": entry["count"],
            "mean_tokens": round(statistics.mean(tokens), 1) if tokens else 0,
            "median_tokens": statistics.median(tokens) if tokens else 0,
            "max_tokens": max(tokens) if tokens else 0,
            "pct_with_reg_no": round(100 * entry["with_reg_no"] / entry["count"], 1) if entry["count"] else 0,
        }
        total_count += entry["count"]
        total_with_reg_no += entry["with_reg_no"]
        all_tokens.extend(tokens)

    report["totals"] = {
        "structured_chunk_count": total_count,
        "fixed_chunk_count": len(fixed_all),
        "mean_tokens": round(statistics.mean(all_tokens), 1) if all_tokens else 0,
        "median_tokens": statistics.median(all_tokens) if all_tokens else 0,
        "max_tokens": max(all_tokens) if all_tokens else 0,
        "pct_with_reg_no": round(100 * total_with_reg_no / total_count, 1) if total_count else 0,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "chunk_stats.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"structured chunks: {total_count} ({report['totals']['pct_with_reg_no']}% with reg_no)")
    print(f"fixed chunks: {len(fixed_all)}")


if __name__ == "__main__":
    main()
