import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey
from app.core.database import Base


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    name = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AnalysisDocument(Base):
    __tablename__ = "analysis_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("analysis_sessions.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ComparisonResult(Base):
    __tablename__ = "comparison_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("analysis_sessions.id"), nullable=False, index=True)
    source_doc_id = Column(String, ForeignKey("documents.id"), nullable=False)
    target_doc_id = Column(String, ForeignKey("documents.id"), nullable=False)
    source_section = Column(String, nullable=True)
    target_section = Column(String, nullable=True)
    source_text = Column(Text, nullable=True)
    target_text = Column(Text, nullable=True)
    support_score = Column(Float, default=0.0)
    contradiction_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    verifier_status = Column(String, nullable=True)
    relation_type = Column(String, nullable=True)
    confidence_state = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
