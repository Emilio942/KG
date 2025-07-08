#!/usr/bin/env python3
"""
KG-System Real-Time Monitor
Provides live monitoring of system status and performance.
"""

import asyncio
import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any

class KGSystemMonitor:
    """Real-time monitoring for the KG-System"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.running = False
        self.monitoring_interval = 5  # seconds
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get current system metrics"""
        try:
            response = requests.get(f"{self.base_url}/metriken", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except Exception as e:
            return []
    
    def get_active_hypotheses(self) -> List[Dict[str, Any]]:
        """Get active hypotheses"""
        try:
            response = requests.get(f"{self.base_url}/hypothesen/aktive", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except Exception as e:
            return []
    
    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def print_status_dashboard(self):
        """Print the real-time status dashboard"""
        self.clear_screen()
        
        print("=" * 80)
        print("🖥️  KG-SYSTEM REAL-TIME MONITOR")
        print("=" * 80)
        print(f"🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Refresh Rate: {self.monitoring_interval}s")
        print()
        
        # System Health
        print("🏥 SYSTEM HEALTH")
        print("-" * 40)
        status = self.get_system_status()
        
        if status.get("status") == "healthy":
            print("✅ Status: HEALTHY")
            print(f"⏱️  Uptime: {self.format_uptime(status.get('uptime_seconds', 0))}")
            print(f"🧠 KG System: {'✅ Ready' if status.get('kg_system_initialized') else '❌ Not Ready'}")
            print(f"📊 Active Tasks: {status.get('active_tasks', 0)}")
        else:
            print("❌ Status: UNHEALTHY")
            print(f"💬 Message: {status.get('message', 'Unknown error')}")
        print()
        
        # System Metrics
        print("📊 SYSTEM METRICS")
        print("-" * 40)
        metrics = self.get_metrics()
        
        if metrics:
            for i, metric in enumerate(metrics[:6]):  # Show top 6 metrics
                metric_name = metric.get('typ', 'Unknown')
                metric_value = metric.get('wert', 'N/A')
                print(f"📈 {metric_name}: {metric_value}")
        else:
            print("❌ No metrics available")
        print()
        
        # Active Hypotheses
        print("🧪 ACTIVE HYPOTHESES")
        print("-" * 40)
        hypotheses = self.get_active_hypotheses()
        
        if hypotheses:
            print(f"📋 Total Active: {len(hypotheses)}")
            for i, hyp in enumerate(hypotheses[:5]):  # Show top 5
                task_id = hyp.get('task_id', 'Unknown')
                status = hyp.get('status', 'Unknown')
                print(f"   {i+1}. {task_id}: {status}")
            
            if len(hypotheses) > 5:
                print(f"   ... and {len(hypotheses) - 5} more")
        else:
            print("📋 No active hypotheses")
        print()
        
        # System Capabilities
        print("⚙️  SYSTEM CAPABILITIES")
        print("-" * 40)
        capabilities = [
            "🧬 Hypothesis Generation",
            "🔬 In-Silico Validation", 
            "⚖️  Critical Evaluation",
            "🧠 Learning & Adaptation",
            "🌐 RESTful API",
            "📊 Real-time Analytics"
        ]
        
        # Show capabilities in two columns
        for i in range(0, len(capabilities), 2):
            left = capabilities[i] if i < len(capabilities) else ""
            right = capabilities[i+1] if i+1 < len(capabilities) else ""
            print(f"   {left:<30} {right}")
        print()
        
        # Control Instructions
        print("🎮 CONTROLS")
        print("-" * 40)
        print("   Ctrl+C: Exit monitor")
        print("   The system is being monitored in real-time...")
        print()
        
        print("=" * 80)
        print("🚀 KG-SYSTEM OPERATIONAL STATUS: ACTIVE")
        print("=" * 80)
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True
        
        try:
            while self.running:
                self.print_status_dashboard()
                await asyncio.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            self.running = False
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            self.running = False
    
    def start_monitoring(self):
        """Start the monitoring process"""
        print("🚀 Starting KG-System Real-Time Monitor...")
        print("Press Ctrl+C to stop monitoring")
        time.sleep(2)
        
        try:
            asyncio.run(self.monitor_loop())
        except KeyboardInterrupt:
            print("\n✅ Monitor stopped successfully")

def main():
    """Main function"""
    monitor = KGSystemMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
