from datetime import datetime
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    source_type: str
    version_id: str
    total_sections: int
    processing_status: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentUploadResponse]
    total: int


class DocumentDetailResponse(DocumentUploadResponse):
    sections: list[dict] | None = None
    error_message: str | None = None
