FROM python:3.13-slim

LABEL maintainer="JP-VI Translation Tool"
LABEL description="Air-gapped Japanese-to-Vietnamese document translation"

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

# Copy frontend
COPY frontend/ /app/frontend/

# Create data directories
RUN mkdir -p /data/uploads /data/output /data/temp /data/db

# Environment defaults
ENV OLLAMA_URL=http://ollama:11434
ENV MODEL=gemma4:e4b
ENV DATABASE_URL=sqlite:///data/db/translations.db
ENV UPLOAD_DIR=/data/uploads
ENV OUTPUT_DIR=/data/output
ENV TEMP_DIR=/data/temp
ENV MAX_WORKERS=1
ENV MAX_CONCURRENT_BATCHES=4

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/api/health'); exit(0 if r.status_code==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
