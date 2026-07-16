"""
clean.py
Use pandas to clean the raw JSON saved by fetch.py ​​into a clean CSV file.

Design Decisions:
1. Retain only country-level data and discard regional or global aggregate rows to avoid double-counting during analysis.
2. Retain only data for females (discarding data for males and combined totals).
3. Drop missing values ​​rather than imputing them; for trend analysis, imputation (e.g., filling with 0 or the mean) would
   severely distort the results. The number of dropped rows is logged to facilitate traceability.
4. Deduplicate using the composite key `(country_code, year, sex)`, keeping the first occurrence.
5. Standardize field types to the correct numeric format to prevent issues in downstream database/analysis caused by numeric values ​​stored as strings.
6. Perform a final validation using Pydantic to filter out rows that do not comply with expected rules.

Note: The fields returned by different indicators may vary slightly. 
Before running the code, it is recommended to open a file from `data/raw/*.json` to check the actual field names and adjust the column names below as needed.
"""

import json
import pandas as pd
from pathlib import Path
from pydantic import ValidationError

from schemas import CleanedIndicatorRecord

RAW_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_CSV = Path(__file__).parent / "data" / "cleaned.csv"


def load_raw(filepath: Path) -> list[dict]:
    raw = json.loads(filepath.read_text())
    return raw["value"]  # The actual data from the GHO API is contained within the `value` field.


def clean_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)  # Convert a list of raw data—composed of individual dictionaries—into a pandas DataFrame.

    # Decision 1: Retain only country-level data and discard rows containing regional or global aggregates to avoid duplication.
    if "SpatialDimType" in df.columns:
        df = df[df["SpatialDimType"] == "COUNTRY"]

    # Decision 2: Select the required columns and rename them with clear names.
    keep_cols = ["SpatialDim", "TimeDim", "Dim1", "NumericValue"]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].rename(columns={
        "SpatialDim": "country_code",
        "TimeDim": "year",
        "Dim1": "sex",
        "NumericValue": "value",
    })

    # Decision 2.5: Only retain female data – there are very few male cases of breast cancer.
    # Mixing them together renders the "average" meaningless and makes it impossible to clearly explain trends during analysis.
    if "sex" in df.columns:
        before_sex_filter = len(df)
        df = df[df["sex"] == "SEX_FMLE"]
        print(f"[clean] kept {len(df)}/{before_sex_filter} rows after filtering to female only")

    # Decision 3: Handle missing values—drop them and print the count, rather than silently imputing them.
    if "value" in df.columns:
        before = len(df)
        df = df.dropna(subset=["value"])
        print(f"[clean] dropped {before - len(df)} rows with missing value")

    # Decision 4: Type Conversion
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Decision 5: Deduplication
    dedup_cols = [c for c in ["country_code", "year", "sex"] if c in df.columns]
    if dedup_cols:
        dupe_count = df.duplicated(subset=dedup_cols).sum()
        if dupe_count > 0:
            print(f"[clean] found {dupe_count} duplicate rows, keeping first occurrence")
            df = df.drop_duplicates(subset=dedup_cols, keep="first")

    return df.reset_index(drop=True)

def validate_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Use schemas.CleanedIndicatorRecord to validate each line and remove lines that do not conform to the expected structure/range
    remove and print instead of allowing dirty data to quietly flow into the database.
    """
    valid_rows = []
    errors = []
    for i, row in df.iterrows():
        try:
            validated = CleanedIndicatorRecord(**row.to_dict())
            valid_rows.append(validated.model_dump())
        except ValidationError as e:
            errors.append((i, str(e)))

    if errors:
        print(f"[clean] {len(errors)} row(s) failed schema validation and were dropped:")
        for i, err in errors[:5]:
            print(f"  row {i}: {err.splitlines()[0]}")

    return pd.DataFrame(valid_rows)

if __name__ == "__main__":
    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        raise FileNotFoundError("No raw data found. Run fetch.py first.")

    latest_raw = raw_files[-1]
    print(f"[clean] using {latest_raw}")
    records = load_raw(latest_raw)

    df = clean_records(records)
    df = validate_records(df)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(df.head())
    print(f"[clean] total rows after cleaning: {len(df)}")
    print(f"[clean] saved to {OUTPUT_CSV}")
