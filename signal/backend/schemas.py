from __future__ import annotations
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Reel & Interaction
# ──────────────────────────────────────────────

class ReelEngagement(BaseModel):
    watch_completion: float = 0.0
    rewatched: bool = False
    liked: bool = False
    saved: bool = False
    shared: bool = False
    commented: bool = False
    skipped_at_sec: Optional[float] = None


class Reel(BaseModel):
    id: str
    title: str
    caption: str
    transcript_excerpt: str
    creator_handle: str
    duration_sec: int
    tags: list[str] = []
    thumbnail_gradient: list[str] = []
    engagement: Optional[ReelEngagement] = None
    # Candidate-only fields
    category: Optional[str] = None
    difficulty: Optional[str] = None
    hook_style: Optional[str] = None
    substance_score: Optional[int] = None


class InteractionRequest(BaseModel):
    session_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    reel_id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    watch_completion: float = Field(ge=0.0, le=1.0)
    rewatched: bool = False
    liked: bool = False
    saved: bool = False
    shared: bool = False
    commented: bool = False
    skipped_at_sec: Optional[float] = None


# ──────────────────────────────────────────────
# Stage 1 — Semantic Decomposition
# ──────────────────────────────────────────────

class ReelDecomposition(BaseModel):
    reel_id: str
    surface_topic: str
    latent_concepts: list[str] = Field(min_length=3, max_length=5)
    domain_signals: list[str]
    intent_signal: Literal[
        "entertainment", "aspiration", "learning",
        "comparison_shopping", "identity_affirmation", "anxiety_relief"
    ]
    affective_tone: str
    sophistication_level: Literal["beginner", "intermediate", "advanced"]


# ──────────────────────────────────────────────
# Stage 2 — Interest Graph
# ──────────────────────────────────────────────

class InterestNode(BaseModel):
    id: str
    label: str
    layer: Literal["L1", "L2", "L3"]
    convergence: float = 0.0
    supporting_reels: list[str] = []
    weight: float = 0.0


class InterestEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0


class InterestGraph(BaseModel):
    nodes: list[InterestNode] = []
    edges: list[InterestEdge] = []
    top_l3_node: Optional[InterestNode] = None
    top_l2_nodes: list[InterestNode] = []
    latent_need: str = ""
    shallow_moves_blocked: list[Any] = []


# ──────────────────────────────────────────────
# Stage 4 — Substance Gate
# ──────────────────────────────────────────────

class SubstancePenalty(BaseModel):
    name: str
    score_delta: int
    triggered_by: Literal["regex", "llm", "both"]
    flagged_phrase: Optional[str] = None


class SubstanceReport(BaseModel):
    candidate_id: str
    title: str
    raw_score: int
    penalties: list[SubstancePenalty] = []
    final_score: int
    passed: bool
    rejection_reason: Optional[str] = None
    transcript_excerpt: Optional[str] = None


# ──────────────────────────────────────────────
# Stage 5 — Fit Ranking
# ──────────────────────────────────────────────

class ScoredCandidate(BaseModel):
    candidate_id: str
    title: str
    category: str
    difficulty: str
    interest_alignment: float = 0.0
    bridge_fit: float = 0.0
    latent_need_match: float = 0.0
    novelty: float = 0.0
    engagement_potential: float = 0.0
    total_fit: float = 0.0
    substance_score: int = 0


# ──────────────────────────────────────────────
# Stage 7 — Explanation & Recommendation
# ──────────────────────────────────────────────

class Recommendation(BaseModel):
    rec_id: str
    candidate_id: str
    title: str
    category: str
    difficulty: Literal["Beginner", "Intermediate", "Advanced"]
    confidence: Literal["High", "Medium", "Low"]
    interest_detected: str
    why_evidence: str
    why_recommendation: str
    formatted_block: str  # the 8-line verbatim output
    is_serendipity: bool = False
    serendipity_label: Optional[str] = None
    creator_handle: str = ""
    hook_style: str = ""
    substance_score: int = 0


# ──────────────────────────────────────────────
# Agent Trace
# ──────────────────────────────────────────────

class AgentTrace(BaseModel):
    session_id: str
    mode: Literal["agent", "shallow"]
    decompositions: list[ReelDecomposition] = []
    interest_graph: Optional[InterestGraph] = None
    composed_query_terms: list[str] = []
    candidate_count: int = 0
    substance_reports: list[SubstanceReport] = []
    passed_candidates: list[str] = []
    rejected_candidates: list[SubstanceReport] = []
    scored_candidates: list[ScoredCandidate] = []
    recommendation: Optional[Recommendation] = None
    alternates: list[Recommendation] = []
    serendipity: Optional[Recommendation] = None
    confidence: Literal["High", "Medium", "Low"] = "Medium"
    confidence_reason: str = ""
    llm_used: bool = False
    stages_log: list[dict[str, Any]] = []
    shallow_moves_blocked: list[Any] = []
