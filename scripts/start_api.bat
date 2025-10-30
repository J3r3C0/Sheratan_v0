@echo off
REM Start Sheratan API (FastAPI) on port 8000
setlocal
if not exist .venv (
  echo Creating venv...
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt
uvicorn core.api.app:app --reload --host 0.0.0.0 --port 8000
