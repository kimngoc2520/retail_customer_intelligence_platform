"""HTTP API for the existing AnalyticsAgent."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator

from src.analytics_agent.agent import AgentResponse, AnalyticsAgent


class AskRequest(BaseModel):
    """Validated request payload for the analytics endpoint."""

    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


def _response_payload(response: AgentResponse) -> dict[str, Any]:
    payload = asdict(response) if is_dataclass(response) else response
    return jsonable_encoder(payload)


def create_app(agent: AnalyticsAgent | None = None) -> FastAPI:
    """Create the API application around one existing agent instance."""

    analytics_agent = agent or AnalyticsAgent()
    app = FastAPI(title="Retail Customer Intelligence API", version="1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(request: AskRequest) -> dict[str, Any]:
        try:
            response = analytics_agent.ask(request.question)
        except Exception as error:  # pragma: no cover - defensive HTTP boundary
            raise HTTPException(status_code=500, detail="Analytics request failed safely.") from error
        return _response_payload(response)

    return app


app = create_app()
