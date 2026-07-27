from pydantic import BaseModel, Field
from uuid import uuid4

class SectionSummary(BaseModel):
    section_name: str
    raw_text: str
    summary: str


class Claim(BaseModel):
    claim_id: str | None = None
    assertion: str
    subject: str | None = None
    context: str | None = None

class ClaimMatch(BaseModel):
    """A candidate claim matched to a query claim during comparison."""
    retrieved_id: str
    retrieved_text: str
    metadata: dict
    cosine_distance: float
    support_score: float
    contradiction_score: float
    verifier_status: str
    confidence: float  # Weighted confidence from [retrieval, analyst, verifier]


class ComparisonResult(BaseModel):
    """Result of comparing a single claim against retrieved candidates."""
    claim_id: str
    claim_text: str
    source_doc_type: str
    version_id: str
    match_count: int
    matches: list[ClaimMatch]

class ParsedDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    version_id: str = "0"  # PIVOT: Removed datetime, set default to "0"
    filename: str
    source_type: str
    doi: str | None = None
    sections: list[SectionSummary]
    claims: list[Claim] = []
    comparisons: list[ComparisonResult] = []  # Populated after cross-document comparison
    total_sections: int
    status: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    source_type: str
    version_id: str
    total_sections: int
    sections: list[SectionSummary]
    claims_count: int = 0
    comparison_count: int = 0
    message: str


class ComparisonEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    support_score: float | None = None
    contradiction_score: float | None = None
    confidence: float | None = None
    verifier_status: str | None = None
    # New semantic dimensions
    relation_type: str | None = None
    confidence_state: str | None = None
    verifier_state: str | None = None

    # Backwards-compatible overloaded field (deprecated)
    flag: str | None = None
    user_override: bool = False
