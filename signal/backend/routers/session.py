from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from backend.db import get_db
from backend.models import Session as SessionModel, Interaction as InteractionModel
from backend.schemas import InteractionRequest

router = APIRouter()


@router.post("/start")
async def start_session(db: AsyncSession = Depends(get_db)):
    session_id = str(uuid.uuid4())
    session = SessionModel(id=session_id)
    db.add(session)
    await db.commit()
    return {"session_id": session_id}


@router.post("/interaction")
async def record_interaction(
    req: InteractionRequest,
    db: AsyncSession = Depends(get_db),
):
    # Verify or upsert session (Part 1.1)
    session = await db.get(SessionModel, req.session_id)
    if not session:
        session = SessionModel(id=req.session_id)
        db.add(session)
        await db.flush()

    interaction = InteractionModel(
        session_id=req.session_id,
        reel_id=req.reel_id,
        watch_completion=req.watch_completion,
        rewatched=req.rewatched,
        liked=req.liked,
        saved=req.saved,
        shared=req.shared,
        commented=req.commented,
        skipped_at_sec=req.skipped_at_sec,
    )
    db.add(interaction)
    await db.commit()
    return {"status": "recorded", "reel_id": req.reel_id}


@router.get("/interactions/{session_id}")
async def get_interactions(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InteractionModel).where(InteractionModel.session_id == session_id)
    )
    interactions = result.scalars().all()
    return [
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
