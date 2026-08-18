"""Stage 3 — Candidate Retrieval via composed query vector"""
from __future__ import annotations
from typing import Any

import structlog

from backend.schemas import InterestGraph
from backend.config import get_config

logger = structlog.get_logger()


def run(
    graph: InterestGraph,
    candidate_library: list[dict[str, Any]],
    chroma_collection: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Returns (candidates, composed_query_terms).
    """
    cfg = get_config()

    composed_terms: list[str] = []
    if graph.top_l2_nodes:
        composed_terms = [n.label for n in graph.top_l2_nodes]
    if graph.top_l3_node:
        composed_terms.append(f"[L3] {graph.top_l3_node.label}")

    # Try Chroma retrieval if available
    if chroma_collection is not None:
        try:
            candidates = _chroma_retrieve(graph, chroma_collection, max(cfg.RETRIEVAL_TOP_K, 35))
            if candidates and len(candidates) >= 20:
                return candidates, composed_terms
        except Exception as e:
            logger.warning("chroma_retrieve_failed", error=str(e))

    # Fallback: deterministic retrieval surfacing relevant domains + planted hype candidates
    candidates = _deterministic_retrieve(graph, candidate_library)
    return candidates, composed_terms


def _chroma_retrieve(
    graph: InterestGraph,
    collection: Any,
    top_k: int,
) -> list[dict[str, Any]]:
    """Retrieve using composed query vector from Chroma."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        l2_text = " ".join(n.label for n in graph.top_l2_nodes[:3])
        l3_text = graph.top_l3_node.label if graph.top_l3_node else ""
        query_text = f"{l2_text} {l3_text}".strip()

        if not query_text:
            return []

        query_embedding = model.encode([query_text])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
        )

        candidates = []
        if results and results.get("metadatas"):
            for meta in results["metadatas"][0]:
                if meta:
                    candidates.append(dict(meta))
        return candidates
    except Exception as e:
        logger.warning("chroma_query_error", error=str(e))
        return []


def _deterministic_retrieve(
    graph: InterestGraph,
    library: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Broad retrieval matching top L2 domains while guaranteeing planted hype reels surface for substance evaluation."""
    from backend.llm.deterministic import CATEGORY_TO_L2

    top_l2_keys = {n.id.replace("l2_", "") for n in graph.top_l2_nodes}
    target_categories: set[str] = set()
    for l2_key in top_l2_keys:
        for cat, key in CATEGORY_TO_L2.items():
            if key == l2_key:
                target_categories.add(cat)

    # Broaden categories so planted hype reels surface
    target_categories.update({"Java", "DSA", "Career", "Hardware", "AI", "HLD", "Cybersecurity"})

    candidates = [c for c in library if c.get("category") in target_categories or c.get("substance_score", 50) < 60]
    if len(candidates) < 30:
        candidates = library[:]

    return candidates[:35]
