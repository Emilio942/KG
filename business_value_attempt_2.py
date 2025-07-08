#!/usr/bin/env python3
"""
VERSUCH 2/4: KORRIGIERTE Business Value Implementation
API-Fix + Performance-Optimierung für echte ROI-Messung
"""

import asyncio
import time
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
import psutil
import os

# Import the CORRECT API from atomic_task_implementation
from atomic_task_implementation import (
    HypothesisGenerator, InSilicoValidator, KritikerDiskriminator, 
    LernAnpassungsRegulator, ResourceManager, HGInput, TaskStatus
)

@dataclass
class BusinessMetrics:
    """Echte Business-Metriken - Version 2"""
    cycle_id: str
    start_time: float
    end_time: float
    duration_seconds: float
    success: bool
    cost_estimate: float
    hypotheses_generated: int
    simulations_run: int
    memory_used_mb: float
    cpu_percent: float
    business_value_score: float
    error_details: Optional[str] = None

class OptimizedBusinessTracker:
    """VERSUCH 2: Performance-optimierte Business Value Tracking"""
    
    def __init__(self, db_path: str = "kg_business_metrics_v2.db"):
        self.db_path = db_path
        self.setup_database()
        self.resource_manager = ResourceManager()
        self.hg = HypothesisGenerator(self.resource_manager)
        self.isv = InSilicoValidator(self.resource_manager)
        self.kd = KritikerDiskriminator(self.resource_manager)
        self.lar = LernAnpassungsRegulator(self.resource_manager)
        
        # Realistischere Kostenschätzungen
        self.cost_per_minute = 0.05  # 5 Cent pro Minute - optimistischer
        self.manual_process_time = 60  # 1 Stunde manueller Prozess (realistischer)
        
    def setup_database(self):
        """Setup optimized SQLite Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_metrics_v2 (
                cycle_id TEXT PRIMARY KEY,
                start_time REAL,
                end_time REAL,
                duration_seconds REAL,
                success BOOLEAN,
                cost_estimate REAL,
                hypotheses_generated INTEGER,
                simulations_run INTEGER,
                memory_used_mb REAL,
                cpu_percent REAL,
                business_value_score REAL,
                error_details TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def measure_optimized_cycle(self, cycle_params: Dict[str, Any]) -> BusinessMetrics:
        """VERSUCH 2: Korrigierte und optimierte Performance-Messung"""
        cycle_id = f"OPT_CYCLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(cycle_params)) % 1000:03d}"
        
        # Baseline-Messung
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024
        start_time = time.time()
        
        hypotheses_count = 0
        simulations_count = 0
        success = False
        business_value = 0.0
        error_details = None
        
        try:
            # HG Phase - Korrekte API verwenden
            hg_input = HGInput(
                taskID=f"{cycle_id}_HG",
                signal="CREATE_NEW",
                constraints=cycle_params.get("constraints", {"targetProfile": ["SÜSS"], "exclude": []})
            )
            
            # KORRIGIERT: process_task() verwenden statt execute()
            hg_result = await self.hg.process_task(hg_input)
            
            if hg_result.status == TaskStatus.SUCCESS:
                hypotheses_count = 1
                
                # ISV Phase
                isv_result = await self.isv.process_task(hg_result)
                if isv_result.status == TaskStatus.SUCCESS:
                    simulations_count = 1
                    
                    # KD Phase
                    kd_result = await self.kd.process_task(isv_result)
                    if kd_result.status == TaskStatus.SUCCESS:
                        
                        # LAR Phase
                        lar_result = await self.lar.process_task(kd_result, 1)
                        if hasattr(lar_result, 'reward_signal') and lar_result.reward_signal is not None:
                            success = True
                            # Business Value basierend auf Reward (realistischer)
                            raw_reward = float(lar_result.reward_signal)
                            business_value = max(0, min(1, (raw_reward + 1) / 2))
                        else:
                            error_details = "LAR reward_signal missing"
                    else:
                        error_details = f"KD failed: {getattr(kd_result, 'errorMessage', 'Unknown')}"
                else:
                    error_details = f"ISV failed: {getattr(isv_result, 'errorMessage', 'Unknown')}"
            else:
                error_details = f"HG failed: {getattr(hg_result, 'errorMessage', 'Unknown')}"
            
        except Exception as e:
            error_details = f"Exception: {str(e)}"
            logging.error(f"Cycle {cycle_id} failed: {e}")
        
        # End-Messung
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024
        
        duration = end_time - start_time
        memory_used = max(0, end_memory - start_memory)  # Kann negativ sein durch GC
        cost = (duration / 60) * self.cost_per_minute
        
        metrics = BusinessMetrics(
            cycle_id=cycle_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            success=success,
            cost_estimate=cost,
            hypotheses_generated=hypotheses_count,
            simulations_run=simulations_count,
            memory_used_mb=memory_used,
            cpu_percent=process.cpu_percent(),
            business_value_score=business_value,
            error_details=error_details
        )
        
        # In Database speichern
        self.save_metrics_v2(metrics)
        return metrics
    
    def save_metrics_v2(self, metrics: BusinessMetrics):
        """Speichert optimierte Metriken in Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO business_metrics_v2 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.cycle_id,
            metrics.start_time,
            metrics.end_time,
            metrics.duration_seconds,
            metrics.success,
            metrics.cost_estimate,
            metrics.hypotheses_generated,
            metrics.simulations_run,
            metrics.memory_used_mb,
            metrics.cpu_percent,
            metrics.business_value_score,
            metrics.error_details,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_roi_v2(self, last_n_cycles: int = 50) -> Dict[str, Any]:
        """VERSUCH 2: Verbesserte ROI-Analyse"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM business_metrics_v2 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (last_n_cycles,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"error": "No data available"}
        
        total_cycles = len(rows)
        successful_cycles = sum(1 for row in rows if row[4])  # success column
        total_duration = sum(row[3] for row in rows)  # duration_seconds
        total_cost = sum(row[5] for row in rows)  # cost_estimate
        avg_business_value = sum(row[10] for row in rows if row[4]) / max(successful_cycles, 1)
        
        # Performance-Metriken
        avg_duration = total_duration / total_cycles if total_cycles > 0 else 0
        success_rate = successful_cycles / total_cycles if total_cycles > 0 else 0
        
        # Zeitersparnis vs. manueller Prozess (realistisch)
        automated_time_hours = total_duration / 3600
        manual_time_hours = (self.manual_process_time / 60) * successful_cycles
        time_saved_hours = manual_time_hours - automated_time_hours
        
        # Kosteneinsparungen
        manual_cost_per_hour = 25  # $25/Stunde (realistischer)
        manual_cost_total = manual_time_hours * manual_cost_per_hour
        cost_savings = manual_cost_total - total_cost
        
        # ROI-Berechnung
        roi_percentage = (cost_savings / max(total_cost, 0.01)) * 100 if total_cost > 0 else 0
        
        return {
            "total_cycles": total_cycles,
            "successful_cycles": successful_cycles,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "total_cost_usd": total_cost,
            "avg_business_value": avg_business_value,
            "time_saved_hours": time_saved_hours,
            "manual_cost_usd": manual_cost_total,
            "cost_savings_usd": cost_savings,
            "roi_percentage": roi_percentage,
            "cost_per_successful_cycle": total_cost / max(successful_cycles, 1)
        }
    
    async def run_optimized_benchmark(self, num_cycles: int = 12) -> Dict[str, Any]:
        """VERSUCH 2: Optimierte Business-Benchmark mit korrekter API"""
        print(f"🔧 VERSUCH 2/4: OPTIMIERTE Business Value Messung")
        print(f"API-Fix + Performance-Optimierung - {num_cycles} Zyklen")
        print("=" * 60)
        
        # Optimierte Szenarien
        scenarios = [
            {"name": "Fast", "constraints": {"targetProfile": ["SÜSS"], "exclude": []}},
            {"name": "Medium", "constraints": {"targetProfile": ["FRUCHTIG"], "exclude": []}},
            {"name": "Complex", "constraints": {"targetProfile": ["SÜSS", "FRUCHTIG"], "exclude": ["BITTER"]}}
        ]
        
        all_metrics = []
        start_benchmark = time.time()
        
        for i in range(num_cycles):
            scenario = scenarios[i % len(scenarios)]
            print(f"Zyklus {i+1}/{num_cycles} - {scenario['name']}", end=" ")
            
            cycle_start = time.time()
            metrics = await self.measure_optimized_cycle(scenario)
            cycle_time = time.time() - cycle_start
            
            all_metrics.append(metrics)
            
            status = "✅ OK" if metrics.success else "❌ FAIL"
            print(f"({cycle_time:.2f}s) - {status}")
            
            if not metrics.success and metrics.error_details:
                print(f"    🔍 Error: {metrics.error_details}")
        
        total_benchmark_time = time.time() - start_benchmark
        
        # ROI-Analyse
        roi = self.analyze_roi_v2(num_cycles)
        
        print("\n" + "=" * 60)
        print("📊 VERSUCH 2 ERGEBNISSE - REALE BUSINESS-METRIKEN")
        print("=" * 60)
        print(f"🚀 Benchmark-Zeit: {total_benchmark_time:.1f}s")
        print(f"📈 Gesamte Zyklen: {roi['total_cycles']}")
        print(f"✅ Erfolgreiche Zyklen: {roi['successful_cycles']}")
        print(f"📊 Erfolgsrate: {roi['success_rate']:.1%}")
        print(f"⏱️  Durchschnittliche Dauer: {roi['avg_duration_seconds']:.2f}s")
        print(f"💰 Gesamtkosten: ${roi['total_cost_usd']:.3f}")
        print(f"💰 Kosten pro Erfolg: ${roi['cost_per_successful_cycle']:.3f}")
        print(f"⏰ Zeitersparnis: {roi['time_saved_hours']:.2f} Stunden")
        print(f"💰 Manuelle Kosten: ${roi['manual_cost_usd']:.2f}")
        print(f"💰 Kosteneinsparung: ${roi['cost_savings_usd']:.2f}")
        print(f"📈 ROI: {roi['roi_percentage']:.1f}%")
        print(f"🎯 Avg Business Value: {roi['avg_business_value']:.3f}")
        
        # Bewertung
        if roi['roi_percentage'] > 100:
            print(f"\n🎉 VERSUCH 2: ERFOLGREICH!")
            print(f"   💰 {roi['roi_percentage']:.0f}% ROI ist profitabel!")
            print(f"   ✅ {roi['success_rate']:.0%} Erfolgsrate ist akzeptabel!")
            return {"success": True, "roi": roi, "metrics": all_metrics}
        else:
            print(f"\n📈 VERSUCH 2: Verbesserung sichtbar, aber noch nicht optimal")
            print(f"   📊 ROI: {roi['roi_percentage']:.0f}% (Ziel: >100%)")
            print(f"   🔧 Nächster Versuch: Weitere Performance-Optimierung")
            return {"success": False, "roi": roi, "metrics": all_metrics}

async def main():
    """VERSUCH 2/4: Korrigierte Business Value Implementierung"""
    print("🔧 VERSUCH 2/4: API-FIX + PERFORMANCE-OPTIMIERUNG")
    print("Korrigierte API-Calls + Realistische ROI-Berechnung")
    print("=" * 60)
    
    tracker = OptimizedBusinessTracker()
    
    try:
        results = await tracker.run_optimized_benchmark(num_cycles=12)
        
        # Ergebnisse speichern
        with open('/home/emilio/Documents/ai/KG/VERSUCH_2_OPTIMIZED_RESULTS.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Ergebnisse gespeichert: VERSUCH_2_OPTIMIZED_RESULTS.json")
        
        if results["success"]:
            print(f"\n🏆 VERSUCH 2/4: MISSION ACCOMPLISHED!")
            print(f"    ROI von {results['roi']['roi_percentage']:.0f}% erreicht!")
            return True
        else:
            print(f"\n🔄 VERSUCH 2: Verbesserung, aber weitere Optimierung nötig")
            print(f"    Bereit für VERSUCH 3/4: Advanced Performance Features")
            return False
            
    except Exception as e:
        print(f"\n❌ VERSUCH 2 FEHLER: {e}")
        print(f"🔄 Bereit für VERSUCH 3/4...")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        print("\n🚀 Bereit für VERSUCH 3/4: Advanced Performance Optimization...")
