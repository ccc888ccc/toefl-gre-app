# ---------- stage 1: build the frontend ----------
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/ ./
RUN npm install --no-audit --no-fund && npm run build

# ---------- stage 2: backend that also serves the built frontend ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY seed/ /app/seed/
COPY --from=frontend /fe/dist /app/frontend/dist
# DB lives on a mounted volume so data survives container rebuilds
ENV DATABASE_URL=sqlite:////data/app.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
