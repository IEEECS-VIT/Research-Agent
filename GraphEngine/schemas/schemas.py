# schemas.py
from typing import Literal
from pydantic import BaseModel


class EdgeCreate(BaseModel):
    source_id: str
    target_id: str

    support_score: float
    contradiction_score: float
    confidence: float

    verifier_status: str


class RetrieveRequest(BaseModel):
    """
    Request body for the /graph/retrieve endpoint.

    Fields align with the ingestion pipeline's metadata schema:
        source_type   – "draft" | "paper" (the document being queried)
        chunk_type    – "summary" | "raw_text" (defaults to "summary")
        top_k         – number of results after reranking (default 8)

    The embedding should be pre-computed by the caller using
    google.genai model "gemini-embedding-2" (dim=3072).
    """
    embedding: list[float]
    source_type: Literal["draft", "paper"]
    chunk_type: Literal["summary", "raw_text"] = "summary"
    top_k: int = 8