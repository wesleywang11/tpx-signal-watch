ONE-GULP STRATEGY MONITOR
Underwater Breakout Pullback Detection System

STRATEGY OVERVIEW:
The "One-Gulp" strategy (一口战法) is a MACD-based technical analysis approach 
that captures high-probability entry points after underwater golden crosses. 
It identifies stocks that have built momentum below the zero line and are 
now pulling back after breaking out, offering optimal risk-reward entries.

SIGNAL LOGIC (4-Stage State Machine):


Stage 0:  Waiting for Setup
          Scanning for underwater golden cross (DEA < DIF < 0)

Stage 1:  Underwater Golden Cross Confirmed
          Waiting for DIF to break above zero line
          Reset if: DIF crosses below DEA (death cross)

Stage 2:  DIF Breakthrough Confirmed
          Waiting for DEA to break above zero line
          Reset if: DIF drops below zero

Stage 3: Both Lines Above Zero - Tracking Mode
          • Track maximum DIF value since DEA crossed zero
          • Alert when DEA retraces to 50% of peak DIF
          • One alert per day to avoid spam
Reset if: DIF drops below zero (new cycle begins)

WHY IT WORKS:
1. Underwater GC shows accumulation phase with reduced selling pressure
2. Double zero-line breakout confirms strong momentum shift
3. 50% retracement provides optimal entry with defined risk
4. Historical validation: captures "gulp" of profit in single move

TECHNICAL SPECIFICATIONS:
- Timeframe: 15-minute candles
- Lookback: 1 month of historical data
- MACD Parameters: EMA(12), EMA(26), Signal(9)
- Trigger: DEA ≤ 50% of peak DIF in Stage 3
- Alert Frequency: Maximum once per day per ticker

Author: Trading System Developer
Version: 4.0 - Enhanced Stage Detection with Historical Peak Tracking
Market: Tokyo Stock Exchange (TSE)
