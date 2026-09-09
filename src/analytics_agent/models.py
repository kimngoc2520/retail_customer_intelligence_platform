"""Dataclasses used by the isolated semantic schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


Aggregation = Literal[
    "none",
    "count",
    "count_distinct",
    "sum",
    "avg",
    "min",
    "max",
]

ConceptType = Literal["entity", "dimension", "metric"]


@dataclass(frozen=True)
class Dimension:
    """Business dimension exposed by an approved view."""

    name: str
    source_column: str
    description: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Metric:
    """Business metric exposed by an approved view."""

    name: str
    source_column: str
    aggregation: Aggregation
    description: str
    business_meaning: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SemanticEntity:
    """Metadata for one approved business view or table."""

    name: str
    source_view: str
    description: str
    grain: str
    dimensions: tuple[Dimension, ...] = field(default_factory=tuple)
    metrics: tuple[Metric, ...] = field(default_factory=tuple)
    business_purpose: str = ""
    sample_questions: tuple[str, ...] = field(default_factory=tuple)
    entity_aliases: tuple[str, ...] = field(default_factory=tuple)

    def dimension(self, name: str) -> Dimension:
        for dimension in self.dimensions:
            if dimension.name == name:
                return dimension
        raise KeyError(f"Unknown dimension for {self.name}: {name}")

    def metric(self, name: str) -> Metric:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        raise KeyError(f"Unknown metric for {self.name}: {name}")


@dataclass(frozen=True)
class SemanticReference:
    """A lightweight pointer from an alias to a semantic concept."""

    entity: str
    concept_type: ConceptType
    name: str


@dataclass(frozen=True)
class QueryPlan:
    """Structured, SQL-free interpretation of a business question."""

    question: str
    intent: str
    entity: str
    metric: Optional[str] = None
    dimension: Optional[str] = None
    aggregation: Optional[Aggregation] = None
    filters: dict[str, Any] = field(default_factory=dict)
    sort_direction: Optional[Literal["asc", "desc"]] = None
    limit: Optional[int] = None
