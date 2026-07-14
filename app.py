"""
app.py（可选加分项）
在清洗好的数据上暴露一个只读小API，模拟真实场景里
其他系统（比如BCFNZ的register platform）怎么消费这份数据。
对应JD里 "build, consume and integrate APIs" 这条要求。
"""

from flask import Flask, jsonify, send_from_directory
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "health.db"

app = Flask(__name__)


def query_db(sql: str, params: tuple = ()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(sql, params)
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows


@app.route("/")
def index():
    """提供极简前端页面，可视化 top/bottom API 的结果"""
    return send_from_directory("static", "index.html")


@app.route("/health")
def health_check():
    """基本的健康检查endpoint——运维/监控最先会打的接口"""
    return jsonify({"status": "ok"})


@app.route("/indicator/top")
def get_top():
    """死亡率最高的10个国家"""
    rows = query_db("""
        SELECT country_code, value
        FROM health_indicator
        ORDER BY value DESC
        LIMIT 10
    """)
    return jsonify(rows)


@app.route("/indicator/bottom")
def get_bottom():
    """死亡率最低的10个国家"""
    rows = query_db("""
        SELECT country_code, value
        FROM health_indicator
        ORDER BY value ASC
        LIMIT 10
    """)
    return jsonify(rows)


@app.route("/indicator/country/<country_code>")
def get_country(country_code: str):
    rows = query_db("""
        SELECT year, sex, value
        FROM health_indicator
        WHERE country_code = ?
        ORDER BY year
    """, (country_code.upper(),))
    if not rows:
        return jsonify({"error": f"No data for country_code={country_code}"}), 404
    return jsonify(rows)


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise FileNotFoundError("No database found. Run fetch.py -> clean.py -> store.py first.")
    app.run(debug=True, host="0.0.0.0", port=5000)
