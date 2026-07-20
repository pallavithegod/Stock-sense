
# -*- coding: utf-8 -*-
from utils import encoding
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def ensure_dict(data, default_value=None):
    """
    Prevent crashes from None/Ellipsis values.
    """
    if data is None or data is ...:
        return default_value if default_value is not None else {}
    if isinstance(data, dict):
        return data
    try:
        if isinstance(data, str):
            return json.loads(data)
        return {}
    except:
        return default_value if default_value is not None else {}

class PredictionHistory:
    """System for immutable prediction logging (Audit Trail)."""
    
    def __init__(self, config):
        self.audit_log_file = config.get('audit_log_file', 'data/prediction_audit.jsonl')
        
        # ✅ Auto-create file and directory if missing
        try:
            path = Path(self.audit_log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
                logger.info(f"Created new audit log file at {path}")
        except Exception as e:
            logger.error(f"Failed to init audit log: {e}")
        
    def log_prediction(self, symbol, prediction_data):
        """
        Log every prediction to JSONL file (compliance trail).
        One prediction per line, immutable, append-only.
        """
        try:
            prediction_data = ensure_dict(prediction_data, {})
            
            audit_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'confidence': prediction_data.get('confidence'),
                'direction': prediction_data.get('direction'),
                'price': prediction_data.get('price'),
                'full_prediction': prediction_data # Optional: store full blob
            }
            
            path = Path(self.audit_log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
            
            logger.debug(f"Logged prediction for {symbol}")
        except Exception as e:
            logger.error(f"Error logging prediction: {e}")

    def get_audit_log(self, symbol, limit=100):
        """Retrieve prediction history for a symbol."""
        try:
            path = Path(self.audit_log_file)
            if not path.exists():
                return []
            
            predictions = []
            with open(path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get('symbol') == symbol:
                                predictions.append(entry)
                        except: continue
            
            return predictions[-limit:]
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
            return []
