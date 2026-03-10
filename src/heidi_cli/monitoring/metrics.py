"""
Advanced monitoring and metrics system for model hosting.
"""

from __future__ import annotations

import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import sqlite3
import logging
from collections import defaultdict, deque
import statistics

logger = logging.getLogger("heidi.monitoring")

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels
        }

@dataclass
class MetricDefinition:
    """Metric definition."""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    labels: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "unit": self.unit,
            "labels": self.labels
        }

@dataclass
class Alert:
    """Alert definition."""
    alert_id: str
    name: str
    severity: AlertSeverity
    condition: str
    threshold: float
    duration_seconds: int
    enabled: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count
        }

class Metric:
    """Base metric class."""
    
    def __init__(self, name: str, metric_type: MetricType, description: str = "",
                 unit: str = "", labels: List[str] = None):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.unit = unit
        self.labels = labels or []
        self._lock = threading.Lock()
        self._points: deque = deque(maxlen=10000)  # Keep last 10k points
    
    def add_point(self, value: float, labels: Dict[str, str] = None):
        """Add a data point."""
        with self._lock:
            point = MetricPoint(
                timestamp=datetime.now(timezone.utc),
                value=value,
                labels=labels or {}
            )
            self._points.append(point)
    
    def get_points(self, since: Optional[datetime] = None, 
                  limit: int = 1000) -> List[MetricPoint]:
        """Get data points."""
        with self._lock:
            points = list(self._points)
            
            if since:
                points = [p for p in points if p.timestamp >= since]
            
            return points[-limit:] if limit else points
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get latest point."""
        with self._lock:
            return self._points[-1] if self._points else None
    
    def get_stats(self, since: Optional[datetime] = None) -> Dict[str, float]:
        """Get statistics for the metric."""
        points = self.get_points(since)
        
        if not points:
            return {}
        
        values = [p.value for p in points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "sum": sum(values)
        }

class Counter(Metric):
    """Counter metric."""
    
    def __init__(self, name: str, description: str = "", unit: str = ""):
        super().__init__(name, MetricType.COUNTER, description, unit)
        self._value = 0.0
    
    def inc(self, amount: float = 1.0, labels: Dict[str, str] = None):
        """Increment counter."""
        with self._lock:
            self._value += amount
            self.add_point(self._value, labels)
    
    def dec(self, amount: float = 1.0, labels: Dict[str, str] = None):
        """Decrement counter."""
        with self._lock:
            self._value -= amount
            self.add_point(self._value, labels)

class Gauge(Metric):
    """Gauge metric."""
    
    def set(self, value: float, labels: Dict[str, str] = None):
        """Set gauge value."""
        with self._lock:
            self.add_point(value, labels)

class Histogram(Metric):
    """Histogram metric."""
    
    def __init__(self, name: str, buckets: List[float] = None, 
                 description: str = "", unit: str = ""):
        super().__init__(name, MetricType.HISTOGRAM, description, unit)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
    
    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe a value."""
        with self._lock:
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
            
            self.add_point(value, labels)
    
    def get_bucket_counts(self) -> Dict[str, float]:
        """Get bucket counts."""
        with self._lock:
            return self._bucket_counts.copy()

class Timer(Metric):
    """Timer metric."""
    
    def __init__(self, name: str, description: str = "", unit: str = "seconds"):
        super().__init__(name, MetricType.TIMER, description, unit)
    
    def time(self, func: Callable, labels: Dict[str, str] = None):
        """Time a function execution."""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                self.observe(duration, labels)
        return wrapper
    
    def observe(self, duration: float, labels: Dict[str, str] = None):
        """Observe a duration."""
        self.add_point(duration, labels)

class MetricsCollector:
    """Collects and manages metrics."""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("state/metrics.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._metrics: Dict[str, Metric] = {}
        self._alerts: Dict[str, Alert] = {}
        self._lock = threading.RLock()
        
        self._init_database()
        self._start_monitoring_thread()
    
    def _init_database(self):
        """Initialize metrics database."""
        with sqlite3.connect(self.db_path) as conn:
            # Metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    value REAL NOT NULL,
                    labels TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_triggered TEXT,
                    trigger_count INTEGER DEFAULT 0
                )
            """)
            
            # Alert triggers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    value REAL NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts (alert_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_triggers_alert_id ON alert_triggers(alert_id)")
            
            conn.commit()
    
    def register_metric(self, metric: Metric):
        """Register a new metric."""
        with self._lock:
            self._metrics[metric.name] = metric
    
    def counter(self, name: str, description: str = "", unit: str = "") -> Counter:
        """Create or get a counter metric."""
        with self._lock:
            if name not in self._metrics:
                counter = Counter(name, description, unit)
                self.register_metric(counter)
            return self._metrics[name]
    
    def gauge(self, name: str, description: str = "", unit: str = "") -> Gauge:
        """Create or get a gauge metric."""
        with self._lock:
            if name not in self._metrics:
                gauge = Gauge(name, description, unit)
                self.register_metric(gauge)
            return self._metrics[name]
    
    def histogram(self, name: str, buckets: List[float] = None,
                 description: str = "", unit: str = "") -> Histogram:
        """Create or get a histogram metric."""
        with self._lock:
            if name not in self._metrics:
                histogram = Histogram(name, buckets, description, unit)
                self.register_metric(histogram)
            return self._metrics[name]
    
    def timer(self, name: str, description: str = "", unit: str = "seconds") -> Timer:
        """Create or get a timer metric."""
        with self._lock:
            if name not in self._metrics:
                timer = Timer(name, description, unit)
                self.register_metric(timer)
            return self._metrics[name]
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def list_metrics(self) -> List[MetricDefinition]:
        """List all registered metrics."""
        with self._lock:
            return [
                MetricDefinition(
                    name=metric.name,
                    metric_type=metric.metric_type,
                    description=metric.description,
                    unit=metric.unit,
                    labels=metric.labels
                )
                for metric in self._metrics.values()
            ]
    
    def get_metric_data(self, name: str, since: Optional[datetime] = None,
                        limit: int = 1000) -> List[MetricPoint]:
        """Get metric data."""
        metric = self.get_metric(name)
        if metric:
            return metric.get_points(since, limit)
        return []
    
    def create_alert(self, name: str, condition: str, threshold: float,
                    severity: AlertSeverity = AlertSeverity.WARNING,
                    duration_seconds: int = 300) -> str:
        """Create a new alert."""
        import uuid
        
        alert_id = str(uuid.uuid4())
        alert = Alert(
            alert_id=alert_id,
            name=name,
            severity=severity,
            condition=condition,
            threshold=threshold,
            duration_seconds=duration_seconds,
            enabled=True,
            created_at=datetime.now(timezone.utc)
        )
        
        with self._lock:
            self._alerts[alert_id] = alert
            self._save_alert(alert)
        
        return alert_id
    
    def get_alerts(self, enabled_only: bool = True) -> List[Alert]:
        """Get alerts."""
        with self._lock:
            alerts = list(self._alerts.values())
            if enabled_only:
                alerts = [a for a in alerts if a.enabled]
            return alerts
    
    def check_alerts(self):
        """Check all alerts and trigger if needed."""
        alerts = self.get_alerts(enabled_only=True)
        
        for alert in alerts:
            try:
                self._check_alert(alert)
            except Exception as e:
                logger.error(f"Error checking alert {alert.alert_id}: {e}")
    
    def _check_alert(self, alert: Alert):
        """Check a single alert."""
        # Parse condition (simplified - in production, use a proper expression parser)
        metric_name = alert.condition.split()[0]
        operator = alert.condition.split()[1] if len(alert.condition.split()) > 1 else ">"
        
        metric = self.get_metric(metric_name)
        if not metric:
            return
        
        latest = metric.get_latest()
        if not latest:
            return
        
        value = latest.value
        
        # Check condition
        triggered = False
        if operator == ">":
            triggered = value > alert.threshold
        elif operator == "<":
            triggered = value < alert.threshold
        elif operator == ">=":
            triggered = value >= alert.threshold
        elif operator == "<=":
            triggered = value <= alert.threshold
        elif operator == "==":
            triggered = value == alert.threshold
        
        if triggered:
            self._trigger_alert(alert, value)
    
    def _trigger_alert(self, alert: Alert, value: float):
        """Trigger an alert."""
        now = datetime.now(timezone.utc)
        
        alert.last_triggered = now
        alert.trigger_count += 1
        
        # Save to database
        self._save_alert(alert)
        self._save_alert_trigger(alert.alert_id, value, now)
        
        logger.warning(f"Alert triggered: {alert.name} - {value} (threshold: {alert.threshold})")
    
    def _save_alert(self, alert: Alert):
        """Save alert to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts (
                    alert_id, name, severity, condition, threshold,
                    duration_seconds, enabled, created_at, last_triggered, trigger_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id, alert.name, alert.severity.value,
                alert.condition, alert.threshold, alert.duration_seconds,
                alert.enabled, alert.created_at.isoformat(),
                alert.last_triggered.isoformat() if alert.last_triggered else None,
                alert.trigger_count
            ))
            conn.commit()
    
    def _save_alert_trigger(self, alert_id: str, value: float, triggered_at: datetime):
        """Save alert trigger to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alert_triggers (alert_id, triggered_at, value)
                VALUES (?, ?, ?)
            """, (alert_id, triggered_at.isoformat(), value))
            conn.commit()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        import psutil
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        metrics = {
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            },
            "application": {
                "metrics_count": len(self._metrics),
                "alerts_count": len(self._alerts),
                "enabled_alerts": len([a for a in self._alerts.values() if a.enabled])
            }
        }
        
        return metrics
    
    def export_metrics(self, format: str = "prometheus", 
                      since: Optional[datetime] = None) -> str:
        """Export metrics in specified format."""
        if format == "prometheus":
            return self._export_prometheus(since)
        elif format == "json":
            return self._export_json(since)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus(self, since: Optional[datetime] = None) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for metric in self._metrics.values():
            # Get latest value
            latest = metric.get_latest()
            if latest and (not since or latest.timestamp >= since):
                labels_str = ""
                if latest.labels:
                    labels_str = "{" + ",".join([f'{k}="{v}"' for k, v in latest.labels.items()]) + "}"
                
                lines.append(f"{metric.name}{labels_str} {latest.value}")
        
        return "\n".join(lines)
    
    def _export_json(self, since: Optional[datetime] = None) -> str:
        """Export metrics in JSON format."""
        data = {}
        
        for metric in self._metrics.values():
            points = metric.get_points(since)
            data[metric.name] = {
                "type": metric.metric_type.value,
                "description": metric.description,
                "unit": metric.unit,
                "points": [point.to_dict() for point in points]
            }
        
        return json.dumps(data, indent=2)
    
    def _start_monitoring_thread(self):
        """Start background monitoring thread."""
        def monitor():
            while True:
                try:
                    # Check alerts
                    self.check_alerts()
                    
                    # Sleep for 30 seconds
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Monitoring thread error: {e}")
                    time.sleep(60)  # Retry in 1 minute
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
