VALID_SOURCES = {"kalshi", "polymarket", "sportsbook"}


def _is_valid(market: dict) -> tuple[bool, str]:
    if not isinstance(market, dict):
        return False, "not a dict"

    if market.get("source") not in VALID_SOURCES:
        return False, f"unknown source: {market.get('source')}"

    if not market.get("title"):
        return False, "missing title"

    yes = market.get("yes")
    no  = market.get("no")

    if not isinstance(yes, (int, float)) or not isinstance(no, (int, float)):
        return False, "yes/no must be numeric"

    if not (0 < yes < 1):
        return False, f"yes={yes} out of range (0, 1)"

    if not (0 < no < 1):
        return False, f"no={no} out of range (0, 1)"

    return True, ""


def normalize(markets: list[dict]) -> list[dict]:
    cleaned  = []
    rejected = 0

    for market in markets:
        valid, reason = _is_valid(market)

        if not valid:
            rejected += 1
            continue

        cleaned.append({
            "id":         str(market.get("id", "")),
            "title":      market["title"].strip(),
            "source":     market["source"],
            "yes":        round(float(market["yes"]), 4),
            "no":         round(float(market["no"]), 4),
            "category":   str(market.get("category", "")).lower().strip(),
            "close_time": str(market.get("close_time", "")),
        })

    if rejected:
        print(f"  [normalizer] Rejected {rejected} invalid markets.")

    return cleaned


def normalize_all(
    kalshi:     list[dict],
    polymarket: list[dict],
    sportsbook: list[dict]
) -> list[dict]:
    
    all_markets = (
        normalize(kalshi) +
        normalize(polymarket) +
        normalize(sportsbook)
    )

    print(f"[normalizer] {len(kalshi)} kalshi + {len(polymarket)} polymarket "
          f"+ {len(sportsbook)} sportsbook = {len(all_markets)} total clean markets")

    return all_markets