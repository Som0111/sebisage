# --- Stage 1: build the dense+BM25 indexes ---
# This stage needs the embedding/reranker models to compute embeddings, but
# its filesystem (including the ~220MB of downloaded model weights) is never
# copied into the final image - only the resulting storage/ (~27MB of index
# files) crosses the stage boundary. Models themselves are downloaded fresh at
# container startup instead (see start.sh) - that's the actual image-size win
# here, not baking the indexes (which are cheap and worth keeping precomputed).
FROM python:3.11-slim AS indexer
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e .
COPY data/processed ./data/processed
COPY scripts ./scripts
RUN python scripts/build_index.py --chunker all

# --- Stage 2: runtime image ---
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
# avoids pulling CUDA wheels that are useless on free CPU tiers.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e .

COPY --from=indexer /app/storage ./storage
COPY data/processed ./data/processed
COPY scripts ./scripts
COPY ui ./ui
COPY reports ./reports
COPY start.sh ./start.sh
RUN chmod +x start.sh

RUN chown -R sebisage:sebisage /app
USER sebisage

ENV PYTHONUNBUFFERED=1
EXPOSE 8000 7860

# start-period bumped from 60s: start.sh now downloads model weights before
# uvicorn even starts listening (see start.sh), which the image-build no
# longer pays for.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()"

CMD ["./start.sh"]
