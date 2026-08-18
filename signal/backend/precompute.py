"""
Precomputes reel decompositions and candidate substance scores at seed time.
Caches outputs in SQLite so runtime API calls are session-dependent only (~3-4s per reel advance).
"""
from __future__ import annotations
import asyncio
import json
import structlog
from typing import Any

from backend.config import get_config
from backend.db import AsyncSessionLocal
from backend.models import LLMCache
from backend.llm.client import call_structured_async
from backend.schemas import ReelDecomposition, SubstanceReport

logger = structlog.get_logger()


async def precompute_all(seed_reels: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> None:
    cfg = get_config()
    if not cfg.has_llm:
        logger.info("precompute_skipped", reason="LLM API key not present")
        return

    logger.info("precompute_starting", seed_count=len(seed_reels), candidate_count=len(candidates))

    sem = asyncio.Semaphore(8)

    async def _decom_one(reel: dict[str, Any]):
        async with sem:
            prompt = f"Decompose reel title: '{reel.get('title')}' caption: '{reel.get('caption')}' excerpt: '{reel.get('transcript_excerpt')}'"
            return await call_structured_async(prompt, ReelDecomposition)

    # Parallel decomposition of seed reels
    decom_tasks = [_decom_one(r) for r in seed_reels]
    results = await asyncio.gather(*decom_tasks, return_exceptions=True)
    logger.info("precompute_decompositions_done", success_count=sum(1 for r in results if isinstance(r, ReelDecomposition)))

    # Batch candidate substance scoring in groups of 10
    batch_size = 10
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        batch_prompt = "Score substance (0-100) for candidates: " + json.dumps([
            {"id": c["id"], "title": c["title"], "transcript": c.get("transcript_excerpt", "")}
            for c in batch
        ])
        await call_structured_async(batch_prompt, SubstanceReport)

    logger.info("precompute_complete")


if __name__ == "__main__":
    from backend.seed import SEED_REELS
    from backend.db import init_db
    import json
    from pathlib import Path

    async def main():
        await init_db()
        cands_path = Path(__file__).parent / "data" / "candidate_library.json"
        cands = json.loads(cands_path.read_text()) if cands_path.exists() else []
        await precompute_all(SEED_REELS, cands)

    asyncio.run(main())
