import os
import asyncio
import traceback
from concurrent.futures import ProcessPoolExecutor
from google import genai
from ingestion_pipeline.schemas import ParsedDocument

USER_HOME = os.path.expanduser("~")
CHROMA_DATA_DIR = os.path.join(USER_HOME, ".local_chroma_data_v12")

# =====================================================================
# PIVOT: OS-LEVEL PROCESS ISOLATION ZONE
# This function is executed in a completely separate Windows process.
# Because it runs separately, ChromaDB's C++ backend never touches the 
# memory space occupied by Docling, entirely preventing the Segfault.
# =====================================================================
def isolated_chroma_upsert(db_path, docs, metas, ids, embeddings):
    import chromadb
    from chromadb.config import Settings
    
    class DummyEmbeddingFunction:
        def __call__(self, input):
            return [[0.0] * 3072 for _ in input]
        def name(self):
            return "gemini-dummy"
            
    print(f"[ISOLATED WORKER] Booting ChromaDB at {db_path}...")
    try:
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection = client.get_or_create_collection(
            name="research_papers_v12",
            embedding_function=DummyEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"[ISOLATED WORKER] Memory clean. Executing C++ upsert for {len(ids)} vectors...")
        collection.upsert(
            documents=docs,
            metadatas=metas,
            ids=ids,
            embeddings=embeddings
        )
        print("[ISOLATED WORKER] Upsert successful! Self-destructing worker process.")
        return True
    except Exception as e:
        print(f"[ISOLATED WORKER] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

# =====================================================================
# MAIN PIPELINE
# =====================================================================
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
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

async def store_document_in_chroma(doc: ParsedDocument):
    print(f"[VECTOR_STORE] Processing Document ID: {doc.doc_id}")
    try:
        docs_to_insert, metadatas, ids = [], [], []

        for section in doc.sections:
            summary_chunks = chunk_text(section.summary, chunk_size=500, overlap=50)
            for i, chunk in enumerate(summary_chunks):
                docs_to_insert.append(chunk.replace('\x00', ''))
                metadatas.append({
                    "doc_id": doc.doc_id,
                    "version_id": doc.version_id,
                    "filename": doc.filename,
                    "source_type": doc.source_type,
                    "section_name": section.section_name,
                    "content_type": "summary"
                })
                ids.append(f"{doc.doc_id}_{section.section_name}_summary_{i}")

            raw_chunks = chunk_text(section.raw_text, chunk_size=1200, overlap=200)
            for i, chunk in enumerate(raw_chunks):
                docs_to_insert.append(chunk.replace('\x00', ''))
                metadatas.append({
                    "doc_id": doc.doc_id,
                    "version_id": doc.version_id,
                    "filename": doc.filename,
                    "source_type": doc.source_type,
                    "section_name": section.section_name,
                    "content_type": "raw_text"
                })
                ids.append(f"{doc.doc_id}_{section.section_name}_raw_{i}")

        if not docs_to_insert:
            print("[VECTOR_STORE] No chunks generated. Skipping.")
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing.")

        client = genai.Client(api_key=api_key)
        all_embeddings = []

        print(f"[VECTOR_STORE] Calling Embeddings API for {len(docs_to_insert)} total chunks...")

        # Embed one chunk at a time so the response shape always matches the
        # chunk list. The previous batch path could return fewer embeddings than
        # inputs, which caused the upload to fail with a data mismatch.
        for text in docs_to_insert:
            retries = 4
            delay = 1
            for attempt in range(retries):
                try:
                    response = await client.aio.models.embed_content(
                        model="gemini-embedding-2",
                        contents=text,
                    )

                    if not getattr(response, "embeddings", None):
                        raise ValueError("API returned an empty embeddings list for chunk.")

                    emb = response.embeddings[0]
                    vals = getattr(emb, "values", None) or emb
                    clean_embedding = [float(v) for v in vals]
                    all_embeddings.append(clean_embedding)
                    break
                except Exception as e:
                    err = str(e).lower()
                    print(f"[VECTOR_STORE] Embedding error (attempt {attempt+1}): {e}")
                    if any(x in err for x in ("429", "quota", "exhausted")):
                        if attempt < retries - 1:
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        raise RuntimeError("Embedding rate limit exceeded.") from e
                    raise

            await asyncio.sleep(0.05)

        if not (len(docs_to_insert) == len(metadatas) == len(ids) == len(all_embeddings)):
            raise ValueError(
                f"Data mismatch between chunks and embeddings: docs={len(docs_to_insert)}, metas={len(metadatas)}, ids={len(ids)}, embeddings={len(all_embeddings)}"
            )

        print("[VECTOR_STORE] Dispatching database write to Isolated Windows Worker Process...")
        
        # PIVOT: The magic command that sends the data to the isolated worker process
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(
                pool,
                isolated_chroma_upsert,
                CHROMA_DATA_DIR,
                docs_to_insert,
                metadatas,
                ids,
                all_embeddings
            )
            
        print("[VECTOR_STORE] Handoff complete. Server process remains perfectly stable.")
        
    except Exception as e:
        print(f"[VECTOR_STORE] Failure: {e}")
        traceback.print_exc()
        raise