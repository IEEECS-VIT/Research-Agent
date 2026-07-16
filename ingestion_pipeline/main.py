import os
import traceback

# [DEBUG-PRO] AGGRESSIVE C++ COLLISION OVERRIDES
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["RAYON_NUM_THREADS"] = "1"

from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import text
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from ingestion_pipeline.summarizer import run_pipeline
from ingestion_pipeline.schemas import ParsedDocument, UploadResponse, Claim, ComparisonEdgeResponse
from ingestion_pipeline.file_utils import save_upload, cleanup, validate_extension
from ingestion_pipeline.chroma_store import store_document_in_chroma
from ingestion_pipeline.claim_extractor import extract_claims_from_section
from GraphEngine.engines.comparison_engine import compare_document
from GraphEngine.engines.langgraph_workflow import run_langgraph_workflow
from GraphEngine.db.crud import get_edges, bulk_upsert_edges
from GraphEngine.db.connection import engine
from GraphEngine.db.models import Base
from GraphEngine.analytics.graph_builder import build_graph_from_sqlite
from GraphEngine.analytics.graph_summary import graph_summary
from GraphEngine.analytics.inference_engine import infer_paper_paper_support_edges
import asyncio

load_dotenv(override=True)

# Do not crash at import time if GEMINI_API_KEY is missing.
# The upload endpoint will raise a clear HTTP error when the key is required.

# ==========================================
# GLOBAL STATE: Tracks the current version
# Resets to 0 when the server restarts
# ==========================================
CURRENT_VERSION = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    Path("uploads").mkdir(exist_ok=True)
    yield
    print("Shutting down server.")


app = FastAPI(
    title="Research Alignment Agent",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Simple landing endpoint so the base URL is not blank/not-found."""
    return {
        "service": "Research Alignment Agent",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    """Health check endpoint that verifies system readiness."""
    health_info = {
        "status": "ok",
        "current_active_version": CURRENT_VERSION,
        "chroma_available": False,
        "database_available": False,
        "gemini_key_set": False,
    }

    # Check GEMINI_API_KEY
    health_info["gemini_key_set"] = bool(os.getenv("GEMINI_API_KEY"))

    # Check ChromaDB connectivity without requiring a pre-existing collection.
    try:
        from GraphEngine.engines.retrieval_engine import _get_client

        client = _get_client()
        client.list_collections()
        health_info["chroma_available"] = True
    except Exception as e:
        print(f"[HEALTH] ChromaDB check failed: {e}")
        health_info["chroma_available"] = False

    # Check database connectivity
    try:
        from GraphEngine.db.connection import SessionLocal

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_info["database_available"] = True
    except Exception as e:
        print(f"[HEALTH] Database check failed: {e}")
        health_info["database_available"] = False

    return health_info


@app.get(
    "/comparisons",
    response_model=list[ComparisonEdgeResponse],
    summary="List persisted comparison edges",
)
async def list_comparisons(source_doc_id: str | None = None):
    """Return comparison edges stored in the graph database."""
    edges = get_edges()
    if source_doc_id:
        edges = [edge for edge in edges if edge.source_id.startswith(f"{source_doc_id}_")]
    return [
        ComparisonEdgeResponse(
            source_id=edge.source_id,
            target_id=edge.target_id,
            support_score=edge.support_score,
            contradiction_score=edge.contradiction_score,
            confidence=edge.confidence,
            verifier_status=edge.verifier_status,
            relation_type=getattr(edge, "relation_type", None),
            confidence_state=getattr(edge, "confidence_state", None),
            verifier_state=getattr(edge, "verifier_state", None),
            flag=edge.flag,
            user_override=bool(edge.user_override),
        )
        for edge in edges
    ]


@app.get(
    "/graph/summary",
    summary="Summarize the reconstructed semantic graph",
)
async def get_graph_summary():
    """Return a lightweight summary of the reconstructed in-memory graph."""
    graph = build_graph_from_sqlite()
    return graph_summary(graph)


@app.post(
    "/graph/infer-transitive-edges",
    summary="Infer implicit Paper-Paper SUPPORT edges through shared Draft intermediaries",
)
async def infer_transitive_edges():
    """Discover Paper-to-Paper SUPPORT relationships without any LLM calls.

    How it works:
      If Paper A and Paper B both SUPPORT the same Draft claim with high
      confidence, we infer that Paper A and Paper B also implicitly agree.

    Quality gates (to prevent naive edge forming):
      - Both bridge edges must be SUPPORT + CONFIRMED + HIGH_CONFIDENCE
      - Both bridge edges must have support_score >= INFER_MIN_SUPPORT_SCORE (default 0.70)
      - SCOPE_MISMATCH or LOW_CONFIDENCE edges are NEVER used as bridges
      - CONTRADICT edges are NEVER inferred (too indirect, too risky)

    Inferred edges are flagged with 'HIGH_CONFIDENCE_SUPPORT_INFERRED'
    so they are clearly distinguishable from directly computed edges.
    """
    loop = asyncio.get_running_loop()

    # Run the pure-Python graph traversal off the event loop
    inferred_records = await loop.run_in_executor(None, infer_paper_paper_support_edges)

    if not inferred_records:
        return {
            "message": "No qualifying bridge edges found. Nothing inferred.",
            "candidate_pairs": 0,
            "edges_written": 0,
        }

    # Bulk-write all inferred edges in a single SQLite transaction
    edges_written = await loop.run_in_executor(None, bulk_upsert_edges, inferred_records)

    return {
        "message": "Transitive inference complete.",
        "candidate_pairs": len(inferred_records),
        "edges_written": edges_written,
    }


# ==========================================
# NEW ENDPOINT: Roll to New Version
# ==========================================
@app.post("/roll-version", summary="Roll to new version")
async def roll_version():
    """
    Clicking 'Execute' in Swagger UI will increment the global version ID.
    All subsequent document uploads will use this new version ID.
    """
    global CURRENT_VERSION
    CURRENT_VERSION += 1

    return {
        "message": "Version rolled successfully",
        "new_version_id": CURRENT_VERSION,
    }


@app.post(
    "/upload",
    response_model=UploadResponse,
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_type: Literal["draft", "paper"] = Form(...),
):
    print(
        f"\n--- Processing Upload: {file.filename} "
        f"(Target Version: {CURRENT_VERSION}) ---"
    )

    if not validate_extension(file.filename):
        raise HTTPException(415, "Unsupported file type")

    tmp_path = await save_upload(file)

    try:
        print(">> Step 1: Parsing and Summarization")
        summaries = await run_pipeline(str(tmp_path))

    except Exception as e:
        cleanup(tmp_path)
        traceback.print_exc()
        raise HTTPException(
            500,
            f"Extraction/Summarization failed: {str(e)}"
        )

    finally:
        cleanup(tmp_path)

    # Extract claims from each section
    extracted_claims: list[Claim] = []

    try:
        print(">> Step 1b: Claim Extraction")

        for section in summaries:
            section_claims = await extract_claims_from_section(
                section_name=section.section_name,
                raw_text=section.raw_text,
                summary=section.summary,
                source_type=source_type,
            )

            for claim_obj in section_claims:
                extracted_claims.append(
                    Claim(
                        assertion=claim_obj.assertion,
                        subject=claim_obj.subject,
                        context=f"section: {section.section_name}",
                    )
                )

    except Exception as e:
        print(f"[WARN] Claim extraction failed: {e}")
        traceback.print_exc()

        # Continue anyway; comparisons will be empty
        # but ingestion still succeeds

    # Inject CURRENT_VERSION into the document payload
    doc = ParsedDocument(
        filename=file.filename,
        source_type=source_type,
        version_id=str(CURRENT_VERSION),
        sections=summaries,
        claims=extracted_claims,
        total_sections=len(summaries),
        status="success",
    )

    try:
        print(">> Step 2: Vector Embeddings and ChromaDB Insertion")
        await store_document_in_chroma(doc)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            500,
            f"Failed to store in Vector DB: {str(e)}"
        )

    # Run automatic comparison if claims were extracted
    comparison_results = []

    if extracted_claims:
        try:
            print(">> Step 3: Automatic Cross-Document Comparison")

            # Prefix claim ids with the document id so edges are namespaced
            claims_dicts = []
            for i, c in enumerate(extracted_claims):
                claims_dicts.append(
                    {
                        "claim_id": f"{doc.doc_id}_{i}",
                        "assertion": c.assertion,
                        "subject": c.subject,
                        "context": c.context,
                    }
                )

            # Run the LangGraph-orchestrated workflow (local fallback if LangGraph SDK unavailable)
            comp_results = await run_langgraph_workflow(
                claims=claims_dicts,
                source_doc_type=source_type,
                version_id=doc.version_id,
                persist=True,
            )

            doc.comparisons = [r.to_dict() for r in comp_results]
            comparison_results = doc.comparisons

        except Exception as e:
            print(f"[WARN] Comparison pipeline failed: {e}")
            traceback.print_exc()

            # Continue; comparisons are optional

    print(f"--- Successfully processed {file.filename} ---")

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        sections=doc.sections,
        claims_count=len(extracted_claims),
        comparison_count=len(comparison_results),
        message=(
            f"Processed successfully: "
            f"{len(extracted_claims)} claims extracted, "
            f"{len(comparison_results)} comparisons performed "
            f"under version {CURRENT_VERSION}"
        ),
    )


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    swagger = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
    )

    extra_script = """
    <script>
    const tryEnable = () => {
        const buttons = Array.from(document.querySelectorAll('button'));

        const tryBtn = buttons.find((button) => {
            const label = (button.textContent || '').trim();
            if (label !== 'Try it out') {
                return false;
            }

            const opblock = button.closest('.opblock');
            return opblock && opblock.innerText && opblock.innerText.includes('/upload');
        });

        if (tryBtn && !tryBtn.dataset.clickedByAgent) {
            tryBtn.dataset.clickedByAgent = 'true';
            tryBtn.click();
            return true;
        }

        return false;
    };

    const startObserver = () => {
        if (tryEnable()) {
            return;
        }

        const observer = new MutationObserver(() => {
            if (tryEnable()) {
                observer.disconnect();
            }
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
        });

        setTimeout(() => observer.disconnect(), 10000);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startObserver);
    } else {
        startObserver();
    }
    </script>
    """

    content = swagger.body.decode().replace("</body>", f"{extra_script}</body>")
    return HTMLResponse(content=content, status_code=200)

