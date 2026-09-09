"""Metadata-only semantic layer for future analytics-agent work."""

from src.analytics_agent.intent_router import IntentRouter, IntentRoutingError
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.semantic_schema import (
    APPROVED_ENTITIES,
    GRAIN,
    SEGMENT_CLUSTER_MAPPING,
    SEMANTIC_REGISTRY,
    get_all_dimensions,
    get_all_metrics,
    get_entity_by_metric,
    lookup_alias,
)

__all__ = [
    "APPROVED_ENTITIES",
    "GRAIN",
    "IntentRouter",
    "IntentRoutingError",
    "QueryPlan",
    "SEGMENT_CLUSTER_MAPPING",
    "SEMANTIC_REGISTRY",
    "get_all_dimensions",
    "get_all_metrics",
    "get_entity_by_metric",
    "lookup_alias",
]
