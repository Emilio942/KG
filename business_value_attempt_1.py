#!/usr/bin/env python3
"""
VERSUCH 1/4: Konkrete Business Value Implementation
Messbare Performance-Optimierung + ROI-Tracking ohne Marketing-Bullshit
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

# Import our atomic task implementation
from atomic_task_implementation import (
    HypothesisGenerator, InSilicoValidator, KritikerDiskriminator, 
    LernAnpassungsRegulator, ResourceManager, HGInput, TaskStatus
)

@dataclass
class BusinessMetrics:
    """Echte Business-Metriken ohne Marketing-Bullshit"""
    cycle_id: str
    start_time: float
    end_time: float
    duration_seconds: float
    success: bool
    cost_estimate: float  # Geschätzte Kosten basierend auf Rechenzeit
    hypotheses_generated: int
    simulations_run: int
    memory_used_mb: float
    cpu_percent: float
    business_value_score: float  # 0-1 basierend auf Qualität der Ergebnisse

@dataclass
class ROIAnalysis:
    """ROI-Analyse basierend auf echten Metriken"""
    total_cycles: int
    successful_cycles: int
    avg_duration: float
    total_cost: float
    avg_cost_per_cycle: float
    time_saved_vs_manual: float  # Geschätzte Zeitersparnis vs. manueller Prozess
    efficiency_score: float
    cost_per_successful_result: float

class BusinessValueTracker:
    """Tracking von echtem Business Value ohne übertriebene Versprechen"""
    
    def __init__(self, db_path: str = "kg_business_metrics.db"):
        self.db_path = db_path
        self.setup_database()
        self.resource_manager = ResourceManager()
        self.hg = HypothesisGenerator(self.resource_manager)
        self.isv = InSilicoValidator(self.resource_manager)
        self.kd = KritikerDiskriminator(self.resource_manager)
        self.lar = LernAnpassungsRegulator(self.resource_manager)
        
        # Realistische Kostenschätzungen (pro Minute Computing)
        self.cost_per_minute = 0.10  # 10 Cent pro Minute - realistisch für Cloud Computing
        self.manual_process_time = 120  # 2 Stunden manueller Prozess für eine Hypothese
        
    def setup_database(self):
        """Setup SQLite Database für Business-Metriken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_metrics (
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
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def measure_cycle_performance(self, cycle_params: Dict[str, Any]) -> BusinessMetrics:
        """Misst Performance eines KG-Zyklus mit echten Business-Metriken"""
        cycle_id = f"BIZ_CYCLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Baseline-Messung
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()
        start_time = time.time()
        
        hypotheses_count = 0
        simulations_count = 0
        success = False
        business_value = 0.0
        
        try:
            # HG Phase
            hg_input = HGInput(
                taskID=f"{cycle_id}_HG",
                signal="CREATE_NEW",
                constraints=cycle_params.get("constraints", {"targetProfile": ["SÜSS"], "exclude": []})
            )
            
            hg_result = self.hg.execute(hg_input)
            if hg_result.status == TaskStatus.SUCCESS:
                hypotheses_count = 1
                
                # ISV Phase  
                isv_result = self.isv.execute(hg_result)
                if isv_result.status == TaskStatus.SUCCESS:
                    simulations_count = 1
                    
                    # KD Phase
                    kd_result = self.kd.execute(isv_result)
                    if kd_result.status == TaskStatus.SUCCESS:
                        
                        # LAR Phase
                        lar_result = self.lar.execute(kd_result, 1)
                        if hasattr(lar_result, 'reward_signal'):
                            success = True
                            # Business Value basierend auf Reward und Qualität
                            business_value = max(0, min(1, (lar_result.reward_signal + 1) / 2))
            
        except Exception as e:
            logging.error(f"Cycle {cycle_id} failed: {e}")
            success = False
        
        # End-Messung
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = process.cpu_percent()
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        cost = (duration / 60) * self.cost_per_minute  # Kosten basierend auf Zeit
        
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
            cpu_percent=end_cpu,
            business_value_score=business_value
        )
        
        # In Database speichern
        self.save_metrics(metrics)
        return metrics
    
    def save_metrics(self, metrics: BusinessMetrics):
        """Speichert Metriken in Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO business_metrics 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_roi(self, last_n_cycles: int = 50) -> ROIAnalysis:
        """Analysiert ROI basierend auf echten Daten"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM business_metrics 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (last_n_cycles,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return ROIAnalysis(0, 0, 0, 0, 0, 0, 0, 0)
        
        total_cycles = len(rows)
        successful_cycles = sum(1 for row in rows if row[4])  # success column
        total_duration = sum(row[3] for row in rows)  # duration_seconds
        total_cost = sum(row[5] for row in rows)  # cost_estimate
        
        avg_duration = total_duration / total_cycles if total_cycles > 0 else 0
        avg_cost = total_cost / total_cycles if total_cycles > 0 else 0
        
        # Zeitersparnis vs. manueller Prozess
        automated_time_hours = total_duration / 3600  # Sekunden zu Stunden
        manual_time_hours = (self.manual_process_time / 60) * successful_cycles  # Minuten zu Stunden
        time_saved = manual_time_hours - automated_time_hours
        
        # Effizienz-Score
        efficiency = successful_cycles / total_cycles if total_cycles > 0 else 0
        
        # Kosten pro erfolgreichem Ergebnis
        cost_per_success = total_cost / successful_cycles if successful_cycles > 0 else float('inf')
        
        return ROIAnalysis(
            total_cycles=total_cycles,
            successful_cycles=successful_cycles,
            avg_duration=avg_duration,
            total_cost=total_cost,
            avg_cost_per_cycle=avg_cost,
            time_saved_vs_manual=time_saved,
            efficiency_score=efficiency,
            cost_per_successful_result=cost_per_success
        )
    
    def run_business_benchmark(self, num_cycles: int = 20) -> Dict[str, Any]:
        """Führt Business-Benchmark mit echten Metriken durch"""
        print(f"🔍 VERSUCH 1/4: Business Value Benchmark")
        print(f"Führe {num_cycles} Zyklen durch mit echten Kosten-/Nutzen-Metriken...")
        print("=" * 60)
        
        # Verschiedene Szenarien testen
        scenarios = [
            {"name": "Simple", "constraints": {"targetProfile": ["SÜSS"], "exclude": []}},
            {"name": "Complex", "constraints": {"targetProfile": ["SÜSS", "FRUCHTIG"], "exclude": ["BITTER"]}},
            {"name": "Challenging", "constraints": {"targetProfile": ["UMAMI", "SAUER"], "exclude": ["SÜSS", "SALZIG"]}}
        ]
        
        all_metrics = []
        
        for i in range(num_cycles):
            scenario = scenarios[i % len(scenarios)]
            print(f"Zyklus {i+1}/{num_cycles} - Szenario: {scenario['name']}")
            
            metrics = self.measure_cycle_performance(scenario)
            all_metrics.append(metrics)
            
            print(f"  ⏱️  Dauer: {metrics.duration_seconds:.2f}s")
            print(f"  💰 Kosten: ${metrics.cost_estimate:.4f}")
            print(f"  ✅ Erfolg: {'Ja' if metrics.success else 'Nein'}")
            print(f"  📊 Business Value: {metrics.business_value_score:.3f}")
            print()
        
        # ROI-Analyse
        roi = self.analyze_roi(num_cycles)
        
        print("=" * 60)
        print("📊 ECHTE ROI-ANALYSE (ohne Marketing-Bullshit)")
        print("=" * 60)
        print(f"📈 Gesamte Zyklen: {roi.total_cycles}")
        print(f"✅ Erfolgreiche Zyklen: {roi.successful_cycles}")
        print(f"📊 Erfolgsrate: {roi.efficiency_score:.1%}")
        print(f"⏱️  Durchschnittliche Dauer: {roi.avg_duration:.2f}s")
        print(f"💰 Gesamtkosten: ${roi.total_cost:.2f}")
        print(f"💰 Kosten pro Zyklus: ${roi.avg_cost_per_cycle:.4f}")
        print(f"💰 Kosten pro Erfolg: ${roi.cost_per_successful_result:.4f}")
        print(f"⏰ Zeitersparnis vs. manuell: {roi.time_saved_vs_manual:.1f} Stunden")
        
        # REALISTISCHE ROI-Berechnung
        manual_cost_per_hour = 50  # $50/Stunde für wissenschaftliche Arbeit
        manual_cost_total = roi.time_saved_vs_manual * manual_cost_per_hour
        automated_cost_total = roi.total_cost
        
        if automated_cost_total > 0:
            cost_savings = manual_cost_total - automated_cost_total
            roi_percentage = (cost_savings / automated_cost_total) * 100
            
            print(f"\n💡 REALISTISCHE ROI-BERECHNUNG:")
            print(f"💰 Manuelle Kosten: ${manual_cost_total:.2f}")
            print(f"💰 Automatisierte Kosten: ${automated_cost_total:.2f}")
            print(f"💰 Kosteneinsparung: ${cost_savings:.2f}")
            print(f"📈 ROI: {roi_percentage:.1f}%")
            
            if roi_percentage > 100:
                print(f"✅ System ist kosteneffektiv! {roi_percentage:.0f}% ROI")
            else:
                print(f"❌ System noch nicht kosteneffektiv. Optimierung nötig.")
        
        return {
            "metrics": [asdict(m) for m in all_metrics],
            "roi_analysis": asdict(roi),
            "realistic_roi_percent": roi_percentage if 'roi_percentage' in locals() else 0
        }

async def main():
    """Hauptfunktion für Business Value Test - VERSUCH 1/4"""
    print("🎯 VERSUCH 1/4: ECHTER BUSINESS VALUE TEST")
    print("Keine Marketing-Versprechen - nur messbare Ergebnisse!")
    print("=" * 60)
    
    tracker = BusinessValueTracker()
    
    try:
        # Business Benchmark durchführen
        results = tracker.run_business_benchmark(num_cycles=15)
        
        # Ergebnisse speichern
        with open('/home/emilio/Documents/ai/KG/VERSUCH_1_BUSINESS_RESULTS.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detaillierte Ergebnisse gespeichert in: VERSUCH_1_BUSINESS_RESULTS.json")
        
        roi_percent = results.get('realistic_roi_percent', 0)
        if roi_percent > 200:
            print(f"\n🎉 VERSUCH 1: ERFOLGREICH! ROI von {roi_percent:.0f}% erreicht")
            return True
        else:
            print(f"\n📝 VERSUCH 1: Ergebniss {roi_percent:.0f}% ROI - Verbesserung nötig")
            print("Nächster Versuch wird auf Performance-Optimierung fokussieren...")
            return False
            
    except Exception as e:
        print(f"\n❌ VERSUCH 1 FEHLER: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        print("\n🔄 Bereit für VERSUCH 2/4...")
