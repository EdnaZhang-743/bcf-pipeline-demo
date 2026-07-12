"""
fetch.py
从 WHO GHO OData API 拉取指定健康指标的原始数据，落盘为 JSON。

设计决策（面试时可以讲）：
1. 先存 raw JSON 再清洗，而不是拉下来直接处理——
   方便调试、清洗逻辑写错了可以重跑，不用重新打 API。
2. 用 raise_for_status() 让错误尽早暴露，而不是把空/错误响应悄悄传到下一步。
3. 加了简单的指数退避重试，模拟真实场景里网络不稳定的情况。

使用前：
1. 去 https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'breast')
   找到你想要的 IndicatorCode，填到下面的 INDICATOR_CODE。
2. 找不到理想的乳腺癌专项指标也没关系，换一个通用癌症/健康指标即可，
   重点是 pipeline 的设计，不是数据本身。
"""

import requests
import json
from pathlib import Path
from datetime import datetime
from time import sleep

INDICATOR_CODE = "SA_0000001438"  # TODO: 换成你自己找到的指标代码
BASE_URL = f"https://ghoapi.azureedge.net/api/{INDICATOR_CODE}"
RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"


def fetch_with_retry(url: str, max_retries: int = 3) -> dict:
    """带指数退避的请求，避免偶发网络问题直接让脚本失败"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"[fetch] attempt {attempt + 1} failed: {e}, retrying in {wait}s...")
            sleep(wait)


def save_raw(data: dict) -> Path:
    """原始数据先落盘，不直接进清洗流程"""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DATA_DIR / f"{INDICATOR_CODE}_{timestamp}.json"
    filepath.write_text(json.dumps(data, indent=2))
    print(f"[fetch] saved raw data to {filepath}")
    return filepath


if __name__ == "__main__":
    print(f"[fetch] requesting {BASE_URL}")
    data = fetch_with_retry(BASE_URL)
    record_count = len(data.get("value", []))
    print(f"[fetch] received {record_count} records")
    save_raw(data)
