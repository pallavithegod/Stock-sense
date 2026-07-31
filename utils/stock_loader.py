import json
import logging
import os
import time

import pandas as pd
import requests

logger = logging.getLogger(__name__)

CACHE_TTL = int(os.getenv("STOCKSENSE_SYMBOL_CACHE_TTL", "86400"))
CACHE_FILE = os.path.join("data", "active_symbols_cache.json")

FALLBACK_SYMBOLS = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited", "exchange": "NSE"},
    {"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Limited", "exchange": "NSE"},
    {"symbol": "LICI.NS", "name": "Life Insurance Corporation of India", "exchange": "NSE"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Limited", "exchange": "NSE"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "exchange": "NSE"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Limited", "exchange": "NSE"},
    {"symbol": "ZOMATO.NS", "name": "Zomato Limited", "exchange": "NSE"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Limited", "exchange": "NSE"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Limited", "exchange": "NSE"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Limited", "exchange": "NSE"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank Limited", "exchange": "NSE"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries Limited", "exchange": "NSE"},
    {"symbol": "ONGC.NS", "name": "Oil & Natural Gas Corporation Limited", "exchange": "NSE"},
    {"symbol": "COALINDIA.NS", "name": "Coal India Limited", "exchange": "NSE"},
    {"symbol": "TITAN.NS", "name": "Titan Company Limited", "exchange": "NSE"},
]


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = float(data.get("timestamp", 0) or 0)
            symbols = data.get("symbols", [])
            if time.time() - ts < CACHE_TTL and isinstance(symbols, list):
                has_bse = any(
                    str(row.get("exchange", "")).upper() == "BSE"
                    or str(row.get("symbol", "")).upper().endswith(".BO")
                    for row in symbols
                    if isinstance(row, dict)
                )
                if not has_bse:
                    logger.warning("[STOCK_LOADER] Symbol cache missing BSE coverage; using available universe cache until BSE refresh completes")
                return symbols
        except Exception:
            pass
    return None


def _save_cache(symbols):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "symbols": symbols}, f)


def _normalize_row(symbol, name, exchange):
    base = str(symbol or "").strip().upper()
    if not base:
        return None

    exch = str(exchange or "").strip().upper()
    if exch == "NSE":
        suffix = ".NS"
    elif exch == "BSE":
        suffix = ".BO"
    else:
        suffix = ""

    if not base.endswith((".NS", ".BO")):
        base = f"{base}{suffix}" if suffix else base

    company = str(name or "").strip()
    if not company:
        company = base.replace(".NS", "").replace(".BO", "")

    return {"symbol": base, "name": company, "exchange": exch or "UNKNOWN"}


def _dedupe_symbols(rows):
    seen = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        if symbol not in seen:
            seen[symbol] = row
    return list(seen.values())


def _fetch_live_nse_active_symbols(limit=50000):
    """Fetch NSE equity list from official NSE CSVs (Main + SME)."""
    out = []
    # 1. Main Board
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df = pd.read_csv(url)
        for _, row in df.iterrows():
            item = _normalize_row(symbol=row.get("SYMBOL", ""), name=row.get("NAME OF COMPANY", ""), exchange="NSE")
            if item: out.append(item)
    except Exception as e:
        logger.debug(f"[STOCK_LOADER] NSE Main fetch failed: {e}")

    # 2. SME Board
    try:
        url_sme = "https://archives.nseindia.com/content/equities/EQUITY_SME_L.csv"
        df_sme = pd.read_csv(url_sme)
        for _, row in df_sme.iterrows():
            item = _normalize_row(symbol=row.get("SYMBOL", ""), name=row.get("NAME OF COMPANY", ""), exchange="NSE")
            if item: out.append(item)
    except Exception as e:
        logger.debug(f"[STOCK_LOADER] NSE SME fetch failed: {e}")

    return out[:limit]


def _fetch_live_bse_active_symbols(limit=50000):
    """Fetch BSE symbol list from BSE API with resilient field parsing."""
    try:
        url = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.bseindia.com/",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}

        candidates = []
        if isinstance(payload, dict):
            for key in ("Table", "table", "Data", "data", "results", "Result"):
                value = payload.get(key)
                if isinstance(value, list):
                    candidates = value
                    break
        elif isinstance(payload, list):
            candidates = payload

        out = []
        for row in candidates:
            if not isinstance(row, dict):
                continue
            symbol = (
                row.get("SecurityId")
                or row.get("securityId")
                or row.get("Security Code")
                or row.get("SecurityCode")
                or row.get("scrip_id")
                or row.get("SCRIP_ID")
                or row.get("ScripId")
                or row.get("Scrip ID")
                or row.get("ScripID")
                or row.get("ScripCode")
                or row.get("SCRIP_CODE")
                or row.get("SC_NAME")
                or row.get("scrip_cd")
                or row.get("SCRIP_CD")
                or row.get("BSECode")
            )
            name = (
                row.get("SecurityName")
                or row.get("securityName")
                or row.get("IssuerName")
                or row.get("CompanyName")
                or row.get("Company Name")
                or row.get("ScripName")
                or row.get("Scrip_Name")
                or row.get("scrip_name")
                or row.get("SHORT_NAME")
                or row.get("ShortName")
                or row.get("SC_NAME")
                or row.get("SecurityDesc")
            )
            item = _normalize_row(symbol=symbol, name=name, exchange="BSE")
            if item:
                out.append(item)

        return out[:limit]
    except Exception as e:
        logger.debug(f"[STOCK_LOADER] BSE fetch failed: {e}")
        # Try secondary endpoint for BSE
        try:
            url2 = "https://api.bseindia.com/BseIndiaAPI/api/EquityTicker/w?status=A"
            resp = requests.get(url2, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                out = []
                for row in data:
                    item = _normalize_row(symbol=row.get("scrip_id") or row.get("SCRIP_ID") or row.get("ScripId") or row.get("SecurityId") or row.get("SecurityCode"), 
                                          name=row.get("scrip_nm") or row.get("scrip_name") or row.get("ScripName") or row.get("SecurityName") or row.get("CompanyName"), 
                                          exchange="BSE")
                    if item: out.append(item)
                return out[:limit]
        except Exception:
            pass
        return []


def _fallback_symbols(limit):
    fallback = list(FALLBACK_SYMBOLS)
    # Add BSE mirror symbols for survivability when remote endpoints are unavailable.
    for row in FALLBACK_SYMBOLS:
        sym = str(row.get("symbol", "")).upper()
        if sym.endswith(".NS"):
            fallback.append({
                "symbol": sym.replace(".NS", ".BO"),
                "name": row.get("name", ""),
                "exchange": "BSE",
            })
    return _dedupe_symbols(fallback)[:limit]


def load_all_stock_symbols(limit=None):
    """
    Dynamic universe loader with NSE + BSE redundancy.
    1) Serve fresh cache
    2) Fetch NSE and BSE lists
    3) Dedupe, cap, cache
    4) Fallback to curated resilient list if both feeds fail
    """
    # allow configuration for very large universes; default to 50k to cover NSE+BSE
    default_limit = int(os.getenv("STOCKSENSE_SYMBOL_UNIVERSE_LIMIT", "50000"))
    limit = max(500, int(limit or default_limit))

    cached = _load_cache()
    if cached:
        return cached[:limit]

    nse_limit = max(300, int(limit * 0.6))
    bse_limit = max(200, limit - nse_limit)

    nse_rows = _fetch_live_nse_active_symbols(limit=nse_limit)
    bse_rows = _fetch_live_bse_active_symbols(limit=bse_limit)

    universe = _dedupe_symbols((nse_rows or []) + (bse_rows or []))
    if not universe:
        universe = _fallback_symbols(limit)

    universe = universe[:limit]
    _save_cache(universe)
    return universe
