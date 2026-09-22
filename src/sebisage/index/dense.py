"""Chroma build/load for the dense vector index."""

import chromadb
from chromadb.errors import NotFoundError
from sentence_transformers import SentenceTransformer

from sebisage.config import CHROMA_DIR, EMBEDDING_MODEL
from sebisage.ingest.schema import Chunk

# BAAI/bge-small-en-v1.5's documented asymmetric-retrieval convention:
# prefix queries (not documents) with this instruction so query and
# document embeddings are comparable.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _client() -> chromadb.ClientAPI:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection_name(chunker: str) -> str:
    return f"sebisage_{chunker}"


def _chunk_metadata(c: Chunk) -> dict:
    return {
        "regulation": c.regulation,
        "reg_no": c.reg_no or "",
        "sub_reg": c.sub_reg or "",
        "chapter": c.chapter or "",
        "page_start": c.page_start,
        "page_end": c.page_end,
        "source_file": c.source_file,
        "chunker": c.chunker,
    }


def build_dense(chunks: list[Chunk], chunker: str, batch_size: int = 64) -> int:
    """Rebuild the dense collection for `chunker` from scratch. Returns count indexed."""
    client = _client()
    name = _collection_name(chunker)
    try:
        client.delete_collection(name)
    except NotFoundError:
        pass
    collection = client.create_collection(name)

    model = _get_model()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = model.encode([c.text for c in batch], normalize_embeddings=True).tolist()
        collection.add(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[_chunk_metadata(c) for c in batch],
            embeddings=embeddings,
        )
    return len(chunks)


def load_collection(chunker: str) -> chromadb.Collection:
    return _client().get_collection(_collection_name(chunker))


def query_dense(query: str, chunker: str, k: int) -> list[dict]:
    collection = load_collection(chunker)
    model = _get_model()
    embedding = model.encode([QUERY_INSTRUCTION + query], normalize_embeddings=True).tolist()
    result = collection.query(query_embeddings=embedding, n_results=k)
    hits = []
    for i in range(len(result["ids"][0])):
        hits.append(
            {
                "id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            }
        )
    return hits
