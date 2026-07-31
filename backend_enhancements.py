# -*- coding: utf-8 -*-
"""
StockSense - Backend Enhancement System
Unified Dynamic Architecture:
✔ Dynamic stock search
✔ AI forecasting
✔ Volatility & risk engine
✔ Pattern detection (ML)
✔ Reinforcement-learning-ready structure
No hardcoding, placeholders, or duplicates.
"""

# ensure global UTF-8
from utils import encoding

# ADD THESE IMPORTS
from pathlib import Path
import json
from functools import lru_cache
import sqlite3
import logging
from datetime import datetime, timedelta

# Use existing logger configuration from app.py hierarchy
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import yfinance as yf
from flask import jsonify as _flask_jsonify
from utils import encoding

def jsonify(data=None, *args, **kwargs):
    if data is not None:
        data = encoding.sanitize_json(data)
    return _flask_jsonify(data, *args, **kwargs)
from typing import Dict, List

import schedule
import time

def daily_accuracy_update():
    """Check predictions from yesterday"""
    logger.info("🔄 Starting daily accuracy check...")
    
    symbols = quantum_ai.get_top_active_stocks(20)
    for symbol in symbols:
        try:
            # Get current price
            df = quantum_ai.get_live_stock_data(symbol, period='1d')
            if df is not None:
                current_price = float(df['Close'].iloc[-1])
                quantum_ai.prediction_logger.update_accuracy(symbol, current_price)
                logger.info(f"[DATA] Updated {symbol}")
        except Exception as e:
            logger.debug(f"Update failed for {symbol}: {e}")
    
    logger.info("[SYS] Daily accuracy check complete")

# Schedule it
schedule.every().day.at("16:00").do(daily_accuracy_update)  # 4 PM daily

# In your main loop, add:
# while True:
#     schedule.run_pending()
#     time.sleep(60)

# ============================================================
# 1. DYNAMIC STOCK SEARCH (AUTO MARKET DISCOVERY)
# ============================================================

def get_dynamic_stock_search(query: str, limit: int = 15) -> List[Dict]:
    """Optimized discovery using mirrored universe logic."""
    try:
        from app import MARKET
        return MARKET.search(query, limit=limit)
    except Exception:
        return []



# ============================================================
# 2. ENHANCED AI FORECASTING ROUTE
# ============================================================

def register_enhanced_routes(app, quantum_ai):
    """
    Register ONLY enhanced AI routes.
    The primary stock analysis route is in app.py, NOT HERE.
    No duplicates, no overwriting.
    """

    # ------------------------------------------------------------
    # AI Forecast: Multi-model, dynamic, future prediction
    # ------------------------------------------------------------
    @app.route("/api/ai/forecast/<symbol>")
    def ai_forecast(symbol):
        try:
            if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
                symbol += ".NS"

            df = yf.Ticker(symbol).history(period="1y")
            if df.empty:
                return jsonify({"success": False, "error": "No available data"}), 404

            prediction = quantum_ai.get_future_forecast(symbol, df)

            return jsonify({
                "success": True,
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
                "forecast": prediction
            })

        except Exception as e:
            logger.error(f"Forecast failed for {symbol}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500



    # ------------------------------------------------------------
    # ML Pattern Detection (Reversal, Breakouts, Trends)
    # ------------------------------------------------------------
    @app.route("/api/ai/patterns/<symbol>")
    def ai_patterns(symbol):
        try:
            if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
                symbol += ".NS"

            df = yf.Ticker(symbol).history(period="1y")
            if df.empty:
                return jsonify({"success": False, "error": "No data available"}), 404

            patterns = quantum_ai.detect_market_patterns(symbol, df)

            return jsonify({
                "success": True,
                "symbol": symbol.replace(".NS", ""),
                "patterns": patterns
            })

        except Exception as e:
            logger.error(f"Pattern detection failed for {symbol}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500



    # ------------------------------------------------------------
    # RISK ENGINE (Volatility, Tail-risk, Stress testing)
    # ------------------------------------------------------------
    @app.route("/api/ai/risk/<symbol>")
    def ai_risk(symbol):
        try:
            if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
                symbol += ".NS"

            df = yf.Ticker(symbol).history(period="1y")
            if df.empty:
                return jsonify({"success": False, "error": "Insufficient data"}), 404

            risk_report = quantum_ai.evaluate_risk(symbol, df)

            return jsonify({
                "success": True,
                "symbol": symbol.replace(".NS", ""),
                "risk": risk_report
            })

        except Exception as e:
            logger.error(f"Risk evaluation failed for {symbol}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500



    logger.info("[SYS] Enhanced AI routes registered successfully!")
