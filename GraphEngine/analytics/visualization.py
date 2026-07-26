"""Optional lightweight visualization helpers for debugging semantic regions."""

from __future__ import annotations

import networkx as nx


def render_semantic_subgraph(graph: nx.DiGraph, node_ids: list[str], output_path: str | None = None) -> dict:
    """Render a small semantic subgraph for inspection.

    If matplotlib is unavailable, returns a serializable graph summary instead of failing.
    """
    subgraph = graph.subgraph(node_ids).copy()

    try:
        import matplotlib.pyplot as plt
    except Exception:
        return {
            "nodes": list(subgraph.nodes(data=True)),
            "edges": list(subgraph.edges(data=True)),
            "rendered": False,
        }

    plt.figure(figsize=(10, 7))
    pos = nx.spring_layout(subgraph, seed=42)
    edge_labels = {
        (u, v): d.get("relation_type", "MIXED") for u, v, d in subgraph.edges(data=True)
    }
    nx.draw(subgraph, pos, with_labels=True, node_size=1200, font_size=8)
    nx.draw_networkx_edge_labels(subgraph, pos, edge_labels=edge_labels, font_size=7)
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
    plt.close()

    return {
        "nodes": list(subgraph.nodes(data=True)),
        "edges": list(subgraph.edges(data=True)),
        "rendered": True,
        "output_path": output_path,
    }
