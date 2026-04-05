(cd frontend && npm run build) && cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8080 --host 0.0.0.0
