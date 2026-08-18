"""Stage 6 — Difficulty and Confidence Calibration"""
from __future__ import annotations

from backend.schemas import InterestGraph, ReelDecomposition
from backend.llm.deterministic import calibrate_confidence


def run(
    graph: InterestGraph,
    decompositions: list[ReelDecomposition],
) -> tuple[str, str]:
    """Returns (confidence: 'High'|'Medium'|'Low', reason: str)"""
    return calibrate_confidence(graph, decompositions)
