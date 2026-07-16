# Research Alignment Agent — Setup & Usage Guide

## ✅ What's Implemented

The pipeline now includes:

1. **Automatic claim extraction** from document sections
2. **Metadata-aware retrieval** with version filtering and cosine similarity
3. **Two-stage reasoning**: Analyst (semantic scoring) + Verifier (logical validation)
4. **Confidence engine** combining retrieval + analyst + verifier scores
5. **Graph persistence** of comparison edges to SQLite
6. **Lazy-loaded ChromaDB** for startup stability
7. **Robust error handling** with retries and graceful fallbacks
8. **Per-section LLM summarization** (avoids huge single-shot prompts)
9. **Batched embeddings** (64 chunks at a time) for efficiency

---

## 🚀 Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individual packages:

```bash
pip install fastapi uvicorn google-genai chromadb sqlalchemy pydantic docling aiofiles python-dotenv
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Initialize the Database

```bash
python -c "from GraphEngine.db.connection import Base, engine; Base.metadata.create_all(bind=engine); print('Database initialized!')"
```

---

## 🎯 Running the System

### Start the FastAPI Server

```bash
uvicorn ingestion_pipeline.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

### Access the Interactive API Documentation

Open in your browser: **http://localhost:8000/docs**

This opens Swagger UI where you can test all endpoints interactively.

---

## 📤 How to Upload Documents

### 1. Health Check (Optional)

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "current_active_version": 0,
  "chroma_available": true,
  "database_available": true,
  "gemini_key_set": true
}
```

### 2. Roll to a New Version (Optional but Recommended)

```bash
curl -X POST http://localhost:8000/roll-version
```

Response:
```json
{
  "message": "Version rolled successfully",
  "new_version_id": 1
}
```

This sets a version ID for all subsequent uploads. Use this to group related documents.

### 3. Upload a Document

**Using Swagger UI (Easiest):**
1. Go to http://localhost:8000/docs
2. Find the `/upload` endpoint
3. Click "Try it out"
4. Select your PDF/DOCX/HTML file
5. Choose `source_type`: "draft" or "paper"
6. Click "Execute"

**Using curl (Command Line):**

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/document.pdf" \
  -F "source_type=draft"
```

or for a paper:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/research_paper.pdf" \
  -F "source_type=paper"
```

**Using Python:**

```python
import requests

with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f},
        data={"source_type": "draft"}
    )

print(response.json())
```

---

## 📊 Expected Response

After uploading, you'll get back:

```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "my_paper.pdf",
  "source_type": "draft",
  "version_id": "1",
  "total_sections": 5,
  "sections": [
    {
      "section_name": "introduction",
      "raw_text": "...",
      "summary": "..."
    },
    ...
  ],
  "claims_count": 12,
  "comparison_count": 45,
  "message": "Processed successfully: 12 claims extracted, 45 comparisons performed under version 1"
}
```

---

## 🔄 Full Workflow Example

```bash
# 1. Start server
uvicorn ingestion_pipeline.main:app --reload

# In another terminal:

# 2. Roll version
curl -X POST http://localhost:8000/roll-version

# 3. Upload a draft
curl -X POST http://localhost:8000/upload \
  -F "file=@draft.pdf" \
  -F "source_type=draft"

# 4. Roll version again
curl -X POST http://localhost:8000/roll-version

# 5. Upload a paper (will be compared against draft)
curl -X POST http://localhost:8000/upload \
  -F "file=@paper.pdf" \
  -F "source_type=paper"

# 6. Check health
curl http://localhost:8000/health
```

---

## 📋 Pipeline Steps for Each Upload

1. **Parse & Summarize** — Docling extracts text, sections split, LLM summarizes each section
2. **Claim Extraction** — Heuristics identify 0..N claims per section
3. **Chunk Embedding** — Gemini embeds chunks (batched for efficiency)
4. **ChromaDB Storage** — Isolated worker process stores embeddings
5. **Claim Comparison** — For each claim:
   - Compute embedding
   - Retrieve top-K matching chunks (opposite doc type)
   - Score with Analyst (semantic similarity)
   - Validate with Verifier (logical compatibility)
   - Compute confidence (weighted combination)
   - Persist edges to graph database
6. **Return** — Full response with extracted claims and comparisons

---

## 🐛 Troubleshooting

### Missing Pydantic / Dependencies
```bash
pip install -r requirements.txt
```

### ChromaDB Not Found
Ensure `chromadb` is installed and CHROMA_DB_PATH exists:
```bash
mkdir -p ~/.local_chroma_data_v12
```

### GEMINI_API_KEY Error
1. Set in `.env` file or environment variable
2. Verify at: http://localhost:8000/health

### Database Lock (SQLite)
SQLite has limited concurrency. For production, migrate to PostgreSQL/MySQL. For now:
- Ensure one server instance at a time
- Use `pool_pre_ping=True` (already configured)

### No Champions Extracted
Small documents may not have enough content. The system falls back to the first sentence as a weak claim.

---

## 📚 File Structure

```
ingestion_pipeline/
  ├── main.py                # FastAPI app + /upload endpoint
  ├── summarizer.py          # Per-section LLM summarization
  ├── claim_extractor.py     # Lightweight claim extraction
  ├── chroma_store.py        # Batched embeddings + isolated worker
  ├── docling_parser.py      # PDF/DOCX parsing
  └── schemas.py             # Pydantic models

GraphEngine/
  ├── engines/
  │   ├── comparison_engine.py     # Orchestrates claim comparison
  │   ├── retrieval_engine.py      # Metadata-aware retrieval
  │   ├── analyst.py               # LLM semantic scoring
  │   ├── verifier.py              # LLM logical validation
  │   └── confidence_engine.py     # Weighted confidence
  ├── db/
  │   ├── crud.py              # Database operations
  │   ├── models.py            # SQLAlchemy schema
  │   └── connection.py        # SQLite setup
  └── utils/
      └── constants.py         # CHROMA_DB_PATH, EMBEDDING_DIM, etc.
```

---

## 🎓 Next Steps

1. **Install & start server** (steps above)
2. **Upload a draft document** — system extracts claims
3. **Upload a paper** — system compares claims automatically
4. **Query graph database** — edges show support/contradiction relationships
5. **Refine Analyst/Verifier** — replace placeholders with domain-specific logic

---

**Ready to go!** 🚀 Run the commands above and start uploading documents.
