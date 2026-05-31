"""Shared Gemini helpers: retries, JSON parsing, and structured generation."""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import threading
import time
from typing import Any, Type

from google import genai
from google.genai import types
from pydantic import BaseModel

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DEFAULT_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
DEFAULT_BASE_DELAY = float(os.getenv("GEMINI_RETRY_BASE_DELAY", "3.0"))
_LLM_SEMAPHORE = threading.Semaphore(int(os.getenv("GEMINI_MAX_CONCURRENT", "3")))


def is_retryable_gemini_error(error: Exception) -> bool:
    error_text = str(error).lower()
    retryable_signatures = (
        "503",
        "unavailable",
        "temporarily",
        "high demand",
        "internal",
        "connection",
        "timeout",
        "rate limit",
        "quota",
        "429",
        "exhausted",
        "resource_exhausted",
    )
    return any(signature in error_text for signature in retryable_signatures)


def extract_json_from_text(text: str | None) -> dict[str, Any] | None:
    """Parse a JSON object from raw model text, including fenced blocks."""
    if not text or not text.strip():
        return None

    candidate = text.strip()

    if candidate.startswith("```"):
        parts = candidate.split("```")
        if len(parts) >= 2:
            candidate = parts[1]
            if candidate.startswith("json"):
                candidate = candidate[4:]
        candidate = candidate.strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^{}]*\}", candidate, re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")
    return genai.Client(api_key=api_key)


def generate_json_sync(
    prompt: str,
    response_schema: Type[BaseModel],
    *,
    label: str = "GEMINI",
    model: str | None = None,
    temperature: float = 0.3,
    max_retries: int | None = None,
    base_delay: float | None = None,
) -> dict[str, Any] | None:
    """Call Gemini with structured JSON output and exponential backoff."""
    max_retries = DEFAULT_MAX_RETRIES if max_retries is None else max_retries
    base_delay = DEFAULT_BASE_DELAY if base_delay is None else base_delay
    model = model or DEFAULT_MODEL

    client = _get_client()

    for attempt in range(max_retries):
        try:
            with _LLM_SEMAPHORE:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )

            parsed = extract_json_from_text(getattr(response, "text", None))
            if parsed is not None:
                return parsed

            print(
                f"[{label}] Empty or unparseable response "
                f"(attempt {attempt + 1}/{max_retries})."
            )
        except Exception as e:
            print(f"[{label}] Error (attempt {attempt + 1}/{max_retries}): {e}")
            if not is_retryable_gemini_error(e) or attempt >= max_retries - 1:
                return None

            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)
            continue

        if attempt < max_retries - 1:
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    return None


async def generate_json_async(
    prompt: str,
    response_schema: Type[BaseModel],
    *,
    label: str = "GEMINI",
    model: str | None = None,
    temperature: float = 0.3,
    max_retries: int | None = None,
    base_delay: float | None = None,
) -> dict[str, Any] | None:
    """Async variant of generate_json_sync."""
    max_retries = DEFAULT_MAX_RETRIES if max_retries is None else max_retries
    base_delay = DEFAULT_BASE_DELAY if base_delay is None else base_delay
    model = model or DEFAULT_MODEL

    client = _get_client()

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            parsed = extract_json_from_text(getattr(response, "text", None))
            if parsed is not None:
                return parsed

            print(
                f"[{label}] Empty or unparseable response "
                f"(attempt {attempt + 1}/{max_retries})."
            )
        except Exception as e:
            print(f"[{label}] Error (attempt {attempt + 1}/{max_retries}): {e}")
            if not is_retryable_gemini_error(e) or attempt >= max_retries - 1:
                return None

            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)
            continue

        if attempt < max_retries - 1:
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)

    return None
