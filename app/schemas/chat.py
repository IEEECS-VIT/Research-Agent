from pydantic import BaseModel
from datetime import datetime


class SendMessageRequest(BaseModel):
    session_id: str | None = None
    message: str


class Source(BaseModel):
    doc_id: str | None = None
    filename: str | None = None
    section: str | None = None
    text: str | None = None
    confidence: float | None = None
    relation_type: str | None = None
    support_score: float | None = None
    contradiction_score: float | None = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list[Source] = []
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[MessageResponse] = []
