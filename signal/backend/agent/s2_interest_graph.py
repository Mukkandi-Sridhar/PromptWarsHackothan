"""Stage 2 — Interest Graph Synthesis"""
from __future__ import annotations
from typing import Any

from backend.schemas import ReelDecomposition, InterestGraph
from backend.llm.deterministic import build_interest_graph


def run(
    decompositions: list[ReelDecomposition],
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
) -> InterestGraph:
    # Always deterministic — the graph logic is rule-based by design.
    # LLM is used only to enrich latent_need in Stage 2+ (future).
    return build_interest_graph(decompositions, interactions, reel_map)
