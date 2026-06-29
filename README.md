# Prediction Market Arbitrage Scanner

Real time arbitrage scanner that monitors Polymarket, Kalshi, and major 
sportsbooks for mispricings in implied probabilities across the same 
real world event.

## What It Does

- Pulls live market prices from Polymarket (CLOB API), Kalshi (REST API), 
  and sportsbooks (The Odds API)
- Normalizes all formats to implied probability, stripping sportsbook vig 
  via fair-odds decomposition
- Matches the same event across venues using fuzzy string normalization
- Flags positive-EV opportunities where fee-adjusted cost of buying both 
  sides is less than $1.00
- Logs all flagged opportunities to SQLite for historical calibration analysis
- Measures per-venue Brier scores and plots calibration curves to identify 
  systematic mispricings

## Math

For venues quoting American odds, implied probability is:

  p = 100 / (odds + 100)        for positive odds
  p = |odds| / (|odds| + 100)   for negative odds

Vig is stripped via fair-odds decomposition:

  p_yes_fair = p_yes_raw / (p_yes_raw + p_no_raw)

Arbitrage condition (fee-adjusted):

  edge = 1 - [p_yes_best * (1 + f_yes)] - [p_no_best * (1 + f_no)]

Opportunities are ranked by ROI = edge / cost.

## Setup

  git clone https://github.com/YOUR_USERNAME/prediction-market-arb-scanner
  
  cd prediction-market-arb-scanner
  
  python -m venv venv && source venv/bin/activate
  
  pip install -r requirements.txt
  
  cp .env.example .env   # add your API keys

## Stack

Python, Kalshi REST API, Polymarket CLOB API, The Odds API, 
SQLite, pandas, rapidfuzz, matplotlib
