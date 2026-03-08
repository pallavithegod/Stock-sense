# -*- coding: utf-8 -*-
"""
NEXUS AI QUANTUM™ - Dynamic Database Manager
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager
import logging
import requests  # For optional automatic symbol info fetching

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class DatabaseManager:
    _initialized = False

    def __init__(self, db_path='data/nexus.db'):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        if not DatabaseManager._initialized:
            self.init_database()
            logger.info(f"Database initialized at: {db_path}")
            DatabaseManager._initialized = True

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    # ----------------------------
    # DATABASE INITIALIZATION
    # ----------------------------
    def init_database(self):
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    quantity INTEGER NOT NULL,
                    avg_price REAL NOT NULL,
                    added_date TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    predicted_price REAL,
                    current_price REAL,
                    target_price REAL,
                    signal TEXT,
                    confidence REAL,
                    models_used TEXT,
                    timestamp TEXT NOT NULL,
                    actual_price REAL,
                    prediction_error REAL
                );

                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    accuracy REAL,
                    weight REAL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dynamic_symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT,
                    sector TEXT,
                    last_updated TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS portfolio_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    trade_date TEXT NOT NULL,
                    fees REAL DEFAULT 0,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS portfolio_lots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    buy_txn_id INTEGER,
                    buy_date TEXT NOT NULL,
                    buy_price REAL NOT NULL,
                    original_quantity REAL NOT NULL,
                    remaining_quantity REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(buy_txn_id) REFERENCES portfolio_transactions(id)
                );

                CREATE TABLE IF NOT EXISTS portfolio_realized_gains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    sell_txn_id INTEGER NOT NULL,
                    lot_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    buy_price REAL NOT NULL,
                    sell_price REAL NOT NULL,
                    gain REAL NOT NULL,
                    gain_percent REAL,
                    holding_days INTEGER,
                    gain_type TEXT NOT NULL,
                    realized_at TEXT NOT NULL,
                    FOREIGN KEY(sell_txn_id) REFERENCES portfolio_transactions(id),
                    FOREIGN KEY(lot_id) REFERENCES portfolio_lots(id)
                );

                CREATE INDEX IF NOT EXISTS idx_portfolio_txn_symbol_date
                    ON portfolio_transactions(symbol, trade_date);
                CREATE INDEX IF NOT EXISTS idx_portfolio_lot_symbol_open
                    ON portfolio_lots(symbol, remaining_quantity, buy_date);
                CREATE INDEX IF NOT EXISTS idx_portfolio_realized_symbol_date
                    ON portfolio_realized_gains(symbol, realized_at);
            ''')
            self._migrate_legacy_portfolio_to_lots(conn)

    def _to_iso_datetime(self, value=None):
        if value is None or value == "":
            return datetime.now().isoformat()
        try:
            text = str(value).strip()
            if len(text) == 10 and text[4] == '-' and text[7] == '-':
                return f"{text}T00:00:00"
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None).isoformat()
        except Exception:
            return datetime.now().isoformat()

    def _migrate_legacy_portfolio_to_lots(self, conn):
        """
        One-time/continuous safe migration:
        If summary rows exist but no open lots exist for symbol, seed a single opening lot.
        """
        rows = conn.execute('SELECT symbol, quantity, avg_price, added_date FROM portfolio').fetchall()
        for row in rows:
            symbol = str(row['symbol']).upper().strip()
            qty = float(row['quantity'] or 0)
            price = float(row['avg_price'] or 0)
            if qty <= 0 or price <= 0:
                continue
            lot_count = conn.execute(
                'SELECT COUNT(*) FROM portfolio_lots WHERE symbol = ? AND remaining_quantity > 0',
                (symbol,)
            ).fetchone()[0]
            if lot_count > 0:
                continue
            trade_date = self._to_iso_datetime(row['added_date'])
            now_iso = datetime.now().isoformat()
            cur = conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'BUY', ?, ?, ?, 0, ?, ?)
                ''',
                (symbol, qty, price, trade_date, 'LEGACY_MIGRATION', now_iso)
            )
            buy_txn_id = cur.lastrowid
            conn.execute(
                '''
                INSERT INTO portfolio_lots
                (symbol, buy_txn_id, buy_date, buy_price, original_quantity, remaining_quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (symbol, buy_txn_id, trade_date, price, qty, qty, now_iso)
            )

    def _rebuild_portfolio_summary(self, conn, symbol):
        symbol = symbol.upper().strip()
        agg = conn.execute(
            '''
            SELECT
                COALESCE(SUM(remaining_quantity), 0) AS qty,
                COALESCE(SUM(remaining_quantity * buy_price), 0) AS cost,
                MIN(buy_date) AS first_buy_date
            FROM portfolio_lots
            WHERE symbol = ? AND remaining_quantity > 0
            ''',
            (symbol,)
        ).fetchone()
        qty = float(agg['qty'] or 0)
        cost = float(agg['cost'] or 0)
        first_buy_date = agg['first_buy_date'] or datetime.now().isoformat()
        if qty <= 0:
            conn.execute('DELETE FROM portfolio WHERE symbol = ?', (symbol,))
            return
        avg_price = (cost / qty) if qty > 0 else 0.0
        conn.execute(
            '''
            INSERT INTO portfolio (symbol, quantity, avg_price, added_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                quantity = excluded.quantity,
                avg_price = excluded.avg_price,
                added_date = excluded.added_date
            ''',
            (symbol, qty, avg_price, first_buy_date)
        )

    def ensure_market_hours_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS market_hours (
            market TEXT PRIMARY KEY,
            timezone TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        with self.get_connection() as conn:
            conn.execute(query)

    # ----------------------------
    # PORTFOLIO MANAGEMENT
    # ----------------------------
    def add_to_portfolio(self, symbol, quantity, avg_price, purchase_date=None):
        symbol = symbol.upper().strip()
        qty = float(quantity or 0)
        price = float(avg_price or 0)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
        if price <= 0:
            raise ValueError("avg_price must be > 0")
        trade_date = self._to_iso_datetime(purchase_date)
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'BUY', ?, ?, ?, 0, NULL, ?)
                ''',
                (symbol, qty, price, trade_date, now_iso)
            )
            buy_txn_id = cur.lastrowid
            conn.execute(
                '''
                INSERT INTO portfolio_lots
                (symbol, buy_txn_id, buy_date, buy_price, original_quantity, remaining_quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (symbol, buy_txn_id, trade_date, price, qty, qty, now_iso)
            )
            self._rebuild_portfolio_summary(conn, symbol)

    def add_portfolio_position(self, symbol, quantity, avg_price, purchase_date=None):
        """Production alias for lot-based BUY insertion."""
        self.add_to_portfolio(symbol, quantity, avg_price, purchase_date)

    def update_portfolio_position_summary(self, symbol, quantity, avg_price, purchase_date=None):
        """
        Administrative correction path (used by inline edit).
        Rewrites open lots as a single correction lot while preserving realized history.
        """
        symbol = symbol.upper().strip()
        qty = float(quantity or 0)
        price = float(avg_price or 0)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
        if price <= 0:
            raise ValueError("avg_price must be > 0")
        trade_date = self._to_iso_datetime(purchase_date)
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'ADJUST', ?, ?, ?, 0, ?, ?)
                ''',
                (symbol, qty, price, trade_date, 'MANUAL_EDIT_SUMMARY', now_iso)
            )
            conn.execute('DELETE FROM portfolio_lots WHERE symbol = ? AND remaining_quantity > 0', (symbol,))
            cur = conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'BUY', ?, ?, ?, 0, ?, ?)
                ''',
                (symbol, qty, price, trade_date, 'MANUAL_EDIT_RESET_LOTS', now_iso)
            )
            buy_txn_id = cur.lastrowid
            conn.execute(
                '''
                INSERT INTO portfolio_lots
                (symbol, buy_txn_id, buy_date, buy_price, original_quantity, remaining_quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (symbol, buy_txn_id, trade_date, price, qty, qty, now_iso)
            )
            self._rebuild_portfolio_summary(conn, symbol)

    def sell_from_portfolio(self, symbol, quantity, sell_price, sell_date=None, method='FIFO', fees=0.0, notes=None):
        symbol = symbol.upper().strip()
        qty_to_sell = float(quantity or 0)
        sell_px = float(sell_price or 0)
        fee_amt = float(fees or 0)
        if qty_to_sell <= 0:
            raise ValueError("quantity must be > 0")
        if sell_px <= 0:
            raise ValueError("sell_price must be > 0")
        method = str(method or 'FIFO').upper()
        if method not in {'FIFO', 'LIFO', 'HIFO'}:
            method = 'FIFO'

        sell_dt = self._to_iso_datetime(sell_date)
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            order_clause = 'buy_date ASC'
            if method == 'LIFO':
                order_clause = 'buy_date DESC'
            elif method == 'HIFO':
                order_clause = 'buy_price DESC, buy_date ASC'

            open_lots = conn.execute(
                f'''
                SELECT id, buy_date, buy_price, remaining_quantity
                FROM portfolio_lots
                WHERE symbol = ? AND remaining_quantity > 0
                ORDER BY {order_clause}
                ''',
                (symbol,)
            ).fetchall()
            if not open_lots:
                raise ValueError(f"no open lots for {symbol}")
            total_open = sum(float(r['remaining_quantity'] or 0) for r in open_lots)
            if qty_to_sell > total_open + 1e-9:
                raise ValueError(f"sell quantity exceeds open quantity ({total_open:.4f})")

            cur = conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?)
                ''',
                (symbol, qty_to_sell, sell_px, sell_dt, fee_amt, notes, now_iso)
            )
            sell_txn_id = cur.lastrowid

            remaining = qty_to_sell
            realized_total = 0.0
            realized_stcg = 0.0
            realized_ltcg = 0.0
            matched = []

            sell_dt_obj = datetime.fromisoformat(sell_dt.replace("Z", "+00:00"))
            for lot in open_lots:
                if remaining <= 1e-9:
                    break
                lot_qty = float(lot['remaining_quantity'] or 0)
                if lot_qty <= 0:
                    continue
                take_qty = min(remaining, lot_qty)
                buy_px = float(lot['buy_price'] or 0)
                buy_dt_text = str(lot['buy_date'])
                buy_dt_obj = datetime.fromisoformat(buy_dt_text.replace("Z", "+00:00"))
                holding_days = max(0, (sell_dt_obj - buy_dt_obj).days)
                gain = (sell_px - buy_px) * take_qty
                gain_type = 'LTCG' if holding_days > 365 else 'STCG'
                gain_pct = ((sell_px - buy_px) / buy_px * 100.0) if buy_px > 0 else 0.0

                conn.execute(
                    '''
                    INSERT INTO portfolio_realized_gains
                    (symbol, sell_txn_id, lot_id, quantity, buy_price, sell_price, gain, gain_percent, holding_days, gain_type, realized_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (symbol, sell_txn_id, int(lot['id']), take_qty, buy_px, sell_px, gain, gain_pct, holding_days, gain_type, sell_dt)
                )
                conn.execute(
                    'UPDATE portfolio_lots SET remaining_quantity = remaining_quantity - ? WHERE id = ?',
                    (take_qty, int(lot['id']))
                )
                remaining -= take_qty
                realized_total += gain
                if gain_type == 'STCG':
                    realized_stcg += gain
                else:
                    realized_ltcg += gain
                matched.append({
                    'lot_id': int(lot['id']),
                    'quantity': round(take_qty, 6),
                    'buy_price': buy_px,
                    'sell_price': sell_px,
                    'gain': round(gain, 6),
                    'holding_days': holding_days,
                    'gain_type': gain_type
                })

            if fee_amt:
                realized_total -= fee_amt

            self._rebuild_portfolio_summary(conn, symbol)
            return {
                'symbol': symbol,
                'sold_quantity': qty_to_sell,
                'sell_price': sell_px,
                'method': method,
                'realized_gain': round(realized_total, 6),
                'realized_stcg': round(realized_stcg, 6),
                'realized_ltcg': round(realized_ltcg, 6),
                'matched_lots': matched
            }

    def remove_from_portfolio(self, symbol):
        symbol = symbol.upper().strip()
        with self.get_connection() as conn:
            conn.execute('DELETE FROM portfolio WHERE symbol = ?', (symbol,))
            conn.execute('DELETE FROM portfolio_lots WHERE symbol = ? AND remaining_quantity > 0', (symbol,))
            conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'REMOVE', 0, 0, ?, 0, ?, ?)
                ''',
                (symbol, datetime.now().isoformat(), 'MANUAL_REMOVE_OPEN_LOTS', datetime.now().isoformat())
            )

    def delete_portfolio_position(self, symbol):
        """Production alias for remove_from_portfolio"""
        self.remove_from_portfolio(symbol)

    def get_portfolio(self):
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM portfolio').fetchall()
            return [dict(row) for row in rows]

    def get_all_positions(self):
        return self.get_portfolio()

    def get_portfolio_lots(self, symbol=None, only_open=False):
        with self.get_connection() as conn:
            clauses = []
            params = []
            if symbol:
                clauses.append("symbol = ?")
                params.append(symbol.upper().strip())
            if only_open:
                clauses.append("remaining_quantity > 0")
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = conn.execute(
                f'''
                SELECT id, symbol, buy_txn_id, buy_date, buy_price, original_quantity, remaining_quantity, created_at
                FROM portfolio_lots
                {where}
                ORDER BY buy_date ASC, id ASC
                ''',
                params
            ).fetchall()
            return [dict(r) for r in rows]

    def update_open_lot(self, lot_id, quantity=None, buy_price=None, buy_date=None):
        """
        Update a specific open purchase lot.
        Safety rule: quantity edits are allowed only for unsold lots
        (original_quantity == remaining_quantity) to keep realized history consistent.
        """
        lot_id = int(lot_id)
        with self.get_connection() as conn:
            lot = conn.execute(
                '''
                SELECT id, symbol, buy_date, buy_price, original_quantity, remaining_quantity
                FROM portfolio_lots
                WHERE id = ?
                ''',
                (lot_id,)
            ).fetchone()
            if not lot:
                raise ValueError(f"lot not found: {lot_id}")
            symbol = str(lot['symbol']).upper()
            original_qty = float(lot['original_quantity'] or 0)
            remaining_qty = float(lot['remaining_quantity'] or 0)
            sold_qty = max(0.0, original_qty - remaining_qty)
            if remaining_qty <= 0:
                raise ValueError("lot is closed")

            new_qty = float(quantity if quantity is not None else remaining_qty)
            new_price = float(buy_price if buy_price is not None else lot['buy_price'])
            new_date = self._to_iso_datetime(buy_date if buy_date is not None else lot['buy_date'])
            if new_qty <= 0:
                raise ValueError("quantity must be > 0")
            if new_price <= 0:
                raise ValueError("buy_price must be > 0")

            if sold_qty > 1e-9 and abs(new_qty - remaining_qty) > 1e-9:
                raise ValueError("cannot change quantity on partially sold lot; use sell workflow")

            if sold_qty > 1e-9:
                final_original = original_qty
                final_remaining = remaining_qty
            else:
                final_original = new_qty
                final_remaining = new_qty

            conn.execute(
                '''
                UPDATE portfolio_lots
                SET buy_date = ?, buy_price = ?, original_quantity = ?, remaining_quantity = ?
                WHERE id = ?
                ''',
                (new_date, new_price, final_original, final_remaining, lot_id)
            )
            conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'ADJUST', ?, ?, ?, 0, ?, ?)
                ''',
                (symbol, final_remaining, new_price, new_date, f'LOT_EDIT:{lot_id}', datetime.now().isoformat())
            )
            self._rebuild_portfolio_summary(conn, symbol)
            return {
                'lot_id': lot_id,
                'symbol': symbol,
                'buy_date': new_date,
                'buy_price': float(new_price),
                'original_quantity': float(final_original),
                'remaining_quantity': float(final_remaining)
            }

    def delete_open_lot(self, lot_id):
        """Delete a specific unsold open lot and rebuild summary."""
        lot_id = int(lot_id)
        with self.get_connection() as conn:
            lot = conn.execute(
                '''
                SELECT id, symbol, buy_date, buy_price, original_quantity, remaining_quantity
                FROM portfolio_lots
                WHERE id = ?
                ''',
                (lot_id,)
            ).fetchone()
            if not lot:
                raise ValueError(f"lot not found: {lot_id}")
            symbol = str(lot['symbol']).upper()
            original_qty = float(lot['original_quantity'] or 0)
            remaining_qty = float(lot['remaining_quantity'] or 0)
            sold_qty = max(0.0, original_qty - remaining_qty)
            if remaining_qty <= 0:
                raise ValueError("lot is already closed")
            if sold_qty > 1e-9:
                raise ValueError("cannot delete partially sold lot; use sell workflow")

            conn.execute('DELETE FROM portfolio_lots WHERE id = ?', (lot_id,))
            conn.execute(
                '''
                INSERT INTO portfolio_transactions
                (symbol, side, quantity, price, trade_date, fees, notes, created_at)
                VALUES (?, 'REMOVE', ?, ?, ?, 0, ?, ?)
                ''',
                (
                    symbol,
                    remaining_qty,
                    float(lot['buy_price'] or 0),
                    self._to_iso_datetime(lot['buy_date']),
                    f'LOT_DELETE:{lot_id}',
                    datetime.now().isoformat()
                )
            )
            self._rebuild_portfolio_summary(conn, symbol)
            return {'lot_id': lot_id, 'symbol': symbol, 'deleted_quantity': remaining_qty}

    def get_realized_gains(self, symbol=None, from_date=None, to_date=None):
        with self.get_connection() as conn:
            clauses = []
            params = []
            if symbol:
                clauses.append("symbol = ?")
                params.append(symbol.upper().strip())
            if from_date:
                clauses.append("realized_at >= ?")
                params.append(self._to_iso_datetime(from_date))
            if to_date:
                clauses.append("realized_at <= ?")
                params.append(self._to_iso_datetime(to_date))
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = conn.execute(
                f'''
                SELECT id, symbol, sell_txn_id, lot_id, quantity, buy_price, sell_price, gain, gain_percent, holding_days, gain_type, realized_at
                FROM portfolio_realized_gains
                {where}
                ORDER BY realized_at DESC, id DESC
                ''',
                params
            ).fetchall()
            return [dict(r) for r in rows]

    def get_tax_lot_metrics(self, symbol, current_price, as_of=None):
        symbol = symbol.upper().strip()
        price = float(current_price or 0)
        as_of_dt = datetime.fromisoformat(self._to_iso_datetime(as_of).replace("Z", "+00:00"))
        with self.get_connection() as conn:
            lots = conn.execute(
                '''
                SELECT buy_date, buy_price, remaining_quantity
                FROM portfolio_lots
                WHERE symbol = ? AND remaining_quantity > 0
                ORDER BY buy_date ASC
                ''',
                (symbol,)
            ).fetchall()
            stcg_unrealized = 0.0
            ltcg_unrealized = 0.0
            open_qty = 0.0
            open_cost = 0.0
            for lot in lots:
                qty = float(lot['remaining_quantity'] or 0)
                buy_px = float(lot['buy_price'] or 0)
                if qty <= 0:
                    continue
                buy_dt = datetime.fromisoformat(str(lot['buy_date']).replace("Z", "+00:00"))
                holding_days = max(0, (as_of_dt - buy_dt).days)
                gain = (price - buy_px) * qty if price > 0 else 0.0
                if holding_days > 365:
                    ltcg_unrealized += gain
                else:
                    stcg_unrealized += gain
                open_qty += qty
                open_cost += (buy_px * qty)

            realized = conn.execute(
                '''
                SELECT
                    COALESCE(SUM(CASE WHEN gain_type = 'STCG' THEN gain ELSE 0 END), 0) AS stcg_realized,
                    COALESCE(SUM(CASE WHEN gain_type = 'LTCG' THEN gain ELSE 0 END), 0) AS ltcg_realized
                FROM portfolio_realized_gains
                WHERE symbol = ?
                ''',
                (symbol,)
            ).fetchone()

            current_value = price * open_qty if price > 0 else 0.0
            return {
                'symbol': symbol,
                'open_qty': round(open_qty, 6),
                'open_cost': round(open_cost, 6),
                'current_value': round(current_value, 6),
                'unrealized_total': round(stcg_unrealized + ltcg_unrealized, 6),
                'stcg_unrealized': round(stcg_unrealized, 6),
                'ltcg_unrealized': round(ltcg_unrealized, 6),
                'stcg_realized': round(float(realized['stcg_realized'] or 0), 6),
                'ltcg_realized': round(float(realized['ltcg_realized'] or 0), 6),
                'lots_count': len(lots)
            }

    def simulate_sell_from_portfolio(self, symbol, quantity, sell_price, sell_date=None, method='FIFO', fees=0.0):
        """Non-mutating sell simulation over current open lots."""
        symbol = symbol.upper().strip()
        qty_to_sell = float(quantity or 0)
        sell_px = float(sell_price or 0)
        fee_amt = float(fees or 0)
        if qty_to_sell <= 0:
            raise ValueError("quantity must be > 0")
        if sell_px <= 0:
            raise ValueError("sell_price must be > 0")
        method = str(method or 'FIFO').upper()
        if method not in {'FIFO', 'LIFO', 'HIFO'}:
            method = 'FIFO'

        sell_dt = self._to_iso_datetime(sell_date)
        sell_dt_obj = datetime.fromisoformat(sell_dt.replace("Z", "+00:00"))
        with self.get_connection() as conn:
            order_clause = 'buy_date ASC'
            if method == 'LIFO':
                order_clause = 'buy_date DESC'
            elif method == 'HIFO':
                order_clause = 'buy_price DESC, buy_date ASC'

            open_lots = conn.execute(
                f'''
                SELECT id, buy_date, buy_price, remaining_quantity
                FROM portfolio_lots
                WHERE symbol = ? AND remaining_quantity > 0
                ORDER BY {order_clause}
                ''',
                (symbol,)
            ).fetchall()
            if not open_lots:
                raise ValueError(f"no open lots for {symbol}")
            total_open = sum(float(r['remaining_quantity'] or 0) for r in open_lots)
            if qty_to_sell > total_open + 1e-9:
                raise ValueError(f"sell quantity exceeds open quantity ({total_open:.4f})")

            remaining = qty_to_sell
            realized_total = 0.0
            realized_stcg = 0.0
            realized_ltcg = 0.0
            matched = []
            for lot in open_lots:
                if remaining <= 1e-9:
                    break
                lot_qty = float(lot['remaining_quantity'] or 0)
                if lot_qty <= 0:
                    continue
                take_qty = min(remaining, lot_qty)
                buy_px = float(lot['buy_price'] or 0)
                buy_dt_text = str(lot['buy_date'])
                buy_dt_obj = datetime.fromisoformat(buy_dt_text.replace("Z", "+00:00"))
                holding_days = max(0, (sell_dt_obj - buy_dt_obj).days)
                gain = (sell_px - buy_px) * take_qty
                gain_type = 'LTCG' if holding_days > 365 else 'STCG'
                gain_pct = ((sell_px - buy_px) / buy_px * 100.0) if buy_px > 0 else 0.0
                days_to_ltcg = max(0, 366 - holding_days)

                remaining -= take_qty
                realized_total += gain
                if gain_type == 'STCG':
                    realized_stcg += gain
                else:
                    realized_ltcg += gain
                matched.append({
                    'lot_id': int(lot['id']),
                    'quantity': round(take_qty, 6),
                    'buy_price': buy_px,
                    'sell_price': sell_px,
                    'gain': round(gain, 6),
                    'gain_percent': round(gain_pct, 4),
                    'holding_days': holding_days,
                    'days_to_ltcg': days_to_ltcg,
                    'gain_type': gain_type
                })

            if fee_amt:
                realized_total -= fee_amt

            # Lightweight tax impact proxy (no tax-rule hardcode in execution path).
            tax_impact_proxy = max(realized_stcg, 0.0) + (0.5 * max(realized_ltcg, 0.0))

            return {
                'symbol': symbol,
                'method': method,
                'sold_quantity': qty_to_sell,
                'sell_price': sell_px,
                'fees': fee_amt,
                'realized_gain': round(realized_total, 6),
                'realized_stcg': round(realized_stcg, 6),
                'realized_ltcg': round(realized_ltcg, 6),
                'tax_impact_proxy': round(tax_impact_proxy, 6),
                'matched_lots': matched
            }

    def compare_sell_methods(self, symbol, quantity, sell_price, sell_date=None, fees=0.0, methods=None):
        """Compare FIFO/LIFO/HIFO sell outcomes and recommend method by tax-efficiency proxy."""
        method_list = methods or ['FIFO', 'LIFO', 'HIFO']
        scenarios = []
        for m in method_list:
            try:
                scenarios.append(
                    self.simulate_sell_from_portfolio(
                        symbol=symbol,
                        quantity=quantity,
                        sell_price=sell_price,
                        sell_date=sell_date,
                        method=m,
                        fees=fees
                    )
                )
            except Exception:
                continue
        if not scenarios:
            raise ValueError("no valid sell scenarios available")

        def _score(s):
            # Lower score preferred; prioritizes lower tax proxy and lower urgency to exit profitable LTCG lots.
            proxy = float(s.get('tax_impact_proxy', 0) or 0)
            gain = float(s.get('realized_gain', 0) or 0)
            harvest = max(0.0, -gain) * 0.05
            return proxy - harvest

        recommended = min(scenarios, key=_score)
        return {
            'symbol': symbol.upper().strip(),
            'sell_quantity': float(quantity or 0),
            'sell_price': float(sell_price or 0),
            'scenarios': scenarios,
            'recommended_method': recommended.get('method', 'FIFO')
        }

    def get_near_ltcg_lots(self, symbol=None, threshold_days=30, as_of=None):
        """Open lots that will become LTCG soon."""
        as_of_dt = datetime.fromisoformat(self._to_iso_datetime(as_of).replace("Z", "+00:00"))
        threshold = max(0, int(threshold_days or 0))
        with self.get_connection() as conn:
            clauses = ["remaining_quantity > 0"]
            params = []
            if symbol:
                clauses.append("symbol = ?")
                params.append(symbol.upper().strip())
            where = f"WHERE {' AND '.join(clauses)}"
            rows = conn.execute(
                f'''
                SELECT id, symbol, buy_date, buy_price, remaining_quantity
                FROM portfolio_lots
                {where}
                ORDER BY buy_date ASC, id ASC
                ''',
                params
            ).fetchall()

            out = []
            for row in rows:
                buy_dt = datetime.fromisoformat(str(row['buy_date']).replace("Z", "+00:00"))
                holding_days = max(0, (as_of_dt - buy_dt).days)
                days_to_ltcg = max(0, 366 - holding_days)
                if days_to_ltcg <= threshold:
                    out.append({
                        'lot_id': int(row['id']),
                        'symbol': str(row['symbol']).upper(),
                        'buy_date': str(row['buy_date']),
                        'buy_price': float(row['buy_price'] or 0),
                        'open_quantity': float(row['remaining_quantity'] or 0),
                        'holding_days': holding_days,
                        'days_to_ltcg': days_to_ltcg
                    })
            out.sort(key=lambda x: (x['days_to_ltcg'], x['symbol'], x['lot_id']))
            return out

    def get_financial_year_realized_summary(self, fy_start_year=None):
        """
        India-style FY summary (Apr 1 -> Mar 31) over realized gains ledger.
        fy_start_year: e.g. 2025 means FY 2025-26.
        """
        now = datetime.now()
        if fy_start_year is None:
            fy_start_year = now.year if now.month >= 4 else (now.year - 1)
        fy_start = datetime(int(fy_start_year), 4, 1, 0, 0, 0)
        fy_end = datetime(int(fy_start_year) + 1, 4, 1, 0, 0, 0)
        fy_label = f"{int(fy_start_year)}-{str(int(fy_start_year) + 1)[-2:]}"

        with self.get_connection() as conn:
            rows = conn.execute(
                '''
                SELECT symbol, gain, gain_type, realized_at
                FROM portfolio_realized_gains
                WHERE realized_at >= ? AND realized_at < ?
                ORDER BY realized_at DESC, id DESC
                ''',
                (fy_start.isoformat(), fy_end.isoformat())
            ).fetchall()

            by_symbol = {}
            stcg = 0.0
            ltcg = 0.0
            total = 0.0
            for row in rows:
                symbol = str(row['symbol']).upper()
                gain = float(row['gain'] or 0)
                gtype = str(row['gain_type'] or 'STCG').upper()
                total += gain
                if gtype == 'LTCG':
                    ltcg += gain
                else:
                    stcg += gain
                slot = by_symbol.setdefault(symbol, {'symbol': symbol, 'stcg': 0.0, 'ltcg': 0.0, 'total': 0.0})
                if gtype == 'LTCG':
                    slot['ltcg'] += gain
                else:
                    slot['stcg'] += gain
                slot['total'] += gain

            symbol_rows = sorted(by_symbol.values(), key=lambda x: x['total'], reverse=True)
            return {
                'fy': fy_label,
                'from': fy_start.isoformat(),
                'to': fy_end.isoformat(),
                'realized_total': round(total, 6),
                'stcg_realized': round(stcg, 6),
                'ltcg_realized': round(ltcg, 6),
                'transactions': len(rows),
                'symbols': symbol_rows
            }

    def get_total_predictions_count(self):
        with self.get_connection() as conn:
            result = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()
            return result[0] if result else 0

    # ----------------------------
    # PREDICTION LOGGING
    # ----------------------------
    def log_prediction(self, prediction_data):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO predictions
                (symbol, predicted_price, current_price, target_price, signal,
                 confidence, models_used, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction_data.get('symbol').upper(),
                prediction_data.get('predicted_price'),
                prediction_data.get('current_price'),
                prediction_data.get('target_price'),
                prediction_data.get('signal'),
                prediction_data.get('confidence'),
                json.dumps(prediction_data.get('models_used', [])),
                datetime.now().isoformat()
            ))

    def get_recent_predictions(self, limit=100):
        """Return recent predictions as dict records for learning pipeline."""
        with self.get_connection() as conn:
            rows = conn.execute(
                '''
                SELECT id, symbol, signal, confidence, current_price, target_price,
                       models_used, timestamp, actual_price, prediction_error
                FROM predictions
                ORDER BY id DESC
                LIMIT ?
                ''',
                (int(limit),)
            ).fetchall()
            return [dict(row) for row in rows]

    def update_prediction_result(self, prediction_id, actual_price, prediction_error):
        """Persist realized price/error for continuous learning evaluation."""
        with self.get_connection() as conn:
            conn.execute(
                '''
                UPDATE predictions
                SET actual_price = ?, prediction_error = ?
                WHERE id = ?
                ''',
                (float(actual_price), float(prediction_error), int(prediction_id))
            )
    def init_predictions_table(db):
        """Initialize predictions tracking table"""
        try:
            db.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    models_used INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            db.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                ON predictions (symbol, timestamp DESC)
            ''')
            
            db.commit()
            print('✅ Predictions table initialized')
        except Exception as e:
            print(f'Warning: Predictions table already exists: {e}')

    # ----------------------------
    # MODEL PERFORMANCE
    # ----------------------------
    def update_model_performance(self, model_name, accuracy, weight):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO model_performance
                (model_name, accuracy, weight, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (model_name, accuracy, weight, datetime.now().isoformat()))

    def get_model_performance(self):
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM model_performance').fetchall()
            return [dict(row) for row in rows]

    # ----------------------------
    # DYNAMIC SYMBOLS MANAGEMENT
    # ----------------------------
    def add_or_update_symbol(self, symbol, name=None, sector='Unknown'):
        symbol = symbol.upper()
        name = name or symbol
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO dynamic_symbols (symbol, name, sector, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    sector=excluded.sector,
                    last_updated=excluded.last_updated
            ''', (symbol, name, sector, datetime.now().isoformat()))

    def search_symbols(self, query, limit=15):
        query = query.upper()
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM dynamic_symbols
                WHERE symbol LIKE ? OR name LIKE ?
                ORDER BY symbol ASC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit)).fetchall()
            return [dict(row) for row in rows]

    # ----------------------------
    # OPTIONAL: Auto-fetch company info
    # ----------------------------
    def fetch_symbol_info(self, symbol):
        """
        Placeholder for external API fetch. Currently returns minimal info.
        """
        symbol = symbol.upper()
        # Example: Replace with real API fetch if needed
        return {
            'symbol': symbol,
            'name': symbol.title(),
            'sector': 'Unknown'
        }

    def ensure_symbol_exists(self, symbol):
        """
        Check if symbol exists; if not, fetch info and add it dynamically.
        """
        results = self.search_symbols(symbol)
        if not results:
            info = self.fetch_symbol_info(symbol)
            self.add_or_update_symbol(**info)
        return self.search_symbols(symbol)

# ----------------------------
# SINGLE INSTANCE FOR APP
# ----------------------------
dynamic_db = DatabaseManager()
