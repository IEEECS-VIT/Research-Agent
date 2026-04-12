import os
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai
from schemas import ParsedDocument

CHROMA_DATA_DIR = os.path.join(os.path.dirname(__file__), "chroma_data")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)

class NewGeminiEmbeddingFunction(EmbeddingFunction):
     # ✅ FIX: Made name a callable method to satisfy ChromaDB's internal checks
     def name(self) -> str:
         return "custom_gemini_genai_embedding_v4"

     def __init__(self):
         api_key = os.getenv("GEMINI_API_KEY")
         if not api_key:
             raise ValueError("GEMINI_API_KEY not found in .env")
         self.client = genai.Client(api_key=api_key)

     def __call__(self, input: Documents) -> Embeddings:
         response = self.client.models.embed_content(
             model="gemini-embedding-001",
             contents=input
         )
         return [e.values for e in response.embeddings]


# ✅ FIX: Bumped collection to v4 to ensure a clean database initialization
collection = chroma_client.get_or_create_collection(
     name="research_papers_v4",
     embedding_function=NewGeminiEmbeddingFunction()
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

         # 2. Chunk and prep the Raw text 
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

     if docs_to_insert:
         collection.upsert(
             documents=docs_to_insert,
             metadatas=metadatas,
             ids=ids
         )
         print(f"Successfully inserted {len(docs_to_insert)} chunks into ChromaDB for Document ID: {doc.doc_id}")