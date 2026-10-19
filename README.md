# Analytics Copilot

A beginner-friendly portfolio project that turns a CSV into a local analytics workspace. A user can explore their data, write SQL, or ask an AI to draft a safe DuckDB query.

## What this demonstrates

- **Python:** a Streamlit app with logic separated into testable functions
- **SQL:** data profiling and analytics queries using DuckDB
- **Data work:** CSV upload, schema inspection, and results tables
- **AI:** natural-language questions translated into DuckDB SQL with the OpenAI Responses API
- **Responsible design:** generated SQL is validated before execution and the app permits only one read-only query

## Run it locally

You need Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in the terminal. Select **Use the included sample data** to try it immediately.

To enable the AI question box, paste an OpenAI API key into the app sidebar. It stays in the browser session only. You can choose a model there or set `OPENAI_MODEL` before starting the app.

## Good first questions

- Which region generated the most revenue?
- Show monthly revenue and units sold.
- Which product has the highest gross margin?
- Compare revenue by sales channel.

## Project structure

```text
app.py              # User interface
src/copilot.py      # Data context, SQL validation, and AI integration
tests/              # SQL safety tests
data/sample_sales.csv
```

## Next improvements

1. Add automatic charts for common question types.
2. Add a query history and downloadable results.
3. Move from CSV files to PostgreSQL.
4. Add evaluation questions to measure whether generated SQL is correct.
5. Add role-based access and real database security before using sensitive data.

## Important limitation

This is a learning project, not a production data-security system. Never paste confidential company data into a model API without appropriate permission, data controls, and review.
