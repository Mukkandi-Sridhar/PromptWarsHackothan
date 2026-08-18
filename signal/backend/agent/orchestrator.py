"""
Agent Orchestrator — runs 7 stages, emits SSE events after each.
Also implements Shallow Mode (honest TF-IDF baseline).
"""
from __future__ import annotations
import json
import re
import uuid
from collections import Counter
from typing import Any, AsyncIterator

import structlog

from backend.schemas import AgentTrace
from backend.agent import (
    s1_decompose, s2_interest_graph, s3_retrieve,
    s4_substance_gate, s5_fit_rank, s6_calibrate, s7_explain,
)
from backend.config import get_config

logger = structlog.get_logger()


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def run_agent(
    session_id: str,
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
    candidate_library: list[dict[str, Any]],
    chroma_collection: Any | None,
    mode: str = "agent",
) -> AsyncIterator[str]:
    """Async generator yielding SSE strings."""
    cfg = get_config()
    trace = AgentTrace(session_id=session_id, mode=mode)  # type: ignore[arg-type]

    if mode == "shallow":
        async for chunk in _run_shallow(session_id, interactions, reel_map, candidate_library, trace):
            yield chunk
        return

    # ── STAGE 1: Decomposition ──────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 1, "label": "Semantic Decomposition"})

    decompositions = []
    valid_interactions = [ia for ia in interactions if ia.get("reel_id") in reel_map]

    for ia in valid_interactions:
        reel = reel_map[ia["reel_id"]]
        # Merge interaction engagement into reel dict
        reel_with_eng = dict(reel)
        reel_with_eng["engagement"] = {
            "watch_completion": ia.get("watch_completion", 0),
            "rewatched": ia.get("rewatched", False),
            "liked": ia.get("liked", False),
            "saved": ia.get("saved", False),
            "shared": ia.get("shared", False),
            "commented": ia.get("commented", False),
            "skipped_at_sec": ia.get("skipped_at_sec"),
        }
        dec = s1_decompose.run(reel_with_eng)
        decompositions.append(dec)
        yield _sse("decomposition", dec.model_dump())

    trace.decompositions = decompositions

    # ── STAGE 2: Interest Graph ─────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 2, "label": "Interest Graph Synthesis"})

    graph = s2_interest_graph.run(decompositions, interactions, reel_map)
    trace.interest_graph = graph
    trace.shallow_moves_blocked = graph.shallow_moves_blocked

    yield _sse("interest_graph", {
        "nodes": [n.model_dump() for n in graph.nodes],
        "edges": [e.model_dump() for e in graph.edges],
        "convergence": {
            n.id: n.convergence for n in graph.nodes if n.layer != "L1"
        },
        "latent_need": graph.latent_need,
        "shallow_moves_blocked": graph.shallow_moves_blocked,
        "top_l3": graph.top_l3_node.model_dump() if graph.top_l3_node else None,
        "top_l2": [n.model_dump() for n in graph.top_l2_nodes],
    })

    # ── STAGE 3: Retrieval ──────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 3, "label": "Candidate Retrieval"})

    candidates, composed_terms = s3_retrieve.run(graph, candidate_library, chroma_collection)
    trace.composed_query_terms = composed_terms
    trace.candidate_count = len(candidates)

    yield _sse("retrieval", {
        "composed_query_terms": composed_terms,
        "candidate_count": len(candidates),
    })

    # ── STAGE 4: Substance Gate ─────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 4, "label": "Substance Gate"})

    passed, reports = s4_substance_gate.run(candidates)
    substance_map = {r.candidate_id: r for r in reports}
    rejected = [r for r in reports if not r.passed]

    trace.substance_reports = reports
    trace.passed_candidates = [p["id"] for p in passed]
    trace.rejected_candidates = rejected

    yield _sse("substance", {
        "passed": [{"id": p["id"], "title": p["title"], "score": substance_map[p["id"]].final_score} for p in passed],
        "rejected": [r.model_dump() for r in rejected],
        "llm_used": cfg.has_llm,
    })

    # ── STAGE 5: Fit Ranking ────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 5, "label": "Fit Ranking"})

    current_reel = _get_current_reel(interactions, reel_map)
    watched_ids = {ia["reel_id"] for ia in interactions}
    current_sophistication = _infer_sophistication(decompositions)
    watched_concepts = set()
    for ia in interactions:
        reel = reel_map.get(ia.get("reel_id", ""), {})
        watched_concepts.update(t.lower() for t in reel.get("tags", []))

    scored, echo_blocked = s5_fit_rank.run(
        passed_candidates=passed,
        graph=graph,
        watched_reel_ids=watched_ids,
        current_sophistication=current_sophistication,
        current_reel=current_reel,
        watched_concepts=watched_concepts,
    )
    trace.scored_candidates = scored
    all_blocked = list(trace.shallow_moves_blocked or []) + list(echo_blocked)
    trace.shallow_moves_blocked = all_blocked

    yield _sse("ranking", {
        "scored": [s.model_dump() for s in scored[:10]],
        "shallow_moves_blocked": all_blocked,
    })

    # ── STAGE 6: Calibration ────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 6, "label": "Confidence Calibration"})

    confidence, confidence_reason = s6_calibrate.run(graph, decompositions)
    trace.confidence = confidence  # type: ignore[assignment]
    trace.confidence_reason = confidence_reason

    # ── STAGE 7: Explanation ────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 7, "label": "Explanation & Recommendation"})

    candidate_map = {c["id"]: c for c in candidate_library}

    primary, alternates, serendipity = s7_explain.run(
        graph=graph,
        scored=scored,
        candidate_map=candidate_map,
        reel_map=reel_map,
        current_reel=current_reel,
        confidence=confidence,
        confidence_reason=confidence_reason,
        substance_map=substance_map,
    )

    trace.recommendation = primary
    trace.alternates = alternates
    trace.serendipity = serendipity
    trace.llm_used = cfg.has_llm

    yield _sse("recommendation", {
        "formatted_block": primary.formatted_block if primary else "",
        "recommendation": primary.model_dump() if primary else None,
        "alternates": [a.model_dump() for a in alternates],
        "serendipity": serendipity.model_dump() if serendipity else None,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "llm_used": cfg.has_llm,
        "offline_mode": not cfg.has_llm,
    })

    yield _sse("trace", trace.model_dump())
    yield _sse("done", {"session_id": session_id})


async def _run_shallow(
    session_id: str,
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
    candidate_library: list[dict[str, Any]],
    trace: AgentTrace,
) -> AsyncIterator[str]:
    """
    Honest Shallow Mode — TF-IDF keyword overlap, no gating, no graph.
    Genuinely returns another Java meme and AI-tools listicle.
    """
    yield _sse("stage_start", {"stage": 1, "label": "Keyword Matching (Shallow)"})

    # Get all tags from watched reels
    watched_tags: list[str] = []
    for ia in interactions:
        reel = reel_map.get(ia.get("reel_id", ""), {})
        watched_tags.extend([t.lower() for t in reel.get("tags", [])])

    tag_freq = Counter(watched_tags)

    # TF-IDF-style: score each candidate by tag overlap with watched corpus
    def shallow_score(cand: dict) -> float:
        cand_tags = [t.lower() for t in cand.get("tags", [])]
        return sum(tag_freq.get(t, 0) for t in cand_tags)

    scored = sorted(candidate_library, key=shallow_score, reverse=True)
    top = scored[:3]  # shallow takes top-3, no gating

    yield _sse("retrieval", {
        "composed_query_terms": list(tag_freq.keys())[:8],
        "candidate_count": len(scored),
        "mode": "shallow",
        "note": "TF-IDF keyword overlap — no substance gate, no abstraction",
    })

    # No substance gating in shallow mode
    recs = []
    for cand in top:
        recs.append({
            "id": cand["id"],
            "title": cand["title"],
            "category": cand.get("category", ""),
            "score": shallow_score(cand),
            "substance_score": cand.get("substance_score", 50),
            "hook_style": cand.get("hook_style", ""),
            "creator_handle": cand.get("creator_handle", ""),
        })

    current_reel = _get_current_reel(interactions, reel_map)

    primary_cand = top[0] if top else {}
    dummy_block = (
        f"CURRENT REEL: {current_reel.get('title', 'unknown')}\n"
        f"INTEREST DETECTED: keyword match → {', '.join(list(tag_freq.keys())[:3])}\n"
        f"WHY: TF-IDF overlap on surface tokens\n"
        f"RECOMMENDED TECH REEL: {primary_cand.get('title', 'N/A')}\n"
        f"CATEGORY: {primary_cand.get('category', 'N/A')}\n"
        f"WHY THIS RECOMMENDATION: Highest keyword overlap with watched tags\n"
        f"DIFFICULTY: {primary_cand.get('difficulty', 'N/A')}\n"
        f"CONFIDENCE: N/A (shallow mode)"
    )

    from backend.schemas import Recommendation
    primary_rec = Recommendation(
        rec_id=str(uuid.uuid4()),
        candidate_id=primary_cand.get("id", ""),
        title=primary_cand.get("title", ""),
        category=primary_cand.get("category", ""),
        difficulty=primary_cand.get("difficulty", "Beginner"),  # type: ignore[arg-type]
        confidence="Low",  # type: ignore[arg-type]
        interest_detected="keyword surface match",
        why_evidence="TF-IDF overlap on surface tokens only",
        why_recommendation="Highest tag overlap with watched content",
        formatted_block=dummy_block,
    ) if primary_cand else None

    alt_recs = []
    for cand in top[1:]:
        alt_recs.append(Recommendation(
            rec_id=str(uuid.uuid4()),
            candidate_id=cand.get("id", ""),
            title=cand.get("title", ""),
            category=cand.get("category", ""),
            difficulty=cand.get("difficulty", "Beginner"),  # type: ignore[arg-type]
            confidence="Low",  # type: ignore[arg-type]
            interest_detected="keyword surface match",
            why_evidence="TF-IDF surface overlap",
            why_recommendation="Surface keyword match",
            formatted_block="",
        ))

    yield _sse("recommendation", {
        "formatted_block": dummy_block,
        "recommendation": primary_rec.model_dump() if primary_rec else None,
        "alternates": [r.model_dump() for r in alt_recs],
        "serendipity": None,
        "candidates_raw": recs,
        "mode": "shallow",
        "note": "No substance gate applied. No abstraction. Surface keyword matching only.",
    })

    trace.recommendation = primary_rec
    trace.alternates = alt_recs
    yield _sse("trace", trace.model_dump())
    yield _sse("done", {"session_id": session_id})


def _infer_sophistication(decompositions) -> str:
    levels = [d.sophistication_level for d in decompositions]
    if "advanced" in levels:
        return "intermediate"
    if "intermediate" in levels:
        return "intermediate"
    return "beginner"


def _get_current_reel(
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Get the most recently watched reel with meaningful engagement."""
    # Prefer saved/shared/rewatched
    for ia in reversed(interactions):
        if ia.get("saved") or ia.get("shared") or ia.get("rewatched"):
            return reel_map.get(ia["reel_id"], {"id": ia["reel_id"], "title": ia["reel_id"]})
    # Fallback: last watched
    if interactions:
        last = interactions[-1]
        return reel_map.get(last["reel_id"], {"id": last["reel_id"], "title": last["reel_id"]})
    return {}
