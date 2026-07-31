import asyncio
import logging
import os
from typing import Any

from pinecone import Pinecone

from app.core.config import get_settings
from GraphEngine.utils.gemini_client import _get_client
from ingestion_pipeline.schemas import ParsedDocument

logger = logging.getLogger(__name__)

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

async def store_document_in_pinecone(doc: ParsedDocument):
    logger.info("Processing Document ID: %s", doc.doc_id)
    settings = get_settings()
    
    if not settings.pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is not set.")
    
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_index_name
    index = pc.Index(index_name)

    try:
        texts_to_embed, metadatas, ids = [], [], []

        for section in doc.sections:
            summary_chunks = chunk_text(section.summary, chunk_size=500, overlap=50)
            for i, chunk in enumerate(summary_chunks):
                texts_to_embed.append(chunk.replace("\x00", ""))
                metadatas.append({
                    "doc_id": doc.doc_id,
                    "version_id": doc.version_id,
                    "filename": doc.filename,
                    "source_type": doc.source_type,
                    "section_name": section.section_name,
                    "content_type": "summary",
                    "doi": doc.doi or "",
                    "text": chunk.replace("\x00", "")
                })
                ids.append(f"{doc.doc_id}_{section.section_name}_summary_{i}")

            raw_chunks = chunk_text(section.raw_text, chunk_size=1200, overlap=200)
            for i, chunk in enumerate(raw_chunks):
                texts_to_embed.append(chunk.replace("\x00", ""))
                metadatas.append({
                    "doc_id": doc.doc_id,
                    "version_id": doc.version_id,
                    "filename": doc.filename,
                    "source_type": doc.source_type,
                    "section_name": section.section_name,
                    "content_type": "raw_text",
                    "doi": doc.doi or "",
                    "text": chunk.replace("\x00", "")
                })
                ids.append(f"{doc.doc_id}_{section.section_name}_raw_{i}")

        if not texts_to_embed:
            logger.warning("No chunks generated. Skipping.")
            return

        gemini_client = _get_client()
        logger.info("Calling Embeddings API for %d total chunks...", len(texts_to_embed))
        EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "20"))

        async def _embed_one(text: str, idx: int) -> list[float]:
            retries = 4
            delay = 1.0
            for attempt in range(retries):
                try:
                    response = await gemini_client.aio.models.embed_content(
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
        total_chunks = len(texts_to_embed)

        for batch_start in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, total_chunks)
            batch = texts_to_embed[batch_start:batch_end]
            logger.info(
                "Embedding batch %d/%d (chunks %d-%d)...",
                batch_start // EMBED_BATCH_SIZE + 1,
                -(-total_chunks // EMBED_BATCH_SIZE),
                batch_start + 1,
                batch_end,
            )
            batch_embeddings = await asyncio.gather(
                *[_embed_one(text, batch_start + i) for i, text in enumerate(batch)]
            )
            all_embeddings.extend(batch_embeddings)

            if batch_end < total_chunks:
                await asyncio.sleep(0.5)

        logger.info("Upserting %d vectors to Pinecone...", len(ids))
        
        vectors = []
        for i in range(len(ids)):
            vectors.append({
                "id": ids[i],
                "values": all_embeddings[i],
                "metadata": metadatas[i]
            })
        
        # Upsert in batches of 100 for Pinecone
        PINECONE_BATCH_SIZE = 100
        for i in range(0, len(vectors), PINECONE_BATCH_SIZE):
            batch = vectors[i:i + PINECONE_BATCH_SIZE]
            index.upsert(vectors=batch)

        logger.info("Pinecone upsert complete.")

    except Exception as e:
        logger.error("Failure: %s", e, exc_info=True)
        raise
