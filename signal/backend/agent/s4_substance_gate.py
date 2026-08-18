"""Stage 4 — Substance Gate with Live OpenAI Scoring & Deterministic Fallback"""
from __future__ import annotations
import json
from typing import Any
from pydantic import BaseModel

from backend.schemas import SubstanceReport
from backend.llm.deterministic import score_substance as det_score
from backend.llm.client import call_structured
from backend.config import get_config


class SubstanceItem(BaseModel):
    candidate_id: str
    final_score: int
    passed: bool
    rejection_reason: str | None = None


class SubstanceBatchReport(BaseModel):
    items: list[SubstanceItem]


def run(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[SubstanceReport]]:
    """
    Returns (passed_candidates, all_reports).
    Evaluates candidate rhetoric quality using OpenAI when available, falling back to deterministic scoring.
    """
    cfg = get_config()
    passed: list[dict[str, Any]] = []
    reports: list[SubstanceReport] = []

    llm_scores: dict[str, SubstanceItem] = {}

    if cfg.has_llm and candidates:
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            prompt = (
                "Score rhetoric substance (0-100) for tech reel candidates. Penalize outcome promises without mechanism, "
                "tool listicles without problem statements, and memes with zero concept depth:\n"
                + json.dumps([{"candidate_id": c["id"], "title": c["title"], "caption": c.get("caption", ""), "tags": c.get("tags", [])} for c in batch])
            )
            res = call_structured(
                prompt=prompt,
                schema=SubstanceBatchReport,
                system="You are an expert technical editor evaluating educational video substance.",
                temperature=0.2,
            )
            if res and res.items:
                for item in res.items:
                    llm_scores[item.candidate_id] = item

    for cand in candidates:
        cand_id = cand["id"]
        report = det_score(cand)

        # Enforce LLM score if returned from OpenAI
        if cand_id in llm_scores:
            llm_item = llm_scores[cand_id]
            report.final_score = llm_item.final_score
            report.passed = llm_item.passed
            if not llm_item.passed and llm_item.rejection_reason:
                report.rejection_reason = llm_item.rejection_reason

        reports.append(report)
        if report.passed:
            passed.append(cand)

    return passed, reports
