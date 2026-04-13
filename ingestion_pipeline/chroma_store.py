import os
import time
import asyncio

# ✅ FIX 1: Keep telemetry disabled at the OS level
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_IMPL"] = "None"

import chromadb
from google import genai
from schemas import ParsedDocument

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Splits text into overlapping chunks to preserve context across boundaries."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def _sync_chroma_write(docs_to_insert, metadatas, ids, all_embeddings, doc_id):
    """
    ✅ FIX 2: This function runs entirely inside a single background worker thread.
    By creating the PersistentClient AND calling upsert in the exact same thread, 
    we completely bypass Windows SQLite thread-locking deadlocks.
    """
    print("    [ChromaDB] Initializing local SQLite database connection...")
    CHROMA_DATA_DIR = os.path.join(os.path.dirname(__file__), "chroma_data_v9")
    
    # 1. Open connection inside this thread
    client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)
    
    # 2. Get collection inside this thread
    collection = client.get_or_create_collection(name="research_papers_v9")
    
    # 3. Write data inside this thread
    collection.upsert(
        documents=docs_to_insert,
        metadatas=metadatas,
        ids=ids,
        embeddings=all_embeddings
    )
    print(f"    [ChromaDB] Successfully inserted {len(docs_to_insert)} vectors for Doc ID: {doc_id}\n")

async def store_document_in_chroma(doc: ParsedDocument):
    docs_to_insert = []
    metadatas = []
    ids = []

    # Prepare all the text chunks
    for section in doc.sections:
        summary_chunks = chunk_text(section.summary, chunk_size=500, overlap=50)
        for i, chunk in enumerate(summary_chunks):
            chunk_id = f"{doc.doc_id}_{section.section_name}_summary_{i}"
            docs_to_insert.append(chunk)
            metadatas.append({
                "doc_id": doc.doc_id,
                "version_id": doc.version_id,
                "filename": doc.filename,
                "source_type": doc.source_type,
                "section_name": section.section_name,
                "content_type": "summary"
            })
            ids.append(chunk_id)

        raw_chunks = chunk_text(section.raw_text, chunk_size=1200, overlap=200)
        for i, chunk in enumerate(raw_chunks):
            chunk_id = f"{doc.doc_id}_{section.section_name}_raw_{i}"
            docs_to_insert.append(chunk)
            metadatas.append({
                "doc_id": doc.doc_id,
                "version_id": doc.version_id,
                "filename": doc.filename,
                "source_type": doc.source_type,
                "section_name": section.section_name,
                "content_type": "raw_text"
            })
            ids.append(chunk_id)

    if not docs_to_insert:
        print("    [ChromaDB] No chunks to insert.")
        return

    # Generate Embeddings Asynchronously
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    all_embeddings = []
    batch_size = 10
    total_batches = (len(docs_to_insert) + batch_size - 1) // batch_size
    
    print(f"\n    [Embedder] Generating vectors for {len(docs_to_insert)} chunks across {total_batches} batches...")
    
    for i in range(0, len(docs_to_insert), batch_size):
        batch_texts = docs_to_insert[i:i + batch_size]
        print(f"      -> API call for batch {(i//batch_size)+1}/{total_batches}...")
        
        try:
            response = await client.aio.models.embed_content(
                model="gemini-embedding-001",
                contents=batch_texts
            )
            all_embeddings.extend([e.values for e in response.embeddings])
            print(f"      -> Success!")
        except Exception as e:
            print(f"      [!] API Error on batch {(i//batch_size)+1}: {e}")
            for _ in batch_texts:
                all_embeddings.append([0.0] * 768)
        
        await asyncio.sleep(2.0)

    print("\n    [ChromaDB] Writing to local database...")
    try:
        # ✅ FIX 3: Hand the data off to the isolated worker thread
        await asyncio.to_thread(
            _sync_chroma_write,
            docs_to_insert,
            metadatas,
            ids,
            all_embeddings,
            doc.doc_id
        )
    except Exception as e:
        print(f"    [ChromaDB] Error writing to database: {e}")
        raise