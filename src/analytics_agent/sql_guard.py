"""Read-only SQL validation for the approved analytics views."""

from __future__ import annotations

import re

from src.analytics_agent.semantic_schema import APPROVED_ENTITIES


class SQLGuardError(ValueError):
    """Raised when SQL falls outside the approved read-only surface."""


class SQLGuard:
    """Validate simple, single-statement SELECT queries without rewriting them."""

    _FORBIDDEN_KEYWORDS = frozenset(
        {
            "alter",
            "begin",
            "call",
            "commit",
            "copy",
            "create",
            "delete",
            "drop",
            "exec",
            "execute",
            "grant",
            "insert",
            "merge",
            "revoke",
            "rollback",
            "savepoint",
            "set",
            "show",
            "truncate",
            "update",
            "vacuum",
            "with",
        }
    )
    _COMMENT_PATTERN = re.compile(r"--|/\*|\*/")
    _TOKEN_PATTERN = re.compile(r"\b[a-z_][a-z0-9_]*\b", re.IGNORECASE)
    _FROM_PATTERN = re.compile(r"\bfrom\s+([a-z_][a-z0-9_]*)\b", re.IGNORECASE)

    def validate(self, sql: str) -> str:
        """Return *sql* unchanged when it is a permitted SELECT statement."""

        if not isinstance(sql, str) or not sql.strip():
            raise SQLGuardError("SQL must be a non-empty string.")
        if self._COMMENT_PATTERN.search(sql):
            raise SQLGuardError("SQL comments are not permitted.")
        if ";" in sql:
            raise SQLGuardError("Semicolons and multi-statement SQL are not permitted.")

        normalized = sql.strip()
        if not re.match(r"^select\b", normalized, re.IGNORECASE):
            raise SQLGuardError("Only SELECT statements are permitted.")

        tokens = {token.lower() for token in self._TOKEN_PATTERN.findall(normalized)}
        forbidden = tokens & self._FORBIDDEN_KEYWORDS
        if forbidden:
            raise SQLGuardError(f"Forbidden SQL keyword: {sorted(forbidden)[0]}")
        if "join" in tokens:
            raise SQLGuardError("JOIN clauses are not permitted.")
        if len(re.findall(r"\bselect\b", normalized, re.IGNORECASE)) != 1:
            raise SQLGuardError("Subqueries are not permitted.")
        if normalized.count("(") != normalized.count(")"):
            raise SQLGuardError("SQL has unbalanced parentheses.")

        sources = self._FROM_PATTERN.findall(normalized)
        if len(sources) != 1:
            raise SQLGuardError("SQL must reference exactly one approved business view.")
        if sources[0].lower() not in APPROVED_ENTITIES:
            raise SQLGuardError(f"Unapproved SQL source: {sources[0]}")
        return sql
