"""
tests/test_store.py
测试数据库层的核心保证：schema建表正常、唯一约束真的能挡住重复数据。
"""

import sys
import sqlite3
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from store import create_schema


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    create_schema(connection)
    yield connection
    connection.close()


def test_schema_creates_table(conn):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "health_indicator" in tables


def test_can_insert_valid_row(conn):
    conn.execute(
        "INSERT INTO health_indicator (country_code, year, sex, value) VALUES (?, ?, ?, ?)",
        ("NZL", 2004, "SEX_FMLE", 20.5),
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM health_indicator").fetchone()[0]
    assert count == 1


def test_uniqueness_constraint_blocks_duplicate(conn):
    conn.execute(
        "INSERT INTO health_indicator (country_code, year, sex, value) VALUES (?, ?, ?, ?)",
        ("NZL", 2004, "SEX_FMLE", 20.5),
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO health_indicator (country_code, year, sex, value) VALUES (?, ?, ?, ?)",
            ("NZL", 2004, "SEX_FMLE", 99.9),
        )
        conn.commit()


def test_different_sex_same_country_year_is_allowed(conn):
    conn.execute(
        "INSERT INTO health_indicator (country_code, year, sex, value) VALUES (?, ?, ?, ?)",
        ("NZL", 2004, "SEX_FMLE", 20.5),
    )
    conn.execute(
        "INSERT INTO health_indicator (country_code, year, sex, value) VALUES (?, ?, ?, ?)",
        ("NZL", 2004, "SEX_MLE", 0.3),
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM health_indicator").fetchone()[0]
    assert count == 2