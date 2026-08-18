from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
import json
from pathlib import Path

from backend.db import AsyncSessionLocal
from backend.models import Interaction as InteractionModel
from backend.agent.orchestrator import run_agent
from backend.seed import get_chroma_collection

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent / "data"
_candidates_cache = None
_reels_cache = None


def _load_candidates():
    global _candidates_cache
    if _candidates_cache is None:
        with open(DATA_DIR / "candidate_library.json") as f:
            _candidates_cache = json.load(f)
    return _candidates_cache


def _load_reels():
    global _reels_cache
    if _reels_cache is None:
        with open(DATA_DIR / "seed_reels.json") as f:
            _reels_cache = json.load(f)
    return _reels_cache


def _build_reel_map():
    reels = _load_reels()
    return {r["id"]: r for r in reels}


@router.get("/stream")
async def recommend_stream(request: Request, session_id: str, mode: str = "agent", current_reel_id: str | None = None):
    async def generate():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InteractionModel).where(
                    InteractionModel.session_id == session_id
                ).order_by(InteractionModel.id)
            )
            db_interactions = result.scalars().all()

        interactions = [
            {
                "reel_id": i.reel_id,
                "watch_completion": i.watch_completion,
                "rewatched": i.rewatched,
                "liked": i.liked,
                "saved": i.saved,
                "shared": i.shared,
                "commented": i.commented,
                "skipped_at_sec": i.skipped_at_sec,
            }
            for i in db_interactions
        ]

        if not interactions:
            yield "event: error\ndata: {\"message\": \"No interactions recorded yet\"}\n\n"
            return

        reel_map = _build_reel_map()
        candidates = _load_candidates()
        chroma = get_chroma_collection()

        async for chunk in run_agent(
            session_id=session_id,
            interactions=interactions,
            reel_map=reel_map,
            candidate_library=candidates,
            chroma_collection=chroma,
            mode=mode,
            current_reel_id=current_reel_id,
        ):
            # Check if client disconnected
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/profile/{session_id}")
async def get_profile(session_id: str):
    """Return current interest graph for a session."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InteractionModel).where(
                InteractionModel.session_id == session_id
            )
        )
        interactions = result.scalars().all()

    ia_list = [
        {
            "reel_id": i.reel_id,
            "watch_completion": i.watch_completion,
            "rewatched": i.rewatched,
            "liked": i.liked,
            "saved": i.saved,
            "shared": i.shared,
            "commented": i.commented,
            "skipped_at_sec": i.skipped_at_sec,
        }
        for i in interactions
    ]

    reel_map = _build_reel_map()
    from backend.agent import s1_decompose, s2_interest_graph

    decompositions = []
    for ia in ia_list:
        reel = reel_map.get(ia["reel_id"], {})
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
        if reel:
            decompositions.append(s1_decompose.run(reel_with_eng))

    if not decompositions:
        return {"nodes": [], "edges": [], "latent_need": ""}

    graph = s2_interest_graph.run(decompositions, ia_list, reel_map)
    return {
        "nodes": [n.model_dump() for n in graph.nodes],
        "edges": [e.model_dump() for e in graph.edges],
        "latent_need": graph.latent_need,
        "top_l3": graph.top_l3_node.model_dump() if graph.top_l3_node else None,
    }
