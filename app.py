"""Streamlit entry point for the Analytics Copilot starter project."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from src.copilot import (
    CopilotError,
    build_table_context,
    generate_sql,
    run_read_only_query,
)


PROJECT_ROOT = Path(__file__).parent
SAMPLE_DATA = PROJECT_ROOT / "data" / "sample_sales.csv"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Keep one in-memory DuckDB database per Streamlit session."""
    if "connection" not in st.session_state:
        st.session_state.connection = duckdb.connect(":memory:")
    return st.session_state.connection


def load_dataframe(dataframe: pd.DataFrame) -> None:
    connection = get_connection()
    connection.register("uploaded_data", dataframe)
    connection.execute("CREATE OR REPLACE TABLE data AS SELECT * FROM uploaded_data")
    connection.unregister("uploaded_data")
    st.session_state.dataset_loaded = True


def use_sample_data() -> None:
    load_dataframe(pd.read_csv(SAMPLE_DATA))
    st.session_state.dataset_name = "sample_sales.csv"


def format_sql(sql: str) -> str:
    return sql.strip().removesuffix(";") + ";"


st.set_page_config(page_title="Analytics Copilot", page_icon="📊", layout="wide")
st.title("📊 Analytics Copilot")
st.caption("Upload a CSV, explore it with SQL, then let AI help write the query.")

with st.sidebar:
    st.header("1. Add data")
    uploaded_file = st.file_uploader("Choose a CSV", type="csv")
    if uploaded_file is not None:
        try:
            load_dataframe(pd.read_csv(uploaded_file))
            st.session_state.dataset_name = uploaded_file.name
            st.success(f"Loaded {uploaded_file.name}")
        except Exception as error:
            st.error(f"I couldn't read that CSV: {error}")

    if st.button("Use the included sample data", use_container_width=True):
        use_sample_data()
        st.rerun()

    st.divider()
    st.header("2. Connect AI (optional)")
    api_key = st.text_input(
        "OpenAI API key",
        type="password",
        help="Kept only in this browser session and never saved to disk.",
    )
    model = st.text_input(
        "Model", value=os.getenv("OPENAI_MODEL", "gpt-6-astra")
    )

if not st.session_state.get("dataset_loaded"):
    st.info("Start by uploading a CSV or choosing the included sample sales dataset.")
    st.stop()

connection = get_connection()
context = build_table_context(connection)

st.success(f"Ready: **{st.session_state.get('dataset_name', 'your data')}**")
overview, query_tab, copilot_tab = st.tabs(["Data overview", "Write SQL", "Ask the copilot"])

with overview:
    metric_a, metric_b = st.columns(2)
    metric_a.metric("Rows", f"{context.row_count:,}")
    metric_b.metric("Columns", len(context.columns))
    st.subheader("Columns")
    st.dataframe(context.schema, use_container_width=True, hide_index=True)
    st.subheader("Preview")
    st.dataframe(context.preview, use_container_width=True, hide_index=True)

with query_tab:
    st.caption("Only one read-only SELECT query against the `data` table is allowed.")
    manual_sql = st.text_area(
        "SQL query",
        value="SELECT * FROM data LIMIT 10",
        height=130,
        key="manual_sql",
    )
    if st.button("Run SQL", key="run_manual_sql", type="primary"):
        try:
            result = run_read_only_query(connection, manual_sql)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.caption(f"{len(result):,} row(s) returned")
        except CopilotError as error:
            st.error(str(error))

with copilot_tab:
    st.write("Ask a business question in plain English.")
    question = st.text_input(
        "Question",
        placeholder="Which region had the highest revenue last month?",
    )
    if st.button("Generate and run query", type="primary", key="ask_copilot"):
        if not question.strip():
            st.warning("Enter a question first.")
        elif not api_key:
            st.warning("Add an OpenAI API key in the sidebar to generate SQL.")
        else:
            try:
                with st.spinner("Writing a safe SQL query..."):
                    sql = generate_sql(question, context, api_key, model)
                st.code(format_sql(sql), language="sql")
                result = run_read_only_query(connection, sql)
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.caption(f"{len(result):,} row(s) returned")
            except CopilotError as error:
                st.error(str(error))

st.divider()
st.caption(
    "Learning note: this app uses DuckDB for local analytics and validates every generated query "
    "before it runs. It is a portfolio starter, not a production security boundary."
)
