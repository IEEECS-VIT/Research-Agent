from datetime import datetime

from pydantic import BaseModel


class CreateAnalysisRequest(BaseModel):
    name: str | None = None
    draft_document_ids: list[str]
    paper_document_ids: list[str]


class AnalysisSessionResponse(BaseModel):
    id: str
    name: str | None = None
    status: str
    created_at: datetime


class ComparisonResultResponse(BaseModel):
    id: str
    source_doc_id: str
    target_doc_id: str
    source_section: str | None = None
    target_section: str | None = None
    source_text: str | None = None
    target_text: str | None = None
    support_score: float
    contradiction_score: float
    confidence: float
    verifier_status: str | None = None
    relation_type: str | None = None
    confidence_state: str | None = None


class AnalysisDetailResponse(AnalysisSessionResponse):
    comparisons: list[ComparisonResultResponse] = []


class ComparisonGraphResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]
