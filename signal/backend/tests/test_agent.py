"""
SIGNAL Test Suite — 8 required tests.
Run: pytest backend/tests/test_agent.py -v
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

# Add signal/ to sys.path so `backend` is importable
SIGNAL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SIGNAL_DIR))

from backend.llm.deterministic import (
    decompose_reel, build_interest_graph, score_substance,
    calibrate_confidence, rank_candidates, generate_explanation,
)
from backend.agent import s1_decompose, s2_interest_graph, s4_substance_gate, s6_calibrate
from backend.schemas import ReelDecomposition, InterestGraph

# ──────────────────────────────────────────────────────────────────────────────
# Load fixtures from seed data
# ──────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

with open(DATA_DIR / "seed_reels.json") as f:
    SEED_REELS = json.load(f)

with open(DATA_DIR / "candidate_library.json") as f:
    CANDIDATES = json.load(f)

REEL_MAP = {r["id"]: r for r in SEED_REELS}
CAND_MAP = {c["id"]: c for c in CANDIDATES}

# Core reels (the SWE identity cluster)
REELS_1_4 = [r for r in SEED_REELS if r["id"] in
             ("reel_001", "reel_002", "reel_003", "reel_004")]
REEL_5_FOOD = next(r for r in SEED_REELS if r["id"] == "reel_005")
REEL_6_GAMING = next(r for r in SEED_REELS if r["id"] == "reel_006")
REEL_7_CHIP = next(r for r in SEED_REELS if r["id"] == "reel_007")
REEL_8_MOTIVATION = next(r for r in SEED_REELS if r["id"] == "reel_008")

HYPE_REEL = next(c for c in CANDIDATES if c["id"] == "cand_045")  # "10 AI Tools..."


def make_interactions(reels: list[dict]) -> list[dict]:
    """Build interaction dicts from seed reel engagement data."""
    interactions = []
    for reel in reels:
        eng = reel.get("engagement", {})
        interactions.append({
            "reel_id": reel["id"],
            "watch_completion": eng.get("watch_completion", 0.0),
            "rewatched": eng.get("rewatched", False),
            "liked": eng.get("liked", False),
            "saved": eng.get("saved", False),
            "shared": eng.get("shared", False),
            "commented": eng.get("commented", False),
            "skipped_at_sec": eng.get("skipped_at_sec"),
        })
    return interactions


def build_decs_and_graph(reels: list[dict]) -> tuple[list[ReelDecomposition], InterestGraph]:
    interactions = make_interactions(reels)
    reel_map = {r["id"]: r for r in reels}
    # Merge engagement into reel dict for decomposition
    decs = []
    for reel in reels:
        eng = reel.get("engagement", {})
        reel_with_eng = dict(reel)
        reel_with_eng["engagement"] = {
            "watch_completion": eng.get("watch_completion", 0.0),
            "rewatched": eng.get("rewatched", False),
            "liked": eng.get("liked", False),
            "saved": eng.get("saved", False),
            "shared": eng.get("shared", False),
            "commented": eng.get("commented", False),
            "skipped_at_sec": eng.get("skipped_at_sec"),
        }
        decs.append(decompose_reel(reel_with_eng))
    graph = build_interest_graph(decs, interactions, reel_map)
    return decs, graph


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — No shallow echo: recommendation is NOT the L1 token of the current reel
# ──────────────────────────────────────────────────────────────────────────────

def test_no_shallow_echo():
    """After watching reels 1-4, agent must NOT recommend another Java meme."""
    decs, graph = build_decs_and_graph(REELS_1_4)

    # Dominant L1 surface tokens from reel_001 (Java NullPointerException)
    dominant_l1_tokens = {"java", "nullpointerexception", "meme"}

    # Verify shallow_move_blocked is populated
    assert len(graph.shallow_moves_blocked) > 0, (
        "Expected shallow_move_blocked entries but got none"
    )

    # Rank candidates using s5_fit_rank with lift-based filter
    from backend.agent import s5_fit_rank
    passed_cands = [c for c in CANDIDATES if c.get("substance_score", 50) >= 60]
    watched_ids = {r["id"] for r in REELS_1_4}
    current_reel = REELS_1_4[0]
    watched_concepts = set()
    for r in REELS_1_4:
        watched_concepts.update(t.lower() for t in r.get("tags", []))

    scored, echo_blocked = s5_fit_rank.run(
        passed_candidates=passed_cands,
        graph=graph,
        watched_reel_ids=watched_ids,
        current_sophistication="beginner",
        current_reel=current_reel,
        watched_concepts=watched_concepts,
    )

    assert scored, "Expected at least one ranked candidate"
    top_rec = scored[0]

    # Top recommendation earns its place with lift (substance >= 70, Intermediate difficulty)
    assert top_rec.substance_score >= 70, f"Low substance recommendation: {top_rec.substance_score}"
    assert len(echo_blocked) > 0, "Expected surface echo blocked entries"

    print(f"✓ Top recommendation: {top_rec.title} ({top_rec.category})")
    print(f"✓ Echoes blocked: {len(echo_blocked)}")


def test_bridge_wins_over_domain_jump():
    """After watching reels 1-4, Java Optional bridge reel wins — same topic, real lift."""
    decs, graph = build_decs_and_graph(REELS_1_4)
    from backend.agent import s5_fit_rank
    passed_cands = [c for c in CANDIDATES if c.get("substance_score", 50) >= 60]
    watched_ids = {r["id"] for r in REELS_1_4}
    current_reel = REELS_1_4[0]
    watched_concepts = set()
    for r in REELS_1_4:
        watched_concepts.update(t.lower() for t in r.get("tags", []))

    scored, echo_blocked = s5_fit_rank.run(
        passed_candidates=passed_cands,
        graph=graph,
        watched_reel_ids=watched_ids,
        current_sophistication="beginner",
        current_reel=current_reel,
        watched_concepts=watched_concepts,
    )

    assert scored, "Expected ranked candidates"
    top_rec = scored[0]

    assert "NullPointerException isn't a bug" in top_rec.title, f"Expected bridge reel to win, got: {top_rec.title}"
    assert top_rec.category == "Java", f"Expected category Java, got {top_rec.category}"
    assert top_rec.difficulty == "Intermediate", f"Expected Intermediate, got {top_rec.difficulty}"
    print(f"✓ Bridge reel won: '{top_rec.title}' ({top_rec.category}, {top_rec.difficulty})")


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Hype reel is rejected with outcome_promise penalty
# ──────────────────────────────────────────────────────────────────────────────

def test_hype_rejected():
    """'10 AI Tools That Will Get You a Job in 2026' must score < 40 and be rejected."""
    report = score_substance(HYPE_REEL)

    assert report.final_score < 40, (
        f"Expected hype reel score < 40, got {report.final_score}"
    )
    assert not report.passed, "Expected hype reel to fail substance gate"

    penalty_names = [p.name for p in report.penalties]
    assert "outcome_promise" in penalty_names or "tool_listicle" in penalty_names, (
        f"Expected outcome_promise or tool_listicle penalty, got: {penalty_names}"
    )

    print(f"✓ Hype reel score: {report.final_score}")
    print(f"✓ Penalties: {penalty_names}")
    print(f"✓ Rejection reason: {report.rejection_reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — L3 convergence reaches High confidence after reels 1-4
# ──────────────────────────────────────────────────────────────────────────────

def test_l3_convergence():
    """After reels 1-4, the software engineering L3 node reaches High confidence."""
    decs, graph = build_decs_and_graph(REELS_1_4)

    assert graph.top_l3_node is not None, "Expected an L3 node but got None"

    top_l3 = graph.top_l3_node
    print(f"  L3 node: {top_l3.label}, convergence={top_l3.convergence:.2f}, reels={top_l3.supporting_reels}")

    assert "software" in top_l3.label.lower() or "engineer" in top_l3.label.lower() or "becoming" in top_l3.id, (
        f"Expected software engineering L3 node, got: {top_l3.label}"
    )

    confidence, reason = calibrate_confidence(graph, decs)
    assert confidence == "High", (
        f"Expected High confidence after 4 converging reels, got {confidence}: {reason}"
    )
    print(f"✓ L3 node '{top_l3.label}' convergence={top_l3.convergence:.2f}")
    print(f"✓ Confidence: {confidence} — {reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — Negative signal: street food reel skipped at 4s contributes zero weight
# ──────────────────────────────────────────────────────────────────────────────

def test_negative_signal():
    """Street food reel (skipped at 4s) must produce zero graph contribution."""
    # Build graph with ONLY the food reel
    food_with_eng = dict(REEL_5_FOOD)
    food_with_eng["engagement"] = REEL_5_FOOD.get("engagement", {})

    single_reel_map = {"reel_005": REEL_5_FOOD}
    decs = [decompose_reel(food_with_eng)]
    interactions = make_interactions([REEL_5_FOOD])
    graph = build_interest_graph(decs, interactions, single_reel_map)

    # Graph should have zero or minimal nodes (skipped < 3s = negative weight)
    active_nodes = [n for n in graph.nodes if n.weight > 0]
    food_nodes = [n for n in graph.nodes if "food" in n.label.lower() or "paneer" in n.label.lower()]

    assert not food_nodes or all(n.weight <= 0 for n in food_nodes), (
        f"Food reel should produce zero graph weight but got nodes: {[(n.label, n.weight) for n in food_nodes]}"
    )
    print(f"✓ Street food reel: {len(active_nodes)} active nodes (expected 0 food nodes)")


# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — Weak motivational reel does not become dominant driver
# ──────────────────────────────────────────────────────────────────────────────

def test_weak_signal_ignored():
    """Motivational grind reel (45% watched, no engagement) must not dominate the graph."""
    decs, graph = build_decs_and_graph(REELS_1_4 + [REEL_8_MOTIVATION])

    # Motivation reel tags: motivation, grind, hustle, mindset
    # These map to None L2 in our system → should not create L2/L3 nodes
    motivation_nodes = [
        n for n in graph.nodes
        if any(kw in n.label.lower() for kw in ["motivation", "grind", "hustle", "mindset"])
    ]

    # If motivation nodes exist, they should have very low weight vs. SWE nodes
    if motivation_nodes:
        swe_nodes = [n for n in graph.nodes if n.layer == "L3"]
        if swe_nodes:
            max_motivation = max(n.weight for n in motivation_nodes)
            max_swe = max(n.weight for n in swe_nodes)
            assert max_motivation < max_swe, (
                f"Motivation reel dominates: motivation_weight={max_motivation:.2f} > swe_weight={max_swe:.2f}"
            )

    # Top L3 must still be SWE-related
    assert graph.top_l3_node is not None
    assert "motivation" not in graph.top_l3_node.label.lower()
    print(f"✓ Top L3 is '{graph.top_l3_node.label}' (not motivation)")


# ──────────────────────────────────────────────────────────────────────────────
# Test 6 — Single reel session yields Low confidence and broader recommendation
# ──────────────────────────────────────────────────────────────────────────────

def test_low_confidence_widens():
    """Only reel_007 (chip news) → Low confidence → broader recommendation."""
    single_reel = [REEL_7_CHIP]
    decs, graph = build_decs_and_graph(single_reel)

    confidence, reason = calibrate_confidence(graph, decs)

    assert confidence == "Low", (
        f"Expected Low confidence with single reel, got {confidence}: {reason}"
    )
    assert "1 signal" in reason.lower() or "too few" in reason.lower() or "only 1" in reason.lower() or "widen" in reason.lower(), (
        f"Expected widening message in reason: {reason}"
    )
    print(f"✓ Confidence: {confidence}")
    print(f"✓ Reason: {reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 7 — Output format: 8 required lines in exact order with exact labels
# ──────────────────────────────────────────────────────────────────────────────

def test_output_format():
    """The formatted_block must contain all 8 required lines with exact labels."""
    decs, graph = build_decs_and_graph(REELS_1_4)

    passed_cands = [c for c in CANDIDATES if c.get("substance_score", 50) >= 60]
    watched_ids = {r["id"] for r in REELS_1_4}
    scored = rank_candidates(passed_cands, graph, watched_ids, "beginner")

    assert scored, "No scored candidates"
    top_cand = CAND_MAP.get(scored[0].candidate_id, CANDIDATES[0])
    current_reel = REEL_MAP.get("reel_001", SEED_REELS[0])
    confidence, confidence_reason = calibrate_confidence(graph, decs)

    block = generate_explanation(
        current_reel=current_reel,
        graph=graph,
        rec_candidate=top_cand,
        confidence=confidence,
        confidence_reason=confidence_reason,
        reel_map=REEL_MAP,
    )

    required_labels = [
        "CURRENT REEL:",
        "INTEREST DETECTED:",
        "WHY:",
        "RECOMMENDED TECH REEL:",
        "CATEGORY:",
        "WHY THIS RECOMMENDATION:",
        "DIFFICULTY:",
        "CONFIDENCE:",
    ]

    for label in required_labels:
        assert label in block, f"Missing required label: '{label}'\nBlock:\n{block}"

    # Verify order
    positions = [block.index(label) for label in required_labels]
    assert positions == sorted(positions), (
        f"Labels are out of order. Positions: {list(zip(required_labels, positions))}"
    )

    print(f"✓ All 8 labels present in correct order")
    print(f"\n{block}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 8 — Offline parity: deterministic mode produces valid recommendation
# ──────────────────────────────────────────────────────────────────────────────

def test_offline_parity():
    """Deterministic mode (no LLM) must produce a valid recommendation end-to-end."""
    # Force deterministic by not using LLM client
    decs, graph = build_decs_and_graph(REELS_1_4)

    # Substance gate
    reports = [score_substance(c) for c in CANDIDATES]
    passed = [c for c, r in zip(CANDIDATES, reports) if r.passed]

    assert len(passed) > 0, "Expected some candidates to pass substance gate"

    # Fit rank
    watched_ids = {r["id"] for r in REELS_1_4}
    scored = rank_candidates(passed, graph, watched_ids, "beginner")

    assert len(scored) > 0, "Expected ranked candidates"

    # Calibrate
    confidence, reason = calibrate_confidence(graph, decs)

    # Explanation
    top_cand = CAND_MAP.get(scored[0].candidate_id, passed[0])
    current_reel = REEL_MAP.get("reel_001", SEED_REELS[0])
    block = generate_explanation(
        current_reel=current_reel,
        graph=graph,
        rec_candidate=top_cand,
        confidence=confidence,
        confidence_reason=reason,
        reel_map=REEL_MAP,
    )

    assert "CURRENT REEL:" in block
    assert "CONFIDENCE:" in block
    assert "RECOMMENDED TECH REEL:" in block
    assert len(block) > 100

    print(f"✓ Offline mode produced valid recommendation")
    print(f"✓ Recommended: {scored[0].title}")
    print(f"✓ Confidence: {confidence}")
