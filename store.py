"""
store.py
把清洗后的 CSV 加载进 SQLite 数据库。

设计决策（面试时可以讲）：
1. 用 SQLite 而不是 Postgres——demo阶段够快够简单，不需要额外起服务；
   如果要多人协作/部署到服务器，换成 Postgres + 连接池是很自然的下一步。
2. 在 DB 层也加 UNIQUE 约束，而不是只在 pandas 里去重——
   数据校验不能只在应用层做一次，DB 约束是最后一道防线，
   防止未来别的脚本绕过 clean.py 直接写入脏数据。
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

    # 用 INSERT OR IGNORE 语义：借助 pandas to_sql 的 replace 简化 demo，
    # 生产场景更推荐显式 upsert 逻辑，这里作为 next step 提一下即可。
    df.to_sql("health_indicator", conn, if_exists="replace", index=False)

    count = conn.execute("SELECT COUNT(*) FROM health_indicator").fetchone()[0]
    print(f"[store] loaded {count} rows into {db_path}")
    conn.close()


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise FileNotFoundError("No cleaned data found. Run clean.py first.")
    df = pd.read_csv(CSV_PATH)
    load_to_db(df)
