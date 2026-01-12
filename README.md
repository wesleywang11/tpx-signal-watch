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

Bullish_Divergence_finder.py:
This script scans a stock watchlist and detects daily bullish MACD divergence.
Logic
A stock is flagged if both conditions are met:
Price condition
The current candle makes the lowest low within the last N bars (default: 10)
Momentum condition
The MACD histogram is rising compared to its previous minimum
Indicates weakening downside momentum
In short:
Price makes a new local low, but MACD histogram fails to confirm it.

3_lines_method.py:
Three-Track Reversal Strategy Monitor
A long-running technical scanner for Tokyo Stock Exchange stocks, designed to detect oversold → momentum reversal → trend confirmation using a three-stage state machine.
What This Script Does
The program continuously monitors a predefined watchlist during TSE trading hours and sends a push notification when all three technical conditions align.
It is meant to run 24/5 on a server (e.g. Raspberry Pi, VPS).
Strategy Logic (Three Tracks)
A stock triggers a BUY signal only when all three tracks occur in order:
Track 1 – Bollinger Band Touch
Price touches or pierces the -2σ lower Bollinger Band
Interpreted as a short-term oversold condition
Track 2 – RSI Reversal
RSI(14) was below 30
RSI breaks back above 30
Signals momentum turning up
Track 3 – MACD Confirmation
Either:
MACD golden cross (DIF crosses above DEA), or
MACD histogram turns from negative to positive
When Track 3 is confirmed → BUY SIGNAL
