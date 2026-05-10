import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.uploads import router as uploads_router
from app.config import describe_openai_key_for_logs, settings
from app.database import Base, engine, ensure_sqlite_dir_writable
from app.services.ai_image import is_configured as openai_images_configured
from app.seed import seed_if_empty


def _configure_logging() -> None:
    level_name = settings.log_level
    level = getattr(logging, level_name, logging.INFO)
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    if not logging.root.handlers:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt, stream=sys.stderr)
    else:
        logging.root.setLevel(level)
    for name in ("app", "app.services", "app.services.job_runner", "app.services.compose", "app.services.ai_image"):
        logging.getLogger(name).setLevel(level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _configure_logging()
    log = logging.getLogger(__name__)
    log.info("LOG_LEVEL=%s", settings.log_level)
    log.info("%s", describe_openai_key_for_logs(settings.openai_api_key))
    ensure_sqlite_dir_writable()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal, migrate_sqlite_schema

    migrate_sqlite_schema()

    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Dealership Creative Automation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(uploads_router)
app.include_router(jobs_router)


@app.get("/api/health")
def health():
    """Liveness check; no secrets."""
    return {
        "status": "ok",
        "copy_shortening": "local",
        "openai_images_configured": openai_images_configured(),
    }
