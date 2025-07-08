#!/usr/bin/env python3
"""
Interactive Web-Dashboard für KG-System
Moderne React-ähnliche Benutzeroberfläche mit Live-Monitoring
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging

# Web-Framework mit moderner UI
try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for
    from flask_socketio import SocketIO, emit, join_room, leave_room
    import plotly.graph_objs as go
    import plotly.utils
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    print("📦 Installing required packages...")
    import subprocess
    import sys
    
    packages = [
        "flask==2.3.3",
        "flask-socketio==5.3.6",
        "plotly==5.17.0",
        "dash==2.14.1",
        "pandas==2.1.1"
    ]
    
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Re-import after installation
    from flask import Flask, render_template, jsonify, request, redirect, url_for
    from flask_socketio import SocketIO, emit, join_room, leave_room
    import plotly.graph_objs as go
    import plotly.utils

class ModernKGDashboard:
    """Moderne Web-Benutzeroberfläche für KG-System"""
    
    def __init__(self, port=5000):
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.config['SECRET_KEY'] = 'kg-system-dashboard-2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.port = port
        self.active_connections = set()
        self.system_metrics = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "current_performance": 0.0,
            "live_tasks": {},
            "performance_history": [],
            "error_logs": []
        }
        
        self.setup_routes()
        self.setup_socketio()
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
            
        @self.app.route('/api/metrics')
        def get_metrics():
            return jsonify(self.system_metrics)
            
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "active_tasks": len(self.system_metrics["live_tasks"]),
                "uptime": "99.9%"
            })
            
        @self.app.route('/api/simulate_cycle', methods=['POST'])
        def simulate_cycle():
            """Simuliert einen KG-System Zyklus für Demo-Zwecke"""
            from atomic_task_implementation import KGSystem
            
            try:
                kg_system = KGSystem()
                result = kg_system.full_system_cycle({
                    "signal": "CREATE_NEW",
                    "constraints": {
                        "category": "FRUIT",
                        "intensity": "MEDIUM",
                        "target_harmony": "> 0.7"
                    }
                })
                
                # Update metrics
                self.system_metrics["total_cycles"] += 1
                if result.get("success", False):
                    self.system_metrics["successful_cycles"] += 1
                
                # Broadcast update to all connected clients
                self.socketio.emit('cycle_update', {
                    "cycle_id": result.get("cycleID"),
                    "status": "SUCCESS" if result.get("success") else "FAILED",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": self.system_metrics
                })
                
                return jsonify(result)
                
            except Exception as e:
                logging.error(f"Simulation error: {e}")
                return jsonify({"error": str(e)}), 500
    
    def setup_socketio(self):
        """Setup SocketIO events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.active_connections.add(request.sid)
            emit('status', {
                "message": "Connected to KG-System Dashboard",
                "timestamp": datetime.now().isoformat(),
                "total_connections": len(self.active_connections)
            })
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.active_connections.discard(request.sid)
            
        @self.socketio.on('request_metrics')
        def handle_metrics_request():
            emit('metrics_update', self.system_metrics)
            
    def create_templates(self):
        """Erstellt moderne HTML-Templates"""
        
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        
        # Modern Dashboard Template
        dashboard_html = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KG-System Dashboard</title>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .glass-effect { 
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .pulse-animation { animation: pulse 2s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body class="gradient-bg min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="glass-effect rounded-xl p-6 mb-8">
            <h1 class="text-4xl font-bold text-white mb-2">🧬 KG-System Dashboard</h1>
            <p class="text-white opacity-80">Real-time Monitoring & Control Center</p>
            <div class="flex items-center mt-4">
                <div class="w-3 h-3 bg-green-400 rounded-full pulse-animation mr-2"></div>
                <span class="text-white">System Operational</span>
                <span class="ml-4 text-white opacity-70" id="timestamp"></span>
            </div>
        </div>

        <!-- Metrics Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="glass-effect rounded-xl p-6">
                <h3 class="text-white text-lg font-semibold mb-2">Total Cycles</h3>
                <p class="text-3xl font-bold text-blue-300" id="total-cycles">0</p>
            </div>
            <div class="glass-effect rounded-xl p-6">
                <h3 class="text-white text-lg font-semibold mb-2">Success Rate</h3>
                <p class="text-3xl font-bold text-green-300" id="success-rate">0%</p>
            </div>
            <div class="glass-effect rounded-xl p-6">
                <h3 class="text-white text-lg font-semibold mb-2">Performance</h3>
                <p class="text-3xl font-bold text-yellow-300" id="performance">0.0</p>
            </div>
            <div class="glass-effect rounded-xl p-6">
                <h3 class="text-white text-lg font-semibold mb-2">Active Tasks</h3>
                <p class="text-3xl font-bold text-purple-300" id="active-tasks">0</p>
            </div>
        </div>

        <!-- Control Panel -->
        <div class="glass-effect rounded-xl p-6 mb-8">
            <h2 class="text-2xl font-bold text-white mb-4">⚡ Control Panel</h2>
            <div class="flex flex-wrap gap-4">
                <button onclick="runSimulation()" 
                        class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors">
                    🚀 Run Simulation Cycle
                </button>
                <button onclick="refreshMetrics()" 
                        class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg transition-colors">
                    🔄 Refresh Metrics
                </button>
                <button onclick="exportData()" 
                        class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg transition-colors">
                    📊 Export Data
                </button>
            </div>
        </div>

        <!-- Performance Chart -->
        <div class="glass-effect rounded-xl p-6 mb-8">
            <h2 class="text-2xl font-bold text-white mb-4">📈 Performance Trends</h2>
            <div id="performance-chart" style="height: 400px;"></div>
        </div>

        <!-- Live Activity Feed -->
        <div class="glass-effect rounded-xl p-6">
            <h2 class="text-2xl font-bold text-white mb-4">📡 Live Activity Feed</h2>
            <div id="activity-feed" class="bg-black bg-opacity-30 rounded-lg p-4 h-64 overflow-y-auto">
                <p class="text-green-400">System initialized. Waiting for activity...</p>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        // Initialize timestamp
        function updateTimestamp() {
            document.getElementById('timestamp').textContent = new Date().toLocaleString();
        }
        updateTimestamp();
        setInterval(updateTimestamp, 1000);
        
        // Socket event handlers
        socket.on('connect', function() {
            addToFeed('✅ Connected to KG-System', 'success');
        });
        
        socket.on('cycle_update', function(data) {
            updateMetrics(data.metrics);
            addToFeed(`🔬 Cycle ${data.cycle_id}: ${data.status}`, data.status === 'SUCCESS' ? 'success' : 'error');
        });
        
        socket.on('metrics_update', function(data) {
            updateMetrics(data);
        });
        
        // Update UI metrics
        function updateMetrics(metrics) {
            document.getElementById('total-cycles').textContent = metrics.total_cycles || 0;
            const successRate = metrics.total_cycles > 0 ? 
                Math.round((metrics.successful_cycles / metrics.total_cycles) * 100) : 0;
            document.getElementById('success-rate').textContent = successRate + '%';
            document.getElementById('performance').textContent = (metrics.current_performance || 0).toFixed(3);
            document.getElementById('active-tasks').textContent = Object.keys(metrics.live_tasks || {}).length;
            
            updatePerformanceChart(metrics.performance_history || []);
        }
        
        // Add message to activity feed
        function addToFeed(message, type = 'info') {
            const feed = document.getElementById('activity-feed');
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'success' ? 'text-green-400' : 
                         type === 'error' ? 'text-red-400' : 'text-blue-400';
            
            const entry = document.createElement('div');
            entry.innerHTML = `<span class="text-gray-400">[${timestamp}]</span> <span class="${color}">${message}</span>`;
            feed.appendChild(entry);
            feed.scrollTop = feed.scrollHeight;
        }
        
        // Control functions
        async function runSimulation() {
            addToFeed('🚀 Starting simulation cycle...', 'info');
            try {
                const response = await fetch('/api/simulate_cycle', { method: 'POST' });
                const result = await response.json();
                if (result.error) {
                    addToFeed(`❌ Simulation failed: ${result.error}`, 'error');
                } else {
                    addToFeed('✅ Simulation cycle initiated', 'success');
                }
            } catch (error) {
                addToFeed(`❌ Network error: ${error.message}`, 'error');
            }
        }
        
        function refreshMetrics() {
            socket.emit('request_metrics');
            addToFeed('🔄 Metrics refreshed', 'info');
        }
        
        function exportData() {
            addToFeed('📊 Exporting data... (Feature coming soon)', 'info');
        }
        
        // Performance chart
        function updatePerformanceChart(data) {
            const trace = {
                x: data.map((_, i) => i),
                y: data,
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#60A5FA', width: 3 },
                marker: { color: '#3B82F6', size: 8 }
            };
            
            const layout = {
                title: { text: 'Performance Over Time', font: { color: 'white' } },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0.3)',
                font: { color: 'white' },
                xaxis: { title: 'Cycle', gridcolor: 'rgba(255,255,255,0.2)' },
                yaxis: { title: 'Performance Score', gridcolor: 'rgba(255,255,255,0.2)' }
            };
            
            Plotly.newPlot('performance-chart', [trace], layout, { responsive: true });
        }
        
        // Initialize empty chart
        updatePerformanceChart([]);
    </script>
</body>
</html>'''
        
        with open(templates_dir / "dashboard.html", "w", encoding="utf-8") as f:
            f.write(dashboard_html)
    
    def run(self, debug=False):
        """Startet das Dashboard"""
        print("🚀 Creating modern dashboard templates...")
        self.create_templates()
        
        print(f"🌐 Starting KG-System Dashboard on http://localhost:{self.port}")
        print("📊 Features:")
        print("  ✅ Real-time monitoring")
        print("  ✅ Interactive controls")
        print("  ✅ Performance visualization")
        print("  ✅ Live activity feed")
        print("  ✅ Modern responsive UI")
        
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=debug)

def main():
    """Hauptfunktion für moderne Dashboard-Demo"""
    print("🧬 KG-System Modern Web Dashboard")
    print("=" * 50)
    
    # Erstelle und starte Dashboard
    dashboard = ModernKGDashboard(port=5000)
    
    try:
        dashboard.run(debug=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard wird beendet...")
    except Exception as e:
        print(f"❌ Fehler beim Starten des Dashboards: {e}")
        print("💡 Stellen Sie sicher, dass alle Dependencies installiert sind:")
        print("   pip install flask flask-socketio plotly dash pandas")

if __name__ == "__main__":
    main()
