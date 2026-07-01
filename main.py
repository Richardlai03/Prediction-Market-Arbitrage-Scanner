import time
from src.venues.kalshi     import fetch_kalshi_markets
from src.venues.polymarket import fetch_polymarket_markets
from src.venues.sportsbook import fetch_sportsbook_markets
from src.core.normalizer   import normalize_all
from src.core.matcher      import match_markets
from src.core.arb_engine   import find_opportunities
from src.core.logger       import init_db, log_all

POLL_INTERVAL = 300  # seconds between full scans (5 minutes)


def run_scan(conn):
    print(f"\n{'='*60}")
    print(f"SCAN STARTED: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"{'='*60}\n")

    kalshi     = fetch_kalshi_markets()
    polymarket = fetch_polymarket_markets()
    sportsbook = fetch_sportsbook_markets()

    all_markets   = normalize_all(kalshi, polymarket, sportsbook)
    groups        = match_markets(all_markets)
    opportunities = find_opportunities(groups)

    if not opportunities:
        print("\nNo opportunities found this scan.")
        return

    logged = log_all(conn, opportunities)
    print(f"\nLogged {logged} opportunities to database.\n")

    print(f"{'─'*60}")
    print(f"{'RANK':<5} {'EDGE':>6} {'ROI':>6}  {'YES':>12} {'NO':>12}  TITLE")
    print(f"{'─'*60}")

    for i, opp in enumerate(opportunities, 1):
        print(
            f"{i:<5} "
            f"{opp['edge']:>5.1%} "
            f"{opp['roi']:>5.1%}  "
            f"{opp['yes_source']:>12} "
            f"{opp['no_source']:>12}  "
            f"{opp['title'][:50]}"
        )

    print(f"{'─'*60}")


def main():
    conn = init_db()
    print("Prediction Market Arbitrage Scanner")
    print(f"Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop.\n")

    while True:
        try:
            run_scan(conn)
        except Exception as e:
            print(f"\n[ERROR] Scan failed: {e}")

        print(f"\nNext scan in {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()