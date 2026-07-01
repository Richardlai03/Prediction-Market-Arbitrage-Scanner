FEES = {
    "kalshi":     0.07,
    "polymarket": 0.02,
    "sportsbook": 0.00,
}

MIN_EDGE = 0.005  # minimum net edge to flag (0.5%) — filters noise


def _fee_adjusted_cost(price: float, source: str) -> float:
    fee = FEES.get(source, 0.0)
    if fee == 0:
        return price
    return price / (1 - fee)


def _find_best_sides(markets: list[dict]) -> tuple[dict, dict]:
    best_yes = min(markets, key=lambda m: _fee_adjusted_cost(m["yes"], m["source"]))
    best_no  = min(markets, key=lambda m: _fee_adjusted_cost(m["no"],  m["source"]))
    return best_yes, best_no


def analyze_group(group: dict) -> dict | None:
    markets = group["markets"]

    if len(markets) < 2:
        return None

    best_yes, best_no = _find_best_sides(markets)

    # Don't count same-venue as arb — must be cross-venue
    if best_yes["source"] == best_no["source"]:
        return None

    yes_cost = _fee_adjusted_cost(best_yes["yes"], best_yes["source"])
    no_cost  = _fee_adjusted_cost(best_no["no"],   best_no["source"])

    total_cost = yes_cost + no_cost
    arb_raw    = 1 - (best_yes["yes"] + best_no["no"])
    edge       = 1 - total_cost
    roi        = edge / total_cost if total_cost > 0 else 0

    if edge < MIN_EDGE:
        return None

    return {
        "title":      group["title"],
        "yes_source": best_yes["source"],
        "no_source":  best_no["source"],
        "yes_price":  best_yes["yes"],
        "no_price":   best_no["no"],
        "yes_cost":   round(yes_cost, 4),
        "no_cost":    round(no_cost, 4),
        "arb_raw":    round(arb_raw, 4),
        "edge":       round(edge, 4),
        "roi":        round(roi, 4),
        "markets":    markets,
    }


def find_opportunities(groups: list[dict]) -> list[dict]:
    opportunities = []

    for group in groups:
        result = analyze_group(group)
        if result:
            opportunities.append(result)

    opportunities.sort(key=lambda x: x["edge"], reverse=True)

    print(f"[arb_engine] {len(opportunities)} opportunities found "
          f"(edge > {MIN_EDGE:.1%}) out of {len(groups)} matched groups")

    return opportunities