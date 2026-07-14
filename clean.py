"""
clean.py
把 fetch.py 存下来的原始 JSON 清洗成一份干净的 CSV。

设计决策（面试时可以讲）：
1. 只保留国家级别的数据，丢掉地区/全球汇总的行——避免统计时重复计数。
2. 缺失值选择丢弃而非填充——对于趋势分析来说，填充（比如填0或均值）会
   严重扭曲结果；丢弃前会打印丢了多少行，方便追溯。
3. 用 UNIQUE 组合键 (country_code, year, sex) 去重，保留第一条。
4. 显式做类型转换，避免下游数据库/分析阶段因为字符串类型的数字出问题。

注意：不同 indicator 返回的字段可能略有差异，运行前建议先打开一份
data/raw/*.json 看看实际字段名，按需调整下面的列名。
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
    return raw["value"]  # GHO API 的实际数据都在 value 字段里


def clean_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)

    # 决策1：只保留国家级别的数据
    if "SpatialDimType" in df.columns:
        df = df[df["SpatialDimType"] == "COUNTRY"]

    # 决策2：挑出需要的列，重命名成清晰的名字
    keep_cols = ["SpatialDim", "TimeDim", "Dim1", "NumericValue"]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].rename(columns={
        "SpatialDim": "country_code",
        "TimeDim": "year",
        "Dim1": "sex",
        "NumericValue": "value",
    })

    # 决策2.5：只保留女性数据——乳腺癌男性病例极少，
    # 混在一起会让"平均值"失去意义，分析时也没法讲清楚趋势
    if "sex" in df.columns:
        before_sex_filter = len(df)
        df = df[df["sex"] == "SEX_FMLE"]
        print(f"[clean] kept {len(df)}/{before_sex_filter} rows after filtering to female only")

    # 决策3：处理缺失值——丢弃并打印数量，而不是静默填充
    if "value" in df.columns:
        before = len(df)
        df = df.dropna(subset=["value"])
        print(f"[clean] dropped {before - len(df)} rows with missing value")

    # 决策4：类型转换
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # 决策5：去重
    dedup_cols = [c for c in ["country_code", "year", "sex"] if c in df.columns]
    if dedup_cols:
        dupe_count = df.duplicated(subset=dedup_cols).sum()
        if dupe_count > 0:
            print(f"[clean] found {dupe_count} duplicate rows, keeping first occurrence")
            df = df.drop_duplicates(subset=dedup_cols, keep="first")

    return df.reset_index(drop=True)

def validate_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    用 schemas.CleanedIndicatorRecord 逐行校验，把不符合预期结构/范围的行
    单独挑出来丢弃并打印，而不是让脏数据悄悄流入数据库。
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
