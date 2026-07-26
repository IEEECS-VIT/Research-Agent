# constants.py
import os

# ── ChromaDB ──────────────────────────────────────────────────────────────
# Must match ingestion_pipeline/chroma_store.py exactly.
USER_HOME = os.path.expanduser("~")
CHROMA_DB_PATH = os.path.join(USER_HOME, ".local_chroma_data_v12")
COLLECTION_NAME = "research_papers_v12"

# Gemini gemini-embedding-2 produces 3072-dimensional vectors.
EMBEDDING_DIM = 3072

# ── Retrieval ─────────────────────────────────────────────────────────────
# TOP_K: number of results to request from ChromaDB before reranking.
TOP_K = 15

# CHUNK_TYPE: default content_type filter for ChromaDB queries.
# Ingestion stores "summary" and "raw_text" chunks per section.
# "summary" is preferred for graph reasoning; use "raw_text" for verifier deep-checks.
CHUNK_TYPE = "summary"   # or "raw_text"

# ── Scoring ───────────────────────────────────────────────────────────────
SUPPORT_THRESHOLD = 0.65
CONTRADICT_THRESHOLD = 0.65

# ── Distance pre-filter ───────────────────────────────────────────────────
# Candidates with a cosine distance ABOVE this threshold are skipped before
# any LLM call is made. ChromaDB cosine distance range: 0 (identical) → 2 (opposite).
# 0.55 ≈ cosine similarity of 0.725 — below this the candidate is very unlikely
# to be semantically related to the claim.
# Tune via CANDIDATE_DISTANCE_THRESHOLD env var.
CANDIDATE_DISTANCE_THRESHOLD = float(
    os.getenv("CANDIDATE_DISTANCE_THRESHOLD", "0.55")
)