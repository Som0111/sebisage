#!/bin/sh
set -e

uvicorn sebisage.api:app --app-dir src --host 0.0.0.0 --port 8000 &
streamlit run ui/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true &

wait
