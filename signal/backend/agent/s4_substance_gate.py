"""Stage 4 — Substance Gate"""
from __future__ import annotations
from typing import Any

from backend.schemas import SubstanceReport
from backend.llm.deterministic import score_substance as det_score
from backend.config import get_config


def run(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[SubstanceReport]]:
    """
    Returns (passed_candidates, all_reports).
    Rejected candidates appear in reports with passed=False.
    """
    passed: list[dict[str, Any]] = []
    reports: list[SubstanceReport] = []

    for cand in candidates:
        report = det_score(cand)
        reports.append(report)
        if report.passed:
            passed.append(cand)

    return passed, reports
