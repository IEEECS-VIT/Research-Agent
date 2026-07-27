import os
import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from GraphEngine.utils.gemini_client import _get_client
from ingestion_pipeline.schemas import ParsedDocument

logger = logging.getLogger(__name__)

USER_HOME = os.path.expanduser("~")
CHROMA_DATA_DIR = os.environ.get("CHROMA_DB_PATH") or os.path.join(USER_HOME, ".local_chroma_data_v12")


def isolated_chroma_upsert(db_path, docs, metas, ids, embeddings):
    import chromadb
    from chromadb.config import Settings

    class DummyEmbeddingFunction:
        def __call__(self, input):
            return [[0.0] * 3072 for _ in input]
        def name(self):
            return "gemini-dummy"

    logger.info("Booting ChromaDB at %s...", db_path)
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

        logger.info("Executing C++ upsert for %d vectors...", len(ids))
        collection.upsert(
            documents=docs,
            metadatas=metas,
            ids=ids,
            embeddings=embeddings
        )
        logger.info("Upsert successful!")
        return True
    except Exception as e:
        logger.error("FATAL ERROR: %s", e, exc_info=True)
        raise


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
    logger.info("Processing Document ID: %s", doc.doc_id)
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
                    "content_type": "summary",
                    "doi": doc.doi or ""
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
                    "content_type": "raw_text",
                    "doi": doc.doi or ""
                })
                ids.append(f"{doc.doc_id}_{section.section_name}_raw_{i}")

        if not docs_to_insert:
            logger.warning("No chunks generated. Skipping.")
            return

        client = _get_client()

        logger.info("Calling Embeddings API for %d total chunks...", len(docs_to_insert))

        EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "20"))

        async def _embed_one(text: str, idx: int) -> list[float]:
            retries = 4
            delay = 1.0
            for attempt in range(retries):
                try:
                    response = await client.aio.models.embed_content(
                        model="gemini-embedding-2",
                        contents=text,
                    )
                    if not getattr(response, "embeddings", None):
                        raise ValueError(f"Empty embeddings returned for chunk {idx}.")
                    emb = response.embeddings[0]
                    vals = getattr(emb, "values", None) or emb
                    return [float(v) for v in vals]
                except Exception as e:
                    err = str(e).lower()
                    logger.warning("Chunk %d embed error (attempt %d): %s", idx, attempt + 1, e)
                    if any(x in err for x in ("429", "quota", "exhausted")):
                        if attempt < retries - 1:
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        raise RuntimeError(f"Embedding rate limit exceeded for chunk {idx}.") from e
                    raise
            raise RuntimeError(f"Embedding failed after {retries} retries for chunk {idx}.")

        all_embeddings: list[list[float]] = []
        total_chunks = len(docs_to_insert)

        for batch_start in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, total_chunks)
            batch = docs_to_insert[batch_start:batch_end]
            logger.info(
                "Embedding batch %d/%d (chunks %d-%d)...",
                batch_start // EMBED_BATCH_SIZE + 1,
                -(-total_chunks // EMBED_BATCH_SIZE),
                batch_start + 1, batch_end,
            )
            batch_embeddings = await asyncio.gather(
                *[_embed_one(text, batch_start + i) for i, text in enumerate(batch)]
            )
            all_embeddings.extend(batch_embeddings)

            if batch_end < total_chunks:
                await asyncio.sleep(0.5)

        if not (len(docs_to_insert) == len(metadatas) == len(ids) == len(all_embeddings)):
            raise ValueError(
                f"Data mismatch: docs={len(docs_to_insert)}, metas={len(metadatas)}, "
                f"ids={len(ids)}, embeddings={len(all_embeddings)}"
            )

        logger.info("Dispatching database write to Isolated Windows Worker Process...")

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

        logger.info("Handoff complete. Server process remains perfectly stable.")

    except Exception as e:
        logger.error("Failure: %s", e, exc_info=True)
        raise
