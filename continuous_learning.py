# -*- coding: utf-8 -*-
from utils import encoding
import ast
import json
import numpy as np
from collections import defaultdict, deque
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_models_used(value):
    """Safely parse stored model names without executing database text."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(model) for model in value if str(model).strip()]
    if not isinstance(value, str):
        return [str(value)] if str(value).strip() else []

    text = value.strip()
    if not text:
        return []

    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = [item.strip() for item in text.split(",") if item.strip()]

    if isinstance(parsed, str):
        return [parsed] if parsed.strip() else []
    if isinstance(parsed, (list, tuple, set)):
        return [str(model) for model in parsed if str(model).strip()]
    return []


class ContinuousLearningEngine:
    """
    Futuristic meta-learning system that:
    - Dynamically tracks any number of models
    - Adjusts weights automatically based on real-time performance
    - Learns optimal update frequency
    - Provides rich analytics and predictive confidence metrics
    """
    
    def __init__(self, database_manager, initial_learning_rate=0.05):
        self.db = database_manager
        self.model_weights = defaultdict(lambda: 1.0)  # Auto-add models
        self.learning_rate = initial_learning_rate
        self.prediction_count = 0
        self.dynamic_update_threshold = 50  # Can adapt over time
        self.performance_history = deque(maxlen=1000)
    
    def log_prediction(self, prediction):
        """
        Log prediction and optionally trigger model weight update
        """
        self.db.log_prediction(prediction)
        self.prediction_count += 1
        self.performance_history.append(prediction)
        
        # Adaptive threshold: update more often if predictions are volatile
        if self.prediction_count >= self.dynamic_update_threshold:
            self.update_model_weights()
            self.prediction_count = 0
    
    def update_model_weights(self):
        """
        Dynamically adjusts model weights based on recent prediction accuracy
        without any hard-coded model names.
        """
        recent_preds = self.db.get_recent_predictions(limit=500)
        completed = [p for p in recent_preds if p['actual_price'] is not None]
        
        if len(completed) < 10:
            logger.info("Insufficient completed predictions for weight update")
            return
        
        # Dynamically discover models
        model_accuracy = defaultdict(list)
        for pred in completed:
            models = parse_models_used(pred.get('models_used'))
            error = pred.get('prediction_error')
            if error is not None:
                accuracy = max(0, 1 - error)
                for model in models:
                    model_accuracy[model].append(accuracy)
                    if model not in self.model_weights:
                        self.model_weights[model] = 0.1  # Initialize unseen model

        # Compute adaptive weights
        avg_accuracy = {m: np.mean(accs) for m, accs in model_accuracy.items()}
        total_accuracy = sum(avg_accuracy.values())
        if total_accuracy > 0:
            for model, acc in avg_accuracy.items():
                current_weight = self.model_weights.get(model, 0.1)
                # Weighted smoothing to avoid sudden jumps
                self.model_weights[model] = (1 - self.learning_rate) * current_weight + self.learning_rate * (acc / total_accuracy)

            # Normalize weights
            total = sum(self.model_weights.values())
            for model in self.model_weights:
                self.model_weights[model] /= total

            # Adaptive threshold: if predictions are highly volatile, update sooner
            volatility = np.std([p['prediction_error'] for p in completed if p['prediction_error'] is not None])
            self.dynamic_update_threshold = max(10, int(50 * (1 - volatility)))  # faster update on high volatility

            logger.info(f"[{datetime.now()}] Updated model weights: {self.model_weights}")
            logger.info(f"Average accuracies: {avg_accuracy}")
            logger.info(f"Next update in {self.dynamic_update_threshold} predictions")
    
    def get_model_weights(self):
        """Return current model weights"""
        return dict(self.model_weights)

    def update_actual_price(self, symbol, actual_price):
        """
        Update actual price and compute prediction error
        """
        try:
            recent_preds = self.db.get_recent_predictions(limit=10)

            for pred in recent_preds:
                if pred['symbol'] == symbol and pred.get('prediction_error') is None:
                    target = pred.get('target_price')
                    if target is None or target == 0:
                        return

                    error = abs(actual_price - target) / target

                    self.db.update_prediction_result(
                        prediction_id=pred['id'],
                        actual_price=actual_price,
                        prediction_error=error
                    )

                    logger.info(
                        f"[LEARNING] {symbol} error={error:.4f}"
                    )
                    return

        except Exception as e:
            logger.warning(f"Learning update failed: {e}")


    def get_learning_stats(self, limit=100):
        """Rich analytics of recent learning performance"""
        recent_preds = self.db.get_recent_predictions(limit=limit)
        completed = [p for p in recent_preds if p.get('actual_price') is not None]
        
        if not completed:
            return {
                'total_predictions': len(recent_preds),
                'evaluated_predictions': 0,
                'average_accuracy': 0,
                'model_weights': dict(self.model_weights),
                'recent_errors': []
            }

        accuracies = [max(0, 1 - p['prediction_error']) for p in completed if p['prediction_error'] is not None]
        recent_errors = [p['prediction_error'] for p in completed[-10:]]
        
        # Advanced metrics
        volatility = np.std(accuracies)
        confidence = np.mean(accuracies) - volatility  # rough predictive confidence

        return {
            'total_predictions': len(recent_preds),
            'evaluated_predictions': len(completed),
            'average_accuracy': np.mean(accuracies),
            'volatility': volatility,
            'predictive_confidence': confidence,
            'model_weights': dict(self.model_weights),
            'recent_errors': recent_errors
        }

