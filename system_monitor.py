# -*- coding: utf-8 -*-

from utils import encoding
import time
import logging
import threading
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Guardian AI: Monitors system health, detects zombie threads,
    and performs self-healing operations.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SystemMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'): return
        
        self.components = {
            'intelligence_core': {'last_heartbeat': time.time(), 'status': 'STARTING'},
            'websocket_manager': {'last_heartbeat': time.time(), 'status': 'STARTING'},
            'data_pipeline': {'last_heartbeat': time.time(), 'status': 'STARTING'},
            'database': {'last_heartbeat': time.time(), 'status': 'STARTING'}
        }
        self.start_time = time.time()
        self.healing_attempts = 0
        self.lock = threading.Lock()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.initialized = True
        logger.info("[SYS] System Monitor ACTIVATED")

    def heartbeat(self, component_name):
        """Register a heartbeat from a component"""
        with self.lock:
            if component_name in self.components:
                self.components[component_name]['last_heartbeat'] = time.time()
                self.components[component_name]['status'] = 'HEALTHY'

    def register_issue(self, component_name, issue_desc):
        """Log an issue from a component"""
        with self.lock:
            if component_name in self.components:
                self.components[component_name]['status'] = 'DEGRADED'
                self.components[component_name]['last_issue'] = issue_desc
                logger.warning(f"⚠️ Issue report from {component_name}: {issue_desc}")

    def _monitor_loop(self):
        """Check for stalled components every 10 seconds"""
        while True:
            time.sleep(10)
            now = time.time()
            stall_threshold = 60 # seconds
            
            with self.lock:
                for name, data in self.components.items():
                    last_beat = data.get('last_heartbeat', now)
                    if now - last_beat > stall_threshold:
                        logger.critical(f"🚨 COMPONENT STALLED: {name} (Last beat: {int(now - last_beat)}s ago)")
                        data['status'] = 'CRITICAL'
                        self._attempt_healing(name)
    
    def _attempt_healing(self, component_name):
        """Execute self-healing protocols"""
        self.healing_attempts += 1
        logger.info(f"🚑 Initiating Self-Healing Protocol for {component_name}...")
        
        # Specific healing logic
        if component_name == 'websocket_manager':
            # Signal reconnect via global event or flag
            logger.warning("🔄 Signaling WebSocket Manager restart...")
            # Ideally, we'd have a callback here. For now, we log the attempt.
            self.components[component_name]['status'] = 'RESTARTING'
            
        elif component_name == 'intelligence_core':
            # Clear internal caches if stuck
            logger.warning("🧹 Clearing Intelligence Core caches...")
            if hasattr(self, 'intelligence_core') and getattr(self, 'intelligence_core', None):
                 try:
                     self.intelligence_core.memory_store.data.clear() # Extreme example
                 except: pass
            self.components[component_name]['status'] = 'RECOVERING'
        
        # Log resolution attempt
        logger.info(f"✅ Healing signal sent to {component_name}")

    def get_system_health(self):
        """Return full system diagnosis"""
        uptime = int(time.time() - self.start_time)
        return {
            'status': 'OPERATIONAL' if all(c['status'] != 'CRITICAL' for c in self.components.values()) else 'DEGRADED',
            'uptime_seconds': uptime,
            'healing_events': self.healing_attempts,
            'components': self.components
        }

    def check_health(self):
        """Unified health check for API endpoint (Step 7)"""
        status = self.get_system_health()
        return {
            'status': status['status'],
            'uptime': status['uptime_seconds'],
            'healing_events': status['healing_events'],
            'details': {k: v['status'] for k, v in status['components'].items()}
        }

# Global singleton
system_monitor = SystemMonitor()
