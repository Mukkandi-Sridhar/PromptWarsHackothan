"""
Unified LLM client — provider-agnostic, Pydantic validated, cached, with retry and explicit fallback diagnostics.
"""
from __future__ import annotations
import hashlib
import json
import asyncio
from typing import Any, Type, TypeVar, Literal

import structlog
from pydantic import BaseModel

from backend.config import get_config

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)

_cache: dict[str, str] = {}


class LLMResult(BaseModel):
    value: Any
    source: Literal["openai", "deterministic"]
    fallback_reason: str | None = None


def _content_hash(prompt: str, schema_name: str) -> str:
    payload = f"{schema_name}::{prompt}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _prepare_json_schema(schema: Type[BaseModel]) -> dict[str, Any]:
    s = schema.model_json_schema()
    def _add_no_extra(d: Any):
        if isinstance(d, dict):
            if d.get("type") == "object" or "properties" in d:
                d["additionalProperties"] = False
            for v in d.values():
                _add_no_extra(v)
        elif isinstance(d, list):
            for item in d:
                _add_no_extra(item)
    _add_no_extra(s)
    return s


async def probe_openai() -> tuple[bool, str]:
    cfg = get_config()
    if not cfg.OPENAI_API_KEY:
        return False, "no api key in environment"
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
        await client.models.list()
        return True, "openai reachable"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def call_structured_async(
    prompt: str,
    schema: Type[T],
    system: str = "",
    temperature: float = 0.2,
    use_strong_model: bool = False,
) -> LLMResult:
    """Async structured output call with strict mode and explicit error diagnostics."""
    cfg = get_config()
    if not cfg.OPENAI_API_KEY:
        return LLMResult(value=None, source="deterministic", fallback_reason="no api key in environment")

    model_name = cfg.OPENAI_MODEL_STRONG if use_strong_model else cfg.OPENAI_MODEL
    cache_key = _content_hash(f"{model_name}::{system}::{prompt}", schema.__name__)

    if cache_key in _cache:
        try:
            val = schema.model_validate_json(_cache[cache_key])
            return LLMResult(value=val, source="openai")
        except Exception:
            pass

    fallback_reason: str | None = None

    try:
        from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APITimeoutError
        from pydantic import ValidationError

        client = AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": _prepare_json_schema(schema),
                },
            },
            timeout=20,
        )
        content = resp.choices[0].message.content
        if content:
            validated = schema.model_validate_json(content)
            _cache[cache_key] = validated.model_dump_json()
            return LLMResult(value=validated, source="openai")
    except AuthenticationError as e:
        fallback_reason = f"openai auth failed: {getattr(e, 'status_code', 401)}"
    except RateLimitError:
        fallback_reason = "openai rate limit"
    except APITimeoutError:
        fallback_reason = "openai timeout after 20s"
    except ValidationError as e:
        fallback_reason = f"schema validation failed: {e.errors()[0]['loc'] if e.errors() else 'validation error'}"
    except Exception as e:
        fallback_reason = f"{type(e).__name__}: {e}"

    logger.warning("llm_fallback", reason=fallback_reason, stage=schema.__name__)
    return LLMResult(value=None, source="deterministic", fallback_reason=fallback_reason)


def call_structured(
    prompt: str,
    schema: Type[T],
    system: str = "",
    temperature: float = 0.2,
    use_strong_model: bool = False,
) -> T | None:
    """Sync helper returning validated model or None on fallback using json_schema strict mode."""
    cfg = get_config()
    if not cfg.has_llm:
        return None

    cache_key = _content_hash(f"{system}::{prompt}", schema.__name__)
    if cache_key in _cache:
        try:
            return schema.model_validate_json(_cache[cache_key])
        except Exception:
            pass

    try:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.OPENAI_API_KEY)
        model_name = cfg.OPENAI_MODEL_STRONG if use_strong_model else cfg.OPENAI_MODEL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=2048,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": _prepare_json_schema(schema),
                },
            },
        )
        content = resp.choices[0].message.content
        if content:
            model = schema.model_validate_json(content)
            _cache[cache_key] = model.model_dump_json()
            return model
    except Exception as e:
        logger.warning("openai_sync_failed", error=str(e))
        return None

    return None
