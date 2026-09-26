"""Downloads the embedding + reranker model weights into the local HF cache.

Run at container startup (not baked into the image) so the ~220MB of model
weight files ship as a runtime download, not as part of the pushed image.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentence_transformers import CrossEncoder, SentenceTransformer

from sebisage.config import EMBEDDING_MODEL, RERANKER_MODEL


def main() -> None:
    SentenceTransformer(EMBEDDING_MODEL)
    CrossEncoder(RERANKER_MODEL)
    print("models warmed")


if __name__ == "__main__":
    main()
