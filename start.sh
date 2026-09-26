#!/bin/sh
set -e

# Model weights aren't baked into the image (see Dockerfile) - download them
# now so the first real /ask request isn't the one paying for it.
python scripts/warm_models.py

uvicorn sebisage.api:app --app-dir src --host 0.0.0.0 --port 8000 &
streamlit run ui/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true &

wait
