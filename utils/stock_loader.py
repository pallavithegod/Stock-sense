import json
import os
import time

import pandas as pd
import requests

CACHE_TTL = int(os.getenv("NEXUS_SYMBOL_CACHE_TTL", "86400"))
CACHE_FILE = os.path.join("data", "active_symbols_cache.json")

FALLBACK_SYMBOLS = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"},
    {"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited", "exchange": "NSE"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "exchange": "NSE"},
]


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = float(data.get("timestamp", 0) or 0)
            symbols = data.get("symbols", [])
            if time.time() - ts < CACHE_TTL and isinstance(symbols, list):
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


def _fetch_live_nse_active_symbols(limit=3000):
    """Fetch NSE equity list from official NSE CSV."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df = pd.read_csv(url)

        out = []
        for _, row in df.iterrows():
            item = _normalize_row(
                symbol=row.get("SYMBOL", ""),
                name=row.get("NAME OF COMPANY", ""),
                exchange="NSE",
            )
            if item:
                out.append(item)

        return out[:limit]
    except Exception:
        return []


def _fetch_live_bse_active_symbols(limit=3000):
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
                or row.get("scrip_id")
                or row.get("ScripID")
                or row.get("SC_NAME")
                or row.get("scrip_cd")
                or row.get("SCRIP_CD")
            )
            name = (
                row.get("SecurityName")
                or row.get("securityName")
                or row.get("IssuerName")
                or row.get("SC_NAME")
                or row.get("SecurityDesc")
            )
            item = _normalize_row(symbol=symbol, name=name, exchange="BSE")
            if item:
                out.append(item)

        return out[:limit]
    except Exception:
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
    default_limit = int(os.getenv("NEXUS_SYMBOL_UNIVERSE_LIMIT", "5000"))
    limit = max(200, int(limit or default_limit))

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
