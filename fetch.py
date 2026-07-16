"""
fetch.py
Fetch raw data for specified health indicators from the WHO GHO OData API and save it as a local JSON file.

Design decisions:
1. Store raw JSON before cleaning, rather than processing it immediately upon retrieval
   — this facilitates debugging and allows for re-running the cleaning logic without needing to call the API again.
2. Use `raise_for_status()` to surface errors early to the "fail-fast" principle instead of silently passing empty or error responses to the next stage.
3. Implemented simple exponential backoff retries to simulate real-world network instability.
4. If the volume of metric data were large I would implement pagination and rate limiting in a production environment.

使用前：
1. Go to https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'breast')
   Find the IndicatorCode you need (the specific indicator for breast cancer) and enter it into the INDICATOR_CODE field below.
"""

import requests
import json
from pathlib import Path
from datetime import datetime
from time import sleep

INDICATOR_CODE = "SA_0000001438"  
BASE_URL = f"https://ghoapi.azureedge.net/api/{INDICATOR_CODE}"
RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"


def fetch_with_retry(url: str, max_retries: int = 3) -> dict:
    """Requests with exponential backoff to prevent the script from failing immediately due to occasional network issues."""
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
    """Raw data is first saved as local JSON and does not go directly into the cleaning process."""
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
