"""Gemini JSON-generation client."""

# this file is responsible for sending requests to Gemini models and returning raw JSON text.
# it handles retries for rate-limiting errors, but does not validate the JSON output.
# validation of the JSON output is handled in mnemo.memory.extract and mnemo.memory.conflicts.

import logging
import random
import time
from functools import lru_cache

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from mnemo.config import get_settings

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


@lru_cache(maxsize=4)
def _get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _is_rate_limit(error: Exception) -> bool:
    if (
        isinstance(error, (ClientError, ServerError))
        and (error.code == 429 or error.status == 429)
    ):
        return True
    return "resource_exhausted" in str(error).casefold()


def generate_json(model: str, system_prompt: str, user_content: str) -> str:
    """Generate raw JSON text, retrying rate limits with backoff and jitter."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for Gemini requests")

    client = _get_client(settings.gemini_api_key)
    for attempt in range(MAX_ATTEMPTS):
        started = time.monotonic()
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            latency = time.monotonic() - started
            logger.info("Gemini model %s completed in %.3fs", model, latency)
            output = response.text
            if output is None:
                raise RuntimeError(f"Gemini model {model} returned no text")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Gemini model %s raw output: %s", model, output)
            return output
        except (ClientError, ServerError) as error:
            if not _is_rate_limit(error) or attempt == MAX_ATTEMPTS - 1:
                raise
            delay = 2**attempt + random.uniform(0, 1)
            logger.warning(
                "Gemini rate limit for model %s; retrying in %.2fs (%d/%d)",
                model,
                delay,
                attempt + 1,
                MAX_ATTEMPTS - 1,
            )
            time.sleep(delay)

    raise RuntimeError(f"Gemini model {model} exhausted retry attempts")
