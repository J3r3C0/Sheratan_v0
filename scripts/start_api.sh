#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv || true
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
uvicorn core.api.app:app --reload --host 0.0.0.0 --port 8000
