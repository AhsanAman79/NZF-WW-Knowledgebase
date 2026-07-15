# ---------- Stage 1: build the frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: python runtime ----------
FROM python:3.12-slim
WORKDIR /app

# Install backend dependencies first (better layer caching)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Backend source
COPY backend/ backend/

# Built frontend from stage 1 (served by FastAPI at "/")
COPY --from=frontend /build/dist frontend/dist

ENV DATA_DIR=/app/backend/data
EXPOSE 8000
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
