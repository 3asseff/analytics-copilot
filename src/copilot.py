"""Safe, testable building blocks for a CSV-to-SQL analytics copilot."""

from __future__ import annotations

from dataclasses import dataclass
import re

import duckdb
import pandas as pd


MAX_RESULT_ROWS = 500
FORBIDDEN_SQL = re.compile(
    r"\b(ALTER|ANALYZE|ATTACH|CALL|COPY|CREATE|DELETE|DETACH|DROP|EXPORT|"
    r"IMPORT|INSERT|INSTALL|LOAD|MERGE|PRAGMA|REPLACE|SET|UPDATE|VACUUM)\b",
    flags=re.IGNORECASE,
)
COMMENT_SQL = re.compile(r"(--|/\*|\*/)")


class CopilotError(Exception):
    """A safe error message that can be shown directly in the application."""


@dataclass(frozen=True)
class TableContext:
    """The limited table information provided to the SQL-writing model."""

    row_count: int
    columns: list[tuple[str, str]]
    schema: pd.DataFrame
    preview: pd.DataFrame

    def as_prompt(self) -> str:
        columns = "\n".join(f"- {name} ({data_type})" for name, data_type in self.columns)
        preview = self.preview.to_csv(index=False)
        return (
            f"There is exactly one DuckDB table named data with {self.row_count} rows.\n"
            f"Columns:\n{columns}\n\n"
            f"Sample rows (CSV):\n{preview}"
        )


def build_table_context(connection: duckdb.DuckDBPyConnection) -> TableContext:
    """Return a small, shareable summary of the user-provided table."""
    schema = connection.execute("DESCRIBE data").fetchdf()
    preview = connection.execute("SELECT * FROM data LIMIT 5").fetchdf()
    row_count = connection.execute("SELECT COUNT(*) FROM data").fetchone()[0]
    columns = list(zip(schema["column_name"].tolist(), schema["column_type"].tolist()))
    return TableContext(row_count=row_count, columns=columns, schema=schema, preview=preview)


def validate_read_only_sql(sql: str) -> str:
    """Permit a single SELECT/CTE statement and reject common write/admin operations."""
    query = sql.strip()
    if not query:
        raise CopilotError("The generated query was empty. Please try asking in another way.")
    if COMMENT_SQL.search(query):
        raise CopilotError("SQL comments are not allowed in this demo.")

    query = query.removesuffix(";").strip()
    if ";" in query:
        raise CopilotError("Only one SQL statement can be run at a time.")
    if not re.match(r"^(SELECT|WITH)\b", query, flags=re.IGNORECASE):
        raise CopilotError("Only read-only SELECT queries are allowed.")
    if FORBIDDEN_SQL.search(query):
        raise CopilotError("That query contains an operation this demo does not allow.")
    if not re.search(r"\bdata\b", query, flags=re.IGNORECASE):
        raise CopilotError("Queries must use the uploaded `data` table.")
    return query


def run_read_only_query(connection: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Validate a query, execute it, and keep the displayed result manageable."""
    query = validate_read_only_sql(sql)
    try:
        result = connection.execute(query).fetchdf()
    except duckdb.Error as error:
        raise CopilotError(f"The query could not run: {error}") from error
    return result.head(MAX_RESULT_ROWS)


def generate_sql(
    question: str,
    context: TableContext,
    api_key: str,
    model: str,
) -> str:
    """Ask OpenAI for a single constrained SQL query, then validate it locally."""
    try:
        from openai import OpenAI
    except ImportError as error:
        raise CopilotError("The OpenAI package is missing. Install the project requirements first.") from error

    system_prompt = """You write DuckDB SQL for a beginner-friendly analytics app.
Return only one SQL query—no Markdown, explanation, comments, or semicolon.
The query must be read-only and must use only the table named data.
Use only the columns supplied below. Prefer clear column aliases.
If the question cannot be answered from this data, return: SELECT 'Not enough data to answer this question' AS note FROM data LIMIT 1
"""
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"{context.as_prompt()}\n\nQuestion: {question}",
                },
            ],
        )
        sql = response.output_text.strip()
    except Exception as error:
        raise CopilotError(f"The AI request failed: {error}") from error
    return validate_read_only_sql(sql)
