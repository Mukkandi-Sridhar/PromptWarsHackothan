"""Stage 7 — Explanation & Recommendation Assembly"""
from __future__ import annotations
import uuid
from typing import Any

from backend.schemas import (
    InterestGraph, ScoredCandidate, Recommendation, SubstanceReport
)
from backend.llm.deterministic import generate_explanation
from backend.llm.client import call_structured
from backend.llm.prompts import EXPLANATION_SYSTEM, EXPLANATION_USER
from backend.config import get_config


def run(
    graph: InterestGraph,
    scored: list[ScoredCandidate],
    candidate_map: dict[str, dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
    current_reel: dict[str, Any],
    confidence: str,
    confidence_reason: str,
    substance_map: dict[str, SubstanceReport],
) -> tuple[Recommendation | None, list[Recommendation], Recommendation | None]:
    """
    Returns (primary, alternates, serendipity).
    """
    if not scored:
        return None, [], None

    cfg = get_config()

    # Pick top, 2 alternates, and serendipity (adjacent L2 domain)
    top_scored = scored[0]
    alt_scored = scored[1:3]

    # Find serendipity: different category, never watched, adjacent
    serendipity_scored: ScoredCandidate | None = None
    serendipity_categories = {"Cybersecurity", "Cloud", "Hardware"}
    top_category = top_scored.category
    for s in scored[3:]:
        if s.category in serendipity_categories and s.category != top_category:
            serendipity_scored = s
            break

    def build_rec(sc: ScoredCandidate, is_serendipity: bool = False) -> Recommendation:
        cand = candidate_map.get(sc.candidate_id, {})
        sr = substance_map.get(sc.candidate_id)

        formatted = generate_explanation(
            current_reel=current_reel,
            graph=graph,
            rec_candidate=cand,
            confidence=confidence,
            confidence_reason=confidence_reason,
            reel_map=reel_map,
        )

        # Try LLM enrichment of explanation
        if cfg.has_llm:
            top_l3 = graph.top_l3_node
            top_l2 = graph.top_l2_nodes[0] if graph.top_l2_nodes else None
            evidence_ids = top_l3.supporting_reels[:3] if top_l3 else []
            evidence_titles = [reel_map.get(r, {}).get("title", r) for r in evidence_ids]

            prompt = EXPLANATION_USER.format(
                current_reel_title=current_reel.get("title", ""),
                current_reel_id=current_reel.get("id", ""),
                l3_node=top_l3.label if top_l3 else "unknown",
                l2_domain=top_l2.label if top_l2 else cand.get("category", ""),
                evidence_reels=", ".join(f'"{t}"' for t in evidence_titles),
                rec_title=cand.get("title", ""),
                category=cand.get("category", ""),
                difficulty=cand.get("difficulty", "Beginner"),
                confidence=confidence,
                confidence_reason=confidence_reason,
                bridge_rationale=f"hook:{cand.get('hook_style','')}, same pain entry point",
            )
            # We can't easily parse free-text output as structured model here
            # so we just use deterministic and rely on it being correct

        top_l3 = graph.top_l3_node
        top_l2 = graph.top_l2_nodes[0] if graph.top_l2_nodes else None

        return Recommendation(
            rec_id=str(uuid.uuid4()),
            candidate_id=sc.candidate_id,
            title=cand.get("title", sc.title),
            category=sc.category,
            difficulty=sc.difficulty,  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            interest_detected=top_l3.label if top_l3 else "technical skill building",
            why_evidence=top_l3.label if top_l3 else "",
            why_recommendation=f"Bridges from current interest via {cand.get('hook_style','')}" ,
            formatted_block=formatted,
            is_serendipity=is_serendipity,
            serendipity_label="Exploration: adjacent domain you haven't watched" if is_serendipity else None,
            creator_handle=cand.get("creator_handle", ""),
            hook_style=cand.get("hook_style", ""),
            substance_score=sr.final_score if sr else (cand.get("substance_score") or 60),
        )

    primary = build_rec(top_scored)
    alternates = [build_rec(s) for s in alt_scored]
    serendipity = build_rec(serendipity_scored, is_serendipity=True) if serendipity_scored else None

    return primary, alternates, serendipity
