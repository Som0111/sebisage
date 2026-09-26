FROM python:3.11-slim

# Non-root user
RUN useradd --create-home --uid 1000 sebisage
WORKDIR /app

# ponytail: no apt-get / build-essential here - torch, pymupdf, chromadb and
# sentence-transformers all ship prebuilt manylinux wheels for this
# python:3.11-slim base, so there's nothing to compile. Add a compiler stage
# back only if a future dependency genuinely needs to build from source.

COPY pyproject.toml ./
COPY src ./src

# CPU-only torch first, matching local dev setup - keeps the image small and
# avoids pulling CUDA wheels that are useless on Hugging Face Spaces' free CPU tier.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e .

COPY data/processed ./data/processed
COPY scripts ./scripts
COPY ui ./ui
COPY reports ./reports
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Bake in the embedding/reranker models and the dense+BM25 indexes at build
# time (not first request) - downloads bge-small + the cross-encoder via
# build_index.py's model loading, and builds storage/chroma + storage/bm25_*.pkl
# from the committed data/processed/ chunks (public regulation text).
RUN python scripts/build_index.py --chunker all

RUN chown -R sebisage:sebisage /app
USER sebisage

ENV PYTHONUNBUFFERED=1
EXPOSE 8000 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()"

CMD ["./start.sh"]
