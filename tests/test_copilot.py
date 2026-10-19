import pytest

from src.copilot import CopilotError, validate_read_only_sql


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM data",
        " select region, sum(revenue) FROM data GROUP BY region; ",
        "WITH totals AS (SELECT region, sum(revenue) AS revenue FROM data GROUP BY region) SELECT * FROM totals",
    ],
)
def test_allows_read_only_queries(query: str) -> None:
    assert validate_read_only_sql(query)


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM data",
        "SELECT * FROM data; DROP TABLE data",
        "SELECT * FROM other_table",
        "SELECT * FROM data -- hide a command",
        "",
    ],
)
def test_rejects_unsafe_or_wrong_table_queries(query: str) -> None:
    with pytest.raises(CopilotError):
        validate_read_only_sql(query)
