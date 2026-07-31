import logging
import os

# [DEBUG-PRO] AGGRESSIVE C++ COLLISION OVERRIDES
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["RAYON_NUM_THREADS"] = "1"

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ingestion_pipeline.pinecone_store import store_document_in_pinecone
from ingestion_pipeline.file_utils import cleanup, save_upload, validate_extension
from ingestion_pipeline.schemas import ParsedDocument, UploadResponse
from ingestion_pipeline.summarizer import run_pipeline

logger = logging.getLogger(__name__)

load_dotenv(override=True)

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env file.")

CURRENT_VERSION = 0

logger.warning(
    "DEPRECATED: ingestion_pipeline/main.py is the legacy standalone pipeline server. "
    "Use `uvicorn app.main:app` (the main application server) instead. "
    "This module will be removed in a future release."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("uploads").mkdir(exist_ok=True)
    yield
    logger.info("Shutting down server.")


app = FastAPI(
    title="Research Alignment Agent (Legacy Pipeline)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "current_active_version": CURRENT_VERSION}


@app.post("/roll-version", summary="Roll to new version")
async def roll_version():
    global CURRENT_VERSION
    CURRENT_VERSION += 1
    return {"message": "Version rolled successfully", "new_version_id": CURRENT_VERSION}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_type: str = Form(...),
):
    logger.info("Processing Upload: %s (Target Version: %d)", file.filename, CURRENT_VERSION)

    if source_type not in ("draft", "paper"):
        raise HTTPException(400, "source_type must be 'draft' or 'paper'")

    if not validate_extension(file.filename):
        raise HTTPException(415, "Unsupported file type")

    tmp_path = await save_upload(file)

    try:
        logger.info("Step 1: Parsing and Summarization")
        summaries, doi = await run_pipeline(str(tmp_path))
    except Exception as e:
        cleanup(tmp_path)
        logger.error("Extraction/Summarization failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Extraction/Summarization failed: {str(e)}")
    finally:
        cleanup(tmp_path)

    doc = ParsedDocument(
        filename=file.filename,
        source_type=source_type,
        version_id=str(CURRENT_VERSION),
        doi=doi,
        sections=summaries,
        total_sections=len(summaries),
        status="success",
    )

    try:
        logger.info("Step 2: Vector Embeddings and ChromaDB Insertion")
        await store_document_in_pinecone(doc)
    except Exception as e:
        logger.error("Failed to store in Vector DB: %s", e, exc_info=True)
        raise HTTPException(500, f"Failed to store in Vector DB: {str(e)}")

    logger.info("Successfully processed %s", file.filename)
    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        sections=doc.sections,
        message=f"Processed and stored successfully under version {CURRENT_VERSION}",
    )
