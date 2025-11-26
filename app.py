from flask import Flask, render_template, request, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytz

app = Flask(__name__, template_folder='../templates', static_folder='../static')

CALIBRATED_WEIGHTS = {
    "price_roc": 0.44, "vwap": 0.25, "volume_spike": 0.49,
    "rsi_oversold": 0.85, "rvol_high": 0.44, "obv_roc": 0.51,
    "mfi": 0.67, "spike_quality": 0.48, "ema_downtrend": 0.46, "stoch_oversold": 0.47
}

TRADING_SETTINGS = {
    "buyPeriodMinutes": 48, "bbLengthMinutes": 24, "rsiLengthMinutes": 14,
    "priceRocPeriodMinutes": 20, "obvRocPeriodMinutes": 20, "mfiPeriodMinutes": 14,
    "vwapPeriodMinutes": 10, "spikePriceRocZThreshold": 1.0,
    "spikeRsiRocZThreshold": 0.5, "spikeObvRocZThreshold": 0.5, "spikeMfiRocZThreshold": 0.6,
    "spikePercentBRocZThreshold": 0.5, "spikeVwapRocZThreshold": 0.5, "spikeVolumeRocZThreshold": 0.5,
    "regularPriceRocThreshold": 2.0, "regularRsiRocThreshold": 5.0, "regularObvRocThreshold": 10.0,
    "regularMfiRocThreshold": 5.0, "regularPercentBRocThreshold": 15.0, "regularVwapRocThreshold": 1.5,
    "regularVolumeRocThreshold": 20.0, "comboSignalThreshold": 0.76, "highProbThreshold": 0.8,
    "stopLossPct": 0.02, "targetGainPercent": 2.0, "macdHistogramRocThreshold": 0.5,
    "stochasticOversoldThreshold": 30, "rvolThreshold": 1.2
}

class PennyBreakoutStrategy:
    def __init__(self):
        self.settings = TRADING_SETTINGS
        self.weights = CALIBRATED_WEIGHTS
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_ema(self, prices, period):
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line, macd_line - signal_line
    
    def calculate_signals(self, df):
        df = df.copy()
        df['RSI'] = self.calculate_rsi(df['Close'], self.settings['rsiLengthMinutes'])
        df['EMA_9'] = self.calculate_ema(df['Close'], 9)
        df['EMA_20'] = self.calculate_ema(df['Close'], 20)
        df['EMA_50'] = self.calculate_ema(df['Close'], 50)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = self.calculate_macd(df['Close'])
        return df

def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="1m", prepost=True)
        if df.empty:
            return None, "No data available"
        return df, None
    except Exception as e:
        return None, str(e)

def get_market_status():
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    current_time = now.time()
    weekday = now.weekday()
    
    if weekday >= 5:
        return "closed", "Weekend - Market Closed"
    
    from datetime import time
    if current_time < time(4, 0):
        return "closed", "Market Closed"
    elif current_time < time(9, 30):
        return "prepost", "Pre-Market"
    elif current_time < time(16, 0):
        return "open", "Market Open"
    elif current_time < time(20, 0):
        return "prepost", "After-Hours"
    else:
        return "closed", "Market Closed"

@app.route('/')
def index():
    market_status, market_text = get_market_status()
    et_tz = pytz.timezone('US/Eastern')
    current_time = datetime.now(et_tz).strftime('%H:%M ET')
    return render_template('index.html', market_status=market_status, market_text=market_text, current_time=current_time)

@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    df, error = fetch_stock_data(ticker.upper())
    if error:
        return jsonify({"error": error}), 400
    
    strategy = PennyBreakoutStrategy()
    df = strategy.calculate_signals(df)
    
    latest = df.iloc[-1]
    current_price = float(latest['Close'])
    open_price = float(df['Open'].iloc[0])
    day_change = ((current_price - open_price) / open_price * 100)
    
    return jsonify({
        "ticker": ticker.upper(),
        "current_price": current_price,
        "day_change": day_change,
        "rsi": float(latest['RSI']),
        "ema9": float(latest['EMA_9']),
        "ema20": float(latest['EMA_20']),
        "ema50": float(latest['EMA_50']),
        "macd": float(latest['MACD']),
        "macd_signal": float(latest['MACD_Signal']),
        "macd_hist": float(latest['MACD_Hist']),
        "chart_data": {
            "dates": df.index.strftime('%H:%M').tolist(),
            "opens": df['Open'].tolist(),
            "highs": df['High'].tolist(),
            "lows": df['Low'].tolist(),
            "closes": df['Close'].tolist(),
            "volumes": df['Volume'].tolist(),
            "rsi": df['RSI'].tolist(),
            "ema9": df['EMA_9'].tolist(),
            "ema20": df['EMA_20'].tolist()
        }
    })

@app.route('/api/market-status')
def market_status_api():
    status, text = get_market_status()
    et_tz = pytz.timezone('US/Eastern')
    current_time = datetime.now(et_tz).strftime('%H:%M ET')
    return jsonify({"status": status, "text": text, "time": current_time})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
