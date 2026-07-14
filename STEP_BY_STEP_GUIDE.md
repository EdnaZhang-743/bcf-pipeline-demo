# 面试项目分步指南：WHO健康数据 Pipeline

> 目标：2.5小时内做出一个能讲清楚"设计决策"的小项目，而不是一个"看起来完整但你说不清楚为什么这么做"的项目。
> **重要提醒**：下面的代码是骨架和示例，请你自己在本地敲一遍、跑一遍、改一遍。面试时面试官会追问细节，只有自己写过才答得上来。

---

## Step 0：环境准备（10分钟）

```bash
mkdir bcf-pipeline-demo && cd bcf-pipeline-demo
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install requests pandas matplotlib

git init
```

**为什么先 `git init`**：JD明确要求 version control。等下每完成一个模块就commit一次，面试时可以直接打开git log讲你的思路演进,而不是一次性甩出一个大commit。

---

## Step 1：探索API，定好要抓什么（15分钟）

先别写代码，用浏览器或curl探索一下API长什么样：

```bash
curl "https://ghoapi.azureedge.net/api/Indicator?\$filter=contains(IndicatorName,%27breast%20cancer%27)"
```

看返回的JSON，找到你要的 `IndicatorCode`（比如某个乳腺癌死亡率/发病率指标）。如果搜不到理想的乳腺癌专项指标，退而求其次用一个通用的癌症死亡率指标也完全没问题，重点不是数据本身，是pipeline的设计。

**记下这几个问题的答案，面试时会用到：**
- 这个指标的字段大概长什么样？（国家代码、年份、性别维度、数值）
- 有没有缺失值？有没有重复的行（比如同一国家同一年有多条记录，因为按性别/年龄分组了）？
- 数据量大概多大？（决定你要不要分页）

---

## Step 2：写 `fetch.py`（40分钟）

```python
import requests
import json
from pathlib import Path
from datetime import datetime

INDICATOR_CODE = "你在Step1里找到的代码"  # 例如 "WHOSIS_000001"
BASE_URL = f"https://ghoapi.azureedge.net/api/{INDICATOR_CODE}"
RAW_DATA_DIR = Path("data/raw")

def fetch_indicator_data(url: str) -> dict:
    """从WHO GHO API拉取指定指标的原始数据"""
    response = requests.get(url, timeout=15)
    response.raise_for_status()  # 非200直接抛错，不要吞掉错误
    return response.json()

def save_raw(data: dict):
    """原始数据先落盘，不直接进清洗流程"""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DATA_DIR / f"{INDICATOR_CODE}_{timestamp}.json"
    filepath.write_text(json.dumps(data, indent=2))
    print(f"Saved raw data to {filepath}")
    return filepath

if __name__ == "__main__":
    data = fetch_indicator_data(BASE_URL)
    save_raw(data)
```

**这里有几个"设计决策"，面试时要能讲出为什么：**

1. **为什么先存raw JSON再清洗，而不是拉下来直接处理？**
   → 如果清洗逻辑写错了，你可以回头重新清洗，不用重新打API；也方便你调试时对照原始数据。

2. **为什么用 `raise_for_status()` 而不是自己判断状态码？**
   → 让错误尽早暴露，而不是把一个空/错误的响应悄悄传到下一步，导致下游报出一个看起来无关的诡异错误。

3. **如果API有分页怎么办？**
   → GHO API通常一次性返回全部数据（不像REST分页API），但如果你的指标数据量很大，可以提一句"生产环境我会加分页处理和限流"，这是加分项，不用真的写。

4. **重试机制**（可选，但值得提一下你考虑过）：
```python
from time import sleep

def fetch_with_retry(url: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            return fetch_indicator_data(url)
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt+1} failed: {e}, retrying...")
            sleep(2 ** attempt)  # 指数退避
```

跑起来，确认 `data/raw/` 下有文件了，commit一次。

```bash
git add fetch.py
git commit -m "Add fetch script for WHO GHO indicator data"
```

---

## Step 3：写 `clean.py`（40分钟）

先打开你存的raw JSON，看一眼 `value` 字段里每条记录长什么样（大概率有 `SpatialDim`国家代码、`TimeDim`年份、`Dim1`可能是性别、`NumericValue`数值、还有一堆你不需要的元数据字段）。

```python
import json
import pandas as pd
from pathlib import Path

def load_raw(filepath: Path) -> list[dict]:
    raw = json.loads(filepath.read_text())
    return raw["value"]  # GHO API的数据都在value字段里

def clean_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)

    # 决策1：只保留国家级别的数据，丢掉地区/全球汇总的行
    # （举例，具体字段名以你实际拿到的数据为准）
    if "SpatialDimType" in df.columns:
        df = df[df["SpatialDimType"] == "COUNTRY"]

    # 决策2：挑出真正需要的列，重命名成清晰的名字
    df = df[["SpatialDim", "TimeDim", "Dim1", "NumericValue"]].rename(columns={
        "SpatialDim": "country_code",
        "TimeDim": "year",
        "Dim1": "sex",
        "NumericValue": "value",
    })

    # 决策3：处理缺失值——这里选择丢弃value为空的行，
    # 因为对于"死亡率趋势分析"来说，缺失值填充（比如填0或均值）会严重扭曲结果，
    # 不如明确丢弃、并在README里注明丢了多少行
    before = len(df)
    df = df.dropna(subset=["value"])
    print(f"Dropped {before - len(df)} rows with missing value")

    # 决策4：类型转换
    df["year"] = df["year"].astype(int)
    df["value"] = df["value"].astype(float)

    # 决策5：去重（同一国家同一年同一性别不应该有多条）
    dupe_count = df.duplicated(subset=["country_code", "year", "sex"]).sum()
    if dupe_count > 0:
        print(f"Found {dupe_count} duplicate rows, keeping first occurrence")
        df = df.drop_duplicates(subset=["country_code", "year", "sex"], keep="first")

    return df.reset_index(drop=True)

if __name__ == "__main__":
    raw_files = sorted(Path("data/raw").glob("*.json"))
    latest_raw = raw_files[-1]  # 用最新的一份
    records = load_raw(latest_raw)
    df = clean_records(records)
    df.to_csv("data/cleaned.csv", index=False)
    print(df.head())
    print(f"Total rows after cleaning: {len(df)}")
```

**这一步是面试官最爱追问的地方**，务必想清楚每个"决策"背后的理由，不要只是"pandas常规操作"糊弄过去。比如：
- 为什么丢弃而不是填充缺失值？
- 如果面试官问"要是这批数据里20%都缺失怎么办"——你的答案应该是"我会先去弄清楚缺失的原因（是数据采集问题还是这个国家真的没上报），而不是直接丢或直接填",这才是体现判断力的回答。

commit：
```bash
git add clean.py
git commit -m "Add cleaning logic: filter, dedupe, handle missing values"
```

---

## Step 4：存入数据库（30分钟）

用SQLite（自带、不用装服务），schema尽量简单：

```python
import sqlite3
import pandas as pd

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
    # UNIQUE约束 = 让重复插入直接失败,而不是悄悄产生脏数据

def load_to_db(df: pd.DataFrame, db_path: str = "data/health.db"):
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    df.to_sql("health_indicator", conn, if_exists="replace", index=False)
    conn.close()

if __name__ == "__main__":
    df = pd.read_csv("data/cleaned.csv")
    load_to_db(df)
    print("Loaded to data/health.db")
```

**设计决策讲点**：
- 为什么是SQLite不是Postgres？——"demo阶段用SQLite够快够简单，如果要多人协作或部署到服务器，我会换成Postgres,加连接池"
- 为什么在DB层也加UNIQUE约束，而不是只在pandas里去重？——"数据校验不能只在应用层做一次，DB约束是最后一道防线，防止未来别的脚本绕过clean.py直接写入脏数据"

这句话非常值得在面试里说一遍，体现你想到了"防御性设计"。

commit：
```bash
git add store.py
git commit -m "Add SQLite storage with schema and uniqueness constraint"
```

---

## Step 5：简单分析 + 一张图（20分钟）

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect("data/health.db")

# 示例查询：过去每年的全球平均值趋势
query = """
    SELECT year, AVG(value) as avg_value
    FROM health_indicator
    GROUP BY year
    ORDER BY year
"""
trend = pd.read_sql(query, conn)
print(trend)

plt.figure(figsize=(8, 5))
plt.plot(trend["year"], trend["avg_value"], marker="o")
plt.title("Global Average Trend Over Time")
plt.xlabel("Year")
plt.ylabel("Value")
plt.tight_layout()
plt.savefig("data/trend.png")
print("Saved chart to data/trend.png")
```

不用做花哨的dashboard，一张折线图 + 一两句你从图里看出什么("过去X年整体呈下降/上升趋势"、"某几个国家明显异常")就够了。这一步的重点是"你会不会用数据回答问题"，不是可视化能力。

---

## Step 6（可选加分项）：暴露一个小API（20分钟）

这一步直接对应JD里"build APIs"的要求，如果时间够务必做：

```python
# app.py
from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route("/indicator/trend")
def get_trend():
    conn = sqlite3.connect("data/health.db")
    cursor = conn.execute("""
        SELECT year, AVG(value) as avg_value
        FROM health_indicator
        GROUP BY year
        ORDER BY year
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"year": r[0], "avg_value": r[1]} for r in rows])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

```bash
pip install flask
python app.py
# 另开一个终端: curl http://localhost:5000/indicator/trend
```

面试时可以说："pipeline的最后一步我加了一个小endpoint，模拟真实场景里其他系统（比如register platform）怎么消费这份清洗好的数据"——这就是在呼应JD里"connect the platform with other systems"这句话。

---

## Step 7：写README（15分钟）

结构建议（不用长，半页纸够）：

```markdown
# Health Indicator Pipeline Demo

## 目标
从WHO GHO公开API拉取一份健康指标数据，清洗后存入SQLite，做简单分析。

## 为什么选这个数据/API
（写你自己的理由，结合BCFNZ的业务背景）

## 架构
fetch.py → data/raw/*.json → clean.py → data/cleaned.csv → store.py → data/health.db → analyze.py / app.py

## 关键设计决策
- 缺失值：丢弃而非填充,理由是...
- DB约束：加UNIQUE防止脏数据,理由是...
- （列出2-3个你觉得最值得讲的）

## 已知局限
- 没有做完整的单元测试
- 没有处理API限流/大规模分页场景
- ...

## Next Steps（如果继续做）
- 用GitHub Actions定时跑fetch.py,实现自动化更新
- 加数据校验层（比如用pydantic或great_expectations）
- Dockerize,方便部署
- 如果涉及真实患者数据：加脱敏、访问控制、审计日志
```

commit：
```bash
git add README.md app.py
git commit -m "Add README, optional API endpoint, and analysis script"
```

---

## Step 8：面试当天怎么讲（重要！）

**不要**打开代码从第一行念到最后一行。按这个顺序讲，5-8分钟：

1. **目标**（30秒）："我做了一个从公开API到数据库的小pipeline，选了和你们业务相关的健康数据"
2. **架构**（1分钟）：画一下 fetch → clean → store → analyze 的流程（口头讲或者提前画个图）
3. **挑1-2个最有意思的决策深入讲**（3分钟）：比如缺失值处理、DB约束设计——不要每个细节都讲,挑你最有把握、最能体现判断力的讲透
4. **展示结果**（1分钟）：跑一下代码，看清洗后的数据/图/API返回
5. **Next steps**（1分钟）：主动说你没做但知道该做的事,尤其提一下数据安全/隐私（呼应他们JD）

**准备好回答这几个追问：**
- "如果这份数据有100万行,你的方案还work吗？"（提示：谈分批处理、数据库索引、不要一次性读进内存）
- "如果API突然改了字段名,你的pipeline会怎样？"（提示：谈schema validation、监控告警）
- "为什么不用pandas直接写excel,非要用数据库？"（提示：谈查询能力、并发访问、数据量增长后的可扩展性）

---

## 时间总览

| 步骤 | 时间 |
|---|---|
| 环境准备 + 探索API | 25分钟 |
| fetch.py | 40分钟 |
| clean.py | 40分钟 |
| store.py | 30分钟 |
| 分析+图 | 20分钟 |
| （可选）API | 20分钟 |
| README | 15分钟 |
| **合计** | 约2.5-3小时（不含API可选项约2.5小时) |

祝你面试顺利！有任何一步卡住了，随时把报错贴给我。
