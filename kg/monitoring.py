# KG-System Monitoring und Metriken
# Prometheus-basierte Metriken und Performance-Monitoring

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import threading

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
except ImportError:
    # Fallback wenn prometheus_client nicht verfügbar
    print("prometheus_client nicht verfügbar - verwende Mock-Implementierung")
    
    class MockMetric:
        def inc(self, amount=1): pass
        def observe(self, amount): pass
        def set(self, value): pass
        def labels(self, **kwargs): return self
    
    Counter = Histogram = Gauge = lambda *args, **kwargs: MockMetric()
    def start_http_server(port): pass
    CollectorRegistry = lambda: None

@dataclass
class PerformanceMetrik:
    """Performance-Metrik für ein Modul"""
    module: str
    operation: str
    duration: float
    success: bool
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemHealth:
    """System-Gesundheitsstatus"""
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    queue_length: int
    error_rate: float
    timestamp: datetime

class KGMetricsCollector:
    """Metriken-Sammler für das KG-System"""
    
    def __init__(self, enable_prometheus: bool = True):
        self.enable_prometheus = enable_prometheus
        self.metrics_history = deque(maxlen=10000)  # Letzten 10k Metriken
        self.module_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0
        })
        
        # System-Status
        self.system_start_time = datetime.now()
        self.health_history = deque(maxlen=1000)
        
        # Prometheus-Metriken
        if self.enable_prometheus:
            self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus-Metriken"""
        
        # Request Counters
        self.request_counter = Counter(
            'kg_requests_total',
            'Anzahl der Requests pro Modul',
            ['module', 'operation', 'status']
        )
        
        # Duration Histograms
        self.duration_histogram = Histogram(
            'kg_request_duration_seconds',
            'Dauer der Requests in Sekunden',
            ['module', 'operation'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf'))
        )
        
        # Gauges für aktuelle Werte
        self.active_tasks_gauge = Gauge(
            'kg_active_tasks',
            'Anzahl aktiver Tasks'
        )
        
        self.cpu_usage_gauge = Gauge(
            'kg_cpu_usage_percent',
            'CPU-Nutzung in Prozent'
        )
        
        self.memory_usage_gauge = Gauge(
            'kg_memory_usage_percent',
            'Memory-Nutzung in Prozent'
        )
        
        self.error_rate_gauge = Gauge(
            'kg_error_rate_percent',
            'Fehlerrate in Prozent',
            ['module']
        )
        
        # Geschäftsspezifische Metriken
        self.hypotheses_generated = Counter(
            'kg_hypotheses_generated_total',
            'Anzahl generierter Hypothesen'
        )
        
        self.hypotheses_approved = Counter(
            'kg_hypotheses_approved_total',
            'Anzahl genehmigter Hypothesen'
        )
        
        self.novelty_score_histogram = Histogram(
            'kg_novelty_score',
            'Novelty-Scores der Hypothesen',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
        )
        
        self.simulation_method_counter = Counter(
            'kg_simulation_method_total',
            'Anzahl Simulationen pro Methode',
            ['method']
        )
    
    def record_request(self, module: str, operation: str, duration: float, 
                      success: bool, metadata: Dict[str, Any] = None):
        """Registriere Request-Metrik"""
        
        metrik = PerformanceMetrik(
            module=module,
            operation=operation,
            duration=duration,
            success=success,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.metrics_history.append(metrik)
        
        # Update Statistiken
        stats = self.module_stats[module]
        stats['total_requests'] += 1
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
        
        stats['total_duration'] += duration
        stats['min_duration'] = min(stats['min_duration'], duration)
        stats['max_duration'] = max(stats['max_duration'], duration)
        
        # Prometheus-Metriken
        if self.enable_prometheus:
            status = 'success' if success else 'error'
            self.request_counter.labels(
                module=module, 
                operation=operation, 
                status=status
            ).inc()
            
            self.duration_histogram.labels(
                module=module, 
                operation=operation
            ).observe(duration)
    
    def record_hypothesis_generated(self, novelty_score: float, approved: bool = False):
        """Registriere Hypothesen-Generierung"""
        if self.enable_prometheus:
            self.hypotheses_generated.inc()
            self.novelty_score_histogram.observe(novelty_score)
            
            if approved:
                self.hypotheses_approved.inc()
    
    def record_simulation_method(self, method: str):
        """Registriere Simulationsmethode"""
        if self.enable_prometheus:
            self.simulation_method_counter.labels(method=method).inc()
    
    def update_system_health(self, health: SystemHealth):
        """Update System-Gesundheit"""
        self.health_history.append(health)
        
        if self.enable_prometheus:
            self.active_tasks_gauge.set(health.active_tasks)
            self.cpu_usage_gauge.set(health.cpu_usage)
            self.memory_usage_gauge.set(health.memory_usage)
    
    def get_module_statistics(self, module: str) -> Dict[str, Any]:
        """Hole Statistiken für ein Modul"""
        stats = self.module_stats[module]
        
        if stats['total_requests'] == 0:
            return {
                'module': module,
                'total_requests': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'min_duration': 0.0,
                'max_duration': 0.0
            }
        
        return {
            'module': module,
            'total_requests': stats['total_requests'],
            'successful_requests': stats['successful_requests'],
            'failed_requests': stats['failed_requests'],
            'success_rate': (stats['successful_requests'] / stats['total_requests']) * 100,
            'average_duration': stats['total_duration'] / stats['total_requests'],
            'min_duration': stats['min_duration'],
            'max_duration': stats['max_duration']
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Hole System-Übersicht"""
        uptime = (datetime.now() - self.system_start_time).total_seconds()
        
        total_requests = sum(stats['total_requests'] for stats in self.module_stats.values())
        total_successful = sum(stats['successful_requests'] for stats in self.module_stats.values())
        
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'total_requests': total_requests,
            'overall_success_rate': overall_success_rate,
            'modules': {module: self.get_module_statistics(module) 
                      for module in self.module_stats.keys()},
            'recent_health': list(self.health_history)[-10:] if self.health_history else []
        }
    
    def get_recent_metrics(self, minutes: int = 30) -> List[PerformanceMetrik]:
        """Hole aktuelle Metriken der letzten N Minuten"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        return [m for m in self.metrics_history if m.timestamp >= cutoff]
    
    def export_metrics_json(self) -> str:
        """Exportiere Metriken als JSON"""
        return json.dumps({
            'system_overview': self.get_system_overview(),
            'recent_metrics': [
                {
                    'module': m.module,
                    'operation': m.operation,
                    'duration': m.duration,
                    'success': m.success,
                    'timestamp': m.timestamp.isoformat(),
                    'metadata': m.metadata
                }
                for m in self.get_recent_metrics(60)  # Letzte Stunde
            ]
        }, indent=2, ensure_ascii=False)

class SystemMonitor:
    """System-Monitor für kontinuierliche Überwachung"""
    
    def __init__(self, metrics_collector: KGMetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring_active = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Starte kontinuierliches Monitoring"""
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stoppe Monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitoring_loop(self, interval_seconds: int):
        """Monitoring-Schleife"""
        while self.monitoring_active:
            try:
                health = self._collect_system_health()
                self.metrics_collector.update_system_health(health)
                
                # Prüfe auf Anomalien
                self._check_for_anomalies(health)
                
            except Exception as e:
                print(f"Fehler im Monitoring: {e}")
            
            time.sleep(interval_seconds)
    
    def _collect_system_health(self) -> SystemHealth:
        """Sammle System-Gesundheitsdaten"""
        try:
            import psutil
            
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            
        except ImportError:
            # Fallback ohne psutil
            cpu_usage = 25.0  # Mock-Werte
            memory_usage = 45.0
        
        # Berechne Fehlerrate der letzten 10 Minuten
        recent_metrics = self.metrics_collector.get_recent_metrics(10)
        if recent_metrics:
            error_count = sum(1 for m in recent_metrics if not m.success)
            error_rate = (error_count / len(recent_metrics)) * 100
        else:
            error_rate = 0.0
        
        return SystemHealth(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            active_tasks=5,  # Mock - würde aus echtem System geholt
            queue_length=2,  # Mock
            error_rate=error_rate,
            timestamp=datetime.now()
        )
    
    def _check_for_anomalies(self, health: SystemHealth):
        """Prüfe auf System-Anomalien"""
        alerts = []
        
        if health.cpu_usage > 90:
            alerts.append(f"Hohe CPU-Nutzung: {health.cpu_usage:.1f}%")
        
        if health.memory_usage > 85:
            alerts.append(f"Hohe Memory-Nutzung: {health.memory_usage:.1f}%")
        
        if health.error_rate > 20:
            alerts.append(f"Hohe Fehlerrate: {health.error_rate:.1f}%")
        
        if health.queue_length > 50:
            alerts.append(f"Lange Warteschlange: {health.queue_length}")
        
        if alerts:
            print(f"🚨 SYSTEM-ALERTS: {', '.join(alerts)}")

class KGMetricsMiddleware:
    """Middleware für automatische Metriken-Sammlung"""
    
    def __init__(self, metrics_collector: KGMetricsCollector):
        self.metrics_collector = metrics_collector
    
    def record_operation(self, module: str, operation: str):
        """Decorator für automatische Metriken-Sammlung"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                metadata = {}
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    
                    # Sammle spezifische Metadaten
                    if hasattr(result, 'hypotheseID'):
                        metadata['hypothese_id'] = result.hypotheseID
                    
                    return result
                    
                except Exception as e:
                    metadata['error'] = str(e)
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    self.metrics_collector.record_request(
                        module, operation, duration, success, metadata
                    )
            
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                metadata = {}
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    metadata['error'] = str(e)
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    self.metrics_collector.record_request(
                        module, operation, duration, success, metadata
                    )
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator

# === Dashboard-HTML für einfache Webansicht ===

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>KG-System Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; margin: 10px 20px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { font-size: 0.9em; color: #666; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-bad { color: #dc3545; }
        .progress-bar { background-color: #e9ecef; border-radius: 4px; height: 10px; margin: 5px 0; }
        .progress-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
    </style>
    <script>
        function refreshData() {
            fetch('/metriken')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDashboard(data) {
            // Update Dashboard mit aktuellen Daten
            console.log('Dashboard-Update:', data);
        }
        
        // Auto-refresh alle 30 Sekunden
        setInterval(refreshData, 30000);
        
        // Initial load
        document.addEventListener('DOMContentLoaded', refreshData);
    </script>
</head>
<body>
    <div class="container">
        <h1>🧪 KG-System Dashboard</h1>
        
        <div class="card">
            <h2>System-Status</h2>
            <div class="metric">
                <div class="metric-value status-good">●</div>
                <div class="metric-label">System Running</div>
            </div>
            <div class="metric">
                <div class="metric-value">2.5h</div>
                <div class="metric-label">Uptime</div>
            </div>
            <div class="metric">
                <div class="metric-value">147</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric">
                <div class="metric-value">94.2%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Performance-Metriken</h2>
            <table>
                <tr>
                    <th>Modul</th>
                    <th>Requests</th>
                    <th>Success Rate</th>
                    <th>Avg. Duration</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>HG</td>
                    <td>45</td>
                    <td>97.8%</td>
                    <td>0.8s</td>
                    <td><span class="status-good">●</span> Healthy</td>
                </tr>
                <tr>
                    <td>ISV</td>
                    <td>42</td>
                    <td>88.1%</td>
                    <td>3.2s</td>
                    <td><span class="status-warning">●</span> Warning</td>
                </tr>
                <tr>
                    <td>KD</td>
                    <td>38</td>
                    <td>100%</td>
                    <td>0.6s</td>
                    <td><span class="status-good">●</span> Healthy</td>
                </tr>
                <tr>
                    <td>LAR</td>
                    <td>22</td>
                    <td>95.5%</td>
                    <td>0.3s</td>
                    <td><span class="status-good">●</span> Healthy</td>
                </tr>
            </table>
        </div>
        
        <div class="card">
            <h2>Ressourcen-Nutzung</h2>
            <div>
                <label>CPU: 25%</label>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 25%; background-color: #28a745;"></div>
                </div>
            </div>
            <div>
                <label>Memory: 45%</label>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 45%; background-color: #007bff;"></div>
                </div>
            </div>
            <div>
                <label>Active Tasks: 3</label>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 30%; background-color: #ffc107;"></div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Geschäfts-Metriken</h2>
            <div class="metric">
                <div class="metric-value">147</div>
                <div class="metric-label">Hypothesen Generiert</div>
            </div>
            <div class="metric">
                <div class="metric-value">132</div>
                <div class="metric-label">Hypothesen Genehmigt</div>
            </div>
            <div class="metric">
                <div class="metric-value">89.8%</div>
                <div class="metric-label">Approval Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">0.87</div>
                <div class="metric-label">Avg. Novelty Score</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# === Test und Demo ===

async def demo_metrics_collection():
    """Demo der Metriken-Sammlung"""
    print("🔍 KG-System Metriken Demo")
    print("=" * 50)
    
    # Setup
    collector = KGMetricsCollector(enable_prometheus=False)
    monitor = SystemMonitor(collector)
    middleware = KGMetricsMiddleware(collector)
    
    # Starte Monitoring
    monitor.start_monitoring(interval_seconds=5)
    
    # Simuliere einige Operations
    print("Simuliere HG-Operationen...")
    for i in range(10):
        duration = 0.5 + i * 0.1
        success = i % 8 != 0  # Alle 8. Operation fehlschlägt
        collector.record_request("HG", "generate_hypothesis", duration, success)
        
        if success:
            collector.record_hypothesis_generated(0.7 + i * 0.02, approved=(i % 3 == 0))
    
    print("Simuliere ISV-Operationen...")
    for i in range(8):
        method = "NEURAL_MD" if i % 2 == 0 else "CLASSIC_MD"
        duration = 1.8 if method == "NEURAL_MD" else 3.5
        success = i % 6 != 0
        
        collector.record_request("ISV", "simulate", duration, success)
        if success:
            collector.record_simulation_method(method)
    
    print("Simuliere KD-Operationen...")
    for i in range(7):
        duration = 0.6 + i * 0.05
        success = True
        collector.record_request("KD", "evaluate", duration, success)
    
    # Warte kurz für Monitoring-Daten
    await asyncio.sleep(2)
    
    # Zeige Ergebnisse
    print("\n📊 SYSTEM-ÜBERSICHT:")
    overview = collector.get_system_overview()
    print(f"Uptime: {overview['uptime_seconds']:.1f}s")
    print(f"Total Requests: {overview['total_requests']}")
    print(f"Success Rate: {overview['overall_success_rate']:.1f}%")
    
    print("\n📈 MODUL-STATISTIKEN:")
    for module, stats in overview['modules'].items():
        print(f"{module}:")
        print(f"  Requests: {stats['total_requests']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"  Avg Duration: {stats['average_duration']:.2f}s")
    
    # Exportiere Metriken
    print("\n💾 Exportiere Metriken...")
    with open("kg_metrics_export.json", "w", encoding="utf-8") as f:
        f.write(collector.export_metrics_json())
    
    print("Metriken exportiert nach: kg_metrics_export.json")
    
    # Stoppe Monitoring
    monitor.stop_monitoring()
    print("\n✅ Demo abgeschlossen!")

if __name__ == "__main__":
    asyncio.run(demo_metrics_collection())
