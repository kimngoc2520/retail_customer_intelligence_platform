"""Offline tests for structured LLM query-plan providers."""

import pytest

from src.analytics_agent.llm_provider import LLMProviderError, LLMResponseError, MockLLMProvider, OpenAIQueryPlanProvider, semantic_context
from src.analytics_agent.models import QueryPlan


def candidate():
    return QueryPlan("top categories", "category_performance", "category_sales", "revenue", "category", "sum", {}, "desc", 5)


def test_mock_provider_returns_a_structured_query_plan():
    assert MockLLMProvider(candidate()).generate_query_plan("anything") == candidate()


def test_mock_provider_can_simulate_failure():
    with pytest.raises(LLMProviderError):
        MockLLMProvider(LLMProviderError("offline")).generate_query_plan("anything")


def test_openai_provider_fails_safely_without_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(LLMProviderError, match="credentials or model"):
        OpenAIQueryPlanProvider().generate_query_plan("top categories")


def test_openai_provider_rejects_malformed_structured_response(monkeypatch):
    provider = OpenAIQueryPlanProvider(api_key="test-key", model="test-model")
    monkeypatch.setattr(
        OpenAIQueryPlanProvider,
        "_request",
        lambda self, payload, api_key: {"choices": [{"message": {"content": "not json"}}]},
    )
    with pytest.raises(LLMResponseError):
        provider.generate_query_plan("top categories")


def test_openai_provider_converts_json_fields_into_the_existing_query_plan():
    plan = OpenAIQueryPlanProvider._to_query_plan(
        "top categories",
        {
            "intent": "category_performance",
            "entity": "category_sales",
            "metric": "revenue",
            "dimension": "category",
            "aggregation": "sum",
            "filters": {},
            "sort_direction": "desc",
            "limit": 5,
        },
    )
    assert plan == candidate()


def test_semantic_context_preserves_customer_and_revenue_rules():
    context = semantic_context()
    assert context["customer_identity"] == "customer_unique_id"
    assert "monthly_sales.revenue" in context["revenue_rules"]
