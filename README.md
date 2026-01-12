MACD_full_breakout_watcher.py:
A real-time MACD monitoring script for Tokyo Stock Exchange stocks.
It tracks a full MACD recovery cycle from below zero and sends a single alert when momentum clearly cools down after a confirmed breakout.
Core Logic: 
Data: 15-minute candles, MACD(12, 26, 9)
Market hours only (TSE)
The script follows a 4-stage MACD state machine:
Stage 0 – Waiting
No valid setup yet
Stage 1 – Underwater Golden Cross
DEA < DIF < 0
Stage 2 – DIF crosses above zero
DIF > 0 , DEA < 0
Stage 3 – Full breakout
DIF > 0 , DEA > 0
Track the maximum DIF peak

Alert Condition (When You Get a Notification)
A push notification is sent only if all are true:
The stock has reached Stage 3
DEA retraces to ≤ 50% of the peak DIF
No alert has been sent for this ticker today
If DIF drops below zero again, the entire state resets.

Push Notification
Platform: iOS
App required: Bark
Delivery: HTTP push via api.day.app
Install Bark on your iPhone, get your personal key, and set it as BARK_KEY in the script.

rsi_macd_low_finder.py:
RSI + MACD Scanner
This script scans a predefined list of Tokyo Stock Exchange stocks and flags tickers that meet a specific technical condition on the latest trading day.
Logic:
A stock is selected if both conditions are true:
RSI(14) < 40
→ The stock has shown recent weakness.
MACD bullish crossover (DIF > DEA)
→ Downward momentum may be slowing.
In plain terms, it looks for stocks that are recently weak but may be starting a short-term rebound.


