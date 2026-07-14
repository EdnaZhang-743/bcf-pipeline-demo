"""
tests/test_clean.py
针对 clean.py 里最有决策含量的部分写测试。
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clean import clean_records, validate_records


def make_record(**overrides):
    base = {
        "SpatialDimType": "COUNTRY",
        "SpatialDim": "NZL",
        "TimeDim": 2004,
        "Dim1": "SEX_FMLE",
        "NumericValue": 20.5,
    }
    base.update(overrides)
    return base


class TestCleanRecords:
    def test_keeps_valid_country_female_row(self):
        records = [make_record()]
        df = clean_records(records)
        assert len(df) == 1
        assert df.iloc[0]["country_code"] == "NZL"

    def test_drops_non_country_rows(self):
        records = [
            make_record(SpatialDim="NZL"),
            make_record(SpatialDimType="REGION", SpatialDim="WPRO"),
        ]
        df = clean_records(records)
        assert len(df) == 1
        assert df.iloc[0]["country_code"] == "NZL"

    def test_filters_to_female_only(self):
        records = [
            make_record(SpatialDim="NZL", Dim1="SEX_FMLE"),
            make_record(SpatialDim="AUS", Dim1="SEX_MLE"),
            make_record(SpatialDim="USA", Dim1="SEX_BTSX"),
        ]
        df = clean_records(records)
        assert len(df) == 1
        assert df.iloc[0]["country_code"] == "NZL"

    def test_drops_missing_values(self):
        records = [
            make_record(SpatialDim="NZL", NumericValue=20.5),
            make_record(SpatialDim="AUS", NumericValue=None),
        ]
        df = clean_records(records)
        assert len(df) == 1
        assert df.iloc[0]["country_code"] == "NZL"

    def test_deduplicates_same_country_year_sex(self):
        records = [
            make_record(SpatialDim="NZL", NumericValue=20.5),
            make_record(SpatialDim="NZL", NumericValue=99.9),
        ]
        df = clean_records(records)
        assert len(df) == 1
        assert df.iloc[0]["value"] == 20.5

    def test_empty_input_returns_empty_dataframe(self):
        df = clean_records([])
        assert len(df) == 0


class TestValidateRecords:
    def test_valid_rows_pass_through(self):
        df = pd.DataFrame([
            {"country_code": "NZL", "year": 2004, "sex": "SEX_FMLE", "value": 20.5},
        ])
        result = validate_records(df)
        assert len(result) == 1

    def test_negative_value_is_dropped(self):
        df = pd.DataFrame([
            {"country_code": "NZL", "year": 2004, "sex": "SEX_FMLE", "value": 20.5},
            {"country_code": "AUS", "year": 2004, "sex": "SEX_FMLE", "value": -5.0},
        ])
        result = validate_records(df)
        assert len(result) == 1
        assert result.iloc[0]["country_code"] == "NZL"

    def test_invalid_country_code_is_dropped(self):
        df = pd.DataFrame([
            {"country_code": "XX", "year": 2004, "sex": "SEX_FMLE", "value": 20.5},
        ])
        result = validate_records(df)
        assert len(result) == 0