"""Unit tests for the offline Phase 8 evaluator."""

from dataclasses import dataclass

from src.analytics_agent.query_executor import QueryResult
from src.analytics_agent.result_validator import ValidatedResult
from tests.evaluation.evaluator import AnalyticsEvaluator
from tests.evaluation.test_cases import EvaluationCase


@dataclass
class FakePlan:
    intent: str
    entity: str
    metric: str | None
    dimension: str | None
    aggregation: str | None


@dataclass
class FakeResponse:
    success: bool
    plan: FakePlan | None = None
    sql: str | None = None
    result: ValidatedResult | None = None
    insight: str | None = None
    error: str | None = None


class FakeAgent:
    def __init__(self, response: FakeResponse):
        self.response = response

    def ask(self, question):
        return self.response


def valid_response() -> FakeResponse:
    result = QueryResult(("segment_name", "monetary"), (("Loyal Customers", 12.5),), 1)
    return FakeResponse(
        True,
        FakePlan("segment_analysis", "customer_segments", "monetary", "segment_name", "sum"),
        "SELECT segment_name, SUM(monetary) AS monetary FROM customer_segments GROUP BY segment_name",
        ValidatedResult(result.columns, result.rows, result.row_count),
        "Customer monetary value by segment: Loyal Customers: 12.50.",
    )


def test_evaluator_reports_all_success_metrics():
    case = EvaluationCase("Show revenue by customer segment.", "segment_analysis", "customer_segments", "monetary", "segment_name", "sum")
    report = AnalyticsEvaluator(FakeAgent(valid_response())).evaluate([case])
    assert report.total_cases == report.passed_cases == 1
    assert report.intent_accuracy == 1
    assert report.sql_validity_rate == 1
    assert report.insight_groundedness_rate == 1
    assert report.average_latency_ms >= 0
    assert report.median_latency_ms >= 0


def test_evaluator_exposes_safe_rejection_without_failing_suite():
    case = EvaluationCase("DROP TABLE customer_segments", expected_success=False)
    response = FakeResponse(False, error="The question is not supported by the analytics agent.")
    report = AnalyticsEvaluator(FakeAgent(response)).evaluate([case])
    assert report.passed_cases == 1
    assert report.safety_rejection_rate == 1


def test_evaluator_marks_fabricated_numeric_insight_failed():
    response = valid_response()
    response.insight = "Customer monetary value by segment: Loyal Customers: 999.00."
    case = EvaluationCase("Show revenue by customer segment.", "segment_analysis", "customer_segments", "monetary", "segment_name", "sum")
    report = AnalyticsEvaluator(FakeAgent(response)).evaluate([case])
    assert report.failed_cases == 1
    assert report.insight_groundedness_rate == 0

