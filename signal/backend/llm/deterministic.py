"""
Deterministic (offline) engine — full pipeline with no LLM.
Build and verify this path first. If wifi dies, we still win.
"""
from __future__ import annotations
import re
from typing import Any

from backend.schemas import (
    ReelDecomposition, InterestNode, InterestEdge, InterestGraph,
    SubstanceReport, SubstancePenalty, ScoredCandidate, Recommendation
)

# ──────────────────────────────────────────────────────────────────────────────
# Tag → concept mapping table
# ──────────────────────────────────────────────────────────────────────────────

TAG_TO_L1: dict[str, str] = {
    "java": "Java", "nullpointerexception": "NullPointerException",
    "leetcode": "LeetCode", "linked-list": "linked-list",
    "macbook": "MacBook", "laptop": "laptop", "m4": "M4",
    "coding-interview": "coding interview", "dsa": "DSA",
    "software-engineer": "software engineering", "bengaluru": "Bengaluru",
    "tech-career": "tech career", "motivation": "motivation",
    "grind": "grind hustle", "snapdragon": "Snapdragon",
    "gaming": "gaming", "street-food": "street food",
    "food": "food", "paneer": "paneer",
}

TAG_TO_L2: dict[str, str] = {
    "java": "backend_engineering", "nullpointerexception": "backend_engineering",
    "leetcode": "interview_technique", "linked-list": "dsa_fundamentals",
    "macbook": "dev_tooling", "laptop": "hardware_selection",
    "coding-interview": "interview_technique", "dsa": "dsa_fundamentals",
    "software-engineer": "swe_career", "tech-career": "swe_career",
    "debug": "debugging", "algorithm": "dsa_fundamentals",
    "system-design": "system_design", "backend": "backend_engineering",
    "security": "security", "cloud": "cloud_engineering",
    "motivation": None, "grind": None,  # no L2 — weak signal
    "gaming": None, "street-food": None, "food": None, "paneer": None,
    "snapdragon": "hardware_selection", "chip": "hardware_selection",
    "hardware": "hardware_selection", "m4": "hardware_selection",
}

L2_TO_L3: dict[str, str] = {
    "backend_engineering": "becoming_swe",
    "dsa_fundamentals": "becoming_swe",
    "interview_technique": "becoming_swe",
    "swe_career": "becoming_swe",
    "dev_tooling": "becoming_swe",
    "hardware_selection": "becoming_swe",
    "system_design": "becoming_swe",
    "debugging": "becoming_swe",
    "security": "becoming_swe",
    "cloud_engineering": "becoming_swe",
}

L2_LABELS: dict[str, str] = {
    "backend_engineering": "Backend Engineering",
    "dsa_fundamentals": "DSA & Algorithms",
    "interview_technique": "Interview Technique",
    "swe_career": "SWE Career Path",
    "dev_tooling": "Developer Tooling",
    "hardware_selection": "Hardware Selection",
    "system_design": "System Design",
    "debugging": "Debugging Practice",
    "security": "Security Fundamentals",
    "cloud_engineering": "Cloud Engineering",
}

L3_LABELS: dict[str, str] = {
    "becoming_swe": "Becoming a software engineer · placement anxiety",
}

INTENT_TO_L2: dict[str, list[str]] = {
    "identity_affirmation": ["backend_engineering", "swe_career"],
    "aspiration": ["swe_career"],
    "anxiety_relief": ["interview_technique", "dsa_fundamentals"],
    "comparison_shopping": ["hardware_selection", "dev_tooling"],
    "learning": ["backend_engineering", "dsa_fundamentals"],
    "entertainment": [],
}

# ──────────────────────────────────────────────────────────────────────────────
# Engagement weights (§3 Stage 2)
# ──────────────────────────────────────────────────────────────────────────────

ENGAGEMENT_WEIGHTS = {
    "watch_completion": 1.0,
    "rewatched": 1.5,
    "saved": 2.0,
    "shared": 1.8,
    "commented": 1.4,
    "liked": 0.6,
    "skipped_lt_3s": -1.2,
}


def compute_engagement_weight(eng: dict[str, Any]) -> float:
    w = eng.get("watch_completion", 0.0) * ENGAGEMENT_WEIGHTS["watch_completion"]
    if eng.get("rewatched"):
        w += ENGAGEMENT_WEIGHTS["rewatched"]
    if eng.get("saved"):
        w += ENGAGEMENT_WEIGHTS["saved"]
    if eng.get("shared"):
        w += ENGAGEMENT_WEIGHTS["shared"]
    if eng.get("commented"):
        w += ENGAGEMENT_WEIGHTS["commented"]
    if eng.get("liked"):
        w += ENGAGEMENT_WEIGHTS["liked"]
    skip = eng.get("skipped_at_sec")
    if skip is not None and skip < 3:
        w += ENGAGEMENT_WEIGHTS["skipped_lt_3s"]
    return max(w, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Deterministic Decomposition
# ──────────────────────────────────────────────────────────────────────────────

def decompose_reel(reel: dict[str, Any]) -> ReelDecomposition:
    tags = [t.lower() for t in reel.get("tags", [])]
    eng = reel.get("engagement", {})
    skip = eng.get("skipped_at_sec")

    # Determine intent from tags + engagement
    intent: str = "entertainment"
    if eng.get("saved"):
        intent = "aspiration"
    elif eng.get("shared"):
        intent = "anxiety_relief"
    elif eng.get("rewatched"):
        intent = "identity_affirmation"
    elif any(t in tags for t in ["interview", "coding-interview", "leetcode", "placement"]):
        intent = "anxiety_relief"
    elif any(t in tags for t in ["day-in-life", "career", "tech-career"]):
        intent = "aspiration"
    elif any(t in tags for t in ["laptop", "macbook", "hardware", "comparison"]):
        intent = "comparison_shopping"
    elif any(t in tags for t in ["motivation", "grind", "hustle"]):
        intent = "entertainment"  # weak signal

    # Surface topic
    title = reel.get("title", "")
    surface_topic = title[:60] if title else " ".join(tags[:3])

    # Latent concepts from tags
    latent_map = {
        "java": "programmer in-group identity",
        "nullpointerexception": "debugging frustration",
        "leetcode": "interview anxiety",
        "linked-list": "DSA stress",
        "macbook": "hardware comparison anxiety",
        "laptop": "developer tool selection",
        "coding-interview": "placement pressure",
        "dsa": "algorithm preparation",
        "software-engineer": "career aspiration",
        "bengaluru": "tech industry geography",
        "motivation": "extrinsic motivation seeking",
        "grind": "hustle culture consumption",
        "snapdragon": "hardware curiosity",
        "gaming": "recreational engagement",
        "street-food": "lifestyle content",
        "food": "lifestyle content",
    }
    latent = []
    for tag in tags:
        if tag in latent_map and latent_map[tag] not in latent:
            latent.append(latent_map[tag])
    if not latent:
        latent = ["general interest", "passive consumption"]
    latent = latent[:5]
    if len(latent) < 3:
        latent += ["contextual browsing"] * (3 - len(latent))

    # Domain signals
    l2_set = set()
    for tag in tags:
        l2 = TAG_TO_L2.get(tag)
        if l2:
            l2_set.add(L2_LABELS.get(l2, l2))

    domain_signals = list(l2_set) if l2_set else ["general media consumption"]

    # Sophistication
    sophistication: str = "beginner"
    if any(t in tags for t in ["internals", "advanced", "architecture", "distributed"]):
        sophistication = "advanced"
    elif any(t in tags for t in ["system-design", "concurrency", "async"]):
        sophistication = "intermediate"

    return ReelDecomposition(
        reel_id=reel["id"],
        surface_topic=surface_topic,
        latent_concepts=latent,
        domain_signals=domain_signals,
        intent_signal=intent,  # type: ignore[arg-type]
        affective_tone=_infer_tone(intent, tags),
        sophistication_level=sophistication,  # type: ignore[arg-type]
    )


def _infer_tone(intent: str, tags: list[str]) -> str:
    tone_map = {
        "identity_affirmation": "humorous, self-deprecating, in-group",
        "aspiration": "aspirational, investigative, slightly anxious",
        "anxiety_relief": "anxious, humorous, relatable",
        "comparison_shopping": "analytical, evaluative",
        "learning": "curious, engaged",
        "entertainment": "passive, neutral",
    }
    return tone_map.get(intent, "neutral")


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Deterministic Interest Graph
# ──────────────────────────────────────────────────────────────────────────────

def build_interest_graph(
    decompositions: list[ReelDecomposition],
    interactions: list[dict[str, Any]],
    reel_map: dict[str, dict[str, Any]],
) -> InterestGraph:
    # Index interactions by reel_id
    eng_map: dict[str, dict] = {}
    for ia in interactions:
        eng_map[ia["reel_id"]] = ia

    l1_nodes: dict[str, InterestNode] = {}
    l2_nodes: dict[str, InterestNode] = {}
    l3_nodes: dict[str, InterestNode] = {}
    edges: list[InterestEdge] = []
    shallow_blocked: list[str] = []

    for dec in decompositions:
        reel = reel_map.get(dec.reel_id, {})
        eng_data = eng_map.get(dec.reel_id, reel.get("engagement", {}))

        # Skip if this reel was abandoned early:
        # - explicit skip < 10s, OR
        # - watch_completion < 0.2 with a recorded skip_at_sec (early scroll-away)
        skip = eng_data.get("skipped_at_sec")
        watch_pct = eng_data.get("watch_completion", 0.0)
        if skip is not None and (skip < 10 or watch_pct < 0.2):
            continue  # negative evidence — no graph contribution

        eng_weight = compute_engagement_weight(eng_data)
        if eng_weight <= 0:
            continue

        tags = [t.lower() for t in reel.get("tags", [])]

        # Build L1 nodes
        for tag in tags:
            l1_label = TAG_TO_L1.get(tag, tag.title())
            l1_id = f"l1_{tag}"
            if l1_id not in l1_nodes:
                l1_nodes[l1_id] = InterestNode(
                    id=l1_id, label=l1_label, layer="L1",
                    convergence=0.0, supporting_reels=[], weight=0.0
                )
            node = l1_nodes[l1_id]
            node.weight += eng_weight
            if dec.reel_id not in node.supporting_reels:
                node.supporting_reels.append(dec.reel_id)

        # Build L2 nodes from tags + intent
        l2_from_intent = INTENT_TO_L2.get(dec.intent_signal, [])
        l2_from_tags = [TAG_TO_L2.get(t) for t in tags if TAG_TO_L2.get(t)]
        all_l2 = list(set(filter(None, l2_from_tags + l2_from_intent)))

        for l2_key in all_l2:
            l2_id = f"l2_{l2_key}"
            if l2_id not in l2_nodes:
                l2_nodes[l2_id] = InterestNode(
                    id=l2_id,
                    label=L2_LABELS.get(l2_key, l2_key),
                    layer="L2",
                    convergence=0.0,
                    supporting_reels=[],
                    weight=0.0,
                )
            node = l2_nodes[l2_id]
            node.weight += eng_weight
            if dec.reel_id not in node.supporting_reels:
                node.supporting_reels.append(dec.reel_id)

            # L1→L2 edges
            for tag in tags:
                if TAG_TO_L2.get(tag) == l2_key:
                    l1_id = f"l1_{tag}"
                    edge = InterestEdge(source=l1_id, target=l2_id, weight=eng_weight)
                    edges.append(edge)

        # Build L3 nodes
        l3_set = set()
        for l2_key in all_l2:
            l3 = L2_TO_L3.get(l2_key)
            if l3:
                l3_set.add(l3)

        for l3_key in l3_set:
            l3_id = f"l3_{l3_key}"
            if l3_id not in l3_nodes:
                l3_nodes[l3_id] = InterestNode(
                    id=l3_id,
                    label=L3_LABELS.get(l3_key, l3_key),
                    layer="L3",
                    convergence=0.0,
                    supporting_reels=[],
                    weight=0.0,
                )
            node = l3_nodes[l3_id]
            node.weight += eng_weight
            if dec.reel_id not in node.supporting_reels:
                node.supporting_reels.append(dec.reel_id)

            # L2→L3 edges
            for l2_key in all_l2:
                if L2_TO_L3.get(l2_key) == l3_key:
                    l2_id = f"l2_{l2_key}"
                    edge = InterestEdge(source=l2_id, target=l3_id, weight=eng_weight)
                    edges.append(edge)

    # Compute convergence
    # convergence(node) = distinct_reels × avg_engagement × (1 + 0.4 × distinct_L1_children)
    for l2_id, node in l2_nodes.items():
        distinct_reels = len(node.supporting_reels)
        avg_eng = node.weight / max(distinct_reels, 1)
        l1_children = sum(
            1 for e in edges if e.target == l2_id and e.source.startswith("l1_")
        )
        node.convergence = distinct_reels * avg_eng * (1 + 0.4 * l1_children)

    for l3_id, node in l3_nodes.items():
        distinct_reels = len(node.supporting_reels)
        avg_eng = node.weight / max(distinct_reels, 1)
        l1_children = sum(
            1 for e in edges if e.target == l3_id and e.source.startswith("l1_")
        )
        node.convergence = distinct_reels * avg_eng * (1 + 0.4 * l1_children)

    # Sort and pick top nodes
    sorted_l2 = sorted(l2_nodes.values(), key=lambda n: n.convergence, reverse=True)
    sorted_l3 = sorted(l3_nodes.values(), key=lambda n: n.convergence, reverse=True)
    top_l3 = sorted_l3[0] if sorted_l3 else None
    top_l2 = sorted_l2[:3]

    # Anti-trap: if L3 converges ≥ threshold, block L1 siblings → log
    CONVERGENCE_THRESHOLD = 3.0
    if top_l3 and top_l3.convergence >= CONVERGENCE_THRESHOLD:
        # Block all L1 tokens of the dominant reel from being recommended
        dominant_tags = []
        for reel_id in top_l3.supporting_reels[:1]:
            reel_data = reel_map.get(reel_id, {})
            dominant_tags = [t.lower() for t in reel_data.get("tags", [])]
        for tag in dominant_tags:
            blocked_msg = f"shallow_move_blocked:l1_{tag}"
            if blocked_msg not in shallow_blocked:
                shallow_blocked.append(blocked_msg)

    # Latent need inference
    latent_need = _infer_latent_need(decompositions, top_l3, top_l2)

    # Normalize convergence to 0–100 range for clean instrumentation display
    max_c = max((n.convergence for n in (list(l2_nodes.values()) + list(l3_nodes.values()))), default=1.0)
    if max_c > 0:
        for n in list(l2_nodes.values()) + list(l3_nodes.values()):
            n.convergence = round(min(100.0, (n.convergence / max_c) * 100), 1)

    all_nodes = (
        list(l1_nodes.values()) + list(l2_nodes.values()) + list(l3_nodes.values())
    )

    return InterestGraph(
        nodes=all_nodes,
        edges=edges,
        top_l3_node=top_l3,
        top_l2_nodes=top_l2,
        latent_need=latent_need,
        shallow_moves_blocked=shallow_blocked,
    )


def get_dominant_l1_token(graph: InterestGraph) -> str:
    """Return top L1 surface token from interest graph."""
    l1_nodes = [n for n in graph.nodes if n.layer == "L1"]
    if not l1_nodes:
        return ""
    sorted_l1 = sorted(l1_nodes, key=lambda n: n.weight, reverse=True)
    return sorted_l1[0].label.lower()


def pluralize(count: int, singular: str, plural: str) -> str:
    """Helper to format pluralized strings cleanly."""
    return f"{count} {singular if count == 1 else plural}"


def _infer_latent_need(
    decompositions: list[ReelDecomposition],
    top_l3: InterestNode | None,
    top_l2: list[InterestNode],
) -> str:
    intents = [d.intent_signal for d in decompositions]
    has_anxiety = "anxiety_relief" in intents
    has_aspiration = "aspiration" in intents
    has_identity = "identity_affirmation" in intents

    if has_anxiety and has_aspiration and has_identity:
        return (
            "The student is pre-placement, comparing themselves to others, "
            "and seeking confirmation they are on the right track. "
            "Latent need: concrete evidence of progress on fundamentals — "
            "not more syntax, not motivation, but visible skill formation."
        )
    elif has_anxiety:
        return (
            "The student is anxious about technical interviews. "
            "Latent need: structured, approachable skill-building with clear milestones."
        )
    elif has_aspiration:
        return (
            "The student is building a mental model of what SWE life looks like. "
            "Latent need: honest, grounded content about the actual work."
        )
    else:
        return "General tech curiosity — broad exploration phase."


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4 — Deterministic Substance Gate
# ──────────────────────────────────────────────────────────────────────────────

PENALTY_PATTERNS: list[tuple[str, str, int]] = [
    (
        r"will get you a job|land.*lpa|get placed|get hired|land.*offer",
        "outcome_promise",
        -35,
    ),
    (
        r"\d+\s*(ai\s+)?tools?\s+(that|to|for)|tools?\s+that\s+will",
        "tool_listicle",
        -30,
    ),
    (
        r"nobody tells? you|they don.?t want you to know|secret (they|nobody)",
        "manufactured_secrecy",
        -20,
    ),
    (
        r"10x your|(\d+x)\s+(your|the)\s+(salary|package|income)",
        "unfalsifiable_claim",
        -15,
    ),
    (
        r"in \d+ days.*(get placed|learn|master|become)|become.*(in \d+ days)",
        "outcome_promise",
        -35,
    ),
    (
        r"passive income|make money|earn.*month|blueprint.*rich",
        "outcome_promise",
        -35,
    ),
]


def score_substance(candidate: dict[str, Any]) -> SubstanceReport:
    """Pure deterministic substance scoring."""
    cand_id = candidate["id"]
    title = candidate.get("title", "")
    caption = candidate.get("caption", "")
    transcript = candidate.get("transcript_excerpt", "")
    full_text = f"{title} {caption} {transcript}".lower()

    # Use pre-authored score if available (from seed data)
    raw_score = candidate.get("substance_score", 50)
    if raw_score is None:
        raw_score = 50

    penalties: list[SubstancePenalty] = []
    total_penalty = 0

    for pattern, penalty_name, delta in PENALTY_PATTERNS:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            flagged = match.group(0)
            penalties.append(SubstancePenalty(
                name=penalty_name,
                score_delta=delta,
                triggered_by="regex",
                flagged_phrase=flagged[:80],
            ))
            total_penalty += delta

    final_score = max(raw_score + total_penalty, 0)
    passed = final_score >= 60

    rejection_reason: str | None = None
    if not passed and penalties:
        names = ", ".join(set(p.name for p in penalties))
        rejection_reason = names
    elif not passed:
        rejection_reason = f"low_substance_score ({final_score})"

    return SubstanceReport(
        candidate_id=cand_id,
        title=title,
        raw_score=raw_score,
        penalties=penalties,
        final_score=final_score,
        passed=passed,
        rejection_reason=rejection_reason,
        transcript_excerpt=transcript[:200],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Stage 5 — Deterministic Fit Ranking
# ──────────────────────────────────────────────────────────────────────────────

CATEGORY_TO_L2: dict[str, str] = {
    "Java": "backend_engineering",
    "DSA": "dsa_fundamentals",
    "HLD": "system_design",
    "Cybersecurity": "security",
    "Cloud": "cloud_engineering",
    "Hardware": "hardware_selection",
    "Career": "swe_career",
    "AI": "backend_engineering",
    "Other": "dev_tooling",
}


def rank_candidates(
    candidates: list[dict[str, Any]],
    graph: InterestGraph,
    watched_reel_ids: set[str],
    current_sophistication: str = "beginner",
) -> list[ScoredCandidate]:
    top_l2_labels = {n.label for n in graph.top_l2_nodes}
    top_l2_ids = {n.id for n in graph.top_l2_nodes}

    scored: list[ScoredCandidate] = []
    for cand in candidates:
        cat = cand.get("category", "Other")
        diff = cand.get("difficulty", "Beginner").lower()
        l2_key = CATEGORY_TO_L2.get(cat, "dev_tooling")
        l2_id = f"l2_{l2_key}"
        l2_label = L2_LABELS.get(l2_key, cat)

        # Interest alignment — is this L2 in the top nodes?
        interest_alignment = 1.0 if l2_id in top_l2_ids else 0.3
        if l2_label in top_l2_labels:
            interest_alignment = 1.0

        # Bridge fit — one step above current sophistication
        soph_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
        cur_soph = soph_order.get(current_sophistication, 0)
        cand_soph = soph_order.get(diff, 0)
        bridge_fit = 1.0 if cand_soph == cur_soph + 1 else (
            0.8 if cand_soph == cur_soph else 0.1
        )

        # Latent need match — career + fundamentals content
        latent_need_match = 0.5
        if cat in ("DSA", "Java", "Career", "HLD") and "placement" in graph.latent_need.lower():
            latent_need_match = 1.0
        elif cat in ("Career",):
            latent_need_match = 0.8

        # Novelty
        novelty = 0.2 if cand["id"] in watched_reel_ids else 1.0

        # Engagement potential (hook style scoring)
        hook = cand.get("hook_style", "")
        good_hooks = {"reframe_pain_point", "visual_build", "myth_bust", "mental_model_shift"}
        engagement_potential = 1.0 if hook in good_hooks else 0.6

        total = (
            0.30 * interest_alignment
            + 0.22 * bridge_fit
            + 0.18 * latent_need_match
            + 0.15 * novelty
            + 0.15 * engagement_potential
        )

        scored.append(ScoredCandidate(
            candidate_id=cand["id"],
            title=cand["title"],
            category=cat,
            difficulty=cand.get("difficulty", "Beginner"),
            interest_alignment=interest_alignment,
            bridge_fit=bridge_fit,
            latent_need_match=latent_need_match,
            novelty=novelty,
            engagement_potential=engagement_potential,
            total_fit=total,
            substance_score=cand.get("substance_score", 60),
        ))

    scored.sort(key=lambda s: s.total_fit, reverse=True)
    return scored


# ──────────────────────────────────────────────────────────────────────────────
# Stage 6 — Confidence Calibration
# ──────────────────────────────────────────────────────────────────────────────

def calibrate_confidence(
    graph: InterestGraph,
    decompositions: list[ReelDecomposition],
) -> tuple[str, str]:
    top_l3 = graph.top_l3_node
    if not top_l3:
        return "Low", "No L3 identity node reached — signal too weak or too broad."

    distinct = len(top_l3.supporting_reels)
    if distinct >= 3:
        return "High", f"{pluralize(distinct, 'distinct reel', 'distinct reels')} converge on '{top_l3.label}' with consistent cross-signal."
    elif distinct >= 2:
        return "Medium", f"{pluralize(distinct, 'converging signal', 'converging signals')} on '{top_l3.label}', mixed intent spread."
    else:
        return "Low", f"Only {distinct} signal — too few to be confident. Widening recommendation scope."


# ──────────────────────────────────────────────────────────────────────────────
# Stage 7 — Deterministic Explanation
# ──────────────────────────────────────────────────────────────────────────────

def generate_explanation(
    current_reel: dict[str, Any],
    graph: InterestGraph,
    rec_candidate: dict[str, Any],
    confidence: str,
    confidence_reason: str,
    reel_map: dict[str, dict[str, Any]],
    current_reel_no_signal: bool = False,
    no_signal_reason: str = "engagement below threshold",
) -> str:
    top_l3 = graph.top_l3_node
    top_l2 = graph.top_l2_nodes[0] if graph.top_l2_nodes else None

    l3_label = top_l3.label if top_l3 else "technical skill building"
    l2_label = top_l2.label if top_l2 else rec_candidate.get("category", "Tech")

    # Gather evidence reels
    evidence_reel_ids = top_l3.supporting_reels[:3] if top_l3 else []
    evidence_titles = []
    for rid in evidence_reel_ids:
        reel_data = reel_map.get(rid, {})
        if reel_data.get("title"):
            evidence_titles.append(f'"{reel_data["title"]}"')
    evidence_str = ", ".join(evidence_titles) if evidence_titles else "the watched session"
    count = len(evidence_reel_ids)
    signal_str = pluralize(count, "converging signal", "converging signals")

    if current_reel_no_signal:
        why_line = (
            f"Current reel contributed no signal — {no_signal_reason}. "
            f"Interest graph unchanged; recommendation continues from {pluralize(count, 'converging reel', 'converging reels')}."
        )
    else:
        why_line = f"Evidence from {evidence_str} with {signal_str} across identity affirmation, aspiration, and anxiety relief intents"

    # Bridge rationale
    hook_style = rec_candidate.get("hook_style", "")
    diff = rec_candidate.get("difficulty", "Beginner")
    bridge_note = (
        f"Shares the same emotional entry point as the watched content "
        f"(hook: {hook_style}) while delivering a transferable concept at "
        f"{diff} level — one step above current demonstrated sophistication."
    )

    curr_title = str(current_reel.get('title', current_reel.get('id', 'unknown'))).replace('\n', ' ').strip()
    block = (
        f"CURRENT REEL: {curr_title}\n"
        f"INTEREST DETECTED: {l3_label}, expressed as {l2_label}\n"
        f"WHY: {why_line}\n"
        f"RECOMMENDED TECH REEL: {rec_candidate.get('title', '')}\n"
        f"CATEGORY: {rec_candidate.get('category', 'Other')}\n"
        f"WHY THIS RECOMMENDATION: {bridge_note}\n"
        f"DIFFICULTY: {rec_candidate.get('difficulty', 'Beginner')}\n"
        f"CONFIDENCE: {confidence}"
    )
    return block
