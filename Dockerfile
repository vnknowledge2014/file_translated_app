# ==========================================
# 1. Frontend Build Stage
# ==========================================
FROM node:22-slim AS frontend-builder
WORKDIR /frontend

# Copy package and install
COPY frontend/package*.json ./
RUN npm install --ignore-scripts

# Copy source and build
COPY frontend/ .
RUN npx @inlang/paraglide-js compile --project project.inlang --outdir src/lib/paraglide
RUN npm run build

# ==========================================
# 2. Production Stage
# ==========================================
FROM python:3.13-slim

LABEL maintainer="Multilingual Translation Tool"
LABEL description="Multilingual document translation powered by AI"

# System deps for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ /app/app/

# Copy built frontend
COPY --from=frontend-builder /frontend/build/ /app/frontend/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Create data directories (owned by appuser)
RUN mkdir -p /data/temp \
    && chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

# Environment defaults (only infrastructure settings that differ between Docker and local)
ENV OLLAMA_URL=http://ollama:11434
ENV LLM_BACKEND=ollama
ENV TEMP_DIR=/data/temp
ENV MAX_WORKERS=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/api/health'); exit(0 if r.status_code==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
