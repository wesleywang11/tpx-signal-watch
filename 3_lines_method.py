# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
import requests
import time
import sys
from datetime import datetime

# ================= CONFIGURATION =================

# Watchlist: Tokyo Stock Exchange stocks
WATCH_LIST = [
    "6723.T", "9432.T", "7011.T", "7203.T", "8058.T", "8306.T", "9501.T", "285A.T", 
    "6758.T", "9434.T", "2760.T", "9984.T", "8035.T", "9503.T", "4324.T", "9433.T", 
    "7272.T", "6367.T", "6146.T", "6269.T", "6501.T", "8316.T", "5706.T", "5016.T", 
    "7974.T", "7013.T", "4063.T", "4502.T", "6762.T", "6361.T", "6503.T", "8053.T", 
    "7267.T", "6981.T", "6702.T", "8002.T", "4568.T", "9502.T", "1911.T", "5802.T"
]
BARK_KEY = "****************"
CHECK_INTERVAL = 120

# Three Track Parameters
BOLL_PERIOD = 20      # Bollinger Bands period
BOLL_STD = 2          # Standard deviation multiplier
RSI_PERIOD = 14       # RSI period
RSI_OVERSOLD = 30     # RSI oversold threshold

# State machine for each ticker
ticker_states = {
    ticker: {
        "stage": 0,              # 0=Waiting, 1=Touched, 2=Reversed, 3=Confirmed
        "touch_date": None,      # Date when touched lower band
        "rsi_min": 100,          # Minimum RSI value in stage 1
        "alert_date": None,      # Last alert date
        "stage_history": []      # Track stage transitions
    } for ticker in WATCH_LIST
}

# =================================================

def is_market_open():
    """Check if Tokyo Stock Exchange is currently open."""
    now = datetime.now()
    if now.weekday() >= 5:
        return False, "Weekend"
    
    current_time = now.strftime("%H:%M")
    if "09:00" <= current_time <= "11:30": 
        return True, "Morning_Session"
    if "11:30" < current_time < "12:30": 
        return False, "Lunch_Break"
    if "12:30" <= current_time <= "15:30": 
        return True, "Afternoon_Session"
    
    return False, "Market_Closed"

def calculate_rsi(series, period=14):
    """Calculate RSI indicator"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def track1_touch_lower_band(df):
    """
    Track 1: Touch Bollinger Lower Band
    Check if price pierces -2sigma lower band (oversold warning)
    
    Returns: (is_touched, price, lower_band, status_text)
    """
    try:
        close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        low = df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low']
        
        # Calculate Bollinger Bands
        sma = close.rolling(window=BOLL_PERIOD).mean()
        std = close.rolling(window=BOLL_PERIOD).std()
        lower_band = sma - (BOLL_STD * std)
        
        current_price = float(close.iloc[-1])
        current_low = float(low.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        
        # Check if price touched or pierced lower band
        is_touched = current_low <= current_lower
        
        distance_pct = ((current_price - current_lower) / current_lower) * 100
        
        if is_touched:
            status = f"OK_Touched_Price={current_price:.2f}_Band={current_lower:.2f}"
        else:
            status = f"Above_Band_{distance_pct:.1f}%"
        
        return is_touched, current_price, current_lower, status
    
    except Exception as e:
        return False, 0, 0, f"Error_{str(e)[:30]}"

def track2_rsi_reversal(df):
    """
    Track 2: RSI Momentum Reversal
    Check if RSI breaks above 30 from oversold zone (<30)
    
    Returns: (is_reversed, current_rsi, rsi_min, status_text)
    """
    try:
        close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        
        # Calculate RSI
        rsi = calculate_rsi(close, RSI_PERIOD)
        
        current_rsi = float(rsi.iloc[-1])
        prev_rsi = float(rsi.iloc[-2])
        
        # Find minimum RSI in recent period (last 10 bars)
        recent_rsi_min = float(rsi.iloc[-10:].min())
        
        # Reversal condition: was below 30, now breaking above 30
        is_reversed = (prev_rsi < RSI_OVERSOLD) and (current_rsi >= RSI_OVERSOLD)
        
        # Also track if currently in oversold zone
        in_oversold = current_rsi < RSI_OVERSOLD
        
        if is_reversed:
            status = f"OK_Reversed_RSI={current_rsi:.1f}_from_{recent_rsi_min:.1f}"
        elif in_oversold:
            status = f"InOversold_RSI={current_rsi:.1f}"
        else:
            status = f"RSI={current_rsi:.1f}"
        
        return is_reversed, current_rsi, recent_rsi_min, status
    
    except Exception as e:
        return False, 0, 0, f"Error_{str(e)[:30]}"

def track3_macd_golden_cross(df):
    """
    Track 3: MACD Golden Cross
    Check if MACD shows golden cross and histogram turning red (positive)
    
    Returns: (is_golden_cross, dif, dea, histogram, status_text)
    """
    try:
        close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        
        # Calculate MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        histogram = dif - dea
        
        current_dif = float(dif.iloc[-1])
        current_dea = float(dea.iloc[-1])
        current_hist = float(histogram.iloc[-1])
        prev_hist = float(histogram.iloc[-2])
        
        # Golden cross: DIF crosses above DEA
        prev_dif = float(dif.iloc[-2])
        prev_dea = float(dea.iloc[-2])
        
        is_golden_cross = (prev_dif <= prev_dea) and (current_dif > current_dea)
        
        # Also check if histogram is turning from green (negative) to red (positive)
        histogram_turning_red = (prev_hist < 0) and (current_hist >= 0)
        
        # Either condition is good
        is_confirmed = is_golden_cross or histogram_turning_red
        
        if is_golden_cross:
            status = f"OK_GoldenCross_DIF={current_dif:.3f}>DEA={current_dea:.3f}"
        elif histogram_turning_red:
            status = f"OK_HistRed_Hist={current_hist:.3f}"
        elif current_dif > current_dea:
            status = f"Above_DIF={current_dif:.3f}>DEA={current_dea:.3f}"
        else:
            status = f"Below_DIF={current_dif:.3f}<DEA={current_dea:.3f}"
        
        return is_confirmed, current_dif, current_dea, current_hist, status
    
    except Exception as e:
        return False, 0, 0, 0, f"Error_{str(e)[:30]}"

def analyze_three_tracks(ticker):
    """
    Main Three-Track Strategy State Machine
    
    Stage 0 (Waiting): Looking for oversold signal
    Stage 1 (Touched): Price touched lower band, waiting for RSI reversal
    Stage 2 (Reversed): RSI reversed, waiting for MACD golden cross
    Stage 3 (Confirmed): All three tracks aligned -> BUY SIGNAL!
    
    Returns: (stage, status_text, should_alert)
    """
    global ticker_states
    
    try:
        # Download daily data (for more stable signals)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        
        if df.empty or len(df) < 50:
            return 0, "Insufficient_Data", False
        
        state = ticker_states[ticker]
        today = datetime.now().date()
        current_stage = state["stage"]
        
        # Analyze all three tracks
        touched, price, lower_band, track1_status = track1_touch_lower_band(df)
        reversed, rsi, rsi_min, track2_status = track2_rsi_reversal(df)
        confirmed, dif, dea, hist, track3_status = track3_macd_golden_cross(df)
        
        # ========== STATE MACHINE LOGIC ==========
        
        # Stage 0 -> Stage 1: Touch lower band
        if current_stage == 0:
            if touched:
                state["stage"] = 1
                state["touch_date"] = today
                state["rsi_min"] = rsi
                state["stage_history"].append(f"S1_{today}")
                status = f"S1_Touched | {track1_status} | {track2_status} | {track3_status}"
                return 1, status, False
            else:
                status = f"S0_Waiting | {track1_status} | {track2_status} | {track3_status}"
                return 0, status, False
        
        # Stage 1 -> Stage 2: RSI reversal (break above 30)
        elif current_stage == 1:
            # Track minimum RSI while in stage 1
            if rsi < state["rsi_min"]:
                state["rsi_min"] = rsi
            
            # Check for reversal
            if reversed:
                state["stage"] = 2
                state["stage_history"].append(f"S2_{today}")
                status = f"S2_Reversed | {track1_status} | {track2_status} | {track3_status}"
                return 2, status, False
            
            # Timeout: if more than 10 days since touch and no reversal, reset
            if state["touch_date"] and (today - state["touch_date"]).days > 10:
                state["stage"] = 0
                state["rsi_min"] = 100
                state["stage_history"].clear()
                status = f"S0_Reset_Timeout | {track1_status} | {track2_status} | {track3_status}"
                return 0, status, False
            
            status = f"S1_WaitRSI | {track1_status} | {track2_status} | {track3_status}"
            return 1, status, False
        
        # Stage 2 -> Stage 3: MACD golden cross
        elif current_stage == 2:
            if confirmed:
                state["stage"] = 3
                state["stage_history"].append(f"S3_{today}")
                
                # Send alert only once per day
                if state["alert_date"] != today:
                    state["alert_date"] = today
                    status = f"***S3_BUY_SIGNAL*** | {track1_status} | {track2_status} | {track3_status}"
                    return 3, status, True
                else:
                    status = f"S3_Already_Alerted | {track1_status} | {track2_status} | {track3_status}"
                    return 3, status, False
            
            # Timeout: if more than 15 days since RSI reversal, reset
            if len(state["stage_history"]) >= 2:
                s2_date_str = state["stage_history"][-1].split("_")[1]
                s2_date = datetime.strptime(s2_date_str, "%Y-%m-%d").date()
                if (today - s2_date).days > 15:
                    state["stage"] = 0
                    state["rsi_min"] = 100
                    state["stage_history"].clear()
                    status = f"S0_Reset_Timeout | {track1_status} | {track2_status} | {track3_status}"
                    return 0, status, False
            
            status = f"S2_WaitMACD | {track1_status} | {track2_status} | {track3_status}"
            return 2, status, False
        
        # Stage 3: Monitor position (can add exit logic here)
        elif current_stage == 3:
            # Auto reset after 5 days to look for next opportunity
            if state["alert_date"] and (today - state["alert_date"]).days > 5:
                state["stage"] = 0
                state["rsi_min"] = 100
                state["stage_history"].clear()
                status = f"S0_Reset_NewCycle | {track1_status} | {track2_status} | {track3_status}"
                return 0, status, False
            
            status = f"S3_InPosition | {track1_status} | {track2_status} | {track3_status}"
            return 3, status, False
        
        return 0, "Unknown_Stage", False
    
    except Exception as e:
        return 0, f"Critical_Error_{type(e).__name__}_{str(e)[:30]}", False

def run_radar():
    """Main monitoring loop"""
    print("=" * 100)
    print(" Three-Track Reversal Strategy Monitor")
    print(" Track 1: Touch -2sigma Band | Track 2: RSI Break 30 | Track 3: MACD Golden Cross")
    print("=" * 100)
    print("\n Strategy Logic:")
    print("  S0: Waiting for oversold signal")
    print("  S1: Price touched lower Bollinger band -> Monitor RSI")
    print("  S2: RSI reversed from <30 to >30 -> Wait for MACD")
    print("  S3: MACD golden cross -> *** BUY SIGNAL ***")
    print("=" * 100)
    
    while True:
        open_status, status_msg = is_market_open()
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not open_status:
            sys.stdout.write(f"\r[{current_time_str}] {status_msg}... Sleeping ")
            sys.stdout.flush()
            time.sleep(600)
            continue
        
        print(f"\n[{current_time_str}] {status_msg} - Scanning Watchlist...")
        print("-" * 100)
        
        # Track alerts
        alert_list = []
        
        # Scan each ticker
        for ticker in WATCH_LIST:
            sys.stdout.write(f"  {ticker:8s} | ")
            sys.stdout.flush()
            
            stage, status_text, is_triggered = analyze_three_tracks(ticker)
            
            # Display with stage indicator
            if stage == 3:
                prefix = "[***]"
            elif stage == 2:
                prefix = "[>>]"
            elif stage == 1:
                prefix = "[!]"
            else:
                prefix = "[ ]"
            
            print(f"{prefix} {status_text}")
            
            # Collect alerts
            if is_triggered:
                alert_list.append((ticker, status_text))
        
        # Send push notifications
        if alert_list:
            print("\n" + "=" * 100)
            for ticker, msg in alert_list:
                try:
                    bark_msg = f"{ticker}_Three_Track_Buy_Signal"
                    detail = f"Bollinger_Touch->RSI_Reversal->MACD_GoldenCross"
                    url = f"https://api.day.app/{BARK_KEY}/{bark_msg}/{detail}"
                    requests.get(url, timeout=5)
                    print(f"  !!! [ALERT SENT] {ticker} - THREE TRACKS CONFIRMED !!!")
                except:
                    print(f"  !!! [ALERT FAILED] {ticker} !!!")
            print("=" * 100)
        
        print(f"\nNext scan in {CHECK_INTERVAL} seconds...")
        print("-" * 100)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        run_radar()
    except KeyboardInterrupt:
        print("\n\nProcess stopped by user")
    except Exception as e:
        print(f"\nCritical error: {e}")
        import traceback
        traceback.print_exc()