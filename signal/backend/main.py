import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog

from backend.db import init_db
from backend.seed import seed_db
from backend.routers import reels, session, recommend
from backend.llm.client import probe_openai
from backend.config import get_config

logger = structlog.get_logger()

app = FastAPI(
    title="SIGNAL API",
    description="Reel Intelligence Agent — reads what students scroll and redirects it.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_backend_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"},
    )


app.include_router(reels.router, prefix="/api/reels", tags=["reels"])
app.include_router(session.router, prefix="/api/session", tags=["session"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["recommend"])


@app.on_event("startup")
async def startup():
    cfg = get_config()
    logger.info("signal_starting", key_prefix=repr(cfg.OPENAI_API_KEY)[:14], provider=cfg.LLM_PROVIDER)
    await seed_db()

    ok, detail = await probe_openai()
    logger.info("llm_probe", ok=ok, detail=detail)

    logger.info("signal_ready")


@app.get("/health")
async def health():
    cfg = get_config()
    ok, detail = await probe_openai()
    return {
        "status": "ok",
        "llm_provider": cfg.LLM_PROVIDER,
        "llm_available": ok,
        "detail": detail,
        "mode": "gpt" if ok else f"offline · {detail}",
    }

# Single-Service Static Mount for Render & Production Deployments
DIST_PATHS = [
    Path(__file__).parent.parent / "frontend" / "dist",
    Path(__file__).parent / "static",
]
for dist_path in DIST_PATHS:
    if dist_path.exists() and dist_path.is_dir():
        logger.info("mounting_static_frontend", path=str(dist_path))
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static_frontend")
        break
