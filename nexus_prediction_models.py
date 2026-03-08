
import logging
import numpy as np
import pandas as pd
import yfinance as yf

from datetime import datetime

logger = logging.getLogger(__name__)

class NexusPredictionEngine:
    """Core AI Prediction Engine for Nexus."""
    
    def __init__(self, quantum_ai_instance):
        self.quantum_ai = quantum_ai_instance
        
    def fetch_data(self, symbol):
        """Fetch stock data from Yahoo Finance."""
        try:
            symbol_clean = symbol.replace('.NS', '').replace('.BO', '').upper()
            ticker_str = f'{symbol_clean}.NS'
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period='1y')
            if hist.empty:
                ticker_str = f'{symbol_clean}.BO'
                stock = yf.Ticker(ticker_str)
                hist = stock.history(period='1y')
            return hist, symbol_clean
        except Exception as e:
            logger.error(f'Data fetch failed for {symbol}: {str(e)}')
            return None, symbol

    def prepare_features(self, hist, volume):
        """Extract Technical Indicators & Features."""
        if hist is None or hist.empty:
            return None

        df = hist.copy()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        df['Returns'] = df['Close'].pct_change()
        df['Volatility'] = df['Returns'].rolling(20).std()
        
        if df.empty:
            return None

        try:
            latest = df.iloc[-1]
        except IndexError:
            return None
        
        features = np.array([
            float(latest['Close']),
            float(latest['MA20'] if not pd.isna(latest['MA20']) else latest['Close']),
            float(latest['MA50'] if not pd.isna(latest['MA50']) else latest['Close']),
            float(latest['Volatility'] if not pd.isna(latest['Volatility']) else 0),
            float(volume) if volume > 0 else 1000000
        ]).reshape(1, -1)
        
        return features

    def predict_ensemble(self, symbol, volume=0):
        """
        Thin adapter — delegates ALL intelligence to QuantumAI.
        """

        hist, symbol_clean = self.fetch_data(symbol)
        if hist is None or hist.empty:
            return None

        return self.quantum_ai.get_comprehensive_prediction(
            symbol_clean,
            hist
        )

