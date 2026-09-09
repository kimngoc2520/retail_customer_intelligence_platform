"""Streamlit presentation layer for the Retail Customer Intelligence agent."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import AnalyticsAPIError, ask_api
from app.ui_helpers import build_chart_spec, query_plan_details, response_is_successful, result_records
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.result_validator import ValidatedResult


SAMPLE_QUESTIONS = (
    "Which categories generated the most revenue?",
    "What was the monthly revenue trend?",
    "Which states generated the highest revenue?",
    "Which customer segment generated the most revenue?",
    "Which customers spent the most?",
)


def main() -> None:
    """Render the analytics interaction surface without accessing data services directly."""

    st.set_page_config(page_title="Retail Customer Intelligence", layout="wide")
    st.title("Retail Customer Intelligence")
    st.caption("AI Analytics Agent")
    st.write("Ask a business question and receive grounded analytics from the retail dataset.")

    _apply_selected_example()
    selected_example = st.selectbox("Sample questions", ("Choose an example", *SAMPLE_QUESTIONS))
    if st.button("Use sample question") and selected_example != "Choose an example":
        st.session_state.selected_example = selected_example
        st.rerun()

    with st.form("analytics_question"):
        question = st.text_area(
            "Business question",
            key="question",
            placeholder="Which product categories generated the most revenue?",
            height=92,
        )
        submitted = st.form_submit_button("Run analysis", type="primary")

    if not submitted:
        return
    if not question.strip():
        st.warning("Enter a business question to begin the analysis.")
        return

    with st.spinner("Running guarded analytics..."):
        try:
            response = _response_from_payload(ask_api(question.strip()))
        except AnalyticsAPIError as error:
            st.error(str(error))
            return
    _render_response(response)


def _response_from_payload(payload: dict) -> object:
    """Adapt the API's JSON payload to the existing UI helper contract."""

    class Response:
        pass

    response = Response()
    response.success = bool(payload.get("success"))
    response.error = payload.get("error")
    response.insight = payload.get("insight")
    response.sql = payload.get("sql")
    response.llm_used = bool(payload.get("llm_used"))
    response.fallback_used = bool(payload.get("fallback_used"))
    plan = payload.get("plan")
    response.plan = QueryPlan(**plan) if isinstance(plan, dict) else None
    result = payload.get("result")
    if isinstance(result, dict):
        response.result = ValidatedResult(
            columns=tuple(result.get("columns", ())),
            rows=tuple(tuple(row) for row in result.get("rows", ())),
            row_count=int(result.get("row_count", 0)),
            valid=bool(result.get("valid", True)),
        )
    else:
        response.result = None
    return response


def _apply_selected_example() -> None:
    selected_example = st.session_state.pop("selected_example", None)
    if selected_example is not None:
        st.session_state.question = selected_example


def _render_response(response) -> None:
    if not response_is_successful(response):
        st.error(response.error or "The analytics request could not be completed.")
        return

    st.subheader("Business Insight")
    st.success(response.insight or "No grounded insight was returned.")

    chart = build_chart_spec(response.plan, response.result)
    if chart is not None:
        st.subheader("Visualization")
        chart_frame = pd.DataFrame(chart.rows, columns=[chart.dimension, chart.metric])
        if chart.kind == "line":
            st.line_chart(chart_frame, x=chart.dimension, y=chart.metric)
        else:
            st.bar_chart(chart_frame, x=chart.dimension, y=chart.metric)

    st.subheader("Data / Evidence")
    records = result_records(response.result)
    if records:
        st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
    else:
        st.info("No matching data was found for this question.")

    with st.expander("Query Plan"):
        st.json(query_plan_details(response.plan))
    if response.sql:
        with st.expander("Generated SQL"):
            st.code(response.sql, language="sql")

    st.caption(
        f"LLM: {'Used' if response.llm_used else 'Not used'} | "
        f"Deterministic fallback: {'Yes' if response.fallback_used else 'No'}"
    )


if __name__ == "__main__":
    main()
