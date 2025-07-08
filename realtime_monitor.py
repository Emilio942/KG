#!/usr/bin/env python3
"""
Real-time KG-System Monitoring Dashboard
Überwacht alle Atomic Tasks in Echtzeit und zeigt Performance-Metriken an
"""

import asyncio
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

# Web framework für Dashboard
try:
    from flask import Flask, render_template, jsonify, request
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask nicht verfügbar. Installieren Sie mit: pip install flask flask-socketio")

@dataclass
class SystemMetrics:
    """System-Metriken für Monitoring"""
    timestamp: str
    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    avg_execution_time: float
    current_load: float
    memory_usage: float
    cpu_usage: float
    active_tasks: Dict[str, Any]
    error_rates: Dict[str, float]
    performance_trends: Dict[str, List[float]]

class KGSystemMonitor:
    """Real-time Monitoring für das KG-System"""
    
    def __init__(self):
        self.metrics_history = []
        self.current_tasks = {}
        self.system_alerts = []
        self.performance_data = {
            "hg_times": [],
            "isv_times": [],
            "kd_times": [],
            "lar_times": [],
            "success_rates": [],
            "throughput": []
        }
        
        self.app = None
        self.socketio = None
        if FLASK_AVAILABLE:
            self.setup_web_interface()
    
    def setup_web_interface(self):
        """Setup Web-Interface für Dashboard"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'kg-system-monitor-2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/api/metrics')
        def get_metrics():
            return jsonify(self.get_current_metrics())
        
        @self.app.route('/api/performance')
        def get_performance():
            return jsonify(self.performance_data)
        
        @self.app.route('/api/alerts')
        def get_alerts():
            return jsonify(self.system_alerts[-10:])  # Letzte 10 Alerts
        
        @self.socketio.on('connect')
        def handle_connect():
            emit('status', {'msg': 'Verbunden mit KG-System Monitor'})
        
        @self.socketio.on('request_update')
        def handle_update_request():
            emit('metrics_update', self.get_current_metrics())
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Aktuelle System-Metriken abrufen"""
        import psutil
        
        # System-Ressourcen
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # KG-System spezifische Metriken
        total_cycles = len(self.metrics_history)
        successful = sum(1 for m in self.metrics_history if m.successful_cycles > 0)
        failed = total_cycles - successful
        
        avg_time = 0
        if self.performance_data["hg_times"]:
            recent_times = self.performance_data["hg_times"][-10:]
            avg_time = sum(recent_times) / len(recent_times)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": {
                "status": "HEALTHY" if cpu_percent < 80 and memory_percent < 80 else "WARNING",
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "active_tasks": len(self.current_tasks)
            },
            "kg_metrics": {
                "total_cycles": total_cycles,
                "success_rate": (successful / max(total_cycles, 1)) * 100,
                "avg_execution_time": avg_time,
                "current_throughput": len(self.current_tasks)
            },
            "performance_trends": self.performance_data,
            "recent_alerts": self.system_alerts[-5:]
        }
    
    def log_task_start(self, task_id: str, module: str, task_type: str):
        """Task-Start logging"""
        self.current_tasks[task_id] = {
            "module": module,
            "type": task_type,
            "start_time": time.time(),
            "status": "RUNNING"
        }
        
        if self.socketio:
            self.socketio.emit('task_started', {
                "task_id": task_id,
                "module": module,
                "type": task_type,
                "timestamp": datetime.now().isoformat()
            })
    
    def log_task_completion(self, task_id: str, success: bool, execution_time: float, module: str):
        """Task-Completion logging"""
        if task_id in self.current_tasks:
            self.current_tasks[task_id]["status"] = "SUCCESS" if success else "FAILED"
            self.current_tasks[task_id]["execution_time"] = execution_time
            
            # Performance-Daten aktualisieren
            if module.lower() in ["hg", "isv", "kd", "lar"]:
                key = f"{module.lower()}_times"
                if key in self.performance_data:
                    self.performance_data[key].append(execution_time)
                    # Nur letzte 100 Werte behalten
                    if len(self.performance_data[key]) > 100:
                        self.performance_data[key] = self.performance_data[key][-100:]
            
            # Alert bei Performance-Problemen
            if execution_time > 30:  # Mehr als 30 Sekunden
                self.add_alert(f"Langsame Ausführung: {module} Task {task_id} brauchte {execution_time:.2f}s", "WARNING")
            
            if not success:
                self.add_alert(f"Task fehlgeschlagen: {module} Task {task_id}", "ERROR")
            
            if self.socketio:
                self.socketio.emit('task_completed', {
                    "task_id": task_id,
                    "module": module,
                    "success": success,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Task aus aktiven Tasks entfernen
            del self.current_tasks[task_id]
    
    def add_alert(self, message: str, severity: str = "INFO"):
        """System-Alert hinzufügen"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "severity": severity
        }
        self.system_alerts.append(alert)
        
        # Nur letzte 100 Alerts behalten
        if len(self.system_alerts) > 100:
            self.system_alerts = self.system_alerts[-100:]
        
        if self.socketio:
            self.socketio.emit('new_alert', alert)
        
        print(f"[{severity}] {message}")
    
    def start_monitoring(self, port: int = 5000):
        """Monitoring-Dashboard starten"""
        if not FLASK_AVAILABLE:
            print("❌ Flask nicht verfügbar. Dashboard kann nicht gestartet werden.")
            return
        
        # Template erstellen
        self.create_dashboard_template()
        
        print(f"🚀 KG-System Monitoring Dashboard startet auf http://localhost:{port}")
        print("📊 Real-time Metriken verfügbar")
        print("🔍 Performance-Tracking aktiv")
        
        # Background-Task für regelmäßige Updates
        def background_updates():
            while True:
                time.sleep(5)  # Alle 5 Sekunden
                if self.socketio:
                    self.socketio.emit('metrics_update', self.get_current_metrics())
        
        update_thread = threading.Thread(target=background_updates)
        update_thread.daemon = True
        update_thread.start()
        
        # Dashboard starten
        self.socketio.run(self.app, host='0.0.0.0', port=port, debug=False)
    
    def create_dashboard_template(self):
        """HTML-Template für Dashboard erstellen"""
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        
        html_content = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KG-System Real-time Monitor</title>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .metric-label { color: #7f8c8d; margin-bottom: 10px; }
        .status-healthy { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-error { color: #e74c3c; }
        .chart-container { height: 300px; margin-top: 20px; }
        .alerts-container { max-height: 200px; overflow-y: auto; }
        .alert { padding: 10px; margin: 5px 0; border-left: 4px solid; }
        .alert-info { border-color: #3498db; background: #ebf3fd; }
        .alert-warning { border-color: #f39c12; background: #fef9e7; }
        .alert-error { border-color: #e74c3c; background: #fdebea; }
        .realtime-indicator { display: inline-block; width: 10px; height: 10px; background: #27ae60; border-radius: 50%; animation: blink 1s infinite; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 KG-System Real-time Monitor</h1>
        <p>Atomic Task Chain Überwachung in Echtzeit <span class="realtime-indicator"></span></p>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">System Status</div>
            <div class="metric-value" id="system-status">HEALTHY</div>
            <div>CPU: <span id="cpu-usage">0%</span> | Memory: <span id="memory-usage">0%</span></div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Total Cycles</div>
            <div class="metric-value" id="total-cycles">0</div>
            <div>Success Rate: <span id="success-rate">0%</span></div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Avg Execution Time</div>
            <div class="metric-value" id="avg-time">0s</div>
            <div>Active Tasks: <span id="active-tasks">0</span></div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Current Throughput</div>
            <div class="metric-value" id="throughput">0</div>
            <div>Tasks/min</div>
        </div>
    </div>
    
    <div class="metrics-grid" style="margin-top: 30px;">
        <div class="metric-card">
            <h3>Performance Trends</h3>
            <div class="chart-container">
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
        
        <div class="metric-card">
            <h3>System Alerts</h3>
            <div class="alerts-container" id="alerts-container">
                <!-- Alerts werden hier dynamisch eingefügt -->
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        
        // Chart Setup
        const ctx = document.getElementById('performance-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'HG Times', data: [], borderColor: '#3498db', fill: false },
                    { label: 'ISV Times', data: [], borderColor: '#e74c3c', fill: false },
                    { label: 'KD Times', data: [], borderColor: '#27ae60', fill: false },
                    { label: 'LAR Times', data: [], borderColor: '#f39c12', fill: false }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
        
        socket.on('connect', function() {
            console.log('Verbunden mit KG-System Monitor');
            socket.emit('request_update');
        });
        
        socket.on('metrics_update', function(data) {
            updateMetrics(data);
        });
        
        socket.on('new_alert', function(alert) {
            addAlert(alert);
        });
        
        socket.on('task_started', function(data) {
            console.log('Task gestartet:', data);
        });
        
        socket.on('task_completed', function(data) {
            console.log('Task abgeschlossen:', data);
        });
        
        function updateMetrics(data) {
            // System Health
            document.getElementById('system-status').textContent = data.system_health.status;
            document.getElementById('system-status').className = 'metric-value status-' + data.system_health.status.toLowerCase();
            document.getElementById('cpu-usage').textContent = data.system_health.cpu_usage.toFixed(1) + '%';
            document.getElementById('memory-usage').textContent = data.system_health.memory_usage.toFixed(1) + '%';
            
            // KG Metrics
            document.getElementById('total-cycles').textContent = data.kg_metrics.total_cycles;
            document.getElementById('success-rate').textContent = data.kg_metrics.success_rate.toFixed(1) + '%';
            document.getElementById('avg-time').textContent = data.kg_metrics.avg_execution_time.toFixed(2) + 's';
            document.getElementById('active-tasks').textContent = data.kg_metrics.current_throughput;
            document.getElementById('throughput').textContent = data.kg_metrics.current_throughput;
            
            // Chart Update
            updateChart(data.performance_trends);
        }
        
        function updateChart(trends) {
            const maxPoints = 20;
            
            // Update nur wenn neue Daten vorhanden
            if (trends.hg_times && trends.hg_times.length > 0) {
                chart.data.labels = trends.hg_times.slice(-maxPoints).map((_, i) => i);
                chart.data.datasets[0].data = trends.hg_times.slice(-maxPoints);
                chart.data.datasets[1].data = trends.isv_times.slice(-maxPoints);
                chart.data.datasets[2].data = trends.kd_times.slice(-maxPoints);
                chart.data.datasets[3].data = trends.lar_times.slice(-maxPoints);
                chart.update('none');
            }
        }
        
        function addAlert(alert) {
            const container = document.getElementById('alerts-container');
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-' + alert.severity.toLowerCase();
            alertDiv.innerHTML = `<strong>${alert.severity}:</strong> ${alert.message} <small>(${new Date(alert.timestamp).toLocaleTimeString()})</small>`;
            container.insertBefore(alertDiv, container.firstChild);
            
            // Nur die letzten 10 Alerts behalten
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        
        // Regelmäßige Updates anfordern
        setInterval(function() {
            socket.emit('request_update');
        }, 5000);
    </script>
</body>
</html>
        """
        
        with open(templates_dir / "dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)

# Globaler Monitor (Singleton)
monitor = KGSystemMonitor()

def start_monitoring_dashboard(port: int = 5000):
    """Dashboard in separatem Thread starten"""
    monitor_thread = threading.Thread(target=monitor.start_monitoring, args=(port,))
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor

if __name__ == "__main__":
    print("🚀 KG-System Real-time Monitoring Dashboard")
    print("=" * 60)
    
    # Test-Daten generieren
    monitor.add_alert("System gestartet", "INFO")
    monitor.log_task_start("TEST-001", "HG", "hypothesis_generation")
    time.sleep(2)
    monitor.log_task_completion("TEST-001", True, 1.5, "HG")
    
    # Dashboard starten
    monitor.start_monitoring()
