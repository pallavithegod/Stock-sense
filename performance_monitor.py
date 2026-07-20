# -*- coding: utf-8 -*-

from utils import encoding  # trigger UTF-8 bootstrap early
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Track API performance metrics."""
    
    def __init__(self, config):
        self.db_path = config.get('db_path', 'data/performance_metrics.db')
        self.init_database()
    
    def init_database(self):
        """Create metrics table."""
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    endpoint TEXT,
                    response_time_ms FLOAT,
                    status_code INTEGER
                )
            ''')
            conn.commit()
            conn.close()
            logger.debug("Performance database initialized")
        except Exception as e:
            logger.error(f"Error initializing performance DB: {e}")
    
    def record_metric(self, endpoint, response_time_ms, status_code=200):
        """Record API metric."""
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute('''
                INSERT INTO metrics (endpoint, response_time_ms, status_code)
                VALUES (?, ?, ?)
            ''', (endpoint, response_time_ms, status_code))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def get_slow_endpoints(self, hours=24):
        """Find slow endpoints."""
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute('''
                SELECT endpoint, AVG(response_time_ms), COUNT(*)
                FROM metrics
                WHERE timestamp > datetime('now', ? || ' hours')
                GROUP BY endpoint
                ORDER BY AVG(response_time_ms) DESC
            ''', (-hours,))
            results = c.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return []
