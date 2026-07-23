"""List routes and run subsystem smoke checks."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(override=True)

from ingestion_pipeline.main import app as ingest_app
from GraphEngine.main import app as graph_app


def print_routes(application, name: str) -> None:
    print(f"\n=== {name} ===")
    for route in sorted(application.routes, key=lambda r: getattr(r, "path", "")):
        if hasattr(route, "methods"):
            methods = ",".join(sorted(route.methods))
            print(f"  {methods:12} {route.path}")


def smoke() -> None:
    print("\n=== Subsystem smoke ===")
    from GraphEngine.db.connection import SessionLocal
    from sqlalchemy import text
    from GraphEngine.engines.retrieval_engine import _get_client
    from GraphEngine.analytics.graph_builder import build_graph_from_sqlite
    from GraphEngine.analytics.traversal import filter_edges, find_claim_neighbors
    from GraphEngine.analytics.graph_summary import graph_summary
    from GraphEngine.langgraph_adapter import adapter

    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception as exc:
        print(f"  SQLite: FAIL ({exc})")
    else:
        print("  SQLite: OK")

    chroma_ok = False
    try:
        client = _get_client()
        cols = client.list_collections()
        chroma_ok = True
        print(f"  ChromaDB: OK ({len(cols)} collection(s))")
    except Exception as exc:
        print(f"  ChromaDB: FAIL ({exc})")

    try:
        g = build_graph_from_sqlite()
        summary = graph_summary(g)
        n = len(filter_edges(g))
        node = next(iter(g.nodes), None)
        neigh = find_claim_neighbors(g, node, {}) if node else []
        print(
            f"  NetworkX rebuild: OK (nodes={summary.get('node_count', g.number_of_nodes())}, "
            f"edges={summary.get('edge_count', g.number_of_edges())}, "
            f"filtered={n}, sample_neighbors={len(neigh)})"
        )
    except Exception as exc:
        print(f"  NetworkX rebuild: FAIL ({exc})")

    print(f"  LangGraph SDK adapter: available={adapter.available}")
    print(f"  GEMINI_API_KEY set: {bool(os.getenv('GEMINI_API_KEY'))}")
    print(f"  graph.db exists: {os.path.exists('graph.db')}")


if __name__ == "__main__":
    print_routes(ingest_app, "ingestion_pipeline.main (uvicorn default :8000)")
    print_routes(graph_app, "GraphEngine.main (separate app, NOT mounted on :8000)")
    smoke()
