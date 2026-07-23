import os
import asyncio
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from ingestion_pipeline.schemas import ParsedDocument, SectionSummary
from ingestion_pipeline.chroma_store import store_document_in_chroma, CHROMA_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

load_dotenv(override=True)

async def test_vector_store():
    logger.info("==================================================")
    logger.info("       CHROMADB ISOLATION PIPELINE CHECKER       ")
    logger.info("==================================================")
    logger.info("Target Database Directory: %s", CHROMA_DATA_DIR)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is missing from your .env file!")
        return

    mock_section = SectionSummary(
        section_name="introduction_test",
        raw_text="This is an automated test chunk verifying Docling and ChromaDB interoperability under Windows 11 execution structures.",
        summary="Testing vector store pipeline operations directly through process executors."
    )
    
    mock_doc = ParsedDocument(
        filename="test_verification_run.pdf",
        source_type="draft",
        sections=[mock_section],
        total_sections=1,
        status="testing"
    )

    logger.info("\n[STEP 1] Generating embeddings and running isolated upsert process...")
    try:
        await store_document_in_chroma(mock_doc)
        logger.info("[SUCCESS] Isolated database pipeline write executed completely.")
    except Exception as e:
        logger.error("[FAIL] High-level storage pipeline crashed: %s", e)
        return

    logger.info("\n[STEP 2] Verifying records inside ChromaDB using independent context...")
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=CHROMA_DATA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collections = client.list_collections()
        logger.info("Available Collections: %s", [col.name for col in collections])
        
        collection = client.get_collection(name="research_papers_v12")
        total_items = collection.count()
        logger.info("Total stored records inside target collection: %d", total_items)
        
        if total_items > 0:
            peek_data = collection.peek(limit=1)
            logger.info("\n--- Sample Record Retrieved From DB ---")
            logger.info("ID: %s", peek_data['ids'][0])
            logger.info("Document Text Snippet: %s", peek_data['documents'][0])
            logger.info("Metadata Content: %s", peek_data['metadatas'][0])
            logger.info("---------------------------------------")
            logger.info("[SUCCESS] ChromaDB is working perfectly and recording your data!")
        else:
            logger.warning("[WARNING] ChromaDB collection opened successfully but no items were tracked.")
            
    except Exception as e:
        logger.error("[FAIL] Error attempting to read or readback verification from ChromaDB: %s", e)

if __name__ == "__main__":
    asyncio.run(test_vector_store())