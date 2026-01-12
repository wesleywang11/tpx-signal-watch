# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
from datetime import datetime

# ================= CONFIGURATION =================

# Tokyo Stock Exchange watch list
WATCH_LIST = [
    "6723.T", "9432.T", "7011.T", "7203.T", "8058.T", "8306.T", "9501.T", "285A.T",
    "6758.T", "9434.T", "2760.T", "9984.T", "8035.T", "9503.T", "4324.T", "9433.T",
    "7272.T", "6367.T", "6146.T", "6269.T", "6501.T", "8316.T", "5706.T", "5016.T",
    "7974.T", "7013.T", "4063.T", "4502.T", "6762.T", "6361.T", "6503.T", "8053.T",
    "7267.T", "6981.T", "6702.T", "8002.T", "4568.T", "9502.T", "1911.T", "5802.T"
]

RSI_THRESHOLD = 40   # RSI threshold
RSI_PERIOD = 14     # RSI calculation period

# =================================================

def calculate_rsi(prices, period=14):
    """
    Calculate RSI indicator
    Args:
        prices: price series
        period: RSI period (default 14)
    Returns:
        RSI series
    """
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze_ticker(ticker):
    """
    Analyze RSI and MACD status for a single ticker
    Returns:
        (bool: match or not, dict: detailed data)
    """
    try:
        # Download daily data (3 months is sufficient for indicators)
        df = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if df.empty or len(df) < 30:
            return False, {"error": "Insufficient data"}

        # Get close price series
        close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']

        # Calculate MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()

        # Calculate RSI
        rsi = calculate_rsi(close, RSI_PERIOD)

        # Latest values
        current_rsi = float(rsi.iloc[-1])
        current_dif = float(dif.iloc[-1])
        current_dea = float(dea.iloc[-1])
        current_price = float(close.iloc[-1])

        # Condition: RSI < threshold AND DIF > DEA (bullish crossover)
        is_match = current_rsi < RSI_THRESHOLD and current_dif > current_dea

        data = {
            "price": current_price,
            "rsi": current_rsi,
            "dif": current_dif,
            "dea": current_dea,
            "diff": current_dif - current_dea  # crossover strength
        }

        return is_match, data

    except Exception as e:
        return False, {"error": str(e)}


def run_scanner():
    """
    Run scanner and print results
    """
    print("=" * 70)
    print(f" RSI Low-Level MACD Bullish Crossover Scanner (RSI < {RSI_THRESHOLD}, DIF > DEA)")
    print("=" * 70)
    print(f"Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Watch list size: {len(WATCH_LIST)}")
    print("-" * 70)

    matches = []

    for ticker in WATCH_LIST:
        print(f"Analyzing {ticker}...", end=" ")

        is_match, data = analyze_ticker(ticker)

        if "error" in data:
            print(f"❌ {data['error']}")
            continue

        if is_match:
            print("✅ Match found!")
            matches.append((ticker, data))
        else:
            print(f"⚪ RSI={data['rsi']:.1f}, DIF-DEA={data['diff']:.3f}")

    # Summary
    print("=" * 70)
    print(f"\n🎯 Found {len(matches)} matching stocks:\n")

    if matches:
        # Sort by RSI ascending
        matches.sort(key=lambda x: x[1]['rsi'])

        print(f"{'Ticker':<12} {'Price':<10} {'RSI':<8} {'DIF':<10} {'DEA':<10} {'Strength':<10}")
        print("-" * 70)

        for ticker, data in matches:
            print(
                f"{ticker:<12} "
                f"{data['price']:<10.2f} "
                f"{data['rsi']:<8.1f} "
                f"{data['dif']:<10.3f} "
                f"{data['dea']:<10.3f} "
                f"{data['diff']:<10.3f}"
            )
    else:
        print("No stocks meet the criteria at this time")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        run_scanner()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Program error: {e}")
