"""Deterministic, metadata-driven routing from questions to query plans.

This module only interprets questions. It does not generate or execute SQL.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from src.analytics_agent.models import Aggregation, QueryPlan, SemanticEntity
from src.analytics_agent.semantic_schema import (
    SEGMENT_CLUSTER_MAPPING,
    SEMANTIC_REGISTRY,
    get_all_dimensions,
    get_all_metrics,
    get_entity_by_metric,
    lookup_alias,
)


class IntentRoutingError(ValueError):
    """Raised when a question cannot be mapped safely to approved metadata."""


class IntentRouter:
    """Route supported business questions using the semantic registry only."""

    # Specific entities must win over broad customer wording in a question.
    _ENTITY_PRIORITY = (
        "customer_segments",
        "category_sales",
        "state_sales",
        "monthly_sales",
        "customer_summary",
    )

    _ENTITY_INTENTS = {
        "monthly_sales": "revenue_trend",
        "category_sales": "category_performance",
        "state_sales": "state_performance",
        "customer_summary": "customer_analysis",
        "customer_segments": "segment_analysis",
    }

    def route(self, question: str) -> QueryPlan:
        """Return a deterministic plan for one supported business question."""

        if not isinstance(question, str) or not question.strip():
            raise IntentRoutingError("A non-empty question is required.")

        normalized_question = self._normalize(question)
        entity_name = self._detect_entity(normalized_question)
        if entity_name is None:
            raise IntentRoutingError("The question does not identify a supported entity.")

        entity = SEMANTIC_REGISTRY[entity_name]
        metric = self._detect_metric(normalized_question, entity)
        dimension = self._detect_dimension(normalized_question, entity)
        filters = self._detect_filters(normalized_question, entity)
        aggregation = self._detect_aggregation(normalized_question, entity, metric)
        # Preserve the existing filtered-segment count plan shape; SQL generation
        # still emits a distinct customer count for this legacy representation.
        if entity_name == "customer_segments" and filters and metric == "customer_unique_id" and aggregation == "count_distinct":
            metric, aggregation = None, "count"
        sort_direction = self._detect_sort_direction(normalized_question)
        limit = self._detect_limit(normalized_question, sort_direction)

        return QueryPlan(
            question=question,
            intent=self._ENTITY_INTENTS[entity_name],
            entity=entity_name,
            metric=metric,
            dimension=dimension,
            aggregation=aggregation,
            filters=filters,
            sort_direction=sort_direction,
            limit=limit,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFD", value.lower())
        without_accents = "".join(
            character for character in decomposed if not unicodedata.combining(character)
        ).replace("đ", "d")
        return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()

    @classmethod
    def _contains_phrase(cls, question: str, phrase: str) -> bool:
        normalized_phrase = cls._normalize(phrase)
        return bool(normalized_phrase) and re.search(
            rf"(?:^|\s){re.escape(normalized_phrase)}(?:$|\s)", question
        ) is not None

    def _detect_entity(self, question: str) -> Optional[str]:
        segment_names = tuple(SEGMENT_CLUSTER_MAPPING.values())
        for entity_name in self._ENTITY_PRIORITY:
            entity = SEMANTIC_REGISTRY[entity_name]
            if entity_name == "state_sales" and re.search(
                r"\b(?:in|for)\s+[a-z]{2}\b", question
            ) and any(self._contains_phrase(question, phrase) for phrase in ("revenue", "sales", "doanh thu")):
                return entity_name
            aliases = [entity.name.replace("_", " "), *entity.entity_aliases]
            for dimension in entity.dimensions:
                for alias in dimension.aliases:
                    references = lookup_alias(alias)
                    if references and all(reference.entity == entity_name for reference in references):
                        aliases.append(alias)

            if entity_name == "customer_segments" and any(
                self._contains_phrase(question, segment_name) for segment_name in segment_names
            ):
                return entity_name

            for alias in aliases:
                if not self._contains_phrase(question, alias):
                    continue
                references = lookup_alias(alias)
                if not references or any(reference.entity == entity_name for reference in references):
                    return entity_name
        return None

    def _detect_metric(self, question: str, entity: SemanticEntity) -> Optional[str]:
        candidates: list[tuple[int, str]] = []
        for metric in entity.metrics:
            if entity.name == "customer_segments" and metric.name == "customer_unique_id":
                continue
            aliases = (metric.name.replace("_", " "), *metric.aliases)
            for alias in aliases:
                if self._contains_phrase(question, alias):
                    candidates.append((len(self._normalize(alias)), metric.name))

        tokens = question.split()
        for start in range(len(tokens)):
            for end in range(start + 1, min(start + 5, len(tokens) + 1)):
                alias = " ".join(tokens[start:end])
                for reference in lookup_alias(alias):
                    if reference.entity == entity.name and reference.concept_type == "metric":
                        candidates.append((len(alias), reference.name))

        if candidates:
            metric_name = max(candidates)[1]
        elif entity.name == "customer_segments" and any(
            self._contains_phrase(question, phrase)
            for phrase in (
                "bao nhieu khach hang", "nhieu khach hang", "how many customers",
                "most customers", "number of customers", "customer count", "customer counts",
            )
        ):
            metric_name = "customer_unique_id"
        elif entity.name == "customer_summary" and any(
            self._contains_phrase(question, phrase)
            for phrase in ("chi tieu", "chi bao nhieu", "spend", "spent", "spending")
        ):
            metric_name = "total_spent"
        elif entity.name == "customer_segments" and any(
            self._contains_phrase(question, phrase)
            for phrase in ("doanh thu", "revenue", "sales", "chi tieu", "spend", "spent", "spending")
        ):
            metric_name = "monetary"
        else:
            return None

        qualified_metric = f"{entity.name}.{metric_name}"
        if qualified_metric not in get_all_metrics():
            return None
        # Retain the semantic helper as the canonical registry check for metric names.
        if get_entity_by_metric(metric_name) is None:
            return None
        return metric_name

    def _detect_dimension(self, question: str, entity: SemanticEntity) -> Optional[str]:
        if entity.name == "customer_segments":
            return "segment_name"
        if entity.name == "customer_segments" and any(
            self._contains_phrase(question, segment_name)
            for segment_name in SEGMENT_CLUSTER_MAPPING.values()
        ):
            return "segment_name"

        candidates: list[tuple[int, str]] = []
        for dimension in entity.dimensions:
            aliases = (dimension.name.replace("_", " "), *dimension.aliases)
            for alias in aliases:
                if self._contains_phrase(question, alias):
                    candidates.append((len(self._normalize(alias)), dimension.name))

        if candidates:
            dimension_name = max(candidates)[1]
        elif entity.name == "customer_segments":
            dimension_name = "segment_name"
        else:
            dimension_name = entity.dimensions[0].name if entity.dimensions else None

        if dimension_name and f"{entity.name}.{dimension_name}" in get_all_dimensions():
            return dimension_name
        return None

    def _detect_aggregation(
        self, question: str, entity: SemanticEntity, metric_name: Optional[str]
    ) -> Optional[Aggregation]:
        if any(self._contains_phrase(question, phrase) for phrase in ("trung binh", "average", "avg")):
            return "avg"
        if any(self._contains_phrase(question, phrase) for phrase in ("tong", "total")):
            return "sum"
        if any(
            self._contains_phrase(question, phrase)
            for phrase in ("bao nhieu", "how many", "number of", "count")
        ):
            return "count_distinct" if entity.name == "customer_segments" and metric_name == "customer_unique_id" else "count"
        if metric_name is None:
            return None

        metric = entity.metric(metric_name)
        if metric.aggregation != "none":
            return metric.aggregation
        if entity.name == "customer_segments" and metric_name == "monetary":
            return "sum"
        if entity.name == "customer_segments" and metric_name == "customer_unique_id":
            return "count_distinct"
        return None

    def _detect_sort_direction(self, question: str) -> Optional[str]:
        if any(
            self._contains_phrase(question, phrase)
            for phrase in ("thap nhat", "nho nhat", "lowest", "smallest", "least")
        ):
            return "asc"
        if any(
            self._contains_phrase(question, phrase)
            for phrase in ("cao nhat", "lon nhat", "nhieu nhat", "top", "highest", "largest", "most")
        ):
            return "desc"
        return None

    def _detect_limit(self, question: str, sort_direction: Optional[str]) -> Optional[int]:
        top_match = re.search(r"\btop\s+(\d+)\b", question)
        ranked_match = re.search(
            r"\b(\d+)\s+(?:danh muc|category|bang|tinh|state|customers?)\b", question
        )
        match = top_match or ranked_match
        if match:
            return int(match.group(1))
        return 1 if sort_direction is not None else None

    def _detect_filters(self, question: str, entity: SemanticEntity) -> dict[str, str]:
        filters: dict[str, str] = {}
        if entity.name == "monthly_sales":
            year_match = re.search(r"\b(?:in|for|year|nam)\s+(20\d{2})\b", question)
            if year_match:
                filters["year"] = year_match.group(1)

        if entity.name == "customer_segments":
            for segment_name in SEGMENT_CLUSTER_MAPPING.values():
                if self._contains_phrase(question, segment_name):
                    filters["segment_name"] = segment_name
                    return filters

        if entity.name == "state_sales":
            state_match = re.search(
                r"\b(?:in|for)\s+(?:(?:state|bang|tinh)\s+)?([a-z]{2})\b|"
                r"\b(?:o|tai)\s+(?:(?:state|bang|tinh)\s+)?([a-z]{2})\b|"
                r"\b(?:bang|tinh)\s+([a-z]{2})\b",
                question,
            )
            if state_match:
                state = next(group for group in state_match.groups() if group is not None)
                filters["customer_state"] = state.upper()
        return filters
