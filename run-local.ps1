# First run only: Copy-Item .env.example .env
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -r requirements.txt
& .\.venv\Scripts\python -m uvicorn app.main:app --reload
