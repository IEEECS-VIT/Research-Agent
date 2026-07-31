import logging
import os

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, ProcessingStatus
from ingestion_pipeline.chroma_store import store_document_in_chroma
from ingestion_pipeline.schemas import SectionSummary
from ingestion_pipeline.summarizer import run_pipeline

logger = logging.getLogger(__name__)

settings = get_settings()


async def process_document(
    db: Session,
    document: Document,
) -> list[SectionSummary]:
    document.processing_status = ProcessingStatus.PROCESSING.value  # type: ignore
    db.commit()

    try:
        file_path = document.file_path
        if not file_path or not os.path.exists(str(file_path)):
            raise FileNotFoundError(f"File not found: {file_path}")

        summaries, doi = await run_pipeline(str(file_path))

        from ingestion_pipeline.schemas import ParsedDocument

        doc = ParsedDocument(
            filename=str(document.original_filename),
            source_type=str(document.source_type),
            version_id=str(document.version_id or "0"),
            doi=doi,
            sections=summaries,
            total_sections=len(summaries),
            status="success",
        )

        try:
            await store_document_in_chroma(doc)
        except Exception as e:
            logger.warning("ChromaDB store failed (non-fatal): %s", e)

        document.doi = doi  # type: ignore
        document.total_sections = len(summaries)  # type: ignore
        document.processing_status = ProcessingStatus.COMPLETED.value  # type: ignore
        db.commit()
        db.refresh(document)

        return summaries

    except Exception as e:
        document.processing_status = ProcessingStatus.FAILED.value  # type: ignore
        document.error_message = str(e)  # type: ignore
        db.commit()
        logger.error("Document processing failed: %s", e, exc_info=True)
        raise
