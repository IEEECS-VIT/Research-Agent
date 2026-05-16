import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure the root folder is accessible in python path
sys.path.append(str(Path(__file__).parent.parent))

from ingestion_pipeline.schemas import ParsedDocument, SectionSummary
from ingestion_pipeline.chroma_store import store_document_in_chroma, CHROMA_DATA_DIR

load_dotenv(override=True)

async def test_vector_store():
    print("==================================================")
    print("       CHROMADB ISOLATION PIPELINE CHECKER       ")
    print("==================================================")
    print(f"Target Database Directory: {CHROMA_DATA_DIR}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is missing from your .env file!")
        return

    # 1. Create mock payload structure conforming to schema
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

    print("\n[STEP 1] Generating embeddings and running isolated upsert process...")
    try:
        await store_document_in_chroma(mock_doc)
        print("[SUCCESS] Isolated database pipeline write executed completely.")
    except Exception as e:
        print(f"[FAIL] High-level storage pipeline crashed: {e}")
        return

    # 2. Querying database directly to ensure validation
    print("\n[STEP 2] Verifying records inside ChromaDB using independent context...")
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=CHROMA_DATA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collections = client.list_collections()
        print(f"Available Collections: {[col.name for col in collections]}")
        
        collection = client.get_collection(name="research_papers_v12")
        total_items = collection.count()
        print(f"Total stored records inside target collection: {total_items}")
        
        if total_items > 0:
            peek_data = collection.peek(limit=1)
            print("\n--- Sample Record Retrieved From DB ---")
            print(f"ID: {peek_data['ids'][0]}")
            print(f"Document Text Snippet: {peek_data['documents'][0]}")
            print(f"Metadata Content: {peek_data['metadatas'][0]}")
            print("---------------------------------------")
            print("[SUCCESS] ChromaDB is working perfectly and recording your data!")
        else:
            print("[WARNING] ChromaDB collection opened successfully but no items were tracked.")
            
    except Exception as e:
        print(f"[FAIL] Error attempting to read or readback verification from ChromaDB: {e}")

if __name__ == "__main__":
    # Windows 11 safe asynchronous event loop execution style
    asyncio.run(test_vector_store())