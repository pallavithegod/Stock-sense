"""Authoritative SQLite schema definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


LATEST_SCHEMA_VERSION = 1

AUXILIARY_DATABASE_OWNERSHIP = {
    "stocksense.db": "Authoritative application data: portfolio, predictions, model metrics, retention archives.",
    "market_intelligence.db": "Separate market-provider cache. Kept separate so provider refresh can be rebuilt independently.",
    "adaptive_thresholds.db": "Legacy adaptive-threshold store. New code maps rows through backend.domain.predictions.adaptive_thresholds before use.",
    "prediction_audit.jsonl": "Append-only audit/export log. SQLite prediction_events owns deduplication inside stocksense.db.",
}


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[object], None]


def _table_exists(conn, table: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone())


def _columns(conn, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}


def _add_missing_column(conn, table: str, column: str, definition: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN {column} {definition}')


def _upgrade_legacy_tables(conn) -> None:
    if _table_exists(conn, "predictions"):
        prediction_columns = {
            "fingerprint": "TEXT",
            "horizon": "TEXT",
            "as_of": "TEXT",
            "expected_return": "REAL",
            "risk": "TEXT",
            "source_type": "TEXT NOT NULL DEFAULT 'unavailable'",
            "provider": "TEXT NOT NULL DEFAULT 'legacy_database'",
            "data_quality": "TEXT NOT NULL DEFAULT 'unavailable'",
            "model_version": "TEXT",
            "feature_version": "TEXT",
            "trained_at": "TEXT",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "matured_at": "TEXT",
            "evaluated_at": "TEXT",
            "directional_accuracy": "REAL",
            "target_error": "REAL",
            "calibration_error": "REAL",
            "coverage": "REAL",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        }
        for column, definition in prediction_columns.items():
            _add_missing_column(conn, "predictions", column, definition)
        conn.execute("UPDATE predictions SET fingerprint = 'legacy-' || id WHERE fingerprint IS NULL OR fingerprint = ''")
        conn.execute("UPDATE predictions SET horizon = '6m' WHERE horizon IS NULL OR horizon = ''")
        conn.execute("UPDATE predictions SET as_of = COALESCE(timestamp, created_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE as_of IS NULL OR as_of = ''")
        conn.execute("UPDATE predictions SET timestamp = COALESCE(timestamp, as_of, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE timestamp IS NULL OR timestamp = ''")
        conn.execute("UPDATE predictions SET created_at = COALESCE(created_at, timestamp, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE created_at IS NULL OR created_at = ''")
        conn.execute("UPDATE predictions SET updated_at = COALESCE(updated_at, timestamp, created_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE updated_at IS NULL OR updated_at = ''")

    if _table_exists(conn, "model_performance"):
        model_columns = {
            "model_version": "TEXT NOT NULL DEFAULT 'legacy'",
            "feature_version": "TEXT NOT NULL DEFAULT 'legacy'",
            "directional_accuracy": "REAL",
            "target_error": "REAL",
            "calibration_error": "REAL",
            "coverage": "REAL",
            "metrics_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for column, definition in model_columns.items():
            _add_missing_column(conn, "model_performance", column, definition)
        conn.execute("UPDATE model_performance SET directional_accuracy = accuracy / 100.0 WHERE directional_accuracy IS NULL AND accuracy IS NOT NULL AND accuracy > 1")
        conn.execute("UPDATE model_performance SET directional_accuracy = accuracy WHERE directional_accuracy IS NULL AND accuracy IS NOT NULL AND accuracy <= 1")


def _create_core_schema(conn) -> None:
    _upgrade_legacy_tables(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            quantity REAL NOT NULL CHECK(quantity > 0),
            avg_price REAL NOT NULL CHECK(avg_price > 0),
            added_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
            quantity REAL NOT NULL CHECK(quantity > 0),
            price REAL NOT NULL CHECK(price > 0),
            trade_date TEXT NOT NULL,
            fees REAL NOT NULL DEFAULT 0 CHECK(fees >= 0),
            notes TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            buy_txn_id INTEGER,
            buy_date TEXT NOT NULL,
            buy_price REAL NOT NULL CHECK(buy_price > 0),
            original_quantity REAL NOT NULL CHECK(original_quantity > 0),
            remaining_quantity REAL NOT NULL CHECK(remaining_quantity >= 0 AND remaining_quantity <= original_quantity),
            created_at TEXT NOT NULL,
            FOREIGN KEY(buy_txn_id) REFERENCES portfolio_transactions(id)
        );

        CREATE TABLE IF NOT EXISTS portfolio_realized_gains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            sell_txn_id INTEGER NOT NULL,
            lot_id INTEGER NOT NULL,
            quantity REAL NOT NULL CHECK(quantity > 0),
            buy_price REAL NOT NULL CHECK(buy_price > 0),
            sell_price REAL NOT NULL CHECK(sell_price > 0),
            gain REAL NOT NULL,
            gain_percent REAL,
            holding_days INTEGER CHECK(holding_days IS NULL OR holding_days >= 0),
            gain_type TEXT NOT NULL CHECK(gain_type IN ('STCG', 'LTCG', 'UNKNOWN')),
            realized_at TEXT NOT NULL,
            FOREIGN KEY(sell_txn_id) REFERENCES portfolio_transactions(id),
            FOREIGN KEY(lot_id) REFERENCES portfolio_lots(id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            horizon TEXT NOT NULL,
            as_of TEXT NOT NULL,
            current_price REAL CHECK(current_price IS NULL OR current_price > 0),
            target_price REAL CHECK(target_price IS NULL OR target_price > 0),
            predicted_price REAL CHECK(predicted_price IS NULL OR predicted_price > 0),
            expected_return REAL,
            signal TEXT,
            confidence REAL CHECK(confidence IS NULL OR (confidence >= 0 AND confidence <= 100)),
            risk TEXT,
            source_type TEXT NOT NULL CHECK(source_type IN (
                'ml_model',
                'statistical',
                'heuristic',
                'sentiment_llm',
                'synthetic_demo',
                'presentation_intelligence',
                'unavailable'
            )),
            provider TEXT NOT NULL,
            data_quality TEXT NOT NULL,
            model_version TEXT,
            feature_version TEXT,
            trained_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            models_used TEXT NOT NULL DEFAULT '[]',
            timestamp TEXT NOT NULL,
            matured_at TEXT,
            evaluated_at TEXT,
            actual_price REAL CHECK(actual_price IS NULL OR actual_price > 0),
            prediction_error REAL CHECK(prediction_error IS NULL OR prediction_error >= 0),
            directional_accuracy REAL CHECK(directional_accuracy IS NULL OR directional_accuracy IN (0, 1)),
            target_error REAL CHECK(target_error IS NULL OR target_error >= 0),
            calibration_error REAL CHECK(calibration_error IS NULL OR calibration_error >= 0),
            coverage REAL CHECK(coverage IS NULL OR (coverage >= 0 AND coverage <= 1)),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS prediction_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT NOT NULL UNIQUE,
            prediction_fingerprint TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            FOREIGN KEY(prediction_fingerprint) REFERENCES predictions(fingerprint)
        );

        CREATE TABLE IF NOT EXISTS model_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            feature_version TEXT NOT NULL,
            accuracy REAL,
            weight REAL,
            directional_accuracy REAL CHECK(directional_accuracy IS NULL OR (directional_accuracy >= 0 AND directional_accuracy <= 1)),
            target_error REAL CHECK(target_error IS NULL OR target_error >= 0),
            calibration_error REAL CHECK(calibration_error IS NULL OR calibration_error >= 0),
            coverage REAL CHECK(coverage IS NULL OR (coverage >= 0 AND coverage <= 1)),
            metrics_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            UNIQUE(model_name, model_version, feature_version)
        );

        CREATE TABLE IF NOT EXISTS dynamic_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT,
            sector TEXT,
            last_updated TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prediction_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS model_performance_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS volatility_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_symbol_as_of
            ON predictions(symbol, as_of DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_fingerprint_unique
            ON predictions(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_predictions_maturity
            ON predictions(matured_at, evaluated_at);
        CREATE INDEX IF NOT EXISTS idx_predictions_model
            ON predictions(model_version, feature_version);
        CREATE INDEX IF NOT EXISTS idx_prediction_events_fingerprint
            ON prediction_events(prediction_fingerprint);
        CREATE INDEX IF NOT EXISTS idx_model_performance_model
            ON model_performance(model_name, model_version, feature_version);
        CREATE INDEX IF NOT EXISTS idx_portfolio_txn_symbol_date
            ON portfolio_transactions(symbol, trade_date);
        CREATE INDEX IF NOT EXISTS idx_portfolio_lot_symbol_open
            ON portfolio_lots(symbol, remaining_quantity, buy_date);
        CREATE INDEX IF NOT EXISTS idx_portfolio_realized_symbol_date
            ON portfolio_realized_gains(symbol, realized_at);
        CREATE INDEX IF NOT EXISTS idx_volatility_logs_symbol_created
            ON volatility_logs(symbol, created_at);
        """
    )


MIGRATIONS = (
    Migration(1, "core_schema_v1", _create_core_schema),
)

REQUIRED_TABLES = {
    "schema_migrations",
    "portfolio",
    "portfolio_transactions",
    "portfolio_lots",
    "portfolio_realized_gains",
    "predictions",
    "prediction_events",
    "model_performance",
    "dynamic_symbols",
    "prediction_archive",
    "model_performance_archive",
    "volatility_logs",
}

REQUIRED_COLUMNS = {
    "portfolio": {"id", "symbol", "quantity", "avg_price", "added_date"},
    "predictions": {
        "id",
        "fingerprint",
        "symbol",
        "horizon",
        "as_of",
        "current_price",
        "target_price",
        "expected_return",
        "signal",
        "confidence",
        "source_type",
        "provider",
        "data_quality",
        "model_version",
        "feature_version",
        "metadata_json",
        "matured_at",
        "evaluated_at",
        "directional_accuracy",
        "target_error",
        "calibration_error",
        "coverage",
    },
    "prediction_events": {"id", "idempotency_key", "prediction_fingerprint", "event_type", "payload_json"},
    "model_performance": {
        "id",
        "model_name",
        "model_version",
        "feature_version",
        "directional_accuracy",
        "target_error",
        "calibration_error",
        "coverage",
        "metrics_json",
        "updated_at",
    },
    "portfolio_transactions": {"id", "symbol", "side", "quantity", "price", "trade_date", "fees", "created_at"},
    "portfolio_lots": {"id", "symbol", "buy_txn_id", "buy_date", "buy_price", "original_quantity", "remaining_quantity", "created_at"},
}
