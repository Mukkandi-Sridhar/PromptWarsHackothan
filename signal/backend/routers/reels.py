from fastapi import APIRouter
from backend.seed import get_chroma_collection
import json
from pathlib import Path

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent / "data"
_seed_cache = None


def _load_seed_reels():
    global _seed_cache
    if _seed_cache is None:
        with open(DATA_DIR / "seed_reels.json") as f:
            _seed_cache = json.load(f)
    return _seed_cache


@router.get("/feed")
async def get_feed():
    """Return the 8 seed reels for the phone feed."""
    return _load_seed_reels()
