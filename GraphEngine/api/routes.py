# routes.py
from fastapi import APIRouter
from GraphEngine.schemas.schemas import EdgeCreate, RetrieveRequest
from GraphEngine.engines.graph_engine import add_graph_edge
from GraphEngine.engines.relation_engine import infer_relation
from GraphEngine.engines.retrieval_engine import retrieve_cross_type
from GraphEngine.engines.reranker import rerank

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.post("/add-paper")
def add_paper(edge: EdgeCreate):
    """Store a scored edge between two documents in the graph DB."""
    return add_graph_edge(edge)


@router.get("/paper-relation/{p1}/{p2}")
def paper_relation(p1: str, p2: str):
    """
    Return the stored relation (AGREE / DISAGREE / MIXED / unknown)
    between two documents identified by their doc_id values.
    """
    return infer_relation(p1, p2)


@router.post("/retrieve")
def retrieve(req: RetrieveRequest):
    """
    Perform a cross-type retrieval from ChromaDB.

    Given an embedding from a draft chunk, this returns the top matching
    paper chunks (and vice-versa), enforcing that draft↔draft and
    paper↔paper matches are never returned.

    Returns a list of { text, distance, metadata } objects.
    """
    raw = retrieve_cross_type(
        query_embedding=req.embedding,
        source_doc_type=req.source_type,
        chunk_type=req.chunk_type,
        n_results=req.top_k * 2,   # fetch extra before reranking
    )
    ranked = rerank(raw, top_n=req.top_k)

    return [
        {"text": text, "distance": dist, "metadata": meta}
        for text, dist, meta in ranked
    ]