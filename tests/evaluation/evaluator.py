"""Reusable deterministic evaluator for the AnalyticsAgent."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Protocol

from src.analytics_agent.sql_guard import SQLGuard, SQLGuardError
from tests.evaluation.test_cases import EvaluationCase


class EvaluatableAgent(Protocol):
    def ask(self, question: str) -> Any: ...


@dataclass(frozen=True)
class CaseEvaluation:
    question: str | None
    expected_success: bool
    actual_success: bool
    intent_correct: bool
    plan_valid: bool
    sql_valid: bool
    safely_rejected: bool
    execution_success: bool
    result_valid: bool
    metric_correct: bool
    insight_grounded: bool
    latency_ms: float
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class EvaluationReport:
    total_cases: int
    passed_cases: int
    failed_cases: int
    intent_accuracy: float
    plan_validity_rate: float
    sql_validity_rate: float
    safety_rejection_rate: float
    execution_success_rate: float
    result_validation_rate: float
    metric_correctness_rate: float
    insight_groundedness_rate: float
    average_latency_ms: float
    median_latency_ms: float
    cases: tuple[CaseEvaluation, ...]


class AnalyticsEvaluator:
    """Evaluate an injected agent without network calls or database assumptions."""

    def __init__(self, agent: EvaluatableAgent, sql_guard: SQLGuard | None = None) -> None:
        self.agent = agent
        self.sql_guard = sql_guard or SQLGuard()

    def evaluate(self, cases: Iterable[EvaluationCase]) -> EvaluationReport:
        evaluations = tuple(self._evaluate_case(case) for case in cases)
        valid = tuple(item for item in evaluations if item.expected_success)
        unsafe = tuple(item for item in evaluations if not item.expected_success)

        def rate(items: tuple[CaseEvaluation, ...], field: str) -> float:
            return sum(bool(getattr(item, field)) for item in items) / len(items) if items else 1.0

        latencies = [item.latency_ms for item in evaluations]
        return EvaluationReport(
            total_cases=len(evaluations),
            passed_cases=sum(item.passed for item in evaluations),
            failed_cases=sum(not item.passed for item in evaluations),
            intent_accuracy=rate(valid, "intent_correct"),
            plan_validity_rate=rate(valid, "plan_valid"),
            sql_validity_rate=rate(valid, "sql_valid"),
            safety_rejection_rate=rate(unsafe, "safely_rejected"),
            execution_success_rate=rate(valid, "execution_success"),
            result_validation_rate=rate(valid, "result_valid"),
            metric_correctness_rate=rate(valid, "metric_correct"),
            insight_groundedness_rate=rate(valid, "insight_grounded"),
            average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            median_latency_ms=statistics.median(latencies) if latencies else 0.0,
            cases=evaluations,
        )

    def _evaluate_case(self, case: EvaluationCase) -> CaseEvaluation:
        started = time.perf_counter()
        try:
            response = self.agent.ask(case.question)
            error = getattr(response, "error", None)
        except Exception as exc:  # evaluator reports failures instead of hiding them
            response = None
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - started) * 1000
        actual_success = bool(getattr(response, "success", False))
        plan = getattr(response, "plan", None)
        result = getattr(response, "result", None)
        insight = getattr(response, "insight", None)
        intent_correct = bool(plan and plan.intent == case.expected_intent) if case.expected_success else True
        plan_valid = self._plan_valid(plan, case) if case.expected_success else True
        sql_valid = self._sql_valid(getattr(response, "sql", None)) if case.expected_success and actual_success else (not case.expected_success)
        safely_rejected = (not actual_success and bool(error)) if not case.expected_success else True
        execution_success = actual_success if case.expected_success else True
        result_valid = bool(result and getattr(result, "valid", False)) if case.expected_success else True
        metric_correct = self._metric_correct(result, case) if case.expected_success and actual_success else True
        insight_grounded = self._insight_grounded(insight, result) if case.expected_success and actual_success else True
        passed = (
            actual_success == case.expected_success
            and intent_correct and plan_valid and sql_valid and safely_rejected
            and execution_success and result_valid and metric_correct and insight_grounded
        )
        return CaseEvaluation(
            question=case.question, expected_success=case.expected_success,
            actual_success=actual_success, intent_correct=intent_correct,
            plan_valid=plan_valid, sql_valid=sql_valid, safely_rejected=safely_rejected,
            execution_success=execution_success, result_valid=result_valid,
            metric_correct=metric_correct, insight_grounded=insight_grounded,
            latency_ms=latency_ms, passed=passed, error=error,
        )

    @staticmethod
    def _plan_valid(plan: Any, case: EvaluationCase) -> bool:
        if plan is None or plan.entity != case.expected_entity:
            return False
        expected = {
            "metric": case.expected_metric,
            "dimension": case.expected_dimension,
            "aggregation": case.expected_aggregation,
        }
        return all(value is None or getattr(plan, field, None) == value for field, value in expected.items())

    def _sql_valid(self, sql: str | None) -> bool:
        if not sql:
            return False
        try:
            self.sql_guard.validate(sql)
        except SQLGuardError:
            return False
        return True

    @staticmethod
    def _metric_correct(result: Any, case: EvaluationCase) -> bool:
        if result is None:
            return False
        expected_column = case.expected_result_metric or case.expected_metric
        return bool(expected_column and expected_column in getattr(result, "columns", ()))

    @staticmethod
    def _insight_grounded(insight: str | None, result: Any) -> bool:
        if not insight or result is None:
            return False
        text = str(insight)
        for row in getattr(result, "rows", ()):
            for value in row:
                try:
                    decimal = Decimal(str(value))
                except (InvalidOperation, ValueError):
                    continue
                if decimal.is_nan():
                    continue
                candidates = {str(value), f"{decimal:,.2f}", f"{decimal:,}"}
                if not any(candidate in text for candidate in candidates):
                    return False
        return True
