# -*- coding: utf-8 -*-
# ============================================================
# StockSense real-time stream engine
# ============================================================

from utils import encoding
import hashlib
import json
import logging
import time
from threading import Thread, Lock
from datetime import datetime, timezone

from market_intelligence import (
    get_market_status,
    get_market_phase,
    market_db,
)

logger = logging.getLogger(__name__)


class LiveDataProvider:
    def __init__(self, fetch_fn):
        self.fetch_fn = fetch_fn

    def snapshot(self):
        return self.fetch_fn()


class WebSocketManager:
    def __init__(self, provider: LiveDataProvider, socketio=None):
        self.provider = provider
        self.socketio = socketio
        self.clients = set()
        self.lock = Lock()
        self._running = False
        self.broadcast_interval = 2.0
        self.last_payload = None
        self.portfolio_manager = None
        self.enricher = None

        # Stabilization controls
        self.state_cache = None
        self.drop_unchanged_payloads = True
        self.max_heartbeat_gap_sec = 5.0
        self._last_emit_at = 0.0
        self._last_payload_hash = None
        self._emit_latency_ms = 0.0
        self._inflight_events = 0

    def start(self):
        """Starts the ai_state broadcast loop."""
        if self._running:
            return

        self._running = True
        logger.info("WebSocketManager loop starting")

        def runner():
            while self._running:
                try:
                    self.broadcast_ai_state()
                except Exception as e:
                    logger.error(f"WS loop error: {e}")

                if self.socketio:
                    self.socketio.sleep(getattr(self, "broadcast_interval", 1.0))
                else:
                    time.sleep(getattr(self, "broadcast_interval", 1.0))

        if self.socketio:
            self.socketio.start_background_task(runner)
        else:
            self.thread = Thread(target=runner, daemon=True)
            self.thread.start()

    def broadcast_ai_state(self):
        """Single iteration of AI state generation + broadcast."""
        try:
            phase = get_market_phase("NSE")
            market_payload = self.provider.snapshot() or {}

            volatility = self._estimate_volatility(market_payload)
            market_db.log_volatility("NSE", volatility)

            if phase == "OPEN":
                self.broadcast_interval = max(0.8, 2.5 - volatility)
            else:
                self.broadcast_interval = min(10.0, 4.0 + volatility)

            rich_ai_state = market_payload.get("ai_state", {})
            system_health = market_payload.get("system_health", {})
            risk_state = market_payload.get("risk_state", {})

            ai_state = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market": {
                    "phase": phase,
                    "status": get_market_status("NSE"),
                    "volatility": round(volatility, 4),
                    "indices": market_payload.get("live_indices", market_payload.get("indices", [])),
                    "correlation": self._cross_market_signal(market_payload),
                },
                "ai_engine": {
                    "interval": round(self.broadcast_interval, 2),
                    "learning_active": True,
                    "accuracy": rich_ai_state.get("accuracy_rate", rich_ai_state.get("accuracy", 0)),
                    "models_active": rich_ai_state.get("active_models", []),
                    "entropy": rich_ai_state.get("system_entropy", 0),
                    "latency": rich_ai_state.get("network_latency", 0),
                    "cpu_load": rich_ai_state.get("cpu_load", 0),
                    "regime": rich_ai_state.get("current_regime", "UNKNOWN"),
                },
                "ai_performance": rich_ai_state,
                "portfolio_intelligence": rich_ai_state.get("portfolio_intelligence", {"positions": []}),
                "system_health": system_health,
                "risk_state": risk_state,
            }

            self._broadcast(ai_state)
            self.last_payload = ai_state

        except Exception as e:
            logger.error(f"Broadcast logic failed: {e}", exc_info=True)

    def _estimate_volatility(self, payload):
        try:
            indices = payload.get("live_indices", [])
            if not indices:
                indices = payload.get("indices", [])
            if not indices:
                return 0.1

            changes = [abs(i.get("change_percent", i.get("percent", i.get("change", 0)))) for i in indices]
            if not changes:
                return 0.1
            return min(2.0, sum(changes) / max(len(changes), 1))
        except Exception:
            return 0.1

    def _cross_market_signal(self, payload):
        try:
            indices = payload.get("live_indices", payload.get("indices", []))
            if not indices:
                return "NEUTRAL"
            score = sum(1 if i.get("change_points", i.get("changepoints", 0)) > 0 else -1 for i in indices)
            return "RISK_ON" if score > 0 else "RISK_OFF"
        except Exception:
            return "NEUTRAL"

    def _broadcast(self, payload):
        """Emit AI state to all connected clients."""
        self._inflight_events += 1
        try:
            if not self.socketio:
                return

            now = time.time()
            payload_json = json.dumps(payload, sort_keys=True, default=str)
            payload_hash = hashlib.sha1(payload_json.encode("utf-8")).hexdigest()
            unchanged = payload_hash == self._last_payload_hash
            silent_gap = now - self._last_emit_at

            if self.drop_unchanged_payloads and unchanged and silent_gap < self.max_heartbeat_gap_sec:
                return

            emit_started = time.perf_counter()
            self.socketio.emit("ai_state", payload)
            self._emit_latency_ms = round((time.perf_counter() - emit_started) * 1000.0, 2)
            self._last_emit_at = now
            self._last_payload_hash = payload_hash

            if isinstance(self.state_cache, dict):
                health = self.state_cache.setdefault("SYSTEM_HEALTH", {})
                health["websocket_latency_ms"] = self._emit_latency_ms
                health["event_queue_depth"] = max(0, int(self._inflight_events) - 1)
                health["connected_clients"] = len(self.clients)
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
        finally:
            self._inflight_events = max(0, self._inflight_events - 1)

    def get_dashboard_data(self):
        return self.last_payload if self.last_payload else {
            "status": "INITIALIZING",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def register_client(self, cid):
        with self.lock:
            self.clients.add(cid)

    def unregister_client(self, cid):
        with self.lock:
            self.clients.discard(cid)

    def shutdown(self):
        self._running = False
