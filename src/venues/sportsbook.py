import os
import time
import requests

from dotenv import load_dotenv

load_dotenv()

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY  = os.getenv("ODDS_API_KEY")

# Sportsbooks to pull from, these three have the best liquidity
BOOKMAKERS = "draftkings,fanduel,betmgm"

SPORTS = [
    "americanfootball_nfl",
    "basketball_nba",
    "baseball_mlb",
    "icehockey_nhl",
    "soccer_epl",
    "soccer_uefa_champs_league",
    "soccer_fifa_world_cup",
    "soccer_usa_mls",
    "soccer_italy_serie_a",
]
MAX_RETRIES  = 3
BASE_BACKOFF = 1.0


def _get(path: str, params: dict = None) -> dict | list:
    url     = ODDS_API_BASE + path
    backoff = BASE_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            # Log remaining quota so we don't burn through free tier
            remaining = response.headers.get("x-requests-remaining", "?")
            used      = response.headers.get("x-requests-used", "?")
            print(f"  [sportsbook] Quota: {remaining} remaining / {used} used")
            return response.json()

        elif response.status_code == 429:
            print(f"  [sportsbook] Rate limited. Backing off {backoff:.1f}s "
                  f"(attempt {attempt}/{MAX_RETRIES})")
            time.sleep(backoff)
            backoff *= 2

        elif response.status_code == 401:
            raise EnvironmentError(
                "ODDS_API_KEY is invalid or missing. "
                "Check your .env file."
            )

        else:
            response.raise_for_status()

    raise RuntimeError(f"Sportsbook GET {path} failed after {MAX_RETRIES} retries.")


def _american_to_prob(odds: int) -> float:
    if odds >= 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def _remove_vig(p_yes: float, p_no: float) -> tuple[float, float]:
    total = p_yes + p_no
    return round(p_yes / total, 4), round(p_no / total, 4)


def _best_prices(event: dict) -> tuple[float | None, float | None]:
    yes_probs_raw = []
    no_probs_raw  = []

    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue

            outcomes = market.get("outcomes", [])
            if len(outcomes) < 2:
                continue

            p0 = _american_to_prob(outcomes[0]["price"])
            p1 = _american_to_prob(outcomes[1]["price"])
            yes_probs_raw.append(p0)
            no_probs_raw.append(p1)

    if not yes_probs_raw or not no_probs_raw:
        return None, None

    # Average across bookmakers then strip vig
    avg_yes = sum(yes_probs_raw) / len(yes_probs_raw)
    avg_no  = sum(no_probs_raw)  / len(no_probs_raw)

    return _remove_vig(avg_yes, avg_no)


def _normalize_event(event: dict, sport: str) -> dict | None:
    yes_price, no_price = _best_prices(event)

    if yes_price is None or no_price is None:
        return None

    if not (0 < yes_price < 1) or not (0 < no_price < 1):
        return None

    home = event.get("home_team", "")
    away = event.get("away_team", "")
    title = f"{away} vs {home}"

    return {
        "id":         event.get("id", ""),
        "title":      title,
        "source":     "sportsbook",
        "yes":        yes_price,
        "no":         no_price,
        "category":   sport,
        "close_time": event.get("commence_time", ""),
    }


def _fetch_sport(sport: str) -> list[dict]:
    print(f"  [sportsbook] Fetching {sport}...")

    try:
        data = _get(
            f"/sports/{sport}/odds",
            params={
                "apiKey":    ODDS_API_KEY,
                "regions":   "us",
                "markets":   "h2h",
                "bookmakers": BOOKMAKERS,
                "oddsFormat": "american",
            }
        )
    except requests.HTTPError as e:
        # 404 means sport is off-season, skip 
        if "404" in str(e):
            print(f"  [sportsbook] {sport} not available (off-season), skipping.")
            return []
        raise

    normalized = []
    for event in data:
        result = _normalize_event(event, sport)
        if result:
            normalized.append(result)

    print(f"  [sportsbook] {sport}: {len(normalized)} events")
    return normalized


def fetch_sportsbook_markets() -> list[dict]:
    if not ODDS_API_KEY:
        raise EnvironmentError(
            "ODDS_API_KEY not set in .env. "
            "Sign up at the-odds-api.com for a free key."
        )

    print("[sportsbook] Starting market fetch...")

    all_markets = []
    for sport in SPORTS:
        markets = _fetch_sport(sport)
        all_markets.extend(markets)
        time.sleep(0.5)  # be gentle with free tier quota

    print(f"[sportsbook] Done. {len(all_markets)} events total.\n")
    return all_markets


if __name__ == "__main__":
    markets = fetch_sportsbook_markets()

    if not markets:
        print("No markets returned. Check your ODDS_API_KEY and active sports seasons.")
    else:
        print(f"Sample markets (first 5 of {len(markets)}):\n")
        for i, m in enumerate(markets[:5], 1):
            print(f"{i}. {m['title']}")
            print(f"   yes={m['yes']:.4f}  no={m['no']:.4f}  category={m['category']}\n")