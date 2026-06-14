from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.analysis import (
    CreateAnalysisRequest,
    AnalysisSessionResponse,
    AnalysisDetailResponse,
    ComparisonResultResponse,
    ComparisonGraphResponse,
)
from app.models.analysis import AnalysisSession, ComparisonResult
from app.services.analysis_service import create_analysis_session, run_comparison

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/sessions", response_model=AnalysisSessionResponse)
async def create_session(
    request: CreateAnalysisRequest,
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = await create_analysis_session(
        db=db,
        user_id=current_user["uid"],
        name=request.name,
        draft_ids=request.draft_document_ids,
        paper_ids=request.paper_document_ids,
    )

    if background_tasks and request.draft_document_ids and request.paper_document_ids:
        background_tasks.add_task(run_comparison, db, session.id, current_user["uid"])

    return AnalysisSessionResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[AnalysisSessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == current_user["uid"])
        .order_by(AnalysisSession.created_at.desc())
        .all()
    )

    return [
        AnalysisSessionResponse(
            id=s.id,
            name=s.name,
            status=s.status,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=AnalysisDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(AnalysisSession).filter(
        AnalysisSession.id == session_id,
        AnalysisSession.user_id == current_user["uid"],
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    comparisons = (
        db.query(ComparisonResult)
        .filter(ComparisonResult.session_id == session_id)
        .all()
    )

    return AnalysisDetailResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        created_at=session.created_at,
        comparisons=[
            ComparisonResultResponse(
                id=c.id,
                source_doc_id=c.source_doc_id,
                target_doc_id=c.target_doc_id,
                source_section=c.source_section,
                target_section=c.target_section,
                source_text=c.source_text,
                target_text=c.target_text,
                support_score=c.support_score,
                contradiction_score=c.contradiction_score,
                confidence=c.confidence,
                verifier_status=c.verifier_status,
                relation_type=c.relation_type,
                confidence_state=c.confidence_state,
            )
            for c in comparisons
        ],
    )


@router.get("/sessions/{session_id}/graph", response_model=ComparisonGraphResponse)
async def get_session_graph(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(AnalysisSession).filter(
        AnalysisSession.id == session_id,
        AnalysisSession.user_id == current_user["uid"],
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    comparisons = (
        db.query(ComparisonResult)
        .filter(ComparisonResult.session_id == session_id)
        .all()
    )

    doc_ids = set()
    for c in comparisons:
        doc_ids.add(c.source_doc_id)
        doc_ids.add(c.target_doc_id)

    from app.models.document import Document

    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
    doc_map = {d.id: d.original_filename for d in docs}

    nodes = [
        {"id": doc_id, "label": doc_map.get(doc_id, doc_id), "type": "document"}
        for doc_id in doc_ids
    ]

    edges = [
        {
            "source": c.source_doc_id,
            "target": c.target_doc_id,
            "support_score": c.support_score,
            "contradiction_score": c.contradiction_score,
            "confidence": c.confidence,
            "relation_type": c.relation_type or "unknown",
        }
        for c in comparisons
    ]

    return ComparisonGraphResponse(nodes=nodes, edges=edges)
