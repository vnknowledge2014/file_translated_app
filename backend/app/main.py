"""FastAPI application with lifespan, CORS, and route registration."""

import os
from contextlib import asynccontextmanager

# Initialize structured logging before any other imports
from app.logging_config import setup_logging

setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.storage import storage
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
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

    # Initialize MinIO buckets
    storage.init_buckets()

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
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


# ── Import and register routes ──
from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.upload import router as upload_router  # noqa: E402
from app.routes.jobs import router as jobs_router  # noqa: E402
from app.routes.download import router as download_router  # noqa: E402
from app.routes.xliff import router as xliff_router  # noqa: E402
from app.routes.segments import router as segments_router  # noqa: E402
from app.routes.glossary import router as glossary_router  # noqa: E402
from app.routes.api_keys import router as api_keys_router  # noqa: E402
from app.routes.wallet_auth import router as wallet_auth_router  # noqa: E402
from app.routes.billing import router as billing_router  # noqa: E402
from app.routes.admin import router as admin_router  # noqa: E402

app.include_router(auth_router, tags=["Auth"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(download_router, prefix="/api", tags=["Download"])
app.include_router(xliff_router, prefix="/api", tags=["XLIFF"])
app.include_router(segments_router, prefix="/api", tags=["Segments"])
app.include_router(glossary_router, prefix="/api", tags=["Glossary"])
app.include_router(api_keys_router, tags=["API Keys"])
app.include_router(wallet_auth_router, tags=["Wallet Auth"])
app.include_router(billing_router, tags=["Billing"])
app.include_router(admin_router, tags=["Admin"])


@app.get("/api/health")
async def health():
    """Health check endpoint — includes LLM, SurrealDB, and worker status."""
    llm_ok = await app.state.llm_client.health_check()
    pool = app.state.worker_pool

    # Check SurrealDB connectivity
    db_ok = False
    try:
        from app.database import db

        await db.query("INFO FOR DB;")
        db_ok = True
    except Exception:
        pass

    overall = "ok" if (llm_ok and db_ok) else "degraded"
    return {
        "status": overall,
        "llm_backend": "ollama",
        "llm": "connected" if llm_ok else "disconnected",
        "database": "connected" if db_ok else "disconnected",
        "model": settings.MODEL,
        "workers": {
            "max": pool.max_workers,
            "active": pool.active_count,
            "queued": pool.queue_size,
        },
    }


from app.languages import list_languages
from app.domains import list_supported_domains
from app.llm.model_router import model_router


@app.get("/api/languages", tags=["Meta"])
async def get_languages():
    """Get all supported languages."""
    return list_languages()


@app.get("/api/domains", tags=["Meta"])
async def get_domains():
    """Get all supported domains."""
    return list_supported_domains()


@app.get("/api/model-routes", tags=["Meta"])
async def get_model_routes():
    """Get all configured model routes for debugging."""
    return model_router.list_routes()


# ── Serve frontend static files with SPA fallback ──
# In Docker: built SvelteKit output is at /app/frontend
# For local dev: run SvelteKit dev server separately (npm run dev)
FRONTEND_DIR = "/app/frontend"
if os.path.isdir(FRONTEND_DIR):
    from fastapi.responses import FileResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    # Mount static assets first (_app/, etc.)
    app.mount(
        "/_app",
        StaticFiles(directory=os.path.join(FRONTEND_DIR, "_app")),
        name="static_app",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """SPA fallback: serve matching HTML file or fallback to index.html.

        Resolution order:
        1. Exact file match (e.g., robots.txt)
        2. {path}.html match (e.g., /translate → translate.html)
        3. Fallback to index.html (SPA catch-all)
        """
        # Security: prevent path traversal using canonical path resolution
        safe_path = full_path.strip("/")
        candidate = os.path.realpath(os.path.join(FRONTEND_DIR, safe_path))
        if not candidate.startswith(os.path.realpath(FRONTEND_DIR)):
            raise StarletteHTTPException(status_code=403)

        # 1) Exact file match (robots.txt, favicon.ico, etc.)
        exact = os.path.join(FRONTEND_DIR, safe_path)
        if os.path.isfile(exact):
            return FileResponse(exact)

        # 2) .html mapping (/login → login.html, /translate → translate.html)
        html_path = os.path.join(FRONTEND_DIR, f"{safe_path}.html")
        if os.path.isfile(html_path):
            return FileResponse(html_path, media_type="text/html")

        # 3) Directory index (/foo/ → foo/index.html)
        index_path = os.path.join(FRONTEND_DIR, safe_path, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")

        # 4) Fallback to root index.html (SPA catch-all)
        fallback = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(fallback):
            return FileResponse(fallback, media_type="text/html")

        raise StarletteHTTPException(status_code=404)
