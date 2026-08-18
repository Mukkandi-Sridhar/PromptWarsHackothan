"""Stage 1 — Semantic Decomposition"""
from __future__ import annotations
from typing import Any

from backend.schemas import ReelDecomposition
from backend.llm.deterministic import decompose_reel as det_decompose
from backend.llm.client import call_structured
from backend.llm.prompts import DECOMPOSITION_SYSTEM, DECOMPOSITION_USER
from backend.config import get_config


def run(reel: dict[str, Any]) -> ReelDecomposition:
    cfg = get_config()
    eng = reel.get("engagement", {})

    if cfg.has_llm:
        prompt = DECOMPOSITION_USER.format(
            reel_id=reel["id"],
            title=reel.get("title", ""),
            caption=reel.get("caption", ""),
            transcript=reel.get("transcript_excerpt", ""),
            duration=reel.get("duration_sec", 0),
            tags=", ".join(reel.get("tags", [])),
            watch_pct=eng.get("watch_completion", 0),
            rewatched=eng.get("rewatched", False),
            liked=eng.get("liked", False),
            saved=eng.get("saved", False),
            shared=eng.get("shared", False),
        )
        result = call_structured(
            prompt=prompt,
            schema=ReelDecomposition,
            system=DECOMPOSITION_SYSTEM,
            temperature=0.2,
        )
        if result:
            # Ensure reel_id is set
            result.reel_id = reel["id"]
            return result

    # Fallback to deterministic
    return det_decompose(reel)
