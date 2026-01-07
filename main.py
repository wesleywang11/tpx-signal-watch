# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import requests
import time
import sys
from datetime import datetime

# ================= CONFIGURATION =================
# Watchlist: 13 stocks from Tokyo Stock Exchange
WATCH_LIST = [
    "6723.T", "9432.T", "7011.T", "7203.T", "8058.T", 
    "8306.T", "9501.T", "285A.T", "6758.T", "9434.T", 
    "2760.T", "9984.T", "8035.T"
]
BARK_KEY = "***********************"  # Push notification service key
CHECK_INTERVAL = 120  # Check every 120 seconds

# State Dictionary: 4-stage state machine for each ticker
ticker_states = {
    ticker: {
        "stage": None,           # None=Need initialization, 0-3=Active stages
        "max_dif": 0.0,          # Peak DIF value in stage 3
        "alert_date": None,      # Last alert date (prevent duplicate alerts on same day)
        "stage1_confirmed": False,  # Mark if we've seen underwater GC in this cycle
        "stage2_confirmed": False,  # Mark if we've seen DIF>0 in this cycle
    } for ticker in WATCH_LIST
}
# =================================================

def is_market_open():
    """
    Check if Tokyo Stock Exchange is currently open.
    Returns: (bool: is_open, str: status_message)
    """
    now = datetime.now()
    if now.weekday() >= 5: 
        return False, "Weekend"
    
    current_time = now.strftime("%H:%M")
    # Tokyo Stock Exchange trading hours (JST)
    if "09:00" <= current_time <= "11:30": 
        return True, "Morning_Session"
    if "11:30" < current_time < "12:30": 
        return False, "Lunch_Break"
    if "12:30" <= current_time <= "15:30": 
        return True, "Afternoon_Session"
    
    return False, "Market_Closed"

def detect_current_stage(current_dif, current_dea, dif_series, dea_series):
    """
    Detect which stage the ticker should be in based on current conditions.
    This is used for initial stage determination when program starts.
    
    Returns: (detected_stage, historical_max_dif)
    """
    # Check if both DIF and DEA are above zero
    if current_dif > 0 and current_dea > 0:
        # Check historical data to confirm underwater GC happened
        # Look back to find if there was a period where DEA < DIF < 0
        underwater_gc_found = False
        dif_crossed_zero_idx = None
        
        for i in range(len(dif_series) - 1, max(0, len(dif_series) - 100), -1):
            dif_val = dif_series.iloc[i]
            dea_val = dea_series.iloc[i]
            
            # If we go back to negative territory
            if dif_val < 0:
                if dea_val < dif_val:  # Found underwater GC
                    underwater_gc_found = True
                break
            
            # Track if DIF crossed zero from below
            if i > 0 and dif_series.iloc[i-1] < 0 and dif_val > 0:
                dif_crossed_zero_idx = i
        
        # If both conditions met, we're in Stage 3
        if underwater_gc_found and dif_crossed_zero_idx is not None:
            # Find max DIF from the point where both lines crossed zero
            # Find when DEA crossed zero
            dea_crossed_zero_idx = None
            for i in range(dif_crossed_zero_idx, len(dea_series)):
                if dea_series.iloc[i] > 0:
                    dea_crossed_zero_idx = i
                    break
            
            # Calculate max DIF from DEA zero cross to now
            if dea_crossed_zero_idx is not None:
                max_dif = dif_series.iloc[dea_crossed_zero_idx:].max()
                return 3, float(max_dif)
            else:
                return 2, 0.0  # DEA hasn't crossed yet
        else:
            return 0, 0.0  # Direct bullish without underwater setup
    
    # Check if DIF > 0 but DEA < 0 (Stage 2 territory)
    elif current_dif > 0 and current_dea < 0:
        # Check if there was underwater GC before
        for i in range(len(dif_series) - 1, max(0, len(dif_series) - 100), -1):
            dif_val = dif_series.iloc[i]
            dea_val = dea_series.iloc[i]
            if dif_val < 0 and dea_val < dif_val:
                return 2, 0.0  # Found underwater GC, now in Stage 2
        return 0, 0.0  # No underwater setup found
    
    # Check for underwater golden cross (Stage 1)
    elif current_dea < current_dif < 0:
        return 1, 0.0
    
    # Default: waiting for setup
    return 0, 0.0

def get_mac_status(ticker):
    """
    Analyze MACD status using 4-stage state machine.
    
    Stage 0: Waiting for underwater golden cross (DEA < DIF < 0)
    Stage 1: Underwater GC confirmed, waiting for DIF > 0
    Stage 2: DIF > 0, waiting for DEA > 0
    Stage 3: Both above zero, track DIF peak and alert on 50% DEA retracement
    
    Returns: (str: status_text, bool: should_alert)
    """
    global ticker_states
    try:
        # Download 1 month of 15-minute candle data
        df = yf.download(ticker, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 30:
            return "Data_Insufficient", False

        # Calculate MACD indicators
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        ema12 = close_series.ewm(span=12, adjust=False).mean()
        ema26 = close_series.ewm(span=26, adjust=False).mean()
        dif_series = ema12 - ema26  # DIF line
        dea_series = dif_series.ewm(span=9, adjust=False).mean()  # DEA is 9-period EMA of DIF
        
        current_dif = float(dif_series.iloc[-1])
        current_dea = float(dea_series.iloc[-1])
        
        state = ticker_states[ticker]
        today = datetime.now().date()

        # Initialize stage on first run
        if state["stage"] is None:
            detected_stage, historical_max = detect_current_stage(current_dif, current_dea, dif_series, dea_series)
            state["stage"] = detected_stage
            
            if state["stage"] == 3:
                # Use historical max DIF instead of current value
                state["max_dif"] = historical_max
                state["stage1_confirmed"] = True
                state["stage2_confirmed"] = True
            elif state["stage"] == 2:
                state["stage1_confirmed"] = True
            elif state["stage"] == 1:
                state["stage1_confirmed"] = True

        current_stage = state["stage"]

        # ========== 4-STAGE STATE MACHINE ==========
        
        # Global reset condition: if DIF drops below zero from any stage
        if current_dif < 0:
            state["stage"] = 0
            state["max_dif"] = 0.0
            state["alert_date"] = None
            state["stage1_confirmed"] = False
            state["stage2_confirmed"] = False
            return f"Stage0_Reset_DIF_Below_Zero_DIF={current_dif:.3f}", False
        
        # Stage 0 → Stage 1: Detect underwater golden cross (DEA < DIF < 0)
        if current_stage == 0:
            if current_dea < current_dif < 0:
                state["stage"] = 1
                state["stage1_confirmed"] = True
                return f"Stage1_Underwater_GoldCross_DIF={current_dif:.3f}", False
            return f"Stage0_Waiting_DIF={current_dif:.3f}_DEA={current_dea:.3f}", False
        
        # Stage 1 → Stage 2: DIF breaks above zero
        elif current_stage == 1:
            if current_dif > 0:
                state["stage"] = 2
                state["stage2_confirmed"] = True
                return f"Stage2_DIF_Crossed_Zero_DIF={current_dif:.3f}", False
            elif current_dif < current_dea:
                # Death cross underwater, reset
                state["stage"] = 0
                state["stage1_confirmed"] = False
                return f"Stage0_Reset_DIF_Below_DEA", False
            return f"Stage1_Waiting_DIF_Cross_Zero_DIF={current_dif:.3f}", False
        
        # Stage 2 → Stage 3: DEA breaks above zero
        elif current_stage == 2:
            if current_dea > 0:
                state["stage"] = 3
                # Find max DIF from when DIF crossed zero to now
                dif_crossed_zero_idx = None
                for i in range(len(dif_series) - 1, max(0, len(dif_series) - 100), -1):
                    if i > 0 and dif_series.iloc[i-1] < 0 and dif_series.iloc[i] > 0:
                        dif_crossed_zero_idx = i
                        break
                
                if dif_crossed_zero_idx is not None:
                    state["max_dif"] = float(dif_series.iloc[dif_crossed_zero_idx:].max())
                else:
                    state["max_dif"] = current_dif
                
                return f"Stage3_DEA_Crossed_Zero_DEA={current_dea:.3f}_MaxDIF={state['max_dif']:.3f}", False
            return f"Stage2_Waiting_DEA_Cross_Zero_DEA={current_dea:.3f}", False
        
        # Stage 3: Track DIF peak, detect DEA retracement
        elif current_stage == 3:
            # Update DIF peak value
            if current_dif > state["max_dif"]:
                state["max_dif"] = current_dif
            
            # Check if DEA has retraced to 50% of peak
            if state["max_dif"] > 0:
                retrace_threshold = state["max_dif"] * 0.5
                
                # Trigger condition: DEA <= 50% peak AND not alerted today
                if current_dea <= retrace_threshold:
                    if state["alert_date"] != today:
                        state["alert_date"] = today
                        return f"SIGNAL_DEA_Retraced_50pct_Peak={state['max_dif']:.3f}_DEA={current_dea:.3f}", True
                    else:
                        return f"Stage3_Already_Alerted_Today", False
            
            return f"Stage3_Tracking_DIF={current_dif:.3f}_MaxDIF={state['max_dif']:.3f}_DEA={current_dea:.3f}", False
        
        return "Unknown_Stage", False

    except Exception as e:
        return f"Err_{type(e).__name__}_{str(e)}", False

def run_radar():
    """
    Main monitoring loop: continuously scan watchlist and send alerts.
    """
    print("=" * 60)
    print(" Radar Guardian V4 (4-Stage Underwater Breakout Monitor)")
    print("=" * 60)

    while True:
        open_status, status_msg = is_market_open()
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not open_status:
            # Market is closed, sleep for 10 minutes
            sys.stdout.write(f"\r[{current_time_str}] {status_msg}... Sleeping ")
            sys.stdout.flush()
            time.sleep(600)
            continue

        print(f"\n[{current_time_str}] {status_msg} - Scanning...")
        
        # Scan each ticker in watchlist
        for ticker in WATCH_LIST:
            sys.stdout.write(f"  > {ticker}: ")
            sys.stdout.flush()
            
            status_text, is_triggered = get_mac_status(ticker)
            sys.stdout.write(f"{status_text}\n")
            
            # Send push notification if signal triggered
            if is_triggered:
                try:
                    # Bark push notification (iOS)
                    state = ticker_states[ticker]
                    msg_body = f"{ticker}_DEA_Retraced_50pct_Peak_{state['max_dif']:.3f}"
                    url = f"https://api.day.app/{BARK_KEY}/Radar_Alert/{msg_body}"
                    requests.get(url, timeout=5)
                    print(f"!!! [PUSH_SENT] {ticker} !!!")
                except:
                    print(f"!!! [PUSH_FAILED] {ticker} !!!")

        print("-" * 60)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        run_radar()
    except KeyboardInterrupt:
        print("\nProcess_Stopped_By_User")
    except Exception as e:
        print(f"\nCritical_Crash: {e}")