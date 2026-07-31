import asyncio
import json
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.analysis import AnalysisDocument, AnalysisSession, ComparisonResult
from app.models.document import Document

logger = logging.getLogger(__name__)

settings = get_settings()

try:
    from GraphEngine.engines.analyst import analyze
    from GraphEngine.engines.verifier import verify

    from GraphEngine.engines.confidence_engine import compute_confidence
    from GraphEngine.engines.retrieval_engine import retrieve_cross_type

    GRAPH_ENGINE_AVAILABLE = True
except ImportError:
    GRAPH_ENGINE_AVAILABLE = False


async def create_analysis_session(
    db: Session,
    user_id: str,
    name: str | None = None,
    draft_ids: list[str] | None = None,
    paper_ids: list[str] | None = None,
) -> AnalysisSession:
    session = AnalysisSession(
        user_id=user_id,
        name=name or f"Analysis {session_count(db, user_id) + 1}",
        status="pending",
    )
    db.add(session)
    db.flush()

    if draft_ids:
        for doc_id in draft_ids:
            db.add(AnalysisDocument(session_id=session.id, document_id=doc_id, role="draft"))

    if paper_ids:
        for doc_id in paper_ids:
            db.add(AnalysisDocument(session_id=session.id, document_id=doc_id, role="paper"))

    db.commit()
    db.refresh(session)
    return session


def session_count(db: Session, user_id: str) -> int:
    return db.query(AnalysisSession).filter(AnalysisSession.user_id == user_id).count()


async def run_comparison(
    db: Session,
    session_id: str,
    user_id: str,
) -> list[ComparisonResult]:
    session = (
        db.query(AnalysisSession)
        .filter(
            AnalysisSession.id == session_id,
            AnalysisSession.user_id == user_id,
        )
        .first()
    )

    if not session:
        raise ValueError("Session not found")

    session.status = "processing" # type: ignore
    db.commit()

    try:
        draft_docs = (
            db.query(Document)
            .join(AnalysisDocument, AnalysisDocument.document_id == Document.id)
            .filter(
                AnalysisDocument.session_id == session_id,
                AnalysisDocument.role == "draft",
            )
            .all()
        )

        paper_docs = (
            db.query(Document)
            .join(AnalysisDocument, AnalysisDocument.document_id == Document.id)
            .filter(
                AnalysisDocument.session_id == session_id,
                AnalysisDocument.role == "paper",
            )
            .all()
        )

        if not draft_docs or not paper_docs:
            raise ValueError("Need at least one draft and one paper for comparison")

        results = []

        for draft in draft_docs:
            for paper in paper_docs:
                comparisons = await _compare_documents(draft, paper)
                for comp in comparisons:
                    comp.session_id = session_id # type: ignore
                    db.add(comp)
                    results.append(comp)

        db.commit()
        session.status = "completed" # type: ignore
        db.commit()

        return results

    except Exception as e:
        session.status = "failed" # type: ignore
        db.commit()
        logger.error("Comparison run failed: %s", e, exc_info=True)
        raise


async def _compare_documents(
    draft: Document,
    paper: Document,
) -> list[ComparisonResult]:
    results = []
    dummy_result = ComparisonResult(
        source_doc_id=draft.id,
        target_doc_id=paper.id,
        support_score=0.0,
        contradiction_score=0.0,
        confidence=0.0,
    )

    if not GRAPH_ENGINE_AVAILABLE:
        return [dummy_result]

    try:
        from google import genai as google_genai

        client = google_genai.Client(api_key=settings.gemini_api_key)

        draft_texts = _get_document_chunks(draft)
        paper_texts = _get_document_chunks(paper)

        for d_text in draft_texts[:5]:
            try:
                response = await client.aio.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=d_text[:2000],
                )
                if not response.embeddings:
                    continue
                embedding = [float(v) for v in response.embeddings[0].values] # type: ignore

                retrieve_cross_type(
                    query_embedding=embedding,
                    source_doc_type="draft",
                    n_results=5,
                )

                for p_text in paper_texts[:3]:
                    analyst_scores = analyze(d_text[:1000], p_text[:1000])
                    verifier_status = verify(d_text[:1000], p_text[:1000])

                    support = analyst_scores.get("support_score", 0.5)
                    contradiction = analyst_scores.get("contradiction_score", 0.5)
                    analyst_strength = max(support, contradiction)
                    distance = 0.5
                    confidence = compute_confidence(
                        rerank_distance=distance,
                        analyst_strength=analyst_strength,
                        verifier_status=verifier_status,
                    )

                    from GraphEngine.utils.helpers import (
                        derive_confidence_state,
                        derive_relation_type,
                    )

                    results.append(
                        ComparisonResult(
                            source_doc_id=draft.id,
                            target_doc_id=paper.id,
                            source_section="draft_section",
                            target_section="paper_section",
                            source_text=d_text[:500],
                            target_text=p_text[:500],
                            support_score=support,
                            contradiction_score=contradiction,
                            confidence=confidence,
                            verifier_status=verifier_status,
                            relation_type=derive_relation_type(support, contradiction),
                            confidence_state=derive_confidence_state(confidence, verifier_status),
                        )
                    )

                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning("Comparison error: %s", e)
                continue

    except ImportError as e:
        logger.error("GraphEngine import error: %s", e)

    return results if results else [dummy_result]


def _get_document_chunks(document: Document) -> list[str]:
    if document.file_path and document.file_path.endswith(".json"):
        try:
            with open(document.file_path) as f: # type: ignore
                data = json.load(f)
                sections = data.get("sections", [])
                return [s.get("raw_text", "") or s.get("summary", "") for s in sections]
        except Exception:
            pass

    return [f"Document: {document.original_filename}"]
