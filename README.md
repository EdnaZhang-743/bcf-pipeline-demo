## Usage

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 1. Find an indicator code at:
#    https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'breast')
#    and set it as INDICATOR_CODE in fetch.py

python fetch.py      # fetch raw data
python clean.py      # clean and validate it
python store.py      # load into SQLite
python analyze.py    # generate comparison chart

# Start the API + frontend
python app.py
# open http://127.0.0.1:5000 in a browser
```

## Running tests

```bash
python -m pytest tests/ -v
```

Tests cover the filtering/deduplication/sex-filtering logic in `clean.py`, the pydantic schema validation, and the database uniqueness constraint in `store.py`. `fetch.py` isn't unit tested since it involves a real network call. `analyze.py` and `app.py` aren't covered either — see Known limitations.

## Data validation

`schemas.py` defines the expected structure of cleaned records using pydantic (field types, country code format, non-negative value range, reasonable year range). `clean.py` validates every row against this schema before writing the CSV; rows that fail are reported and dropped rather than silently flowing downstream or corrupting the database.

## CI

`.github/workflows/ci.yml` runs `pytest tests/` automatically on every push or pull request to `main`, so a future change that breaks the cleaning logic or the database constraint gets caught immediately rather than discovered later.

## Deployment

Deployed on Render: **https://bcf-pipeline-demo.onrender.com**

The build step installs dependencies and runs the full pipeline (`fetch.py` → `clean.py` → `store.py`) to populate the database, then the app is served with Gunicorn (`gunicorn app:app`) — not Flask's built-in dev server, which is used only for local development.
Build Command: pip install -r requirements.txt && python fetch.py && python clean.py && python store.py
Start Command: gunicorn app:app

**Note**: this runs on Render's free tier, which spins down after 15 minutes of inactivity — the first request after idle time may take 30–60 seconds to respond while the instance wakes up.

I initially set up a Dockerfile for containerized deployment, but ran into a local Docker Desktop environment issue I didn't have time to fully resolve, so I used Render's platform-managed deployment instead — it required less local environment setup and got to the same outcome (a live, publicly accessible service) faster. The Dockerfile has since been removed since it's no longer part of the actual deployment path.

## Key design decisions

- **Missing values**: dropped rather than imputed. For this kind of comparative analysis, imputation would distort the results; the number of dropped rows is printed before dropping, so the decision stays traceable.
- **Raw data persisted before cleaning**: fetch and clean are kept as separate steps, so debugging and re-running the cleaning logic doesn't require re-hitting the API.
- **Database uniqueness constraint**: deduplication isn't only handled in pandas — a `UNIQUE(country_code, year, sex)` constraint is also enforced at the DB schema level, as a last line of defense against bad data entering through a different path in the future.
- **Retry logic**: the fetch step uses exponential backoff retries to handle transient network issues.
- **Pivoted from trend analysis to a cross-country comparison**: the original plan was a time-trend analysis, but after cleaning the data it turned out the chosen indicator (WHO `SA_0000001438`) only covers a single year (2004) — there's no time series to analyze. The analysis was adjusted to compare death rates across countries instead (highest vs. lowest 10), which surfaced a >10x gap between the two groups. That gap is more likely explained by differences in countries' medical reporting and diagnostic capacity than by true differences in incidence — countries with weaker registration systems will tend to under-report, not necessarily have lower real rates.
- **Schema validation as a safety net**: `clean.py` assumed stable field names from the API. Adding a pydantic schema check catches malformed or out-of-range data (e.g. a negative death rate, an invalid country code) explicitly, rather than letting it silently corrupt the database or surface as a confusing downstream error.
- **Deployment platform over Docker**: chose Render's platform-managed deployment after a local Docker environment issue, prioritizing a working, publicly accessible outcome over debugging local tooling further.

## Known limitations

- Dataset is small (191 rows after cleaning); the code doesn't handle pagination or streaming for larger volumes
- Database writes use full replacement (`if_exists="replace"`), not incremental upserts
- Tests cover `clean.py` and `store.py` only, not `analyze.py` or `app.py`
- The pipeline only runs on deploy (via the Render build step) — there's no scheduled/incremental re-fetch yet

## Next steps

- Schedule `fetch.py` via GitHub Actions (or Render's cron jobs) for automated incremental updates — current CI only runs tests, not the pipeline itself
- Add logging and basic monitoring/alerting
- Move from full-table replacement to incremental upserts as the dataset grows
- Add test coverage for `analyze.py` and `app.py`
- If working with real patient data: add de-identification, access control, and audit logging (matching this role's requirements around sensitive clinical data)