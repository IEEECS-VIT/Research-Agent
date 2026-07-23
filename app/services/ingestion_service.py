import os
import asyncio
import logging
from pathlib import Path

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from app.core.config import get_settings
from app.models.document import Document, ProcessingStatus
from ingestion_pipeline.summarizer import run_pipeline
from ingestion_pipeline.schemas import SectionSummary
from ingestion_pipeline.chroma_store import store_document_in_chroma
from ingestion_pipeline.file_utils import validate_extension

settings = get_settings()


async def process_document(
    db: Session,
    document: Document,
) -> list[SectionSummary]:
    document.processing_status = ProcessingStatus.PROCESSING.value
    db.commit()

    try:
        file_path = document.file_path
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        summaries = await run_pipeline(str(file_path))

        from ingestion_pipeline.schemas import ParsedDocument

        doc = ParsedDocument(
            filename=document.original_filename,
            source_type=document.source_type,
            version_id=document.version_id or "0",
            sections=summaries,
            total_sections=len(summaries),
            status="success",
        )

        try:
            await store_document_in_chroma(doc)
        except Exception as e:
            logger.warning("ChromaDB store failed (non-fatal): %s", e)

        document.total_sections = len(summaries)
        document.processing_status = ProcessingStatus.COMPLETED.value
        db.commit()
        db.refresh(document)

        return summaries

    except Exception as e:
        document.processing_status = ProcessingStatus.FAILED.value
        document.error_message = str(e)
        db.commit()
        logger.error("Document processing failed: %s", e, exc_info=True)
        raise
