"""
Seed the database and build the Chroma vector index.
Run once: python -m backend.seed
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path

import structlog

from backend.db import init_db, AsyncSessionLocal
from backend.models import Reel as ReelModel, Session as SessionModel

logger = structlog.get_logger()

DATA_DIR = Path(__file__).parent / "data"
CHROMA_PATH = DATA_DIR / "chroma"


def load_seed_reels() -> list[dict[str, Any]]:
    seed_path = DATA_DIR / "seed_reels.json"
    if seed_path.exists():
        with open(seed_path) as f:
            return json.load(f)
    return []


async def seed_db() -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        # Load seed reels
        seed_path = DATA_DIR / "seed_reels.json"
        with open(seed_path) as f:
            seed_reels = json.load(f)

        for reel in seed_reels:
            existing = await db.get(ReelModel, reel["id"])
            if existing:
                continue
            eng = reel.pop("engagement", {})
            db_reel = ReelModel(
                id=reel["id"],
                title=reel["title"],
                caption=reel["caption"],
                transcript_excerpt=reel["transcript_excerpt"],
                creator_handle=reel["creator_handle"],
                duration_sec=reel["duration_sec"],
                tags=reel.get("tags", []),
                thumbnail_gradient=reel.get("thumbnail_gradient", []),
                is_candidate=False,
            )
            db.add(db_reel)

        # Load candidate library
        cand_path = DATA_DIR / "candidate_library.json"
        with open(cand_path) as f:
            candidates = json.load(f)

        for cand in candidates:
            existing = await db.get(ReelModel, cand["id"])
            if existing:
                continue
            db_cand = ReelModel(
                id=cand["id"],
                title=cand["title"],
                caption=cand["caption"],
                transcript_excerpt=cand["transcript_excerpt"],
                creator_handle=cand["creator_handle"],
                duration_sec=cand["duration_sec"],
                tags=cand.get("tags", []),
                thumbnail_gradient=["#1a1a2e", "#16213e"],
                is_candidate=True,
                category=cand.get("category"),
                difficulty=cand.get("difficulty"),
                hook_style=cand.get("hook_style"),
                substance_score=cand.get("substance_score"),
            )
            db.add(db_cand)

        await db.commit()
        logger.info("db_seeded", seed_count=len(seed_reels), candidate_count=len(candidates))

    # Build Chroma index
    await build_chroma_index(candidates)


async def build_chroma_index(candidates: list[dict]) -> None:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        try:
            collection = client.get_collection("candidates")
            logger.info("chroma_collection_exists")
            return
        except Exception:
            pass

        collection = client.create_collection("candidates")
        model = SentenceTransformer("all-MiniLM-L6-v2")

        texts = []
        ids = []
        metadatas = []

        for cand in candidates:
            text = f"{cand['title']} {cand['caption']} {cand['transcript_excerpt']}"
            texts.append(text)
            ids.append(cand["id"])
            meta = {
                "id": cand["id"],
                "title": cand["title"],
                "category": cand.get("category", ""),
                "difficulty": cand.get("difficulty", ""),
                "creator_handle": cand.get("creator_handle", ""),
                "hook_style": cand.get("hook_style", ""),
                "substance_score": str(cand.get("substance_score", 50)),
            }
            metadatas.append(meta)

        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        collection.add(embeddings=embeddings, ids=ids, metadatas=metadatas)
        logger.info("chroma_indexed", count=len(ids))

    except ImportError as e:
        logger.warning("chroma_unavailable", reason=str(e))
    except Exception as e:
        logger.warning("chroma_index_failed", error=str(e))


def get_chroma_collection():
    """Return Chroma collection or None if unavailable."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        return client.get_collection("candidates")
    except Exception:
        return None


if __name__ == "__main__":
    asyncio.run(seed_db())
