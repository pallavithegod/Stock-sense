# -*- coding: utf-8 -*-
"""
StockSense - Enhanced Cache Manager
"""

from utils import encoding

import time
import json
from functools import wraps
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class SmartCache:
    def __init__(self, default_ttl=300):
        self.cache = {}
        self.timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key):
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.default_ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key, value, ttl=None):
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def invalidate(self, key):
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]
    
    def clear(self):
        self.cache.clear()
        self.timestamps.clear()

def cached(ttl=300):
    def decorator(func):
        cache = {}
        timestamps = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                if time.time() - timestamps[key] < ttl:
                    return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = time.time()
            return result
        return wrapper
    return decorator
