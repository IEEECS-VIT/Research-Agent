import os
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, get_logger
from app.core.ratelimit import rate_limiter
from app.api import auth, documents, analysis, chat, health

load_dotenv(override=True)

settings = get_settings()
setup_logging(settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("%s v%s initialized", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    logger.debug(
        "%s %s -> %d (%.2fms)",
        request.method, request.url.path, response.status_code, elapsed * 1000,
    )
    response.headers["X-Response-Time-Ms"] = str(round(elapsed * 1000, 2))
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    await rate_limiter(request)
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/metrics")
async def metrics():
    import platform
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "python_version": platform.python_version(),
        "debug": settings.debug,
    }
