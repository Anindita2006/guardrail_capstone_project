"""Shared OpenAI-compatible client + bounded-retry completion helper, used by
both the advisory agent and the evaluation judge."""
from __future__ import annotations

import time

from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL

# Some OpenAI-compatible providers (observed: Groq's gpt-oss models) occasionally let
# chain-of-thought reasoning bleed into the slot where a structured tool call is
# expected, and reject the response with a 400 rather than returning it. This is a
# transient generation issue, not a logic error, so it gets a small bounded retry.
_RETRYABLE_ERROR_CODES = {"tool_use_failed", "output_parse_failed"}
_MAX_COMPLETION_RETRIES = 2
# Groq's free tier occasionally times out or drops the connection under load rather
# than returning an error response — also transient, also worth a bounded retry with
# a short backoff so one slow request doesn't fail the whole scenario.
_MAX_NETWORK_RETRIES = 2
_NETWORK_RETRY_BACKOFF_SECONDS = 2


def get_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def create_completion_with_retry(client: OpenAI, **kwargs):
    last_err = None
    for attempt in range(_MAX_COMPLETION_RETRIES + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            if e.code in _RETRYABLE_ERROR_CODES:
                last_err = e
                continue
            raise
        except (APITimeoutError, APIConnectionError) as e:
            last_err = e
            if attempt < _MAX_NETWORK_RETRIES:
                time.sleep(_NETWORK_RETRY_BACKOFF_SECONDS)
                continue
            raise
    raise last_err
