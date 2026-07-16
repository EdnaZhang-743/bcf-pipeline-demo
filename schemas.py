"""
schemas.py
Use Pydantic to define the required structure for the cleaned data and perform validation before writing it to the database.
"""

from pydantic import BaseModel, field_validator


class CleanedIndicatorRecord(BaseModel):
    country_code: str
    year: int
    sex: str
    value: float

    @field_validator("country_code")
    @classmethod
    def country_code_must_be_valid(cls, v: str) -> str:
        if not (isinstance(v, str) and len(v) == 3 and v.isalpha()):
            raise ValueError(f"country_code should be a 3-letter code, got: {v!r}")
        return v.upper()

    @field_validator("year")
    @classmethod
    def year_must_be_reasonable(cls, v: int) -> int:
        if not (1900 <= v <= 2100):
            raise ValueError(f"year out of reasonable range: {v}")
        return v

    @field_validator("value")
    @classmethod
    def value_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"value should not be negative, got: {v}")
        return v