"""Gemini JSON-generation client."""

# this file is responsible for sending requests to Gemini models and returning raw JSON text.
# it handles retries for rate-limiting errors, but does not validate the JSON output.
# validation of the JSON output is handled in mnemo.memory.extract and mnemo.memory.conflicts.

import logging
import random
import time
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from mnemo.config import get_settings

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


@lru_cache(maxsize=4)
def _get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


# function to determine if an error is retryable based on its type and status code
# retryable errors include rate-limiting (429) and server errors (503)
# also checks for certain error messages that indicate the service is overloaded or unavailable
# daily quota errors (containing "PerDay") are non-retryable
def _is_retryable(error: Exception) -> bool:
    if "PerDay" in str(error):
        return False
    if isinstance(error, (ClientError, ServerError)):
        code = getattr(error, "code", None) or getattr(error, "status", None)
        if code in (429, 503):
            return True
    err_str = str(error).casefold()
    return (
        "resource_exhausted" in err_str
        or "overloaded" in err_str
        or "unavailable" in err_str
    )


# this funtion executes a call to the Gemini API with retry logic for transient errors
def _execute_with_retry(
    model: str,
    call_fn: Any,
) -> str:
    for attempt in range(MAX_ATTEMPTS):
        started = time.monotonic()
        try:
            response = call_fn()
            latency = time.monotonic() - started
            logger.info("Gemini model %s completed in %.3fs", model, latency)
            output = response.text
            if output is None:
                raise RuntimeError(f"Gemini model {model} returned no text")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Gemini model %s raw output: %s", model, output)
            return output
        except (ClientError, ServerError) as error:
            if not _is_retryable(error) or attempt == MAX_ATTEMPTS - 1:
                raise
            delay = 2**attempt + random.uniform(0, 1)
            logger.warning(
                "Gemini transient error for model %s; retrying in %.2fs (%d/%d)",
                model,
                delay,
                attempt + 1,
                MAX_ATTEMPTS - 1,
            )
            time.sleep(delay)

    raise RuntimeError(f"Gemini model {model} exhausted retry attempts")


def generate_json(model: str, system_prompt: str, user_content: str) -> str:
    """Generate raw JSON text, retrying rate limits and server errors with backoff."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for Gemini requests")

    client = _get_client(settings.gemini_api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
                response_mime_type="application/json",
            ),
        )

    return _execute_with_retry(model, _call)


def generate_text(
    model: str,
    system_prompt: str,
    messages: Sequence[Mapping[str, str]],
    temperature: float = 0.6,
) -> str:
    """Generate plain text response for multi-turn chat conversations."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for Gemini requests")

    client = _get_client(settings.gemini_api_key)

    contents: list[types.Content] = []
    for msg in messages:
        role = msg.get("role", "user")
        text = msg.get("content", "")
        # Map "assistant" role to Gemini's "model" role
        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=text)],
            )
        )

    def _call():
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )

    return _execute_with_retry(model, _call)
