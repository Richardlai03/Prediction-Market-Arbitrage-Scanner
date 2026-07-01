import time
import requests

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

MAX_RETRIES  = 3
BASE_BACKOFF = 1.0
PAGE_LIMIT   = 100


def _get(base_url: str, path: str, params: dict = None) -> dict | list:
    url     = base_url + path
    backoff = BASE_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429:
            print(f"  [polymarket] Rate limited. Backing off {backoff:.1f}s "
                  f"(attempt {attempt}/{MAX_RETRIES})")
            time.sleep(backoff)
            backoff *= 2

        else:
            response.raise_for_status()

    raise RuntimeError(f"Polymarket GET {path} failed after {MAX_RETRIES} retries.")


def _fetch_all_open_markets() -> list[dict]:
    all_markets = []
    offset      = 0
    page        = 1
    MAX_OFFSET  = 2000  # API throws 422 beyond this

    while offset <= MAX_OFFSET:
        print(f"  [polymarket] Fetching page {page}...")
        params = {
            "limit":    PAGE_LIMIT,
            "offset":   offset,
            "active":   "true",
            "closed":   "false",
            "archived": "false",
        }

        data = _get(GAMMA_BASE, "/markets", params=params)

        if not isinstance(data, list) or not data:
            break

        all_markets.extend(data)

        if len(data) < PAGE_LIMIT:
            break

        offset += PAGE_LIMIT
        page   += 1

    print(f"  [polymarket] Found {len(all_markets)} markets total.")
    return all_markets

def _normalize_market(market: dict) -> dict | None:
    # Use bestAsk directly, no CLOB call needed
    yes_price = market.get("bestAsk")
    
    # outcomePrices is a list ["yes_price", "no_price"] as strings
    outcome_prices = market.get("outcomePrices")

    if yes_price is None and outcome_prices:
        try:
            yes_price = float(outcome_prices[0])
        except (ValueError, IndexError):
            return None

    if yes_price is None:
        return None

    try:
        yes_price = round(float(yes_price), 4)
        no_price  = round(1 - yes_price, 4)
    except (ValueError, TypeError):
        return None

    if not (0 < yes_price < 1):
        return None

    return {
        "id":         market.get("slug", str(market.get("id", ""))),
        "title":      market.get("question", ""),
        "source":     "polymarket",
        "yes":        yes_price,
        "no":         no_price,
        "category":   "",
        "close_time": market.get("endDateIso", ""),
    }

def fetch_polymarket_markets() -> list[dict]:
    print("[polymarket] Starting market fetch...")

    raw_markets = _fetch_all_open_markets()

    normalized = []
    skipped    = 0

    for i, market in enumerate(raw_markets):
        result = _normalize_market(market)
        if result:
            normalized.append(result)
        else:
            skipped += 1

        # Progress update every 50 markets
        if (i + 1) % 50 == 0:
            print(f"  [polymarket] Processed {i + 1}/{len(raw_markets)}...")

    print(f"[polymarket] Done. {len(normalized)} markets with liquidity, "
          f"{skipped} skipped.\n")

    return normalized


if __name__ == "__main__":
    markets = fetch_polymarket_markets()

    if not markets:
        print("No markets returned.")
    else:
        print(f"Sample markets (first 5 of {len(markets)}):\n")
        for i, m in enumerate(markets[:5], 1):
            print(f"{i}. {m['title']}")
            print(f"   yes={m['yes']:.4f}  no={m['no']:.4f}  category={m['category']}\n")