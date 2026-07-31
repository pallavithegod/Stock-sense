# -*- coding: utf-8 -*-
# ============================================================
# StockSense market intelligence engine
# Single File | Self-Healing | Global | Production Ready
# ============================================================
from utils import encoding  # enforce global UTF-8 at import time

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging
import sqlite3
import os
import threading
import time

logger = logging.getLogger(__name__)

# ============================================================
# PATHS
# ============================================================

DATA_DIR = "data"
DB_PATH = os.getenv(
    "STOCKSENSE_MARKET_DB_PATH",
    os.path.join(DATA_DIR, "market_intelligence.db"),
)

# ============================================================
# MARKET DATABASE (PRIVATE, NO CONFLICT)
# ============================================================

class MarketDB:
    def __init__(self):
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._auto_seed()

    def _init_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS market_hours (
            market TEXT PRIMARY KEY,
            timezone TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS market_holidays (
            market TEXT,
            date TEXT,
            description TEXT,
            PRIMARY KEY (market, date)
        );

        CREATE TABLE IF NOT EXISTS volatility_log (
            market TEXT,
            value REAL,
            timestamp TEXT
        );
        """)
        self.conn.commit()

    def _auto_seed(self):
        count = self.conn.execute(
            "SELECT COUNT(*) FROM market_hours"
        ).fetchone()[0]

        if count == 0:
            logger.warning("⚠️ Bootstrapping default global market configs")
            now = datetime.now(timezone.utc).isoformat()
            self.conn.executemany("""
            INSERT INTO market_hours VALUES (?,?,?,?,?)
            """, [
                ("NSE", "Asia/Kolkata", "09:15", "15:30", now),
                ("BSE", "Asia/Kolkata", "09:15", "15:30", now),
                ("NYSE", "America/New_York", "09:30", "16:00", now),
                ("NASDAQ", "America/New_York", "09:30", "16:00", now),
                ("SGX", "Asia/Singapore", "09:00", "17:00", now),
            ])
            self.conn.commit()

    # ---------------- READ ----------------

    def get_market_hours(self, market):
        row = self.conn.execute(
            "SELECT * FROM market_hours WHERE market=?",
            (market.upper(),)
        ).fetchone()
        return dict(row) if row else None

    def get_market_holidays(self, market):
        rows = self.conn.execute(
            "SELECT date FROM market_holidays WHERE market=?",
            (market.upper(),)
        ).fetchall()
        return {r["date"] for r in rows}

    # ---------------- WRITE ----------------

    def upsert_holiday(self, market, date, description):
        self.conn.execute("""
        INSERT OR REPLACE INTO market_holidays
        VALUES (?,?,?)
        """, (market.upper(), date, description))
        self.conn.commit()

    def log_volatility(self, market, value):
        self.conn.execute("""
        INSERT INTO volatility_log VALUES (?,?,?)
        """, (market.upper(), value, datetime.now(timezone.utc).isoformat()))
        self.conn.commit()


# ============================================================
# SINGLE DB INSTANCE
# ============================================================

_market_db = MarketDB()
# Public, read-only alias (for websocket, analytics, etc.)
market_db = _market_db

# ------------------------------------------------------------
# DATABASE EXTENSIONS (AUTO-CREATED)
# ------------------------------------------------------------

def _init_advanced_tables():
    market_db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS market_bias_log (
        date TEXT PRIMARY KEY,
        bias TEXT,
        confidence REAL,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS global_influence_log (
        date TEXT PRIMARY KEY,
        dominant_market TEXT,
        influence REAL,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS explainability_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        explanation TEXT,
        confidence REAL,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS anomaly_log (
        date TEXT PRIMARY KEY,
        anomaly_score REAL,
        detected INTEGER,
        created_at TEXT
    );
    """)
    market_db.conn.commit()

_init_advanced_tables()

# ============================================================
# MARKET CONFIG
# ============================================================

def get_market_config(market_name="NSE"):
    cfg = _market_db.get_market_hours(market_name)
    if not cfg:
        raise RuntimeError(f"Market config missing for {market_name}")
    return cfg

# ============================================================
# MARKET STATUS (FRONTEND SAFE)
# ============================================================

def get_market_status(market_name="NSE"):
    try:
        cfg = get_market_config(market_name)
        tz = ZoneInfo(cfg["timezone"])
        now = datetime.now(tz)

        session_time = now.strftime("%H:%M:%S")
        today = now.strftime("%d-%b-%Y").upper()

        open_t = datetime.strptime(cfg["open_time"], "%H:%M").time()
        close_t = datetime.strptime(cfg["close_time"], "%H:%M").time()

        market_open = datetime.combine(now.date(), open_t, tzinfo=tz)
        market_close = datetime.combine(now.date(), close_t, tzinfo=tz)

        holidays = _market_db.get_market_holidays(market_name)
        is_weekday = now.weekday() < 5

        is_open = (
            is_weekday and
            today not in holidays and
            market_open <= now <= market_close
        )

        # Next open date (DD-MMM-YYYY)
        probe = now + timedelta(days=1)
        next_open = "--"
        for _ in range(15):
            d = probe.strftime("%d-%b-%Y").upper()
            if probe.weekday() < 5 and d not in holidays:
                next_open = d
                break
            probe += timedelta(days=1)

        return {
            "market": market_name.upper(),
            "status": "OPEN" if is_open else "CLOSED",
            "session": session_time,
            "market_open_time": cfg["open_time"],
            "market_close_time": cfg["close_time"],
            "next_open": next_open,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Market status error [{market_name}]: {e}", exc_info=True)
        return {
            "market": market_name.upper(),
            "status": "UNKNOWN",
            "session": "--",
            "market_open_time": "--",
            "market_close_time": "--",
            "next_open": "--",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================
# MARKET PHASE (AI-CRITICAL)
# ============================================================

def get_market_phase(market_name="NSE"):
    status = get_market_status(market_name)
    if status["status"] != "OPEN":
        return "CLOSED"

    cfg = get_market_config(market_name)
    tz = ZoneInfo(cfg["timezone"])
    now = datetime.now(tz).time()

    open_t = datetime.strptime(cfg["open_time"], "%H:%M").time()
    close_t = datetime.strptime(cfg["close_time"], "%H:%M").time()

    pre_open = (
        datetime.combine(datetime.today(), open_t) - timedelta(minutes=30)
    ).time()

    post_close = (
        datetime.combine(datetime.today(), close_t) + timedelta(minutes=30)
    ).time()

    if pre_open <= now < open_t:
        return "PRE_OPEN"
    elif open_t <= now <= close_t:
        return "OPEN"
    elif close_t < now <= post_close:
        return "POST_CLOSE"
    return "CLOSED"

# ============================================================
# AI BEHAVIOR SWITCH
# ============================================================

def apply_market_ai_policy(quantum_ai, market_name="NSE"):
    phase = get_market_phase(market_name)
    regime = detect_market_regime(market_name)

    confidence = 1.0

    if regime == "HIGH_VOLATILITY":
        confidence *= 0.75
    elif regime == "LOW_VOLATILITY":
        confidence *= 1.1

    if phase == "OPEN":
        quantum_ai.set_mode(predictions=True, retraining=False, confidence_weight=confidence)

    elif phase == "PRE_OPEN":
        quantum_ai.set_mode(predictions=True, retraining=False, confidence_weight=confidence * 0.8)

    elif phase == "POST_CLOSE":
        quantum_ai.set_mode(predictions=False, retraining=True, confidence_weight=confidence * 0.6)

    else:
        quantum_ai.set_mode(predictions=False, retraining=True, confidence_weight=confidence * 0.4)

    logger.info(
        f"🧠 AI Policy | Phase={phase} | Regime={regime} | Confidence={confidence:.2f}"
    )


# ============================================================
# HOLIDAY AUTO-SYNC (OFFICIAL API READY)
# ============================================================
import requests

def fetch_nse_holidays_api():
    """
    Fetch NSE holidays from official NSE endpoint.
    Returns: [{date: 'DD-MMM-YYYY', name: 'Holiday Name'}]
    """
    url = "https://www.nseindia.com/api/holiday-master?type=trading"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    holidays = []
    for h in data.get("CM", []):
        holidays.append({
            "date": datetime.strptime(h["tradingDate"], "%d-%b-%Y").strftime("%d-%b-%Y").upper(),
            "name": h["description"]
        })
    return holidays

import threading
import time
import logging
import random

logger = logging.getLogger(__name__)

_stop_event = threading.Event()

def _holiday_sync_loop():
    while not _stop_event.is_set():
        try:
            holidays = fetch_nse_holidays_api()

            for h in holidays:
                _market_db.upsert_holiday(
                    exchange="NSE",
                    date=h["date"],
                    name=h["name"]
                )

            logger.info("[DATA] NSE holidays synced (%d)", len(holidays))

            # Success → daily sync with small jitter
            sleep_seconds = 24 * 60 * 60 + random.randint(0, 900)
            _stop_event.wait(sleep_seconds)

        except Exception:
            logger.exception("❌ NSE holiday sync failed")

            # Failure → retry with delay + jitter
            sleep_seconds = 6 * 60 * 60 + random.randint(0, 900)
            _stop_event.wait(sleep_seconds)


def start_holiday_sync():
    thread = threading.Thread(
        target=_holiday_sync_loop,
        name="nse-holiday-sync",
        daemon=True
    )
    thread.start()
    return thread


def stop_holiday_sync():
    _stop_event.set()

def detect_market_regime(market="NSE"):
    """
    Determines market regime using volatility history.
    """
    try:
        rows = _market_db.conn.execute("""
            SELECT value FROM volatility_log
            WHERE market=?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (market.upper(),)).fetchall()

        if len(rows) < 10:
            return "NORMAL"

        values = [r["value"] for r in rows]
        avg_vol = sum(values) / len(values)

        if avg_vol > 0.035:
            return "HIGH_VOLATILITY"
        elif avg_vol < 0.015:
            return "LOW_VOLATILITY"
        return "NORMAL"

    except Exception:
        return "NORMAL"

def get_market_intelligence_summary(market="NSE"):
    status = get_market_status(market)
    phase = get_market_phase(market)
    regime = detect_market_regime(market)

    return {
        "market": market,
        "status": status["status"],
        "phase": phase,
        "regime": regime,
        "session": status["session"],
        "next_open": status["next_open"],
        "open_time": status["market_open_time"],
        "close_time": status["market_close_time"]
    }

# ------------------------------------------------------------
# 🔮 NEXT-DAY OPENING BIAS (UP / DOWN / FLAT)
# ------------------------------------------------------------

def compute_next_day_bias(indices):
    """
    Learns from recent index momentum and volatility.
    """
    try:
        score = sum(i["percent"] for i in indices)
        vol = sum(abs(i["percent"]) for i in indices) / max(len(indices), 1)

        if score > 0.4:
            bias = "UP"
        elif score < -0.4:
            bias = "DOWN"
        else:
            bias = "FLAT"

        confidence = min(0.95, max(0.55, abs(score) / (vol + 0.01)))

        market_db.conn.execute("""
        INSERT OR REPLACE INTO market_bias_log
        VALUES (?,?,?,?)
        """, (
            datetime.now(timezone.utc).date().isoformat(),
            bias,
            confidence,
            datetime.now(timezone.utc).isoformat()
        ))
        market_db.conn.commit()

        return bias, confidence

    except Exception:
        return "FLAT", 0.55

# ------------------------------------------------------------
# 🌍 GLOBAL MARKET INFLUENCE (DOW → NSE GAP LOGIC)
# ------------------------------------------------------------

def compute_global_influence(global_indices):
    """
    Measures how US markets influence next NSE session.
    """
    try:
        influence_score = sum(i["percent"] for i in global_indices)
        dominant = max(global_indices, key=lambda x: abs(x["percent"]))["name"]

        influence = max(-1.0, min(1.0, influence_score / 3))

        market_db.conn.execute("""
        INSERT OR REPLACE INTO global_influence_log
        VALUES (?,?,?,?)
        """, (
            datetime.now(timezone.utc).date().isoformat(),
            dominant,
            influence,
            datetime.now(timezone.utc).isoformat()
        ))
        market_db.conn.commit()

        return dominant, influence

    except Exception:
        return "UNKNOWN", 0.0

# ------------------------------------------------------------
# 📊 EXPLAINABLE AI TIMELINE (WHY BUY / SELL)
# ------------------------------------------------------------

def log_explainability(symbol, factors, confidence):
    """
    Stores human-readable AI reasoning.
    """
    explanation = " | ".join(factors)

    market_db.conn.execute("""
    INSERT INTO explainability_log
    (symbol, explanation, confidence, created_at)
    VALUES (?,?,?,?)
    """, (
        symbol,
        explanation,
        confidence,
        datetime.now(timezone.utc).isoformat()
    ))
    market_db.conn.commit()

    return explanation

# ------------------------------------------------------------
# 🛡️ MARKET ANOMALY DETECTION (PRE-OPEN ALERTS)
# ------------------------------------------------------------

def detect_market_anomaly(indices):
    """
    Detects abnormal volatility or correlation breaks.
    """
    try:
        changes = [abs(i["percent"]) for i in indices]
        avg = sum(changes) / max(len(changes), 1)
        variance = sum((c - avg) ** 2 for c in changes) / max(len(changes), 1)
        anomaly_score = math.sqrt(variance)

        detected = 1 if anomaly_score > 1.2 else 0

        market_db.conn.execute("""
        INSERT OR REPLACE INTO anomaly_log
        VALUES (?,?,?,?)
        """, (
            datetime.now(timezone.utc).date().isoformat(),
            anomaly_score,
            detected,
            datetime.now(timezone.utc).isoformat()
        ))
        market_db.conn.commit()

        return anomaly_score, detected

    except Exception:
        return 0.0, 0

# ------------------------------------------------------------
# 🔗 SINGLE ENTRY POINT (USED BY DASHBOARD PIPELINE)
# ------------------------------------------------------------

def enrich_market_intelligence(payload):
    """
    This function ENRICHES existing dashboard payload.
    UI automatically reflects behavior changes.
    """

    indices = payload.get("indices", [])
    global_indices = payload.get("global_indices", indices)

    # 1️⃣ Next-day bias
    bias, bias_conf = compute_next_day_bias(indices)

    # 2️⃣ Global influence
    dominant, influence = compute_global_influence(global_indices)

    # 3️⃣ Anomaly detection
    anomaly_score, anomaly = detect_market_anomaly(indices)

    payload["market"]["bias"] = bias
    payload["market"]["bias_confidence"] = round(bias_conf, 2)

    payload["ai_explain"] = {
        "global_influence": dominant,
        "influence_score": round(influence, 2),
        "anomaly": bool(anomaly),
        "anomaly_score": round(anomaly_score, 2)
    }

    return payload

def normalize_market_df(df, symbol=None):
    """
    Universal data integrity gate.
    Guarantees df is safe for ALL downstream models.
    """
    if df is None:
        raise ValueError("Market data is None")

    if not hasattr(df, 'empty') or df.empty:
        raise ValueError("Market data is empty")

    if 'Close' not in df.columns:
        raise ValueError("Missing Close column")

    # Force numeric, drop poisoned rows
    df = df.copy()
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df.dropna(subset=['Close'], inplace=True)

    if df.empty:
        raise ValueError("No valid Close prices after normalization")

    return df

# ============================================================
# PUBLIC API
# ============================================================

__all__ = [
    "get_market_status",
    "get_market_phase",
    "apply_market_ai_policy",
    "get_market_config",
    "compute_next_day_bias",
    "compute_global_influence",
    "log_explainability",
    "detect_market_anomaly",
    "enrich_market_intelligence"
]
