"""Stage 2 — Interest Graph Synthesis with OpenAI Latent Need Enrichment"""
from __future__ import annotations
import json
from typing import Any

from backend.schemas import ReelDecomposition, InterestGraph
from backend.llm.deterministic import build_interest_graph
from backend.llm.client import call_structured
from backend.config import get_config
from pydantic import BaseModel


class LatentNeedLLM(BaseModel):
    latent_need: str
    identity_summary: str


def run(
    decompositions: list[ReelDecomposition],
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
) -> InterestGraph:
    graph = build_interest_graph(decompositions, interactions, reel_map)
    cfg = get_config()

    if cfg.has_llm and decompositions:
        prompt = (
            "Analyze these reel decompositions for a student watching tech reels:\n"
            + json.dumps([d.model_dump() for d in decompositions], default=str)
            + "\nSynthesize the underlying latent career goal or identity need in 1 precise sentence."
        )
        res = call_structured(
            prompt=prompt,
            schema=LatentNeedLLM,
            system="You are an expert AI cognitive profiler analyzing student watching intent.",
            temperature=0.2,
            use_strong_model=True,
        )
        if res and res.latent_need:
            graph.latent_need = res.latent_need

    return graph
