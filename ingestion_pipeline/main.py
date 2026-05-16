import os
import traceback

# [DEBUG-PRO] AGGRESSIVE C++ COLLISION OVERRIDES
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["RAYON_NUM_THREADS"] = "1"

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from summarizer import run_pipeline
from schemas import ParsedDocument, UploadResponse
from file_utils import save_upload, cleanup, validate_extension

# PIVOT: Removed init_chroma to prevent C++ libraries from loading in the main process
from chroma_store import store_document_in_chroma 

load_dotenv(override=True)

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env file.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("uploads").mkdir(exist_ok=True)
    yield
    print("Shutting down server.")

app = FastAPI(
    title="Research Alignment Agent",
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
    return {"status": "ok"}

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_type: str = Form(...),
):
    print(f"\n--- Processing Upload: {file.filename} ---")
    
    if source_type not in ("draft", "paper"):
        raise HTTPException(400, "source_type must be 'draft' or 'paper'")

    if not validate_extension(file.filename):
        raise HTTPException(415, "Unsupported file type")

    tmp_path = await save_upload(file)

    try:
        print(">> Step 1: Parsing and Summarization")
        summaries = await run_pipeline(str(tmp_path))
    except Exception as e:
        cleanup(tmp_path)
        traceback.print_exc()
        raise HTTPException(500, f"Extraction/Summarization failed: {str(e)}")
    finally:
        cleanup(tmp_path)

    doc = ParsedDocument(
        filename=file.filename,
        source_type=source_type,
        sections=summaries,
        total_sections=len(summaries),
        status="success",
    )

    try:
        print(">> Step 2: Vector Embeddings and ChromaDB Insertion")
        await store_document_in_chroma(doc)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Failed to store in Vector DB: {str(e)}")

    print(f"--- Successfully processed {file.filename} ---")
    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        sections=doc.sections,
        message="Processed and stored successfully",
    )