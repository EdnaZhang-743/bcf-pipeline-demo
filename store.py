"""
store.py
Load the cleaned CSV into the SQLite database.

Design decisions:
1. Used SQLite instead of PostgreSQL 
   it is fast and simple enough for the demo phase and requires no additional server setup;
   switching to PostgreSQL with connection pooling would be a natural next step if moving to multi-user collaboration or server deployment.

2. Implemented `UNIQUE` constraints at the database level rather than relying solely on pandas for deduplication
   data validation shouldn't happen only at the application layer; database constraints serve as the final line of defense,
   preventing other scripts from bypassing `clean.py` and writing "dirty" data in the future.
"""

import sqlite3
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "cleaned.csv"
DB_PATH = Path(__file__).parent / "data" / "health.db"


def create_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_indicator (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT NOT NULL,
            year INTEGER NOT NULL,
            sex TEXT,
            value REAL NOT NULL,
            UNIQUE(country_code, year, sex)
        )
    """)
    conn.commit()


def load_to_db(df: pd.DataFrame, db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    df.to_sql("health_indicator", conn, if_exists="replace", index=False)

    count = conn.execute("SELECT COUNT(*) FROM health_indicator").fetchone()[0]
    print(f"[store] loaded {count} rows into {db_path}")
    conn.close()


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise FileNotFoundError("No cleaned data found. Run clean.py first.")
    df = pd.read_csv(CSV_PATH)
    load_to_db(df)
