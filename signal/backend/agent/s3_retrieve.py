"""Stage 3 — Candidate Retrieval via composed query vector using numpy cosine matrix search"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np
import structlog

from backend.schemas import InterestGraph

logger = structlog.get_logger()

# Load precomputed vectors locally
VECTORS_PATH = Path(__file__).parent.parent / "data" / "vectors.json"
VECTORS_DATA: dict[str, Any] = {}
if VECTORS_PATH.exists():
    try:
        VECTORS_DATA = json.loads(VECTORS_PATH.read_text())
    except Exception as e:
        logger.warning("vectors_load_failed", error=str(e))

CAND_IDS = list(VECTORS_DATA.get("candidates", {}).keys())
CAND_MAT = np.array([VECTORS_DATA["candidates"][i] for i in CAND_IDS], dtype=np.float32) if CAND_IDS else np.empty((0, 384), dtype=np.float32)
if CAND_MAT.shape[0] > 0:
    norms = np.linalg.norm(CAND_MAT, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    CAND_MAT /= norms

NODES = {k: np.array(v, dtype=np.float32) for k, v in VECTORS_DATA.get("nodes", {}).items()}


def run(
    graph: InterestGraph,
    candidate_library: list[dict[str, Any]],
    chroma_collection: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Retrieves top 35 candidates via numpy matrix cosine search over composed interest graph vector.
    """
    composed_terms: list[str] = []
    if graph.top_l2_nodes:
        composed_terms = [n.label for n in graph.top_l2_nodes]
    if graph.top_l3_node:
        composed_terms.append(f"[L3] {graph.top_l3_node.label}")

    cand_map = {c["id"]: c for c in candidate_library}

    if CAND_MAT.shape[0] > 0 and (graph.top_l2_nodes or graph.top_l3_node):
        try:
            # Build composed query vector
            q_vec = np.zeros(384, dtype=np.float32)
            for node in graph.top_l2_nodes:
                if node.label in NODES:
                    q_vec += (node.weight or 1.0) * NODES[node.label]
            if graph.top_l3_node and graph.top_l3_node.label in NODES:
                q_vec += 0.25 * NODES[graph.top_l3_node.label]

            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec /= q_norm
                scores = CAND_MAT @ q_vec
                top_indices = np.argsort(-scores)[:35]
                retrieved_ids = [CAND_IDS[i] for i in top_indices]
                candidates = [cand_map[cid] for cid in retrieved_ids if cid in cand_map]
                if len(candidates) >= 20:
                    return candidates, composed_terms
        except Exception as e:
            logger.warning("numpy_vector_retrieve_failed", error=str(e))

    # Fallback to broad library slice
    candidates = candidate_library[:35] if candidate_library else []
    return candidates, composed_terms
