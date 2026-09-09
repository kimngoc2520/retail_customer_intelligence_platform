"""Small HTTP client used by Streamlit to call the API service."""

from __future__ import annotations

import os
from typing import Any

import httpx


class AnalyticsAPIError(RuntimeError):
    """Raised when the API cannot return an analytics response."""


def api_base_url() -> str:
    """Return the configured API URL for Docker or local Streamlit."""

    return os.getenv("ANALYTICS_API_URL", "http://localhost:8000").rstrip("/")


def ask_api(question: str, *, base_url: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    """Send one question to FastAPI and return its JSON AgentResponse payload."""

    try:
        response = httpx.post(
            f"{(base_url or api_base_url()).rstrip('/')}/ask",
            json={"question": question},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise AnalyticsAPIError("The analytics API could not be reached.") from error
    if not isinstance(payload, dict):
        raise AnalyticsAPIError("The analytics API returned an invalid response.")
    return payload
