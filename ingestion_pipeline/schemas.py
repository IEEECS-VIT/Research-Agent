from pydantic import BaseModel, Field
from uuid import uuid4

class SectionSummary(BaseModel):
    section_name: str
    raw_text: str
    summary: str

class ParsedDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    version_id: str = "0"  # PIVOT: Removed datetime, set default to "0"
    filename: str
    source_type: str
    sections: list[SectionSummary]
    total_sections: int
    status: str

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    source_type: str
    version_id: str
    total_sections: int
    sections: list[SectionSummary]
    message: str