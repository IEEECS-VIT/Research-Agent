from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatSessionDetailResponse,
    ChatSessionResponse,
    MessageResponse,
    SendMessageRequest,
    Source,
)
from app.services.research_rag_service import get_rag_agent

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = ChatSession(
        user_id=current_user["uid"],
        title="New Conversation",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user["uid"])
        .order_by(desc(ChatSession.updated_at))
        .all()
    )
    return [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user["uid"],
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sources=[Source(**s) for s in (m.sources or [])],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user["uid"],
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()

    return {"status": "deleted"}


@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.session_id

    if not session_id:
        session = ChatSession(
            user_id=current_user["uid"],
            title=request.message[:80] + ("..." if len(request.message) > 80 else ""),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user["uid"],
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    agent = get_rag_agent()
    answer, sources = await agent.answer_question(request.message, current_user["uid"])

    sources_data = [s.model_dump() for s in sources]

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        sources=sources_data,
    )
    db.add(assistant_message)

    now = datetime.now(UTC)
    session.updated_at = now
    if session.title == "New Conversation" or session.title is None:
        session.title = request.message[:80] + ("..." if len(request.message) > 80 else "")

    db.commit()
    db.refresh(assistant_message)

    return MessageResponse(
        id=assistant_message.id,
        session_id=assistant_message.session_id,
        role=assistant_message.role,
        content=assistant_message.content,
        sources=sources,
        created_at=assistant_message.created_at,
    )
