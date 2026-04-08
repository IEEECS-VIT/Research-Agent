import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from summarizer import run_pipeline
from schemas import ParsedDocument, UploadResponse
from file_utils import save_upload, cleanup, validate_extension

# ✅ Load env
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env file.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("uploads").mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="Research Alignment Agent — Team A",
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
    file: UploadFile = File(...),
    source_type: str = Form(...),
):
    if source_type not in ("draft", "paper"):
        raise HTTPException(400, "source_type must be 'draft' or 'paper'")

    if not validate_extension(file.filename):
        raise HTTPException(415, "Unsupported file type")

    tmp_path = await save_upload(file)

    try:
        summaries = await run_pipeline(str(tmp_path))
    except Exception as e:
        cleanup(tmp_path)
        raise HTTPException(500, str(e))
    finally:
        cleanup(tmp_path)

    doc = ParsedDocument(
        filename=file.filename,
        source_type=source_type,
        sections=summaries,
        total_sections=len(summaries),
        status="success",
    )

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        sections=doc.sections,
        message="Processed successfully",
    )