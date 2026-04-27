"""FastAPI application with lifespan, CORS, and route registration."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.llm.factory import create_llm_client
from app.worker import WorkerPool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB + Ollama client."""
    # Startup SurrealDB
    await init_db()
    # Select LLM backend
    app.state.llm_client = create_llm_client(
        url=settings.OLLAMA_URL,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    # Keep backward-compatible alias
    app.state.ollama_client = app.state.llm_client

    # Ensure directories exist
    for d in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        os.makedirs(d, exist_ok=True)

    # Start worker pool (bounded by MAX_WORKERS)
    pool = WorkerPool(max_workers=settings.MAX_WORKERS)
    app.state.worker_pool = pool
    await pool.start()

    yield

    # Shutdown worker pool first (let active jobs finish)
    await pool.shutdown()

    # Shutdown
    await app.state.llm_client.close()
    from app.database import close_db
    await close_db()


app = FastAPI(
    title="Multilingual Document Translation",
    description="Air-gapped multilingual document translation system powered by local LLM",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Import and register routes ──
from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.upload import router as upload_router  # noqa: E402
from app.routes.jobs import router as jobs_router  # noqa: E402
from app.routes.download import router as download_router  # noqa: E402
from app.routes.xliff import router as xliff_router  # noqa: E402
from app.routes.segments import router as segments_router  # noqa: E402
from app.routes.glossary import router as glossary_router  # noqa: E402

app.include_router(auth_router, tags=["Auth"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(download_router, prefix="/api", tags=["Download"])
app.include_router(xliff_router, prefix="/api", tags=["XLIFF"])
app.include_router(segments_router, prefix="/api", tags=["Segments"])
app.include_router(glossary_router, prefix="/api", tags=["Glossary"])


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    llm_ok = await app.state.llm_client.health_check()
    pool = app.state.worker_pool
    return {
        "status": "ok",
        "llm_backend": "ollama",
        "llm": "connected" if llm_ok else "disconnected",
        "workers": {
            "max": pool.max_workers,
            "active": pool.active_count,
            "queued": pool.queue_size,
        },
    }

from app.languages import list_languages
from app.domains import list_supported_domains

@app.get("/api/languages", tags=["Meta"])
async def get_languages():
    """Get all supported languages."""
    return list_languages()

@app.get("/api/domains", tags=["Meta"])
async def get_domains():
    """Get all supported domains."""
    return list_supported_domains()


# ── Serve frontend static files ──
# In Docker: built SvelteKit output is at /app/frontend
# For local dev: run SvelteKit dev server separately (npm run dev)
FRONTEND_DIR = "/app/frontend"
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
