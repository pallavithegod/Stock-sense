"""Market, search, stock, and market-chart route handlers."""

from __future__ import annotations

from typing import Any, Mapping

from flask import Blueprint, jsonify, request


def configure_market_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose legacy app dependencies used by market/search handlers."""
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value


def api_search():
    q = request.args.get("q", "")
    limit = int(request.args.get("limit", 15))
    if not q:
        return jsonify({"success": True, "results": []})

    return jsonify({
        "success": True,
        "results": _build_search_results(q, limit)
    })



def _build_search_results(query: str, limit: int = 15):
    ensure_market_universe_exchange_coverage()
    # quick bounds
    fetch_limit = max(1, min(limit, 60))
    raw = MARKET.search(query, limit=max(fetch_limit * 4, 80))

    price_map = dict(MARKET._price_cache)
    change_percent_map = {}
    change_value_map = {}

    # try to overlay dashboard/top-stock prices for liveliness
    try:
        dash = get_dashboard_cache() or {}
        for stock in ((dash.get("data") or {}).get("top_stocks") or []):
            base = normalize_symbol(stock.get("symbol") or stock.get("full_symbol"))
            if not base:
                continue
            if (p := stock.get("current_price")) is not None:
                price_map[base] = float(p)
            if (cp := stock.get("change_percent") or stock.get("price_change_percent")) is not None:
                change_percent_map[base] = float(cp)
            if (cv := stock.get("change_value") or stock.get("price_change")) is not None:
                change_value_map[base] = float(cv)
    except Exception:
        pass

    # and overlay AI cache if present
    try:
        for sym, pred in AI_ENGINE_STATE.get("predictions", {}).items():
            base = str(sym).upper().replace(".NS", "").replace(".BO", "")
            if not base:
                continue
            if (p := pred.get("current_price") or pred.get("price")) is not None:
                price_map[base] = float(p)
            if (cp := pred.get("change_percent") or pred.get("change_pct")) is not None:
                change_percent_map[base] = float(cp)
            if (cv := pred.get("change_value") or pred.get("price_change")) is not None:
                change_value_map[base] = float(cv)
    except Exception:
        pass

    results = []
    for item in raw:
        base = str(item.get("symbol", "")).upper()
        if not base:
            continue

        display = item.get("display", base)
        # if user explicitly included suffix, respect it verbatim
        if query.upper().endswith(".NS") or query.upper().endswith(".BO"):
            display = query.upper()

        price = price_map.get(base)
        cp = change_percent_map.get(base)
        cv = change_value_map.get(base)

        results.append({
            "symbol": base,
            "display": display,
            "name": item.get("name", ""),
            "exchange": item.get("exchange") or ("BSE" if ".BO" in str(display).upper() else "NSE"),
            "price": round(float(price), 2) if price is not None else None,
            "current_price": round(float(price), 2) if price is not None else None,
            "change_percent": round(float(cp), 2) if cp is not None else None,
            "change_value": round(float(cv), 2) if cv is not None else None
        })

    if len(query.strip()) >= 2:
        q = query.strip().upper()
        index_results = []
        for sym, name in (get_dynamic_index_symbols() or {}).items():
            base = normalize_market_asset_key(sym)
            if not base:
                continue
            symbol_text = str(sym).upper()
            name_text = str(name).upper()
            if q not in base and q not in symbol_text and q not in name_text:
                continue
            if any(existing.get("symbol") == base for existing in results + index_results):
                continue
            index_results.append({
                "symbol": base,
                "display": symbol_text,
                "name": name,
                "exchange": "INDEX",
                "price": round(float(price_map.get(base)), 2) if price_map.get(base) is not None else None,
                "current_price": round(float(price_map.get(base)), 2) if price_map.get(base) is not None else None,
                "change_percent": round(float(change_percent_map.get(base)), 2) if change_percent_map.get(base) is not None else None,
                "change_value": round(float(change_value_map.get(base)), 2) if change_value_map.get(base) is not None else None,
            })
        results.extend(index_results)

    # if nothing found from our static universe, attempt dynamic lookup (expensive)
    if not results and len(query) >= 2:
        try:
            from backend_enhancements import get_dynamic_stock_search
            dyn = get_dynamic_stock_search(query, limit=5)
            for d in dyn:
                base = normalize_symbol(d.get("symbol"))
                if not base:
                    continue
                display_sym = d.get("symbol", base)
                # cache into MARKET for subsequent fast lookup
                if base not in MARKET.symbols:
                    MARKET.symbols[base] = {
                        "symbol": base,
                        "exchange_symbols": [display_sym],
                        "name": d.get("name", base)
                    }
                else:
                    if display_sym not in MARKET.symbols[base].get("exchange_symbols", []):
                        MARKET.symbols[base].setdefault("exchange_symbols", []).append(display_sym)
                results.append({
                    "symbol": base,
                    "display": display_sym,
                    "name": d.get("name", ""),
                    "price": d.get("current_price"),
                    "current_price": d.get("current_price"),
                    "change_percent": None,
                    "change_value": None
                })
        except Exception:
            pass

    def search_relevance_key(result):
        q_raw = str(query or "").upper().strip()
        q_base = q_raw.replace(".NS", "").replace(".BO", "")
        q_compact = re.sub(r"[^A-Z0-9]", "", q_base)

        symbol = str(result.get("symbol") or "").upper()
        display = str(result.get("display") or symbol).upper()
        display_base = display.replace(".NS", "").replace(".BO", "")
        name = str(result.get("name") or "").upper()
        name_compact = re.sub(r"[^A-Z0-9]", "", name)

        if not q_compact:
            relevance = 99
        elif symbol == q_compact or display_base == q_compact or display == q_raw:
            relevance = 0
        elif symbol.startswith(q_compact) or display_base.startswith(q_compact):
            relevance = 1
        elif name_compact.startswith(q_compact):
            relevance = 2
        elif q_compact in symbol or q_compact in display_base:
            relevance = 3
        elif q_compact in name_compact:
            relevance = 4
        else:
            relevance = 5

        exchange = str(result.get("exchange") or "").upper()
        exchange_priority = 0 if exchange == "NSE" or display.endswith(".NS") else 1 if exchange == "BSE" or display.endswith(".BO") else 2
        price_priority = 0 if result.get("price") is not None else 1
        length_gap = abs(len(display_base) - len(q_compact))

        return (relevance, length_gap, exchange_priority, price_priority, symbol, display)

    results.sort(key=search_relevance_key)
    return results[:limit]



def market_debug():
    if not debug_endpoints_enabled():
        return jsonify({"success": False, "error": "Debug endpoint disabled"}), 404
    return jsonify({
        "count": len(MARKET.symbols),
        "sample": list(MARKET.symbols.keys())[:50]
    })
    
    # ...........................................................................
    # DYNAMIC ANALYSIS
    # ...........................................................................
    
    def get_optimal_analysis_period(self, symbol: str) -> str:
        """Get optimal analysis period based on volatility"""
        try:
            df = self.get_live_stock_data(symbol, period='1y')
            if df is None or len(df) < 60:
                return '1mo'
            
            # Calculate volatility
            returns = df['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)
            
            # Dynamic period selection (no hardcoding)
            if volatility > 0.4:
                return '1mo'  # High vol = short term
            elif volatility > 0.2:
                return '3mo'  # Medium vol
            else:
                return '1y'   # Low vol = longer term
        except:
            return '1y'
    
    def get_stock_metadata(self, symbol: str) -> Dict:
        """Get stock metadata dynamically"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'longName': info.get('longName', symbol),
                'sector': info.get('sector', 'General'),
                'industry': info.get('industry', 'Unknown'),
                'exchange': info.get('exchange', 'NSE'),
                'marketCap': info.get('marketCap', 0)
            }
        except Exception as e:
            logger.warning(f"Metadata fetch failed for {symbol}: {e}")
            return {
                'longName': symbol,
                'sector': 'General',
                'industry': 'Unknown',
                'exchange': 'NSE',
                'marketCap': 0
            }
    
    # ...........................................................................
    # TECHNICAL INDICATORS (100% SAFE, NO NaN VALUES)
    # ...........................................................................
    
    @staticmethod
    def safe_calculate_indicators(df: pd.DataFrame) -> Dict:
        """
        Calculate indicators with ZERO NaN values
        o. Safe defaults for all calculations
        o. No crashes from missing data
        o. Returns complete dictionary
        """
        if df is None or df.empty:
            return {
                'ma_20': 0, 'ma_50': 0, 'ma_200': 0,
                'rsi': 50, 'volatility': 0,
                'macd': 0, 'signal_line': 0,
                'upper_band': 0, 'lower_band': 0,
                'current_price': 0
            }
        
        try:
            close = df['Close']
            current_price = float(close.iloc[-1]) if not close.empty else 0
            
            # Moving averages with NaN handling
            ma_20 = float(close.rolling(20).mean().iloc[-1]) if len(df) >= 20 else current_price
            ma_50 = float(close.rolling(50).mean().iloc[-1]) if len(df) >= 50 else ma_20
            ma_200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else ma_50
            
            # Replace NaN with fallbacks
            ma_20 = ma_20 if not np.isnan(ma_20) else current_price
            ma_50 = ma_50 if not np.isnan(ma_50) else ma_20
            ma_200 = ma_200 if not np.isnan(ma_200) else ma_50
            
            # RSI with safety
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi_series = 100 - (100 / (1 + rs))
            current_rsi = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 and not np.isnan(rsi_series.iloc[-1]) else 50.0
            
            # MACD with safety
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9, adjust=False).mean()
            
            current_macd = float(macd.iloc[-1]) if not macd.empty and not np.isnan(macd.iloc[-1]) else 0.0
            current_signal = float(signal_line.iloc[-1]) if not signal_line.empty and not np.isnan(signal_line.iloc[-1]) else 0.0
            
            # Bollinger Bands with safety
            sma = close.rolling(20).mean()
            std = close.rolling(20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            current_upper = float(upper_band.iloc[-1]) if not upper_band.empty and not np.isnan(upper_band.iloc[-1]) else current_price * 1.1
            current_lower = float(lower_band.iloc[-1]) if not lower_band.empty and not np.isnan(lower_band.iloc[-1]) else current_price * 0.9
            
            # Volatility with safety
            returns = close.pct_change().dropna()
            volatility = float(returns.std() * np.sqrt(252) * 100) if len(returns) > 0 else 0.0
            volatility = volatility if not np.isnan(volatility) else 0.0
            
            return {
                'ma_20': round(ma_20, 2),
                'ma_50': round(ma_50, 2),
                'ma_200': round(ma_200, 2),
                'rsi': round(current_rsi, 1),
                'volatility': round(volatility, 1),
                'macd': round(current_macd, 2),
                'signal_line': round(current_signal, 2),
                'upper_band': round(current_upper, 2),
                'lower_band': round(current_lower, 2),
                'current_price': round(current_price, 2)
            }
        
        except Exception as e:
            logger.error(f"Safe indicator calculation error: {e}")
            return {
                'ma_20': 0, 'ma_50': 0, 'ma_200': 0,
                'rsi': 50, 'volatility': 0,
                'macd': 0, 'signal_line': 0,
                'upper_band': 0, 'lower_band': 0,
                'current_price': 0
            }
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators with fallback values"""
        try:
            indicators = {}
            
            # RSI
            if len(df) >= 14:
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
            else:
                indicators['rsi'] = 50.0
            
            # Moving Averages
            indicators['ma5'] = float(df['Close'].rolling(5).mean().iloc[-1]) if len(df) >= 5 else float(df['Close'].iloc[-1])
            indicators['ma20'] = float(df['Close'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else indicators['ma5']
            indicators['ma50'] = float(df['Close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else indicators['ma20']
            
            # MACD
            if len(df) >= 26:
                ema12 = df['Close'].ewm(span=12).mean()
                ema26 = df['Close'].ewm(span=26).mean()
                macd = ema12 - ema26
                macd_signal = macd.ewm(span=9).mean()
                indicators['macd'] = float(macd.iloc[-1])
                indicators['macd_signal'] = float(macd_signal.iloc[-1])
            else:
                indicators['macd'] = 0.0
                indicators['macd_signal'] = 0.0
            
            # Volatility
            returns = df['Close'].pct_change().dropna()
            indicators['volatility'] = float(returns.tail(20).std() * np.sqrt(252) * 100) if len(returns) >= 20 else 25.0
            
            # Volume
            indicators['volume_sma'] = float(df['Volume'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else float(df['Volume'].iloc[-1])
            indicators['volume_ratio'] = float(df['Volume'].iloc[-1]) / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1.0
            
            return indicators
        
        except Exception as e:
            logger.error(f"Technical indicators failed: {e}")
            return {
                'rsi': 50, 'ma5': 0, 'ma20': 0, 'ma50': 0,
                'macd': 0, 'macd_signal': 0, 'volatility': 25,
                'volume_sma': 0, 'volume_ratio': 1
            }
    
    # ...........................................................................
    # PREDICTION METHODS
    # ...........................................................................
    
    def get_technical_prediction(self, indicators: Dict) -> Dict:
        """Technical analysis prediction"""
        rsi = indicators.get('rsi', 50)
        signal = 0
        
        if rsi < 30:
            signal += 3
        elif rsi > 70:
            signal -= 3
        
        ma5 = indicators.get('ma5', 0)
        ma20 = indicators.get('ma20', 0)
        if ma5 > ma20:
            signal += 2
        else:
            signal -= 2
        
        return {'prediction': signal, 'confidence': 75}
    
    def get_quantum_lstm_prediction(self, df: pd.DataFrame) -> Dict:
        """Get prediction from QuantumLSTM"""
        if not self._quantum_lstm_model or len(df) < 60:
            return None
        
        try:
            result = self._quantum_lstm_model.predict(df, days_ahead=1)
            if result and result.get('success') and result.get('predictions'):
                current_price = float(df['Close'].iloc[-1])
                predicted_price = result['predictions']
                return (predicted_price - current_price) / current_price * 100
        except Exception as e:
            logger.debug(f"LSTM prediction failed: {e}")
        
        return None
    
    def get_quantum_risk_prediction(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """Get prediction from QuantumRiskAgent"""
        if not self._quantum_risk_model:
            return None
        
        try:
            volatility = indicators.get('volatility', 25)
            confidence = max(50, min(90, 80 - volatility))
            prediction = 2 if volatility < 20 else -1 if volatility > 40 else 0.5
            return {'prediction': prediction, 'confidence': confidence}
        except Exception as e:
            logger.debug(f"RL prediction failed: {e}")
        
        return None
    
    def get_ml_prediction(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """Get prediction from ML models"""
        if not self.models or len(df) < 50:
            return None
        
        try:
            features = np.array([
                indicators.get('rsi', 50),
                indicators.get('ma5', 0),
                indicators.get('ma20', 0),
                indicators.get('macd', 0),
                indicators.get('volatility', 25),
                indicators.get('volume_ratio', 1)
            ]).reshape(1, -1)
            
            predictions = []
            model_names = []
            
            for name, model in self.models.items():
                try:
                    pred = model.predict(features)
                    predictions.append(pred)
                    model_names.append(name.upper())
                except:
                    continue
            
            if predictions:
                avg_pred = np.mean(predictions)
                confidence = min(85, 70 + (1 - np.std(predictions) / 15))
                return {'prediction': avg_pred, 'confidence': confidence, 'models': model_names}
        
        except Exception as e:
            logger.debug(f"ML prediction failed: {e}")
        
        return None
    
    def generate_signal(self, prediction: float, confidence: float) -> str:
        """Generate trading signal"""
        if prediction > 3 and confidence > 80:
            return 'STRONG BUY'
        elif prediction > 1.5 and confidence > 70:
            return 'BUY'
        elif prediction < -3 and confidence > 80:
            return 'STRONG SELL'
        elif prediction < -1.5 and confidence > 70:
            return 'SELL'
        else:
            return 'HOLD'
    
    def assess_risk(self, indicators: Dict, prediction: float) -> tuple:
        """Assess risk level"""
        risk_factors = []
        
        volatility = indicators.get('volatility', 25)
        if volatility > 40:
            risk_factors.append(30)
        elif volatility > 25:
            risk_factors.append(20)
        else:
            risk_factors.append(10)
        
        risk_factors.append(min(25, abs(prediction) * 2))
        
        risk_score = max(0, min(100, sum(risk_factors)))
        
        if risk_score > 70:
            return 'HIGH', risk_score
        elif risk_score > 40:
            return 'MEDIUM', risk_score
        else:
            return 'LOW', risk_score
    
    def create_fallback_prediction(self, symbol: str, df: pd.DataFrame,
                                   current_price: float = None,
                                   indicators: Dict = None) -> Dict:
        """Create fallback prediction when main system fails"""
        try:
            if current_price is None:
                current_price = float(df['Close'].iloc[-1]) if len(df) > 0 else 1000.0
            
            if indicators is None:
                indicators = self.calculate_technical_indicators(df)
            
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'confidence': 50.0,
                'target_price': round(current_price, 2),
                'predicted_return': 0.0,
                'current_price': current_price,
                'risk_level': 'MEDIUM',
                'models_used': ['Fallback'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Fallback prediction failed: {e}")
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'confidence': 50.0,
                'target_price': 1000.0,
                'predicted_return': 0.0,
                'current_price': 1000.0,
                'risk_level': 'MEDIUM',
                'models_used': ['Emergency'],
                'timestamp': datetime.now().isoformat()
            }



def smart_symbol_normalize(query: str) -> str:
    """Auto-add .NS suffix for Indian stocks"""
    query = query.strip().upper()
    
    # If already has suffix, return as-is
    if any(query.endswith(s) for s in ['.NS', '.BO', '.BSE', '.BOM']):
        return query
    
    # For Indian stocks, try .NS first
    if len(query) <= 5 and query.isalpha():
        return f"{query}.NS"
    
    return query




def get_stocks():
    """
    Get top stocks with REAL predictions
    o. 100% Live data
    o. Real AI predictions (4-model ensemble)
    o. Parallel fetching (bounded: max_workers=5)
    o. Dynamic stock discovery
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        query = request.args.get('search', '').strip()

        if query:
            search_results = _build_search_results(query, limit=limit)
            data = []
            for item in search_results:
                base_symbol = item.get('symbol', '')
                display_symbol = item.get('display', base_symbol)
                data.append({
                    'symbol': display_symbol,
                    'display': display_symbol,
                    'name': item.get('name', base_symbol),
                    'exchange': item.get('exchange', 'NSE'),
                    'current_price': item.get('current_price') or item.get('price'),
                    'price': item.get('current_price') or item.get('price'),
                    'change_percent': item.get('change_percent'),
                    'change_value': item.get('change_value'),
                    'volume': item.get('volume') or 0,
                    'prediction_signal': None,
                    'prediction_confidence': None,
                    'aiprediction': None,
                    'aiconfidence': None,
                    'confidence': None,
                    'target_price': item.get('target_price'),
                    'aitargetprice': item.get('target_price'),
                    'models_used': [],
                    'risk_level': None
                })
            return jsonify({
                'success': True,
                'data': data,
                'total': len(data),
                'timestamp': datetime.now().isoformat()
            })

        # 1. Get Top Active Stocks (Dynamic)
        active_stocks = quantum_ai.get_top_active_stocks(limit)
        
        # 2. Merge with User Tickers & Remove Hidden
        # Use set for uniqueness
        combined_set = set(active_stocks)
        
        # Add user tickers (ensure they are normalized if needed, but assuming they are)
        if hasattr(quantum_ai, 'user_tickers'):
            combined_set.update(quantum_ai.user_tickers)
            
        # Remove hidden tickers
        if hasattr(quantum_ai, 'hidden_tickers'):
            combined_set.difference_update(quantum_ai.hidden_tickers)
            
        # Convert back to list
        symbols = list(combined_set)
        
        def fetch_and_predict(symbol):
            """Fetch data + prediction for a single stock (runs in thread)"""
            try:
                df = quantum_ai.get_live_stock_data(symbol, period='1y')
                if df is None or len(df) < 10:
                    return None
                
                current_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
                
                prediction = quantum_ai.get_comprehensive_prediction(symbol, df)
                
                current_volume = int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
                avg_volume = int(df['Volume'].rolling(20).mean().iloc[-1]) if 'Volume' in df.columns and len(df) >= 20 else current_volume
                
                return {
                    'symbol': symbol.replace('.NS', ''),
                    'name': symbol.replace('.NS', ''),
                    'current_price': round(current_price, 2),
                    'price': round(current_price, 2),
                    'change_percent': round((current_price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0,
                    'volume': current_volume,
                    'volume_avg': avg_volume,
                    'prediction_signal': prediction.get('signal', 'HOLD'),
                    'prediction_confidence': round(prediction.get('confidence', 50), 1),
                    'aiprediction': prediction.get('signal', 'HOLD'),
                    'aiconfidence': round(prediction.get('confidence', 50), 1),
                    'confidence': round(prediction.get('confidence', 50), 1),
                    'target_price': round(prediction.get('target_price', current_price), 2),
                    'aitargetprice': round(prediction.get('target_price', current_price), 2),
                    'models_used': prediction.get('models_used', []),
                    'risk_level': prediction.get('risk_level', 'MEDIUM')
                }
            except Exception as e:
                logger.debug(f"Error processing {symbol}: {e}")
                return None
        
        # Parallel fetch with bounded workers (avoids yfinance rate limits)
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_and_predict, sym): sym for sym in symbols}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        logger.info(f"o. Returning {len(results)} stocks (parallel fetch)")
        
        return jsonify({
            'success': True,
            'data': results,
            'total': len(results),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Stocks API error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500



def save_user_tickers():
    """Save user-managed ticker lists (added & hidden)"""
    try:
        data = validate_user_tickers(request.get_json(silent=True), normalize_symbol=normalize_symbol)
    except ValidationError as exc:
        return jsonify(validation_error_payload(exc)), 400

    if "added" in data:
        quantum_ai.user_tickers = data["added"]
    if "hidden" in data:
        quantum_ai.hidden_tickers = data["hidden"]
    if "tickers" in data and "added" not in data:
        quantum_ai.user_tickers = data["tickers"]
        
    return jsonify({
        "success": True, 
        "added": quantum_ai.user_tickers,
        "hidden": quantum_ai.hidden_tickers
    })



def get_stock_prediction(symbol):
    """
    Get detailed prediction for single stock
    o. Real-time data
    o. All indicators
    o. Risk analysis
    o. Model breakdown
    """
    try:
        # Normalize symbol
        symbol = smart_symbol_normalize(symbol)
        
        # Get live data
        df = quantum_ai.get_live_stock_data(symbol, period='1y')
        if df is None or len(df) < 10:
            return jsonify({
                'success': False,
                'error': f'Insufficient data for {symbol}'
            }), 404
        
        # Get prediction
        prediction = quantum_ai.get_comprehensive_prediction(symbol, df)
        
        # Calculate indicators
        indicators = QuantumAINexusAI.safe_calculate_indicators(df)
        
        # Current price
        current_price = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
        
        # Historical data (last 30 days)
        df_recent = df.tail(30)
        history = []
        for date, row in df_recent.iterrows():
            history.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'change_percent': round((current_price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0,
                'prediction': {
                    'signal': prediction.get('signal', 'HOLD'),
                    'confidence': round(prediction.get('confidence', 50), 1),
                    'target_price': round(prediction.get('target_price', current_price), 2),
                    'predicted_return': round(prediction.get('predicted_return', 0), 2),
                    'risk_level': prediction.get('risk_level', 'MEDIUM'),
                    'models_used': prediction.get('models_used', [])
                },
                'indicators': {
                    'rsi': indicators.get('rsi', 50),
                    'ma_20': indicators.get('ma_20', 0),
                    'ma_50': indicators.get('ma_50', 0),
                    'ma_200': indicators.get('ma_200', 0),
                    'macd': indicators.get('macd', 0),
                    'signal_line': indicators.get('signal_line', 0),
                    'volatility': indicators.get('volatility', 0),
                    'upper_band': indicators.get('upper_band', 0),
                    'lower_band': indicators.get('lower_band', 0)
                },
                'history': history,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Stock prediction error for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



def get_technical_indicators(symbol):
    """
    Get detailed technical indicators
    o. All indicators
    o. Visual data points
    o. Signal interpretation
    """
    try:
        symbol = smart_symbol_normalize(symbol)
        
        df = quantum_ai.get_live_stock_data(symbol, period='1y')
        if df is None or len(df) < 10:
            return jsonify({'success': False, 'error': 'Insufficient data'}), 404
        
        indicators = QuantumAINexusAI.safe_calculate_indicators(df)
        
        # RSI interpretation
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            rsi_signal = 'Oversold - Potential BUY'
        elif rsi > 70:
            rsi_signal = 'Overbought - Potential SELL'
        else:
            rsi_signal = 'Neutral'
        
        # MACD interpretation
        macd = indicators.get('macd', 0)
        signal_line = indicators.get('signal_line', 0)
        if macd > signal_line:
            macd_signal = 'Bullish'
        else:
            macd_signal = 'Bearish'
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'indicators': indicators,
                'signals': {
                    'rsi': rsi_signal,
                    'macd': macd_signal
                },
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Indicators error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def get_historical_data(symbol):
    """
    Get historical OHLCV data
    o. Configurable period
    o. Full price history
    o. Volume data
    """
    try:
        symbol = smart_symbol_normalize(symbol)
        period = request.args.get('period', '1y')
        
        df = quantum_ai.get_live_stock_data(symbol, period=period)
        if df is None or len(df) < 10:
            return jsonify({'success': False, 'error': 'No data available'}), 404
        
        history = []
        for date, row in df.iterrows():
            history.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'period': period,
                'total_days': len(history),
                'history': history,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def compare_stocks():
    """
    Compare multiple stocks
    o. Side-by-side predictions
    o. Performance comparison
    o. Risk comparison
    """
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols or len(symbols) < 2:
            return jsonify({'success': False, 'error': 'Provide at least 2 symbols'}), 400
        
        symbols = [smart_symbol_normalize(s) for s in symbols]
        comparison = []
        
        for symbol in symbols:
            try:
                df = quantum_ai.get_live_stock_data(symbol, period='1y')
                if df is None or len(df) < 10:
                    continue
                
                prediction = quantum_ai.get_comprehensive_prediction(symbol, df)
                current_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
                
                comparison.append({
                    'symbol': symbol,
                    'current_price': round(current_price, 2),
                    'change_percent': round((current_price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0,
                    'signal': prediction.get('signal'),
                    'confidence': round(prediction.get('confidence', 50), 1),
                    'target_price': round(prediction.get('target_price'), 2),
                    'risk_level': prediction.get('risk_level')
                })
            except:
                continue
        
        return jsonify({
            'success': True,
            'data': {
                'comparison': comparison,
                'total_stocks': len(comparison),
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Compare stocks error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def comprehensive_search():
    q = request.args.get("q", "").strip().upper()
    limit = int(request.args.get("limit", 10))
    if not q:
        return jsonify({"success": True, "results": []})
    return jsonify({"success": True, "results": _build_search_results(q, limit)})


def stock_analysis(symbol):
    """Complete AI + Technical + Fundamental stock analysis (Dynamic & Clean)"""
    try:
        import yfinance as yf

        # Ensure .NS suffix
        if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
            symbol = symbol + '.NS'

        yf_obj = yf.Ticker(symbol)

        # Fetch live 1-day data for high/low/volume
        day_df = yf_obj.history(period='1d')
        if day_df.empty:
            return jsonify({'success': False, 'error': 'No live market data available'}), 404

        day_high = float(day_df['High'].iloc[-1])
        day_low = float(day_df['Low'].iloc[-1])
        day_volume = int(day_df['Volume'].iloc[-1])

        # Fetch 1-year data for AI + technicals
        df = quantum_ai.get_live_stock_data(symbol, period='1y')
        if df is None or df.empty or len(df) < 50:
            return jsonify({'success': False, 'error': 'Insufficient data'}), 404

        # AI Prediction
        prediction = quantum_ai.get_comprehensive_prediction(symbol, df)

        # Fundamental info
        info = yf_obj.info

        pe_ratio = info.get("trailingPE") or info.get("regularMarketPE") or None
        eps = info.get("trailingEps") or None
        market_cap = info.get("marketCap") or None
        pb_ratio = info.get("priceToBook") or None
        debt_to_equity = info.get("debtToEquity") or None
        roce = info.get("returnOnCapitalEmployed") or None
        roe = info.get("returnOnEquity") or None
        dividend_yield = info.get("dividendYield") or None
        dividend_rate = info.get("dividendRate") or None
        face_value = (
            info.get("faceValue")
            or info.get("bookValue")
            or info.get("defaultKeyStatistics", {}).get("faceValue")
            or None
        )

        # Technical metrics
        current_price = float(df['Close'].iloc[-1])
        returns = df['Close'].pct_change().dropna()

        ma_20 = df['Close'].rolling(20).mean().iloc[-1]
        ma_50 = df['Close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma_20
        ma_200 = df['Close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else ma_50

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if len(rsi) else 50

        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9).mean()
        current_macd = float(macd.iloc[-1])
        current_signal = float(signal_line.iloc[-1])

        bb_middle = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)

        volatility = returns.std() * np.sqrt(252) * 100

        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume else 1.0

        high_52w = df['High'].max()
        low_52w = df['Low'].min()
        price_position_52w = ((current_price - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50

        # Key Factors (unchanged from your model)
        key_factors = []

        if ma_20 > ma_50:
            key_factors.append({"factor": "Technical Momentum", "status": "Positive",
                                "detail": f"MA20 ({ma_20:.2f}) above MA50 ({ma_50:.2f})"})
        else:
            key_factors.append({"factor": "Technical Momentum", "status": "Negative",
                                "detail": f"MA20 ({ma_20:.2f}) below MA50 ({ma_50:.2f})"})

        if volume_ratio > 1.5:
            key_factors.append({"factor": "Volume", "status": "High Activity",
                                "detail": f"{volume_ratio:.1f}x normal volume"})
        elif volume_ratio < 0.7:
            key_factors.append({"factor": "Volume", "status": "Low Activity",
                                "detail": f"{volume_ratio:.1f}x normal volume"})
        else:
            key_factors.append({"factor": "Volume", "status": "Normal",
                                "detail": f"{volume_ratio:.1f}x normal volume"})

        if current_rsi > 70:
            key_factors.append({"factor": "RSI", "status": "Overbought",
                                "detail": f"RSI {current_rsi:.1f}"})
        elif current_rsi < 30:
            key_factors.append({"factor": "RSI", "status": "Oversold",
                                "detail": f"RSI {current_rsi:.1f}"})
        else:
            key_factors.append({"factor": "RSI", "status": "Neutral",
                                "detail": f"RSI {current_rsi:.1f}"})


        # ========== FINAL OUTPUT (Matches Your Frontend EXACTLY) ==========
        return jsonify({
            "success": True,
            "data": {
                # For Dashboard + Modal
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
                "company_name": info.get("longName") or info.get("shortName") or symbol,
                "sector": info.get("sector") or "Unknown",

                # ===== Fundamentals =====
                "pe_ratio": pe_ratio,
                "eps": eps,
                "market_cap": market_cap,
                "pb_ratio": pb_ratio,
                "debt_to_equity": debt_to_equity,
                "roce": roce,
                "roe": roe,
                "dividend_yield": dividend_yield,
                "dividend_rate": dividend_rate,
                "face_value": face_value,

                # ===== Live Metrics =====
                "day_high": day_high,
                "day_low": day_low,
                "volume": day_volume,

                # ===== AI Analysis =====
                "analysis": {
                    "data_points_analyzed": len(df),
                    "confidence": prediction["confidence"],
                    "recommendation": prediction["signal"],
                    "models_used": prediction["models_used"]
                },

                # ===== Technical =====
                "technical_metrics": {
                    "current_price": round(current_price, 2),
                    "target_price": prediction["target_price"],
                    "ma_20": round(ma_20, 2),
                    "ma_50": round(ma_50, 2),
                    "ma_200": round(ma_200, 2),
                    "rsi": round(current_rsi, 1),
                    "macd": round(current_macd, 2),
                    "signal_line": round(current_signal, 2),
                    "bb_upper": round(bb_upper.iloc[-1], 2),
                    "bb_middle": round(bb_middle.iloc[-1], 2),
                    "bb_lower": round(bb_lower.iloc[-1], 2),
                    "volatility": round(volatility, 1),
                    "price_52w_high": round(high_52w, 2),
                    "price_52w_low": round(low_52w, 2),
                    "price_position_52w": round(price_position_52w, 1),
                    "volume_ratio": round(volume_ratio, 1),
                },

                # ===== Risk =====
                "risk_metrics": {
                    "risk_level": prediction.get("risk_level", "MEDIUM"),
                    "volatility_percentile": min(99, max(1, int((volatility / 50) * 100))),
                    "predicted_return": prediction.get("predicted_return", 0)
                },

                "key_factors": key_factors,
                "future_outlook": prediction.get("future_outlook"),
                "ai_decision": prediction.get("ai_decision"),
                "ai_reason": prediction.get("ai_reason"),
                "model_details": prediction.get("model_details", {}),
                "indicators": {
                    "RSI": round(current_rsi, 1),
                    "MACD": round(current_macd, 2),
                    "MA 20": round(ma_20, 2),
                    "MA 50": round(ma_50, 2),
                    "MA 200": round(ma_200, 2),
                    "Volatility": f"{volatility:.1f}%",
                    "Vol Ratio": round(volume_ratio, 1)
                },
                "confidence_history": [
                    {"timestamp": p['timestamp'][11:16], "confidence": p['confidence']}
                    for p in quantum_ai.prediction_history
                    if p.get('symbol') == symbol
                ][-10:],
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def autocomplete():
    query = request.args.get("q", "").upper()
    db = load_all_stock_symbols() + PRELOADED_STOCKS
    matches = fuzzy_filter(query, db, limit=10)

    return jsonify([{
        "symbol": m["symbol"],
        "name": m["name"]
    } for m in matches])


def api_sector_chart_data():
    """Sector performance chart data derived from cached analytics."""
    try:
        with cache_lock:
            cached = STATE_CACHE.get("SECTOR_STATE", {}).get("analytics_snapshot") or {}
        sector_data = ((cached.get("data") or {}).get("sectoranalysis") or {})
        labels = []
        values = []
        for sector, metrics in sector_data.items():
            labels.append(sector)
            values.append(_safe_float((metrics or {}).get("avgchange", (metrics or {}).get("avgscore", 0)), 0.0))
        return jsonify({"success": True, "data": {"labels": labels, "values": values}})
    except Exception as e:
        logger.error(f"Sector chart error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def api_stock_history_chart(symbol):
    """Stock price history chart endpoint expected by chart.js."""
    try:
        period = request.args.get("period", "6mo")
        if not str(symbol).upper().endswith((".NS", ".BO")):
            symbol = f"{symbol}.NS"
        df = quantum_ai.get_live_stock_data(symbol, period=period)
        if df is None or df.empty or "Close" not in df:
            return jsonify({"success": True, "data": {"labels": [], "values": []}})
        tail = df.tail(120)
        labels = [idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx) for idx in tail.index]
        values = [round(_safe_float(v, 0.0), 2) for v in tail["Close"].tolist()]
        return jsonify({"success": True, "data": {"labels": labels, "values": values}})
    except Exception as e:
        logger.error(f"Stock history chart error for {symbol}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def api_risk_return_chart():
    """Risk/return scatter data for chart.js."""
    try:
        rows = _get_prediction_rows()
        points = []
        for row in rows:
            expected_return = _safe_float(row.get("predicted_return", row.get("return_percent", row.get("expected_return", 0))), 0.0)
            risk_raw = row.get("risk", row.get("risk_level", 0))
            if isinstance(risk_raw, str):
                risk = {"LOW": 1, "MEDIUM": 2, "NORMAL": 2, "HIGH": 3}.get(risk_raw.upper(), 2)
            else:
                risk = _safe_float(risk_raw, 0.0)
            points.append({"x": risk, "y": expected_return})
        return jsonify({"success": True, "data": {"points": points}})
    except Exception as e:
        logger.error(f"Risk-return chart error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def api_market_trends_chart():
    """Index trend data for the multi-line market trend chart."""
    try:
        index_map = {
            "nifty": "^NSEI",
            "sensex": "^BSESN",
            "banknifty": "^NSEBANK",
        }
        series = {}
        labels = []
        for key, symbol in index_map.items():
            df = quantum_ai.get_live_stock_data(symbol, period=request.args.get("period", "1mo"))
            if df is None or df.empty or "Close" not in df:
                series[key] = []
                continue
            tail = df.tail(60)
            if not labels:
                labels = [idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx) for idx in tail.index]
            series[key] = [round(_safe_float(v, 0.0), 2) for v in tail["Close"].tolist()]
        return jsonify({"success": True, "data": {"labels": labels, **series}})
    except Exception as e:
        logger.error(f"Market trends chart error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




MARKET_ROUTE_SPECS = [
    ("/api/search", "api_search", ["GET"]),
    ("/api/search/comprehensive", "comprehensive_search", ["GET"]),
    ("/api/market_universe", "market_debug", ["GET"]),
    ("/api/stocks", "get_stocks", ["GET"]),
    ("/api/user_tickers", "save_user_tickers", ["POST"]),
    ("/api/stock/<symbol>", "get_stock_prediction", ["GET"]),
    ("/api/stock/<symbol>/history", "api_stock_history_chart", ["GET"]),
    ("/api/stock/analysis/<symbol>", "stock_analysis", ["GET"]),
    ("/api/indicators/<symbol>", "get_technical_indicators", ["GET"]),
    ("/api/historical/<symbol>", "get_historical_data", ["GET"]),
    ("/api/compare", "compare_stocks", ["POST"]),
    ("/api/analytics/market-trends", "api_market_trends_chart", ["GET"]),
    ("/api/autocomplete", "autocomplete", ["GET"]),
    ("/api/analytics/sectors", "api_sector_chart_data", ["GET"]),
    ("/api/analytics/risk-return", "api_risk_return_chart", ["GET"]),
]


def create_market_blueprint(*, handlers: Mapping[str, object] | None = None) -> Blueprint:
    blueprint = Blueprint("market", __name__)
    handler_map = dict(handlers or {})

    for rule, handler_name, methods in MARKET_ROUTE_SPECS:
        view_func = handler_map.get(handler_name) or globals()[handler_name]
        if handler_name == "api_search" and "api_cache" in globals():
            view_func = api_cache(ttl=30)(view_func)
        blueprint.add_url_rule(
            rule,
            endpoint=handler_name,
            view_func=view_func,
            methods=methods,
        )

    return blueprint
