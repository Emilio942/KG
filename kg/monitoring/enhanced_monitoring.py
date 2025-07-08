# Enhanced Real-time Monitoring System for KG-System
# Provides detailed metrics, alerts, and performance tracking

import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import logging

class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Metric:
    """Represents a system metric"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""

@dataclass
class Alert:
    """Represents a system alert"""
    id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    module: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class MetricsCollector:
    """
    Enhanced metrics collector with real-time capabilities
    """
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        self.alerts: List[Alert] = []
        self.alert_rules: List[Dict[str, Any]] = []
        
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Start background collection
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        # Setup default alert rules
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Setup default alerting rules"""
        self.alert_rules = [
            {
                "name": "high_error_rate",
                "condition": lambda metrics: self._check_error_rate(metrics),
                "level": AlertLevel.ERROR,
                "message": "High error rate detected"
            },
            {
                "name": "resource_exhaustion",
                "condition": lambda metrics: self._check_resource_exhaustion(metrics),
                "level": AlertLevel.CRITICAL,
                "message": "System resources nearly exhausted"
            },
            {
                "name": "slow_processing",
                "condition": lambda metrics: self._check_slow_processing(metrics),
                "level": AlertLevel.WARNING,
                "message": "Processing time above normal"
            },
            {
                "name": "module_failure",
                "condition": lambda metrics: self._check_module_failures(metrics),
                "level": AlertLevel.ERROR,
                "message": "Module failure detected"
            }
        ]
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        with self.lock:
            self.counters[name] += value
            self._add_metric(name, MetricType.COUNTER, self.counters[name], tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        with self.lock:
            self.gauges[name] = value
            self._add_metric(name, MetricType.GAUGE, value, tags)
    
    def observe_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Add observation to histogram"""
        with self.lock:
            self.histograms[name].append(value)
            self._add_metric(name, MetricType.HISTOGRAM, value, tags)
    
    def time_operation(self, name: str, tags: Dict[str, str] = None):
        """Context manager for timing operations"""
        return TimerContext(self, name, tags)
    
    def _add_metric(self, name: str, metric_type: MetricType, value: float, tags: Dict[str, str] = None):
        """Add metric to collection"""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        self.metrics[name].append(metric)
        
        # Keep only recent metrics
        if len(self.metrics[name]) > 10000:
            self.metrics[name] = self.metrics[name][-5000:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self.lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "count": len(values),
                        "avg": sum(values) / len(values) if values else 0,
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0
                    } for name, values in self.histograms.items()
                },
                "alerts": {
                    "total": len(self.alerts),
                    "active": len([a for a in self.alerts if not a.resolved]),
                    "by_level": defaultdict(int)
                }
            }
            
            # Count alerts by level
            for alert in self.alerts:
                if not alert.resolved:
                    summary["alerts"]["by_level"][alert.level.value] += 1
            
            return summary
    
    def get_metric_history(self, name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metric history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            if name in self.metrics:
                return [
                    {
                        "value": m.value,
                        "timestamp": m.timestamp.isoformat(),
                        "tags": m.tags
                    }
                    for m in self.metrics[name]
                    if m.timestamp > cutoff_time
                ]
            return []
    
    def _collection_loop(self):
        """Background loop for metrics collection and alerting"""
        while True:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check alert rules
                self._check_alert_rules()
                
                # Cleanup old data
                self._cleanup_old_data()
                
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            import psutil
            
            # CPU usage
            self.set_gauge("system.cpu.usage_percent", psutil.cpu_percent())
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge("system.memory.usage_percent", memory.percent)
            self.set_gauge("system.memory.available_gb", memory.available / (1024**3))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.set_gauge("system.disk.usage_percent", disk.percent)
            self.set_gauge("system.disk.free_gb", disk.free / (1024**3))
            
        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _check_alert_rules(self):
        """Check all alert rules and generate alerts"""
        current_metrics = self.get_metrics_summary()
        
        for rule in self.alert_rules:
            try:
                if rule["condition"](current_metrics):
                    self._create_alert(
                        rule["name"],
                        rule["level"],
                        rule["message"],
                        "system"
                    )
            except Exception as e:
                self.logger.error(f"Error checking alert rule {rule['name']}: {e}")
    
    def _check_error_rate(self, metrics: Dict[str, Any]) -> bool:
        """Check if error rate is too high"""
        error_count = metrics["counters"].get("errors.total", 0)
        total_count = metrics["counters"].get("requests.total", 1)
        
        error_rate = error_count / total_count if total_count > 0 else 0
        return error_rate > 0.1  # 10% error rate threshold
    
    def _check_resource_exhaustion(self, metrics: Dict[str, Any]) -> bool:
        """Check if system resources are nearly exhausted"""
        cpu_usage = metrics["gauges"].get("system.cpu.usage_percent", 0)
        memory_usage = metrics["gauges"].get("system.memory.usage_percent", 0)
        disk_usage = metrics["gauges"].get("system.disk.usage_percent", 0)
        
        return cpu_usage > 90 or memory_usage > 90 or disk_usage > 90
    
    def _check_slow_processing(self, metrics: Dict[str, Any]) -> bool:
        """Check if processing is slower than normal"""
        processing_times = self.histograms.get("processing.time.seconds", deque())
        
        if len(processing_times) < 10:
            return False
        
        recent_avg = sum(list(processing_times)[-10:]) / 10
        return recent_avg > 300  # 5 minutes threshold
    
    def _check_module_failures(self, metrics: Dict[str, Any]) -> bool:
        """Check for module failures"""
        failures = metrics["counters"].get("module.failures.total", 0)
        return failures > 0
    
    def _create_alert(self, name: str, level: AlertLevel, message: str, module: str):
        """Create a new alert"""
        alert_id = f"ALERT-{int(time.time())}-{name}"
        
        # Check if similar alert already exists
        for existing_alert in self.alerts:
            if (not existing_alert.resolved and 
                existing_alert.module == module and 
                name in existing_alert.id):
                return  # Don't create duplicate alert
        
        alert = Alert(
            id=alert_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
            module=module
        )
        
        self.alerts.append(alert)
        self.logger.warning(f"Alert created: {alert_id} - {message}")
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [
            {
                "id": alert.id,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "module": alert.module
            }
            for alert in self.alerts
            if not alert.resolved
        ]
    
    def _cleanup_old_data(self):
        """Clean up old metrics and alerts"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        with self.lock:
            # Clean up old metrics
            for name in list(self.metrics.keys()):
                self.metrics[name] = [
                    m for m in self.metrics[name]
                    if m.timestamp > cutoff_time
                ]
                
                if not self.metrics[name]:
                    del self.metrics[name]
            
            # Clean up old resolved alerts
            self.alerts = [
                alert for alert in self.alerts
                if not alert.resolved or 
                (alert.resolved_at and alert.resolved_at > cutoff_time)
            ]

class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.observe_histogram(f"{self.name}.duration_seconds", duration, self.tags)
            self.collector.timers[self.name].append(duration)

class KGSystemMonitor:
    """
    Enhanced monitoring system for KG-System
    Provides module-specific monitoring and dashboards
    """
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.module_monitors: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Module-specific metrics
        self.setup_module_monitors()
    
    def setup_module_monitors(self):
        """Setup monitoring for each module"""
        modules = ["HG", "ISV", "KD", "LAR"]
        
        for module in modules:
            self.module_monitors[module] = {
                "start_time": datetime.now(),
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_processing_time": 0.0,
                "current_active_tasks": 0
            }
    
    def track_task_start(self, module: str, task_id: str):
        """Track when a task starts"""
        self.metrics_collector.increment_counter(f"{module.lower()}.tasks.started")
        self.metrics_collector.increment_counter(f"{module.lower()}.tasks.active")
        
        if module in self.module_monitors:
            self.module_monitors[module]["total_requests"] += 1
            self.module_monitors[module]["current_active_tasks"] += 1
    
    def track_task_complete(self, module: str, task_id: str, duration: float, success: bool):
        """Track when a task completes"""
        status = "success" if success else "failure"
        
        self.metrics_collector.increment_counter(f"{module.lower()}.tasks.completed")
        self.metrics_collector.increment_counter(f"{module.lower()}.tasks.{status}")
        self.metrics_collector.increment_counter(f"{module.lower()}.tasks.active", -1)
        self.metrics_collector.observe_histogram(f"{module.lower()}.processing.time", duration)
        
        if module in self.module_monitors:
            monitor = self.module_monitors[module]
            monitor["current_active_tasks"] = max(0, monitor["current_active_tasks"] - 1)
            
            if success:
                monitor["successful_requests"] += 1
            else:
                monitor["failed_requests"] += 1
            
            # Update average processing time
            total_completed = monitor["successful_requests"] + monitor["failed_requests"]
            if total_completed > 0:
                old_avg = monitor["avg_processing_time"]
                monitor["avg_processing_time"] = (old_avg * (total_completed - 1) + duration) / total_completed
    
    def track_resource_usage(self, module: str, resource_type: str, amount: float):
        """Track resource usage"""
        self.metrics_collector.set_gauge(f"{module.lower()}.resources.{resource_type}", amount)
    
    def track_hypothesis_generated(self, task_id: str, novelty_score: float, component_count: int):
        """Track hypothesis generation"""
        self.metrics_collector.increment_counter("hypotheses.generated")
        self.metrics_collector.observe_histogram("hypotheses.novelty_score", novelty_score)
        self.metrics_collector.observe_histogram("hypotheses.component_count", component_count)
    
    def track_simulation_result(self, method: str, duration: float, confidence: float, success: bool):
        """Track simulation results"""
        status = "success" if success else "failure"
        self.metrics_collector.increment_counter(f"simulations.{method.lower()}.{status}")
        self.metrics_collector.observe_histogram(f"simulations.{method.lower()}.duration", duration)
        
        if success:
            self.metrics_collector.observe_histogram("simulations.confidence", confidence)
    
    def track_evaluation_result(self, verdict: str, score: float):
        """Track evaluation results"""
        self.metrics_collector.increment_counter(f"evaluations.{verdict.lower()}")
        self.metrics_collector.observe_histogram("evaluations.score", score)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        return {
            "system_status": self._get_system_status(),
            "module_status": self._get_module_status(),
            "metrics_summary": metrics_summary,
            "active_alerts": self.metrics_collector.get_active_alerts(),
            "recent_activity": self._get_recent_activity(),
            "resource_usage": self._get_resource_usage(),
            "performance_trends": self._get_performance_trends()
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        metrics = self.metrics_collector.get_metrics_summary()
        
        total_requests = sum(metrics["counters"].get(f"{module.lower()}.tasks.started", 0) 
                           for module in ["hg", "isv", "kd", "lar"])
        total_errors = sum(metrics["counters"].get(f"{module.lower()}.tasks.failure", 0) 
                         for module in ["hg", "isv", "kd", "lar"])
        
        success_rate = ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 100
        
        return {
            "overall_health": "healthy" if success_rate > 90 else "degraded" if success_rate > 70 else "unhealthy",
            "total_requests": total_requests,
            "success_rate": round(success_rate, 2),
            "active_alerts": len(self.metrics_collector.get_active_alerts()),
            "uptime_hours": (datetime.now() - min(monitor["start_time"] for monitor in self.module_monitors.values())).total_seconds() / 3600
        }
    
    def _get_module_status(self) -> Dict[str, Any]:
        """Get status for each module"""
        status = {}
        
        for module, monitor in self.module_monitors.items():
            total = monitor["successful_requests"] + monitor["failed_requests"]
            success_rate = (monitor["successful_requests"] / total * 100) if total > 0 else 100
            
            status[module] = {
                "success_rate": round(success_rate, 2),
                "avg_processing_time": round(monitor["avg_processing_time"], 3),
                "active_tasks": monitor["current_active_tasks"],
                "total_processed": total
            }
        
        return status
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent system activity"""
        # This would typically come from a more detailed event log
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "event": "Task completed",
                "module": "HG",
                "details": "Hypothesis generation successful"
            }
        ]
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        metrics = self.metrics_collector.get_metrics_summary()
        
        return {
            "cpu_usage": metrics["gauges"].get("system.cpu.usage_percent", 0),
            "memory_usage": metrics["gauges"].get("system.memory.usage_percent", 0),
            "disk_usage": metrics["gauges"].get("system.disk.usage_percent", 0),
            "available_memory_gb": metrics["gauges"].get("system.memory.available_gb", 0)
        }
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends over time"""
        # This would analyze historical data to show trends
        return {
            "processing_time_trend": "stable",
            "success_rate_trend": "improving",
            "resource_usage_trend": "stable"
        }

# Global monitoring instance
kg_monitor = KGSystemMonitor()
