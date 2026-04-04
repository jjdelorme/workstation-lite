(cd frontend && npm run build) && rm -rf backend/app/static && cp -r frontend/dist backend/app/static && cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8080
