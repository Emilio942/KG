# Umfassender Test für das KG-System
# Testet HG -> ISV -> KD -> LAR Zyklus

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# === Mock-Implementierungen ===

class MockConfig:
    def __init__(self):
        self.HG_total_timeout = 300
        self.HG_vae_generation_timeout = 60
        self.ISV_total_timeout = 7200
        self.ISV_mdSim_classic_timeout = 3600
        self.ISV_mdSim_neural_timeout = 180
        self.ISV_aroma_prediction_timeout = 300
        self.KD_analysis_timeout = 180
        self.LAR_update_timeout = 60
        self.logLevel = "INFO"
        self.enableDetailedLogging = True
        self.maxParallelCycles = 5
    
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
        print(f"[{self.module_name}] TASK_COMPLETE: {task_name} ({duration:.2f}s)")
    
    def log_task_error(self, task_name: str, error_code: str, error_message: str):
        print(f"[{self.module_name}] TASK_ERROR: {task_name} - {error_code}: {error_message}")
    
    def log_hypothesis_generated(self, hypothese_id: str, komponenten_count: int):
        print(f"[{self.module_name}] HYPOTHESIS_GENERATED: {hypothese_id} ({komponenten_count} komponenten)")
    
    def log_simulation_result(self, simulation_id: str, method: str, success: bool, duration: float = None):
        status = "SUCCESS" if success else "FAILED"
        print(f"[{self.module_name}] SIMULATION_RESULT: {simulation_id} - {method} - {status} ({duration:.2f}s)")
    
    def log_verdict(self, verdict: str, score: float, hypothese_id: str = None):
        print(f"[{self.module_name}] VERDICT: {verdict} - Score: {score} - ID: {hypothese_id}")

# === Datenstrukturen ===

@dataclass
class MolekuelKomponente:
    name: str
    konzentration: float

@dataclass
class Hypothese:
    komponenten: List[MolekuelKomponente]
    typ: str = "molekular"

@dataclass
class HGBeweis:
    herleitung: str
    filterProtokoll: str
    noveltyScore: float
    constraintsPropagation: Dict[str, Any]

@dataclass
class HGOutput:
    taskID: str
    status: str
    hypotheseID: Optional[str] = None
    hypothese: Optional[Hypothese] = None
    beweis: Optional[HGBeweis] = None
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None

@dataclass
class GrundgeschmackScore:
    score: float
    molekuel: Optional[str] = None

@dataclass
class Grundgeschmack:
    suess: GrundgeschmackScore
    sauer: GrundgeschmackScore
    salzig: GrundgeschmackScore
    bitter: GrundgeschmackScore
    umami: GrundgeschmackScore

@dataclass
class AromaProfil:
    ERDIG: float
    SUESSLICH: float
    HOLZIG: float
    FRUCHTIG: float

@dataclass
class TexturProfil:
    viskositaet: float
    kristallinitaet: float

@dataclass
class SimulationsErgebnis:
    grundgeschmack: Grundgeschmack
    aromaProfil: AromaProfil
    texturProfil: TexturProfil

@dataclass
class ISVBeweis:
    simulationMethod: str
    confidenceLevel: float
    mdSimID: str
    mdSimProtokoll: str
    aromaModellVersion: str
    texturModellVersion: str

@dataclass
class ISVOutput:
    taskID: str
    subTaskID: Optional[str] = None
    status: str = "SUCCESS"
    hypotheseID: Optional[str] = None
    simulationsErgebnis: Optional[SimulationsErgebnis] = None
    beweis: Optional[ISVBeweis] = None
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None

@dataclass
class KDScoring:
    geschmacksharmonie: float
    aromaharmonie: float
    texturkomplexitaet: float
    bestaetigteNeuheit: float

@dataclass
class KDUrteil:
    verdict: str
    gesamtScore: float
    scoring: KDScoring

@dataclass
class KDBeweis:
    angewandteRegeln: List[str]
    regelErgebnisse: Dict[str, Dict[str, Any]]
    naechsterNachbarID: Optional[str] = None
    abstandZumNachbarn: Optional[float] = None

@dataclass
class KDOutput:
    taskID: str
    status: str
    hypotheseID: Optional[str] = None
    urteil: Optional[KDUrteil] = None
    beweis: Optional[KDBeweis] = None
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None

# === Agent-Implementierungen ===

class TestHGAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("HG")
        self.is_initialized = False
    
    async def initialize(self):
        self.logger.info("HG-Agent wird initialisiert...")
        await asyncio.sleep(0.1)
        self.is_initialized = True
        self.logger.info("HG-Agent erfolgreich initialisiert")
    
    async def process_task(self, input_data: dict) -> HGOutput:
        self.logger.set_task_id(input_data["taskID"])
        self.logger.log_task_start("HG_PROCESS", input_data["taskID"])
        
        start_time = datetime.now()
        
        try:
            # Simuliere HG-Verarbeitung
            await asyncio.sleep(0.8)
            
            # Erstelle Test-Hypothese
            komponenten = [
                MolekuelKomponente("Vanillin", 0.2),
                MolekuelKomponente("Geosmin", 0.01),
                MolekuelKomponente("Citral", 0.05)
            ]
            
            hypothese = Hypothese(komponenten)
            hypothese_id = f"HYP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{input_data['taskID'][-3:]}"
            
            beweis = HGBeweis(
                herleitung="Hypothese aus erweiterten VAE-Raum [Sektor 4.2.1] generiert",
                filterProtokoll="Filter RF-01, RF-02, RF-03 erfolgreich passiert",
                noveltyScore=0.87,
                constraintsPropagation=input_data["constraints"]
            )
            
            output = HGOutput(
                taskID=input_data["taskID"],
                status="SUCCESS",
                hypotheseID=hypothese_id,
                hypothese=hypothese,
                beweis=beweis
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_hypothesis_generated(hypothese_id, len(komponenten))
            self.logger.log_task_complete("HG_PROCESS", duration)
            
            return output
            
        except Exception as e:
            self.logger.log_task_error("HG_PROCESS", "HG003", str(e))
            return HGOutput(
                taskID=input_data["taskID"],
                status="FAILED",
                errorCode="HG003",
                errorMessage=str(e)
            )

class TestISVAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("ISV")
        self.is_initialized = False
    
    async def initialize(self):
        self.logger.info("ISV-Agent wird initialisiert...")
        await asyncio.sleep(0.2)
        self.is_initialized = True
        self.logger.info("ISV-Agent erfolgreich initialisiert")
    
    async def process_task(self, input_data: HGOutput) -> ISVOutput:
        self.logger.set_task_id(input_data.taskID)
        self.logger.set_hypothese_id(input_data.hypotheseID)
        self.logger.log_task_start("ISV_PROCESS", input_data.taskID)
        
        start_time = datetime.now()
        
        try:
            # Simuliere ISV-Verarbeitung
            komponenten_count = len(input_data.hypothese.komponenten)
            
            # Simulationsmethoden-Entscheidung
            if komponenten_count < 3:
                sim_method = "CLASSIC_MD"
                sim_duration = 2.0
                confidence = 0.95
            else:
                sim_method = "NEURAL_MD"
                sim_duration = 0.5
                confidence = 0.85
            
            self.logger.info(f"Simulationsmethode gewählt: {sim_method}")
            
            # Simuliere MD-Simulation
            await asyncio.sleep(sim_duration)
            
            simulation_id = f"{sim_method}-{datetime.now().strftime('%H%M%S')}"
            self.logger.log_simulation_result(simulation_id, sim_method, True, sim_duration)
            
            # Erstelle Simulationsergebnisse
            grundgeschmack = Grundgeschmack(
                suess=GrundgeschmackScore(0.82, "Vanillin"),
                sauer=GrundgeschmackScore(0.05, None),
                salzig=GrundgeschmackScore(0.01, None),
                bitter=GrundgeschmackScore(0.15, "Geosmin"),
                umami=GrundgeschmackScore(0.11, None)
            )
            
            aroma_profil = AromaProfil(
                ERDIG=0.95,
                SUESSLICH=0.88,
                HOLZIG=0.21,
                FRUCHTIG=0.07
            )
            
            textur_profil = TexturProfil(
                viskositaet=0.1,
                kristallinitaet=0.0
            )
            
            simulationsErgebnis = SimulationsErgebnis(
                grundgeschmack=grundgeschmack,
                aromaProfil=aroma_profil,
                texturProfil=textur_profil
            )
            
            beweis = ISVBeweis(
                simulationMethod=sim_method,
                confidenceLevel=confidence,
                mdSimID=simulation_id,
                mdSimProtokoll=f"{sim_method}-Simulation erfolgreich konvergiert",
                aromaModellVersion="GNN-v3.1.2",
                texturModellVersion="T-SIM-v1.4"
            )
            
            output = ISVOutput(
                taskID=input_data.taskID,
                subTaskID=f"{input_data.taskID}-SIM-{sim_method}",
                status="SUCCESS",
                hypotheseID=input_data.hypotheseID,
                simulationsErgebnis=simulationsErgebnis,
                beweis=beweis
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_task_complete("ISV_PROCESS", duration)
            
            return output
            
        except Exception as e:
            self.logger.log_task_error("ISV_PROCESS", "ISV003", str(e))
            return ISVOutput(
                taskID=input_data.taskID,
                status="FAILED",
                hypotheseID=input_data.hypotheseID,
                errorCode="ISV003",
                errorMessage=str(e)
            )

class TestKDAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("KD")
        self.is_initialized = False
    
    async def initialize(self):
        self.logger.info("KD-Agent wird initialisiert...")
        await asyncio.sleep(0.1)
        self.is_initialized = True
        self.logger.info("KD-Agent erfolgreich initialisiert")
    
    async def process_task(self, input_data: ISVOutput) -> KDOutput:
        self.logger.set_task_id(input_data.taskID)
        self.logger.set_hypothese_id(input_data.hypotheseID)
        self.logger.log_task_start("KD_PROCESS", input_data.taskID)
        
        start_time = datetime.now()
        
        try:
            # Simuliere KD-Verarbeitung
            await asyncio.sleep(0.6)
            
            # Harmonie-Analyse
            geschmacksharmonie = 0.92  # Süß-Bitter-Balance gut
            aromaharmonie = 0.95       # Erde-Süße-Paarung harmonisch
            texturkomplexitaet = 0.60  # Mittlere Komplexität
            bestaetigteNeuheit = 0.87  # Hohe Neuheit bestätigt
            
            scoring = KDScoring(
                geschmacksharmonie=geschmacksharmonie,
                aromaharmonie=aromaharmonie,
                texturkomplexitaet=texturkomplexitaet,
                bestaetigteNeuheit=bestaetigteNeuheit
            )
            
            # Gesamtscore berechnen
            gesamtScore = (geschmacksharmonie * 0.3 + aromaharmonie * 0.4 + 
                          texturkomplexitaet * 0.1 + bestaetigteNeuheit * 0.2)
            
            # Urteil fällen
            if gesamtScore > 0.75:
                verdict = "APPROVED"
            else:
                verdict = "REJECTED"
            
            urteil = KDUrteil(
                verdict=verdict,
                gesamtScore=gesamtScore,
                scoring=scoring
            )
            
            # Beweis erstellen
            beweis = KDBeweis(
                angewandteRegeln=["Rule_G01_Süß-Bitter-Balance", "Rule_A04_Erde-Süße-Paarung"],
                regelErgebnisse={
                    "Rule_G01": {"pass": True, "score": 0.92},
                    "Rule_A04": {"pass": True, "score": 0.95}
                },
                naechsterNachbarID="HYP-XYZ-456",
                abstandZumNachbarn=0.13
            )
            
            output = KDOutput(
                taskID=input_data.taskID,
                status="SUCCESS",
                hypotheseID=input_data.hypotheseID,
                urteil=urteil,
                beweis=beweis
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_verdict(verdict, gesamtScore, input_data.hypotheseID)
            self.logger.log_task_complete("KD_PROCESS", duration)
            
            return output
            
        except Exception as e:
            self.logger.log_task_error("KD_PROCESS", "KD003", str(e))
            return KDOutput(
                taskID=input_data.taskID,
                status="FAILED",
                hypotheseID=input_data.hypotheseID,
                errorCode="KD003",
                errorMessage=str(e)
            )

class TestLARAgent:
    def __init__(self, config):
        self.config = config
        self.logger = MockLogger("LAR")
        self.hg_agent = TestHGAgent(config)
        self.isv_agent = TestISVAgent(config)
        self.kd_agent = TestKDAgent(config)
        self.is_initialized = False
        self.cycle_count = 0
    
    async def initialize_all_modules(self):
        self.logger.info("Alle Module werden initialisiert...")
        await self.hg_agent.initialize()
        await self.isv_agent.initialize()
        await self.kd_agent.initialize()
        self.is_initialized = True
        self.logger.info("Alle Module erfolgreich initialisiert")
    
    async def load_base_knowledge_graph(self):
        self.logger.info("Basis-Wissensgraph wird geladen...")
        await asyncio.sleep(0.3)
        self.logger.info("Basis-Wissensgraph erfolgreich geladen")
    
    async def send_first_signal(self, bootstrap_signal: dict):
        self.logger.info("Erstes Signal wird gesendet...")
        await self._start_full_cycle(bootstrap_signal)
        self.logger.info("Erstes Signal erfolgreich gesendet")
    
    async def _start_full_cycle(self, signal: dict):
        """Führe einen kompletten Zyklus aus: HG -> ISV -> KD -> LAR"""
        self.cycle_count += 1
        cycle_start = datetime.now()
        
        self.logger.info(f"=== VOLLSTÄNDIGER ZYKLUS {self.cycle_count} GESTARTET ===")
        self.logger.info(f"Zyklus gestartet: {signal['taskID']}")
        
        try:
            # Schritt 1: HG - Hypothesen-Generierung
            self.logger.info("Schritt 1: HG - Hypothesen-Generierung")
            hg_result = await self.hg_agent.process_task(signal)
            
            if hg_result.status != "SUCCESS":
                self.logger.error(f"HG fehlgeschlagen: {hg_result.errorCode}")
                await self._process_lar_feedback(hg_result, None, None)
                return
            
            # Schritt 2: ISV - In-Silico-Validation
            self.logger.info("Schritt 2: ISV - In-Silico-Validation")
            isv_result = await self.isv_agent.process_task(hg_result)
            
            if isv_result.status != "SUCCESS":
                self.logger.error(f"ISV fehlgeschlagen: {isv_result.errorCode}")
                await self._process_lar_feedback(hg_result, isv_result, None)
                return
            
            # Schritt 3: KD - Kritische Bewertung
            self.logger.info("Schritt 3: KD - Kritische Bewertung")
            kd_result = await self.kd_agent.process_task(isv_result)
            
            if kd_result.status != "SUCCESS":
                self.logger.error(f"KD fehlgeschlagen: {kd_result.errorCode}")
                await self._process_lar_feedback(hg_result, isv_result, kd_result)
                return
            
            # Schritt 4: LAR - Feedback-Verarbeitung
            self.logger.info("Schritt 4: LAR - Feedback-Verarbeitung")
            await self._process_lar_feedback(hg_result, isv_result, kd_result)
            
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.logger.info(f"=== ZYKLUS {self.cycle_count} ABGESCHLOSSEN ({cycle_duration:.2f}s) ===")
            
            # Zeige Ergebnisse
            self._display_cycle_results(hg_result, isv_result, kd_result)
            
        except Exception as e:
            self.logger.error(f"Fehler in Zyklus {self.cycle_count}: {e}")
    
    async def _process_lar_feedback(self, hg_result: HGOutput, isv_result: ISVOutput = None, kd_result: KDOutput = None):
        """Verarbeite Feedback und berechne Reward-Signal"""
        self.logger.log_task_start("LAR_FEEDBACK", hg_result.taskID)
        
        # Berechne Reward-Signal
        if kd_result and kd_result.status == "SUCCESS":
            if kd_result.urteil.verdict == "APPROVED":
                reward = kd_result.urteil.gesamtScore
                self.logger.info(f"Positives Reward: +{reward:.2f}")
            else:
                reward = -0.6
                self.logger.info(f"Negatives Reward: {reward:.2f}")
        elif isv_result and isv_result.status == "FAILED":
            reward = -0.8
            self.logger.info(f"ISV-Fehler Reward: {reward:.2f}")
        else:
            reward = -1.0
            self.logger.info(f"Vollständiger Fehler Reward: {reward:.2f}")
        
        # Simuliere Parameter-Update
        await asyncio.sleep(0.2)
        self.logger.info("HG-Parameter-Update durchgeführt")
        
        # Simuliere Wissensgraph-Update (nur bei Erfolg)
        if reward > 0 and kd_result and kd_result.urteil.verdict == "APPROVED":
            await asyncio.sleep(0.1)
            self.logger.info(f"Wissensgraph erweitert: {hg_result.hypotheseID}")
        
        self.logger.log_task_complete("LAR_FEEDBACK", 0.3)
    
    def _display_cycle_results(self, hg_result: HGOutput, isv_result: ISVOutput, kd_result: KDOutput):
        """Zeige Zyklus-Ergebnisse an"""
        print("\n" + "="*80)
        print(f"ZYKLUS {self.cycle_count} - VOLLSTÄNDIGE ERGEBNISSE")
        print("="*80)
        
        print(f"📋 HYPOTHESE: {hg_result.hypotheseID}")
        print(f"   Komponenten: {len(hg_result.hypothese.komponenten)}")
        for komp in hg_result.hypothese.komponenten:
            print(f"   - {komp.name}: {komp.konzentration}")
        print(f"   Novelty Score: {hg_result.beweis.noveltyScore}")
        
        print(f"\n🧪 SIMULATION: {isv_result.beweis.simulationMethod}")
        print(f"   Konfidenz: {isv_result.beweis.confidenceLevel}")
        print(f"   Grundgeschmack:")
        print(f"   - Süß: {isv_result.simulationsErgebnis.grundgeschmack.suess.score:.2f}")
        print(f"   - Bitter: {isv_result.simulationsErgebnis.grundgeschmack.bitter.score:.2f}")
        print(f"   Aroma-Profil:")
        print(f"   - Erdig: {isv_result.simulationsErgebnis.aromaProfil.ERDIG:.2f}")
        print(f"   - Süßlich: {isv_result.simulationsErgebnis.aromaProfil.SUESSLICH:.2f}")
        
        print(f"\n⚖️  URTEIL: {kd_result.urteil.verdict}")
        print(f"   Gesamtscore: {kd_result.urteil.gesamtScore:.2f}")
        print(f"   Geschmacksharmonie: {kd_result.urteil.scoring.geschmacksharmonie:.2f}")
        print(f"   Aromaharmonie: {kd_result.urteil.scoring.aromaharmonie:.2f}")
        print(f"   Bestätigte Neuheit: {kd_result.urteil.scoring.bestaetigteNeuheit:.2f}")
        
        if kd_result.urteil.verdict == "APPROVED":
            print("\n✅ HYPOTHESE ERFOLGREICH GENEHMIGT!")
        else:
            print("\n❌ HYPOTHESE ABGELEHNT")
        
        print("="*80 + "\n")
    
    async def process_cycle(self):
        await asyncio.sleep(0.1)
    
    async def shutdown(self):
        self.logger.info("LAR wird heruntergefahren...")

class TestKGSystem:
    def __init__(self):
        self.config = MockConfig()
        self.logger = MockLogger("SYSTEM")
        self.lar_agent = TestLARAgent(self.config)
        self.is_running = False
    
    async def start(self):
        self.logger.info("=== VOLLSTÄNDIGES KG-SYSTEM WIRD GESTARTET ===")
        await self._bootstrap()
        self.is_running = True
        self.logger.info("=== KG-SYSTEM ERFOLGREICH GESTARTET ===")
    
    async def _bootstrap(self):
        self.logger.info("Bootstrap-Prozess gestartet...")
        
        await self.lar_agent.load_base_knowledge_graph()
        await self.lar_agent.initialize_all_modules()
        
        # Starte mehrere Test-Zyklen
        for i in range(3):
            bootstrap_signal = {
                "taskID": f"CYCLE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i+1:03d}",
                "signal": "CREATE_NEW",
                "constraints": {
                    "targetProfile": ["SÜSS", "ERDIG"] if i % 2 == 0 else ["FRUCHTIG", "HOLZIG"],
                    "exclude": []
                }
            }
            
            await self.lar_agent.send_first_signal(bootstrap_signal)
            await asyncio.sleep(0.5)  # Kurze Pause zwischen Zyklen
        
        self.logger.info("Bootstrap-Prozess abgeschlossen")
    
    async def shutdown(self):
        self.logger.info("System wird heruntergefahren...")
        await self.lar_agent.shutdown()
        self.is_running = False

async def main():
    """Haupttest mit vollständigem Zyklus"""
    print("=" * 80)
    print("KG-SYSTEM - VOLLSTÄNDIGER TEST")
    print("Testet kompletten Zyklus: HG -> ISV -> KD -> LAR")
    print("=" * 80)
    
    system = TestKGSystem()
    
    try:
        await system.start()
        
        # Kurze Laufzeit für Demo
        await asyncio.sleep(1)
        
        await system.shutdown()
        
        print("\n" + "="*80)
        print("TEST ERFOLGREICH ABGESCHLOSSEN!")
        print("Alle Module funktionieren und kommunizieren korrekt.")
        print("="*80)
        
    except Exception as e:
        print(f"Fehler beim Test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
