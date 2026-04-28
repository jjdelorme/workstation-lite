# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Backend & Serve
FROM python:3.11-slim
WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/app ./app

# Copy built frontend assets to the location FastAPI expects
COPY --from=frontend-builder /app/backend/app/static ./app/static

# Expose port required by Cloud Run
ENV PORT=8080
EXPOSE 8080

# Run Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
