"""Deterministic orchestration for the approved analytics workflow."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from src.analytics_agent.insight_generator import InsightGenerationError, InsightGenerator
from src.analytics_agent.intent_router import IntentRouter, IntentRoutingError
from src.analytics_agent.llm_provider import LLMProvider, LLMProviderError, LLMResponseError
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.plan_validator import QueryPlanValidationError, QueryPlanValidator
from src.analytics_agent.query_executor import QueryExecutionError, QueryExecutor
from src.analytics_agent.result_validator import ResultValidationError, ValidatedResult, ResultValidator
from src.analytics_agent.sql_generator import GeneratedQuery, SQLGenerationError, SQLGenerator
from src.analytics_agent.sql_guard import SQLGuardError


@dataclass(frozen=True)
class AgentResponse:
    """Structured outcome of one deterministic analytics request."""

    success: bool
    question: str
    plan: Optional[QueryPlan] = None
    sql: Optional[str] = None
    params: Optional[dict[str, object]] = None
    result: Optional[ValidatedResult] = None
    insight: Optional[str] = None
    error: Optional[str] = None
    llm_used: bool = False
    fallback_used: bool = False


class AnalyticsAgent:
    """Orchestrate routing, guarded execution, validation, and grounded insight text."""

    def __init__(
        self,
        router: IntentRouter | None = None,
        sql_generator: SQLGenerator | None = None,
        executor: QueryExecutor | None = None,
        validator: ResultValidator | None = None,
        insight_generator: InsightGenerator | None = None,
        llm_provider: LLMProvider | None = None,
        plan_validator: QueryPlanValidator | None = None,
    ) -> None:
        self._router = router or IntentRouter()
        self._sql_generator = sql_generator or SQLGenerator()
        self._executor = executor or QueryExecutor()
        self._validator = validator or ResultValidator()
        self._insight_generator = insight_generator or InsightGenerator()
        self._llm_provider = llm_provider
        self._plan_validator = plan_validator or QueryPlanValidator()

    def ask(self, question: str) -> AgentResponse:
        """Answer one supported question through the established analytics pipeline."""

        if self._is_unsafe_request(question):
            return self._failure(
                question,
                "The question is not supported by the analytics agent.",
            )

        plan, llm_used, fallback_used = self._resolve_plan(question)
        if plan is None:
            return self._failure(question, "The question is not supported by the analytics agent.", fallback_used=fallback_used)

        try:
            generated_query = self._sql_generator.generate(plan)
        except SQLGenerationError:
            return self._failure(question, "The question could not be converted into an approved analytics query.", plan, llm_used=llm_used, fallback_used=fallback_used)

        try:
            query_result = self._executor.execute(generated_query)
        except SQLGuardError:
            return self._failure(question, "The generated query did not meet analytics safety requirements.", plan, generated_query, llm_used, fallback_used)
        except QueryExecutionError:
            return self._failure(question, "The analytics query could not be executed.", plan, generated_query, llm_used, fallback_used)

        try:
            validated_result = self._validator.validate(query_result, plan)
        except ResultValidationError:
            return self._failure(question, "The returned data could not be validated.", plan, generated_query, llm_used, fallback_used)

        try:
            insight = self._insight_generator.generate(plan, validated_result)
        except InsightGenerationError:
            return self._failure(question, "The returned data could not be summarized.", plan, generated_query, llm_used, fallback_used)

        return AgentResponse(
            success=True,
            question=question,
            plan=plan,
            sql=generated_query.sql,
            params=generated_query.params,
            result=validated_result,
            insight=insight,
            llm_used=llm_used,
            fallback_used=fallback_used,
        )

    @staticmethod
    def _is_unsafe_request(question: object) -> bool:
        """Reject SQL control/destructive requests before semantic routing."""

        if not isinstance(question, str):
            return False
        return re.search(
            r"\b(?:DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
            r"EXEC|EXECUTE|COPY|COMMIT|ROLLBACK)\b",
            question,
            flags=re.IGNORECASE,
        ) is not None

    def _resolve_plan(self, question: str) -> tuple[QueryPlan | None, bool, bool]:
        if self._llm_provider is not None:
            try:
                return self._plan_validator.validate(self._llm_provider.generate_query_plan(question)), True, False
            except (LLMProviderError, LLMResponseError, QueryPlanValidationError):
                fallback_used = True
            else:
                fallback_used = False
        else:
            fallback_used = False
        try:
            return self._router.route(question), False, fallback_used
        except IntentRoutingError:
            return None, False, fallback_used

    @staticmethod
    def _failure(
        question: str,
        error: str,
        plan: QueryPlan | None = None,
        generated_query: GeneratedQuery | None = None,
        llm_used: bool = False,
        fallback_used: bool = False,
    ) -> AgentResponse:
        return AgentResponse(
            success=False,
            question=question,
            plan=plan,
            sql=generated_query.sql if generated_query else None,
            params=generated_query.params if generated_query else None,
            error=error,
            llm_used=llm_used,
            fallback_used=fallback_used,
        )
