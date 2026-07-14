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

Tests cover the filtering/deduplication/sex-filtering logic in `clean.py`, the pydantic schema validation, and the database uniqueness constraint in `store.py`. `fetch.py` isn't unit tested since it involves a real network call.

## Data validation

`schemas.py` defines the expected structure of cleaned records using pydantic (field types, country code format, non-negative value range, reasonable year range). `clean.py` validates every row against this schema before writing the CSV; rows that fail are reported and dropped rather than silently flowing downstream or corrupting the database.

## CI

`.github/workflows/ci.yml` runs `pytest tests/` automatically on every push or pull request to `main`, so a future change that breaks the cleaning logic or the database constraint gets caught immediately rather than discovered later.

## Deployment (Docker) — configured but not yet verified

A `Dockerfile` and `entrypoint.sh` are included: the container is designed to check whether `data/health.db` exists on startup, run the full fetch → clean → store pipeline if not, and then start the Flask app, listening on `0.0.0.0:5000`.

```bash
docker build -t bcf-pipeline-demo .
docker run -p 5000:5000 bcf-pipeline-demo
```

**Honest note**: I wrote this configuration but haven't been able to fully verify it builds and runs end-to-end due to a local Docker Desktop environment issue. The application runs correctly outside Docker; containerizing it is the next thing I'd confirm given a bit more time.

## Key design decisions

- **Missing values**: dropped rather than imputed. For this kind of comparative analysis, imputation would distort the results; the number of dropped rows is printed before dropping, so the decision stays traceable.
- **Raw data persisted before cleaning**: fetch and clean are kept as separate steps, so debugging and re-running the cleaning logic doesn't require re-hitting the API.
- **Database uniqueness constraint**: deduplication isn't only handled in pandas — a `UNIQUE(country_code, year, sex)` constraint is also enforced at the DB schema level, as a last line of defense against bad data entering through a different path in the future.
- **Retry logic**: the fetch step uses exponential backoff retries to handle transient network issues.
- **Pivoted from trend analysis to a cross-country comparison**: the original plan was a time-trend analysis, but after cleaning the data it turned out the chosen indicator (WHO `SA_0000001438`) only covers a single year (2004) — there's no time series to analyze. The analysis was adjusted to compare death rates across countries instead (highest vs. lowest 10), which surfaced a >10x gap between the two groups. That gap is more likely explained by differences in countries' medical reporting and diagnostic capacity than by true differences in incidence — countries with weaker registration systems will tend to under-report, not necessarily have lower real rates.
- **Schema validation as a safety net**: `clean.py` assumed stable field names from the API. Adding a pydantic schema check catches malformed or out-of-range data (e.g. a negative death rate, an invalid country code) explicitly, rather than letting it silently corrupt the database or surface as a confusing downstream error.

## Known limitations

- Dataset is small (191 rows after cleaning); the code doesn't handle pagination or streaming for larger volumes
- Database writes use full replacement (`if_exists="replace"`), not incremental upserts
- Docker setup is written but not build-verified locally (see Deployment section above)
- The Flask app uses its built-in development server, not suitable for production
- Tests cover `clean.py` and `store.py` only, not `analyze.py` or `app.py`

## Next steps

- Verify and finish the Docker setup once the local Docker Desktop issue is resolved
- Schedule `fetch.py` via GitHub Actions for automated incremental updates (current CI only runs tests, not the pipeline itself)
- Swap the Flask dev server for a production WSGI server (e.g. Gunicorn) if actually deployed
- Add logging and basic monitoring/alerting
- If working with real patient data: add de-identification, access control, and audit logging (matching this role's requirements around sensitive clinical data)
