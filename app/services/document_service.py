import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, ProcessingStatus

settings = get_settings()


async def upload_document(
    db: Session,
    user_id: str,
    file: UploadFile,
    source_type: str,
    version_id: str = "0",
) -> Document:
    if source_type not in ("draft", "paper"):
        raise HTTPException(status_code=400, detail="source_type must be 'draft' or 'paper'")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".html", ".txt", ".md"):
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext}")

    upload_dir = Path(settings.upload_dir) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = upload_dir / safe_filename

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        user_id=user_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        source_type=source_type,
        version_id=str(version_id),
        processing_status=ProcessingStatus.PENDING.value,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_user_documents(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    source_type: str | None = None,
) -> tuple[list[Document], int]:
    query = db.query(Document).filter(Document.user_id == user_id)

    if source_type:
        query = query.filter(Document.source_type == source_type)

    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    return documents, total


def get_document(db: Session, document_id: str, user_id: str) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        .first()
    )


def delete_document(db: Session, document: Document) -> None:
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    db.delete(document)
    db.commit()
