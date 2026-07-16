"""
analyze.py
Perform a cross-country comparison of data from SQLite and generate a bar chart 
Displaying the 10 countries with the highest and lowest mortality rates.
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "health.db"
CHART_PATH = Path(__file__).parent / "data" / "trend.png"


def get_top_bottom_countries(conn: sqlite3.Connection, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    A cross-country comparison of mortality rate rankings.
    """
    top = pd.read_sql(f"""
        SELECT country_code, value
        FROM health_indicator
        ORDER BY value DESC
        LIMIT {n}
    """, conn)
    bottom = pd.read_sql(f"""
        SELECT country_code, value
        FROM health_indicator
        ORDER BY value ASC
        LIMIT {n}
    """, conn)
    return top, bottom


def plot_comparison(top: pd.DataFrame, bottom: pd.DataFrame, out_path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].barh(top["country_code"], top["value"], color="crimson")
    axes[0].set_title("Highest Death Rate (Top 10)")
    axes[0].invert_yaxis()

    axes[1].barh(bottom["country_code"], bottom["value"], color="steelblue")
    axes[1].set_title("Lowest Death Rate (Bottom 10)")
    axes[1].invert_yaxis()

    plt.tight_layout()
    plt.savefig(out_path)
    print(f"[analyze] saved chart to {out_path}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise FileNotFoundError("No database found. Run store.py first.")

    conn = sqlite3.connect(DB_PATH)
    top, bottom = get_top_bottom_countries(conn)
    print("Top 10 (highest):")
    print(top)
    print("\nBottom 10 (lowest):")
    print(bottom)

    plot_comparison(top, bottom, CHART_PATH)
    conn.close()
