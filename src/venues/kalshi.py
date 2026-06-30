import os
import time
import requests

from dotenv import load_dotenv
from src.venues.kalshi_auth import build_headers

load_dotenv()

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
MAX_RETRIES = 3       # number of retry attempts on 429 or network error
BASE_BACKOFF = 1.0    # starting backoff in seconds; doubles each retry
PAGE_LIMIT   = 100    # markets per page (Kalshi max is 100)

def _get(path: str, params: dict = None) -> dict:
    url     = BASE_URL + path.replace("/trade-api/v2", "")
    backoff = BASE_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):
        headers  = build_headers(method="GET", path=path)
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429:
            # Rate limited, wait and retry with exponential backoff
            print(f"  [kalshi] Rate limited (429). "
                  f"Backing off {backoff:.1f}s (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(backoff)
            backoff *= 2
            continue

        else:
            # Any other error is unrecoverable, raise immediately
            response.raise_for_status()

    raise RuntimeError(
        f"Kalshi GET {path} failed after {MAX_RETRIES} retries."
    )

def _fetch_all_open_markets() -> list[dict]:
    all_markets = []
    cursor      = None
    page        = 1

    while True:
        params = {
            "limit":                100,
            "status":               "open",
            "with_nested_markets":  "true"
        }
        if cursor:
            params["cursor"] = cursor

        print(f"  [kalshi] Fetching page {page}...")
        data   = _get("/trade-api/v2/events", params=params)
        events = data.get("events", [])

        for event in events:
            for market in event.get("markets", []):
                market["category"] = event.get("category", "")
                all_markets.append(market)

        if len(events) < 100:
            break

        cursor = data.get("cursor")
        if not cursor:
            break

        page += 1

    print(f"  [kalshi] Found {len(all_markets)} markets across {page} pages.")
    return all_markets

def _extract_prices(market: dict) -> tuple[float | None, float | None]:
    yes_ask = market.get("yes_ask_dollars")
    no_ask  = market.get("no_ask_dollars")

    if yes_ask is None or no_ask is None:
        return None, None

    return round(float(yes_ask), 4), round(float(no_ask), 4)

def _normalize_market(market: dict) -> dict | None:
    yes_price, no_price = _extract_prices(market)

    # Skip illiquid markets
    if yes_price is None or no_price is None:
        return None

    # Skip markets with invalid prices
    if not (0 < yes_price < 1) or not (0 < no_price < 1):
        return None

    return {
        "id":         market.get("ticker", ""),
        "title":      market.get("title", ""),
        "source":     "kalshi",
        "yes":        yes_price,
        "no":         no_price,
        "category":   market.get("category", ""),
        "close_time": market.get("close_time", ""),
    }

def fetch_kalshi_markets() -> list[dict]:
    print("[kalshi] Starting market fetch...")

    raw_markets = _fetch_all_open_markets()

    normalized = []
    skipped    = 0

    for market in raw_markets:
        result = _normalize_market(market)
        if result:
            normalized.append(result)
        else:
            skipped += 1

    print(f"[kalshi] Done. {len(normalized)} markets with liquidity, "
          f"{skipped} skipped (no liquidity or invalid prices).\n")

    return normalized

if __name__ == "__main__":
    markets = fetch_kalshi_markets()

    if not markets:
        print("No markets returned. Check your API key and private key setup.")
    else:
        print(f"Sample markets (first 5 of {len(markets)}):\n")
        for i, m in enumerate(markets[:5], 1):
            print(f"{i}. {m['title']}")
            print(f"   yes={m['yes']:.4f}  no={m['no']:.4f}  "
                  f"category={m['category']}\n")