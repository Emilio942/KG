# Test-Script für das KG-System
# Einfacher Test ohne alle Dependencies

import asyncio
import json
import sys
from datetime import datetime

# Mock-Implementierungen für Tests ohne Dependencies
class MockConfig:
    def __init__(self):
        self.HG_total_timeout = 300
        self.HG_vae_generation_timeout = 60
        self.logLevel = "INFO"
        self.enableDetailedLogging = True
    
    def get_timeout(self, module: str, task: str = None) -> int:
        if task:
            return getattr(self, f"{module}_{task}_timeout", 300)
        return getattr(self, f"{module}_total_timeout", 300)

class MockLogger:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.task_id = None
        self.hypothese_id = None
    
    def set_task_id(self, task_id: str):
        self.task_id = task_id
    
    def set_hypothese_id(self, hypothese_id: str):
        self.hypothese_id = hypothese_id
    
    def info(self, message: str, **kwargs):
        print(f"[{self.module_name}] INFO: {message}")
    
    def error(self, message: str, **kwargs):
        print(f"[{self.module_name}] ERROR: {message}")
    
    def debug(self, message: str, **kwargs):
        print(f"[{self.module_name}] DEBUG: {message}")
    
    def warning(self, message: str, **kwargs):
        print(f"[{self.module_name}] WARNING: {message}")
    
    def log_task_start(self, task_name: str, task_id: str = None):
        print(f"[{self.module_name}] TASK_START: {task_name} ({task_id})")
    
    def log_task_complete(self, task_name: str, duration: float = None):
        print(f"[{self.module_name}] TASK_COMPLETE: {task_name} ({duration}s)")
    
    def log_task_error(self, task_name: str, error_code: str, error_message: str):
        print(f"[{self.module_name}] TASK_ERROR: {task_name} - {error_code}: {error_message}")
    
    def log_hypothesis_generated(self, hypothese_id: str, komponenten_count: int):
        print(f"[{self.module_name}] HYPOTHESIS_GENERATED: {hypothese_id} ({komponenten_count} komponenten)")

# Mock-Schemas
class MockHGInput:
    def __init__(self, taskID: str, signal: str, constraints: dict):
        self.taskID = taskID
        self.signal = signal
        self.constraints = constraints

class MockMolekuelKomponente:
    def __init__(self, name: str, konzentration: float):
        self.name = name
        self.konzentration = konzentration

class MockHypothese:
    def __init__(self, komponenten: list, typ: str = "molekular"):
        self.komponenten = komponenten
        self.typ = typ

class MockHGBeweis:
    def __init__(self, herleitung: str, filterProtokoll: str, noveltyScore: float, constraintsPropagation: dict):
        self.herleitung = herleitung
        self.filterProtokoll = filterProtokoll
        self.noveltyScore = noveltyScore
        self.constraintsPropagation = constraintsPropagation

class MockHGOutput:
    def __init__(self, taskID: str, status: str, hypotheseID: str = None, hypothese = None, beweis = None, errorCode: str = None, errorMessage: str = None):
        self.taskID = taskID
        self.status = status
        self.hypotheseID = hypotheseID
        self.hypothese = hypothese
        self.beweis = beweis
        self.errorCode = errorCode
        self.errorMessage = errorMessage

# Vereinfachte HG-Implementierung für Tests
class TestHGAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("HG")
        self.is_initialized = False
        self.error_codes = {
            "HG001": "Keine Hypothese gefunden",
            "HG002": "Input ungültig",
            "HG003": "VAE-Modell nicht verfügbar",
            "HG004": "Timeout erreicht"
        }
    
    async def initialize(self):
        self.logger.info("HG-Agent wird initialisiert...")
        await asyncio.sleep(0.1)
        self.is_initialized = True
        self.logger.info("HG-Agent erfolgreich initialisiert")
    
    async def process_task(self, input_data: MockHGInput) -> MockHGOutput:
        self.logger.set_task_id(input_data.taskID)
        self.logger.log_task_start("HG_PROCESS", input_data.taskID)
        
        try:
            # Simuliere Verarbeitung
            await asyncio.sleep(0.5)
            
            # Erstelle Test-Hypothese
            komponenten = [
                MockMolekuelKomponente("Vanillin", 0.2),
                MockMolekuelKomponente("Geosmin", 0.01)
            ]
            
            hypothese = MockHypothese(komponenten)
            
            hypothese_id = f"HYP-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            beweis = MockHGBeweis(
                herleitung="Test-Hypothese aus Mock-VAE",
                filterProtokoll="Alle Test-Filter bestanden",
                noveltyScore=0.85,
                constraintsPropagation=input_data.constraints
            )
            
            output = MockHGOutput(
                taskID=input_data.taskID,
                status="SUCCESS",
                hypotheseID=hypothese_id,
                hypothese=hypothese,
                beweis=beweis
            )
            
            self.logger.log_hypothesis_generated(hypothese_id, len(komponenten))
            self.logger.log_task_complete("HG_PROCESS", 0.5)
            
            return output
            
        except Exception as e:
            self.logger.log_task_error("HG_PROCESS", "HG003", str(e))
            return MockHGOutput(
                taskID=input_data.taskID,
                status="FAILED",
                errorCode="HG003",
                errorMessage=str(e)
            )

# Test-LAR
class TestLARAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("LAR")
        self.hg_agent = TestHGAgent(config)
        self.is_initialized = False
    
    async def initialize_all_modules(self):
        self.logger.info("Alle Module werden initialisiert...")
        await self.hg_agent.initialize()
        self.is_initialized = True
        self.logger.info("Alle Module erfolgreich initialisiert")
    
    async def load_base_knowledge_graph(self):
        self.logger.info("Basis-Wissensgraph wird geladen...")
        await asyncio.sleep(0.2)
        self.logger.info("Basis-Wissensgraph erfolgreich geladen")
    
    async def send_first_signal(self, bootstrap_signal: dict):
        self.logger.info("Erstes Signal wird gesendet...")
        
        hg_input = MockHGInput(
            taskID=bootstrap_signal["taskID"],
            signal=bootstrap_signal["signal"],
            constraints=bootstrap_signal["constraints"]
        )
        
        await self._start_cycle(hg_input)
        self.logger.info("Erstes Signal erfolgreich gesendet")
    
    async def _start_cycle(self, hg_input: MockHGInput):
        self.logger.info(f"Neuer Zyklus gestartet: {hg_input.taskID}")
        
        result = await self.hg_agent.process_task(hg_input)
        
        if result.status == "SUCCESS":
            self.logger.info(f"Zyklus erfolgreich: {result.hypotheseID}")
            print(f"\n=== ERFOLGREICH GENERIERTE HYPOTHESE ===")
            print(f"ID: {result.hypotheseID}")
            print(f"Komponenten:")
            for komp in result.hypothese.komponenten:
                print(f"  - {komp.name}: {komp.konzentration}")
            print(f"Novelty Score: {result.beweis.noveltyScore}")
            print(f"=========================================\n")
        else:
            self.logger.error(f"Zyklus fehlgeschlagen: {result.errorCode}")
    
    async def process_cycle(self):
        await asyncio.sleep(0.1)
    
    async def shutdown(self):
        self.logger.info("LAR wird heruntergefahren...")

# Test-KG-System
class TestKGSystem:
    def __init__(self):
        self.config = MockConfig()
        self.logger = MockLogger("SYSTEM")
        self.lar_agent = TestLARAgent(self.config)
        self.is_running = False
    
    async def start(self):
        self.logger.info("=== KG Test-System wird gestartet ===")
        
        await self._bootstrap()
        
        self.is_running = True
        self.logger.info("=== KG Test-System erfolgreich gestartet ===")
    
    async def _bootstrap(self):
        self.logger.info("Bootstrap-Prozess gestartet...")
        
        await self.lar_agent.load_base_knowledge_graph()
        await self.lar_agent.initialize_all_modules()
        
        bootstrap_signal = {
            "taskID": f"BOOTSTRAP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-001",
            "signal": "BOOTSTRAP_COMPLETE",
            "constraints": {
                "targetProfile": ["SÜSS", "ERDIG"],
                "exclude": []
            }
        }
        
        await self.lar_agent.send_first_signal(bootstrap_signal)
        self.logger.info("Bootstrap-Prozess abgeschlossen")
    
    async def shutdown(self):
        self.logger.info("Test-System wird heruntergefahren...")
        await self.lar_agent.shutdown()
        self.is_running = False

async def main():
    """Haupttest-Funktion"""
    print("=" * 60)
    print("KG-System Test - Vereinfachte Implementierung")
    print("=" * 60)
    
    system = TestKGSystem()
    
    try:
        await system.start()
        
        # Kurze Testlaufzeit
        await asyncio.sleep(1)
        
        await system.shutdown()
        
    except Exception as e:
        print(f"Fehler beim Test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
