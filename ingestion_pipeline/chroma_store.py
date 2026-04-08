import os
import chromadb
from chromadb.utils import embedding_functions
from schemas import ParsedDocument

# Initialize Chroma Persistent Client (creates a local folder for the DB)
CHROMA_DATA_DIR = os.path.join(os.path.dirname(__file__), "chroma_data")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)

# Use Gemini to generate embeddings for the chunks
def get_gemini_embedding_function():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    return embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=api_key)

# Get or create the collection for our research papers
collection = chroma_client.get_or_create_collection(
    name="research_papers",
    embedding_function=get_gemini_embedding_function()
)

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

def store_document_in_chroma(doc: ParsedDocument):
    """
    Chunks the summaries (and optionally raw text), attaches metadata including
    the doc_id, and upserts them into ChromaDB.
    """
    docs_to_insert = []
    metadatas = []
    ids = []

    for section in doc.sections:
        # 1. Chunk and prep the Summary text
        summary_chunks = chunk_text(section.summary, chunk_size=500, overlap=50)
        for i, chunk in enumerate(summary_chunks):
            # Create a unique, deterministic ID for this specific chunk
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

        # 2. Chunk and prep the Raw text (Optional, but recommended for deeper retrieval)
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

    # Execute the upsert to ChromaDB
    if docs_to_insert:
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully inserted {len(docs_to_insert)} chunks into ChromaDB for Document ID: {doc.doc_id}")