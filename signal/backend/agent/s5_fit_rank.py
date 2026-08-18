"""Stage 5 — Fit Ranking with Distinctive Echo Filtering & Distance Ceiling"""
from __future__ import annotations
from typing import Any

import structlog
from backend.schemas import InterestGraph, ScoredCandidate
from backend.llm.deterministic import rank_candidates, get_dominant_l1_token, CATEGORY_TO_L2

logger = structlog.get_logger()

GENERIC_STOPLIST = {
    "software-engineer", "software engineer", "software engineering",
    "tech-career", "tech career", "day-in-life", "day in life",
    "work-culture", "work culture", "programming", "coding", "developer", "career",
    "techjobs", "tech-jobs", "swe", "swife", "bengaluru"
}


def is_distinctive_token(token: str, candidate_library: list[dict[str, Any]] | None = None) -> bool:
    """A token qualifies as echo-triggering only if it is rare across the candidate library (DF < 0.20)."""
    if not token or token.lower() in GENERIC_STOPLIST:
        return False
    if candidate_library:
        total = max(len(candidate_library), 1)
        matches = sum(
            1 for c in candidate_library
            if token.lower() in f"{c.get('title','')} {c.get('caption','')} {' '.join(c.get('tags',[]))}".lower()
        )
        df = matches / total
        return df < 0.20
    return True


def run(
    passed_candidates: list[dict[str, Any]],
    graph: InterestGraph,
    watched_reel_ids: set[str],
    current_sophistication: str = "beginner",
    current_reel: dict[str, Any] | None = None,
    watched_concepts: set[str] | None = None,
) -> tuple[list[ScoredCandidate], list[dict[str, str]]]:
    """
    Evaluates S4-survived candidates against distinctive lift-based echo filter and distance ceiling.
    Returns (scored_candidates, shallow_moves_blocked).
    """
    if current_reel is None:
        current_reel = {}
    if watched_concepts is None:
        watched_concepts = set()

    dominant_l1 = get_dominant_l1_token(graph)
    is_distinctive = is_distinctive_token(dominant_l1, passed_candidates)

    soph_map = {"beginner": 0, "intermediate": 1, "advanced": 2}
    current_soph_rank = soph_map.get(current_sophistication.lower(), 0)

    # Active L2 keys present in graph
    active_l2_keys = {n.id.replace("l2_", "") for n in graph.nodes if n.layer == "L2" and n.weight > 0}

    blocked_echoes: list[dict[str, str]] = []
    candidates_filtered: list[dict[str, Any]] = []

    for cand in passed_candidates:
        title = cand.get("title", "")
        cand_text = f"{title} {cand.get('caption', '')} {' '.join(cand.get('tags', []))}".lower()
        cand_cat = cand.get("category", "")
        cand_diff_rank = soph_map.get(cand.get("difficulty", "Beginner").lower(), 0)
        cand_substance = cand.get("substance_score", 50)

        # 1. Lift-based echo evaluation on DISTINCTIVE tokens only (Part 3.2)
        is_echo = False
        echo_reason: str | None = None

        if is_distinctive and dominant_l1 and dominant_l1 in cand_text:
            if cand_substance < 70:
                is_echo = True
                echo_reason = f"same surface topic '{dominant_l1}' · no transferable concept"
            elif cand_diff_rank <= current_soph_rank:
                is_echo = True
                echo_reason = f"same surface topic '{dominant_l1}' · no step up in difficulty"
            else:
                # Concept overlap Jaccard
                cand_concepts = set(t.lower() for t in cand.get("tags", []))
                if watched_concepts and cand_concepts:
                    inter = cand_concepts.intersection(watched_concepts)
                    union = cand_concepts.union(watched_concepts)
                    overlap = len(inter) / len(union) if union else 0.0
                    if overlap > 0.60:
                        is_echo = True
                        echo_reason = f"same surface topic '{dominant_l1}' · {int(overlap * 100)}% concept overlap"

        if is_echo and echo_reason:
            blocked_echoes.append({
                "candidate": title,
                "reason": echo_reason,
            })
            continue

        # 2. Distance Ceiling evaluation (Part 1.4)
        cand_l2_key = CATEGORY_TO_L2.get(cand_cat, "dev_tooling")
        has_l2_overlap = bool(active_l2_keys and cand_l2_key in active_l2_keys)
        if active_l2_keys and not has_l2_overlap:
            blocked_echoes.append({
                "candidate": title,
                "reason": "no L2 overlap with interest graph",
            })
            continue

        candidates_filtered.append(cand)

    if not candidates_filtered:
        candidates_filtered = [c for c in passed_candidates if c.get("substance_score", 50) >= 70]
        if not candidates_filtered:
            candidates_filtered = passed_candidates

    scored = rank_candidates(candidates_filtered, graph, watched_reel_ids, current_sophistication)

    # Dev assertion per Part 1.2
    if scored:
        top_cand = next((c for c in passed_candidates if c["id"] == scored[0].candidate_id), {})
        top_substance = top_cand.get("substance_score", 0)
        curr_cat = current_reel.get("category", "")
        if curr_cat and top_cand.get("category") == curr_cat and top_substance < 70:
            raise ValueError(f"shallow echo escaped the filter: '{top_cand.get('title')}' has score {top_substance} < 70")

    return scored, blocked_echoes
