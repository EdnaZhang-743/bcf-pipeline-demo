# Health Indicator Pipeline Demo

A small pipeline that fetches health indicator data from the WHO GHO public API, cleans it, and stores it in SQLite.

## Goal

Practice a complete data pipeline: fetch → clean → store → analyze, and use it to demonstrate the kind of engineering trade-offs that come up in real-world work (error handling, missing data handling, database constraints, etc.).

## Why this dataset

WHO's Global Health Observatory provides free, unauthenticated access to health statistics, including cancer-related indicators — relevant to the role's domain (a breast cancer foundation).

## Architecture
fetch.py  →  data/raw/*.json  →  clean.py  →  data/cleaned.csv
↓
store.py
↓
data/health.db
↙        ↘
analyze.py       app.py
(top/bottom country      (read-only API)
comparison)

## Usage

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 1. Find an indicator code at:
#    https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'breast')
#    and set it as INDICATOR_CODE in fetch.py

python fetch.py      # fetch raw data
python clean.py      # clean it
python store.py      # load into SQLite
python analyze.py    # generate comparison chart

# Optional: start the API
python app.py
# curl http://localhost:5000/indicator/trend
```

## Key design decisions

- **Missing values**: dropped rather than imputed. For this kind of comparative analysis, imputation would distort the results; the number of dropped rows is printed before dropping, so the decision stays traceable.
- **Raw data persisted before cleaning**: fetch and clean are kept as separate steps, so debugging and re-running the cleaning logic doesn't require re-hitting the API.
- **Database uniqueness constraint**: deduplication isn't only handled in pandas — a `UNIQUE(country_code, year, sex)` constraint is also enforced at the DB schema level, as a last line of defense against bad data entering through a different path in the future.
- **Retry logic**: the fetch step uses exponential backoff retries to handle transient network issues.
- **Pivoted from trend analysis to a cross-country comparison**: the original plan was a time-trend analysis, but after cleaning the data it turned out the chosen indicator (WHO `SA_0000001438`) only covers a single year (2004) — there's no time series to analyze. The analysis was adjusted to compare death rates across countries instead (highest vs. lowest 10), which surfaced a >10x gap between the two groups. That gap is more likely explained by differences in countries' medical reporting and diagnostic capacity than by true differences in incidence — countries with weaker registration systems will tend to under-report, not necessarily have lower real rates.

## Known limitations

- No unit tests
- Dataset is small (191 rows after cleaning); the code doesn't handle pagination or streaming for larger volumes
- Database writes use full replacement (`if_exists="replace"`), not incremental upserts
- No input schema validation (e.g. via pydantic) — the code currently assumes the API's field names stay stable

## Next steps

- Schedule `fetch.py` via GitHub Actions for automated incremental updates
- Add a data validation layer (pydantic / great_expectations) to catch upstream schema changes early
- Dockerize for easier deployment
- Add logging and basic monitoring/alerting
- If working with real patient data: add de-identification, access control, and audit logging (matching this role's requirements around sensitive clinical data)
