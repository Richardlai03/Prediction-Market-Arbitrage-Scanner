from rapidfuzz import fuzz

DEFAULT_THRESHOLD = 80  # minimum similarity score (0-100) to count as a match


def _similarity(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(a.lower(), b.lower())


def _find_matches(
    query:      dict,
    candidates: list[dict],
    threshold:  int
) -> list[dict]:

    results = []
    for candidate in candidates:
        score = _similarity(query["title"], candidate["title"])
        if score >= threshold:
            results.append((score, candidate))

    results.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in results]


def match_markets(
    all_markets: list[dict],
    threshold:   int = DEFAULT_THRESHOLD
) -> list[dict]:

    # Split by source
    kalshi     = [m for m in all_markets if m["source"] == "kalshi"]
    polymarket = [m for m in all_markets if m["source"] == "polymarket"]
    sportsbook = [m for m in all_markets if m["source"] == "sportsbook"]

    matched_poly   = set()
    matched_sports = set()
    groups         = []

    # Pass 1: Kalshi as anchor, search poly and sportsbook
    for km in kalshi:
        group_markets = [km]

        poly_matches   = _find_matches(km, polymarket, threshold)
        sports_matches = _find_matches(km, sportsbook, threshold)

        if poly_matches:
            best_poly = poly_matches[0]
            group_markets.append(best_poly)
            matched_poly.add(best_poly["id"])

        if sports_matches:
            best_sport = sports_matches[0]
            group_markets.append(best_sport)
            matched_sports.add(best_sport["id"])

        if len(group_markets) >= 2:
            groups.append({
                "title":   km["title"],
                "markets": group_markets
            })

    # Pass 2: Remaining Polymarket vs sportsbook (not already matched to Kalshi)
    remaining_poly = [m for m in polymarket if m["id"] not in matched_poly]

    for pm in remaining_poly:
        sports_matches = _find_matches(pm, sportsbook, threshold)

        if sports_matches:
            best_sport = sports_matches[0]
            if best_sport["id"] not in matched_sports:
                groups.append({
                    "title":   pm["title"],
                    "markets": [pm, best_sport]
                })
                matched_sports.add(best_sport["id"])

    print(f"[matcher] Found {len(groups)} cross-venue event matches "
          f"(threshold={threshold})")

    return groups