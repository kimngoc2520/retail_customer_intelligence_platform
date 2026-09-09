from fastapi.testclient import TestClient

from app.api import create_app
from src.analytics_agent.agent import AgentResponse
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.result_validator import ValidatedResult


def _success_response() -> AgentResponse:
    plan = QueryPlan(
        question="Show revenue by month.",
        intent="revenue_trend",
        entity="monthly_sales",
        metric="revenue",
        dimension="month",
        aggregation="none",
    )
    result = ValidatedResult(("month", "revenue"), (("2018-01-01", 10),), 1)
    return AgentResponse(True, plan.question, plan, "SELECT month, revenue FROM monthly_sales", {}, result, "Revenue was 10.")


class FakeAgent:
    def ask(self, question: str) -> AgentResponse:
        return _success_response()


def test_health_endpoint() -> None:
    client = TestClient(create_app(FakeAgent()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_validates_request() -> None:
    client = TestClient(create_app(FakeAgent()))
    assert client.post("/ask", json={}).status_code == 422
    assert client.post("/ask", json={"question": "  "}).status_code == 422


def test_ask_returns_agent_response() -> None:
    client = TestClient(create_app(FakeAgent()))
    response = client.post("/ask", json={"question": "Show revenue by month."})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["plan"]["intent"] == "revenue_trend"
    assert response.json()["result"]["row_count"] == 1


class FailingAgent:
    def ask(self, question: str) -> AgentResponse:
        raise RuntimeError("database unavailable")


def test_ask_handles_agent_error_safely() -> None:
    client = TestClient(create_app(FailingAgent()))
    response = client.post("/ask", json={"question": "Show revenue by month."})
    assert response.status_code == 500
    assert response.json()["detail"] == "Analytics request failed safely."
