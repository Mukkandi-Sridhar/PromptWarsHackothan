from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class Reel(Base):
    __tablename__ = "reels"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    caption: Mapped[str] = mapped_column(Text)
    transcript_excerpt: Mapped[str] = mapped_column(Text)
    creator_handle: Mapped[str] = mapped_column(String)
    duration_sec: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    thumbnail_gradient: Mapped[list] = mapped_column(JSON, default=list)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    hook_style: Mapped[str | None] = mapped_column(String, nullable=True)
    substance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    interest_graph: Mapped[dict] = mapped_column(JSON, default=dict)


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    reel_id: Mapped[str] = mapped_column(String)
    watch_completion: Mapped[float] = mapped_column(Float, default=0.0)
    rewatched: Mapped[bool] = mapped_column(Boolean, default=False)
    liked: Mapped[bool] = mapped_column(Boolean, default=False)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    commented: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped_at_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LLMCache(Base):
    __tablename__ = "llm_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String, index=True, unique=True)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecommendationRecord(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    mode: Mapped[str] = mapped_column(String)
    trace: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
