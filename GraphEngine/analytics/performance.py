"""Performance measurement helpers for graph analytics and validation."""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict

from GraphEngine.analytics.graph_builder import build_graph_from_sqlite
from GraphEngine.analytics.graph_summary import graph_summary
from GraphEngine.analytics.traversal import get_high_confidence_contradictions, get_low_confidence_edges
from GraphEngine.analytics.clustering import find_contradiction_clusters, find_low_confidence_regions


@dataclass
class PerformanceMetrics:
    ingestion_speed_rps: float = 0.0
    graph_reconstruction_seconds: float = 0.0
    traversal_latency_seconds: float = 0.0
    clustering_runtime_seconds: float = 0.0
    sqlite_query_latency_seconds: float = 0.0
    networkx_memory_hint_nodes: int = 0
    networkx_memory_hint_edges: int = 0


def measure_graph_pipeline_performance() -> dict:
    """Collect a small set of timing and size metrics for diagnostics."""
    start = time.perf_counter()
    graph = build_graph_from_sqlite()
    graph_reconstruction_seconds = time.perf_counter() - start

    traversal_start = time.perf_counter()
    _ = get_high_confidence_contradictions(graph)
    _ = get_low_confidence_edges(graph)
    traversal_latency_seconds = time.perf_counter() - traversal_start

    clustering_start = time.perf_counter()
    _ = find_contradiction_clusters(graph)
    _ = find_low_confidence_regions(graph)
    clustering_runtime_seconds = time.perf_counter() - clustering_start

    summary = graph_summary(graph)
    metrics = PerformanceMetrics(
        graph_reconstruction_seconds=graph_reconstruction_seconds,
        traversal_latency_seconds=traversal_latency_seconds,
        clustering_runtime_seconds=clustering_runtime_seconds,
        networkx_memory_hint_nodes=summary["total_nodes"],
        networkx_memory_hint_edges=summary["total_edges"],
    )

    # Simple derived metric: edges reconstructed per second.
    if graph_reconstruction_seconds > 0:
        metrics.ingestion_speed_rps = summary["total_edges"] / graph_reconstruction_seconds

    return asdict(metrics)
