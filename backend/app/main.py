"""FastAPI application with lifespan, CORS, and route registration."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.ollama.client import OllamaClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB + Ollama client."""
    # Startup
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_url = "sqlite+aiosqlite:///" + db_url[len("sqlite:///"):]
    engine, session_factory = await init_db(db_url)
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    app.state.ollama_client = OllamaClient(settings.OLLAMA_URL)

    # Ensure directories exist
    for d in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        os.makedirs(d, exist_ok=True)

    yield

    # Shutdown
    await app.state.ollama_client.close()
    await engine.dispose()


app = FastAPI(
    title="JP→VI Document Translation",
    description="Air-gapped Japanese-to-Vietnamese document translation system",
    version="0.1.0",
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
from app.routes.upload import router as upload_router  # noqa: E402
from app.routes.jobs import router as jobs_router  # noqa: E402
from app.routes.download import router as download_router  # noqa: E402
from app.routes.xliff import router as xliff_router  # noqa: E402

app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(download_router, prefix="/api", tags=["Download"])
app.include_router(xliff_router, prefix="/api", tags=["XLIFF"])


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    ollama_ok = await app.state.ollama_client.health_check()
    return {
        "status": "ok",
        "ollama": "connected" if ollama_ok else "disconnected",
    }


# ── Serve frontend static files ──
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # Docker path
    DOCKER_FRONTEND = "/app/frontend"
    if os.path.isdir(DOCKER_FRONTEND):
        app.mount("/", StaticFiles(directory=DOCKER_FRONTEND, html=True), name="frontend")
