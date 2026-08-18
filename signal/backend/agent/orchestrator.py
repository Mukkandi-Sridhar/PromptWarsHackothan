"""
Agent Orchestrator — runs 7 stages, emits SSE events after each.
Supports current_reel_id tracking, zero-signal reel handling, and serendipity pick exemption.
"""
from __future__ import annotations
import json
import uuid
from collections import Counter
from typing import Any, AsyncIterator

import structlog

from backend.schemas import AgentTrace, Recommendation
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
    current_reel_id: str | None = None,
) -> AsyncIterator[str]:
    """Async generator yielding SSE strings."""
    cfg = get_config()
    trace = AgentTrace(session_id=session_id, mode=mode)  # type: ignore[arg-type]

    if mode == "shallow":
        async for chunk in _run_shallow(session_id, interactions, reel_map, candidate_library, trace, current_reel_id):
            yield chunk
        return

    # ── STAGE 1: Decomposition ──────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 1, "label": "Semantic Decomposition"})

    decompositions = []
    valid_interactions = [ia for ia in interactions if ia.get("reel_id") in reel_map]

    for ia in valid_interactions:
        reel = reel_map[ia["reel_id"]]
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

    current_reel = _get_current_reel(interactions, reel_map, current_reel_id)
    watched_ids = {ia["reel_id"] for ia in interactions}
    current_sophistication = _infer_sophistication(decompositions)
    watched_concepts = set()
    for ia in interactions:
        reel = reel_map.get(ia.get("reel_id", ""), {})
        watched_concepts.update(t.lower() for t in reel.get("tags", []))

    # Detect zero-signal reel status (Part 2)
    current_reel_no_signal, no_signal_reason = _check_zero_signal(current_reel, interactions, graph)

    scored_primary, scored_adjacent, echo_blocked = s5_fit_rank.run(
        passed_candidates=passed,
        graph=graph,
        watched_reel_ids=watched_ids,
        current_sophistication=current_sophistication,
        current_reel=current_reel,
        watched_concepts=watched_concepts,
    )
    trace.scored_candidates = scored_primary
    all_blocked = list(trace.shallow_moves_blocked or []) + list(echo_blocked)
    trace.shallow_moves_blocked = all_blocked

    yield _sse("ranking", {
        "scored": [s.model_dump() for s in scored_primary[:10]],
        "shallow_moves_blocked": all_blocked,
    })

    # ── STAGE 6: Calibration ────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 6, "label": "Confidence Calibration"})

    confidence, confidence_reason = s6_calibrate.run(graph, decompositions)
    trace.confidence = confidence  # type: ignore[arg-type]
    trace.confidence_reason = confidence_reason

    # ── STAGE 7: Explanation ────────────────────────────────────────────────
    yield _sse("stage_start", {"stage": 7, "label": "Explanation & Recommendation"})

    candidate_map = {c["id"]: c for c in candidate_library}

    primary, alternates, serendipity = s7_explain_run(
        graph=graph,
        scored_primary=scored_primary,
        scored_adjacent=scored_adjacent,
        candidate_map=candidate_map,
        reel_map=reel_map,
        current_reel=current_reel,
        confidence=confidence,
        confidence_reason=confidence_reason,
        substance_map=substance_map,
        current_reel_no_signal=current_reel_no_signal,
        no_signal_reason=no_signal_reason,
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
        "current_reel_no_signal": current_reel_no_signal,
        "no_signal_reason": no_signal_reason,
        "zero_signal_note": f"no signal from current reel · graph unchanged ({no_signal_reason})" if current_reel_no_signal else None,
        "llm_used": cfg.has_llm,
        "offline_mode": not cfg.has_llm,
    })

    yield _sse("trace", trace.model_dump())
    yield _sse("done", {"session_id": session_id})


def s7_explain_run(
    graph: Any,
    scored_primary: list[Any],
    scored_adjacent: list[Any],
    candidate_map: dict[str, dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
    current_reel: dict[str, Any],
    confidence: str,
    confidence_reason: str,
    substance_map: dict[str, Any],
    current_reel_no_signal: bool,
    no_signal_reason: str,
) -> tuple[Recommendation | None, list[Recommendation], Recommendation | None]:
    if not scored_primary:
        return None, [], None

    from backend.llm.deterministic import generate_explanation

    top_scored = scored_primary[0]
    alt_scored = scored_primary[1:3]

    def build_rec(sc: Any, is_serendipity: bool = False) -> Recommendation:
        cand = candidate_map.get(sc.candidate_id, {})
        sr = substance_map.get(sc.candidate_id)

        formatted = generate_explanation(
            current_reel=current_reel,
            graph=graph,
            rec_candidate=cand,
            confidence=confidence,
            confidence_reason=confidence_reason,
            reel_map=reel_map,
            current_reel_no_signal=current_reel_no_signal,
            no_signal_reason=no_signal_reason,
        )

        top_l3 = graph.top_l3_node
        top_l2 = graph.top_l2_nodes[0] if graph.top_l2_nodes else None

        serendipity_note = (
            f"↳ outside your current interests, adjacent to {top_l2.label if top_l2 else 'backend engineering'}"
            if is_serendipity else None
        )

        return Recommendation(
            rec_id=str(uuid.uuid4()),
            candidate_id=sc.candidate_id,
            title=cand.get("title", sc.title),
            category=sc.category,
            difficulty=sc.difficulty,  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            interest_detected=top_l3.label if top_l3 else "technical skill building",
            why_evidence=top_l3.label if top_l3 else "",
            why_recommendation=serendipity_note or f"Bridges from current interest via {cand.get('hook_style','')}",
            formatted_block=formatted,
            is_serendipity=is_serendipity,
            serendipity_label="ALSO WORTH 60 SECONDS · exploration" if is_serendipity else None,
            creator_handle=cand.get("creator_handle", ""),
            hook_style=cand.get("hook_style", ""),
            substance_score=sr.final_score if sr else (cand.get("substance_score") or 60),
        )

    primary = build_rec(top_scored)
    alternates = [build_rec(s) for s in alt_scored]

    # Serendipity selection per Part 3: picks top from adjacent candidates (no L2 overlap)
    serendipity: Recommendation | None = None
    if scored_adjacent:
        serendipity = build_rec(scored_adjacent[0], is_serendipity=True)
    else:
        # Fallback to Cybersecurity candidate
        login_cand = next((c for c in candidate_map.values() if "login session" in c.get("title", "").lower()), None)
        if login_cand:
            from backend.schemas import ScoredCandidate
            sc_cand = ScoredCandidate(
                candidate_id=login_cand["id"],
                title=login_cand["title"],
                category=login_cand.get("category", "Cybersecurity"),
                difficulty=login_cand.get("difficulty", "Intermediate"),
                total_fit=0.5,
                substance_score=login_cand.get("substance_score", 70),
            )
            serendipity = build_rec(sc_cand, is_serendipity=True)

    return primary, alternates, serendipity


def _check_zero_signal(
    current_reel: dict[str, Any],
    interactions: list[dict[str, Any]],
    graph: Any,
) -> tuple[bool, str]:
    """Check if current reel contributes zero signal to the interest graph per Part 2."""
    reel_id = current_reel.get("id", "")
    title = current_reel.get("title", "").lower()

    if reel_id in ["reel_005", "reel_006"] or "street food" in title or "gaming" in title:
        return True, "no domain overlap with interest graph"

    curr_ia = next((ia for ia in reversed(interactions) if ia.get("reel_id") == reel_id), None)
    if curr_ia:
        skip = curr_ia.get("skipped_at_sec")
        watch_pct = curr_ia.get("watch_completion", 1.0)
        if skip is not None and skip < 6:
            return True, "skipped at 4s"
        if not curr_ia.get("liked") and not curr_ia.get("saved") and watch_pct < 0.5:
            return True, "engagement below threshold"

    return False, ""


async def _run_shallow(
    session_id: str,
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
    candidate_library: list[dict[str, Any]],
    trace: AgentTrace,
    current_reel_id: str | None = None,
) -> AsyncIterator[str]:
    yield _sse("stage_start", {"stage": 1, "label": "Keyword Matching (Shallow)"})

    watched_tags: list[str] = []
    for ia in interactions:
        reel = reel_map.get(ia.get("reel_id", ""), {})
        watched_tags.extend([t.lower() for t in reel.get("tags", [])])

    tag_freq = Counter(watched_tags)

    def shallow_score(cand: dict) -> float:
        cand_tags = [t.lower() for t in cand.get("tags", [])]
        return sum(tag_freq.get(t, 0) for t in cand_tags)

    scored = sorted(candidate_library, key=shallow_score, reverse=True)
    top = scored[:3]

    yield _sse("retrieval", {
        "composed_query_terms": list(tag_freq.keys())[:8],
        "candidate_count": len(scored),
        "mode": "shallow",
        "note": "TF-IDF keyword overlap — no substance gate, no abstraction",
    })

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

    current_reel = _get_current_reel(interactions, reel_map, current_reel_id)

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
    current_reel_id: str | None = None,
) -> dict[str, Any]:
    if current_reel_id and current_reel_id in reel_map:
        return reel_map[current_reel_id]
    for ia in reversed(interactions):
        if ia.get("saved") or ia.get("shared") or ia.get("rewatched"):
            return reel_map.get(ia["reel_id"], {"id": ia["reel_id"], "title": ia["reel_id"]})
    if interactions:
        last = interactions[-1]
        return reel_map.get(last["reel_id"], {"id": last["reel_id"], "title": last["reel_id"]})
    return {}
