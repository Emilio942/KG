# In-Silico-Validator (ISV) - Simuliert Geschmackshypothesen
# Implementiert klassische und neuronale MD-Simulation

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from kg.utils.config import Config
from kg.utils.logging_config import KGLogger
from kg.schemas import (
    HGOutput, ISVOutput, ISVBeweis, SimulationsErgebnis,
    Grundgeschmack, AromaProfil, TexturProfil, GrundgeschmackScore,
    ResourceLock, SimulationMethod, TaskStatus
)

# ML Model imports
try:
    from kg.ml_models.neural_md import NeuralMDSimulator
    NEURAL_MD_AVAILABLE = True
except ImportError:
    NEURAL_MD_AVAILABLE = False

@dataclass
class ResourceAllocation:
    """Ressourcen-Zuteilung für Simulationen"""
    cpu_cores: int
    memory_mb: int
    gpu_slots: int
    lock_id: str
    acquired_at: datetime

class ISVAgent:
    """
    In-Silico-Validator Agent
    Implementiert die atomare Aufgabenstruktur:
    2.1 Input-Validierung & Parsing
    2.1a Simulationsmethoden-Entscheidung & Resource-Locking
    2.2 Adaptive MD-Simulation
    2.3 Aroma- & Textur-Prognose
    2.4 Aggregation und Output-Formatierung
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = KGLogger("ISV")
        self.classic_md_model = None
        self.neural_md_model = None
        self.aroma_model = None
        self.texture_model = None
        self.resource_locks = {}
        self.is_initialized = False
        
        # Initialize Neural MD if available
        if NEURAL_MD_AVAILABLE:
            try:
                self.neural_md_simulator = NeuralMDSimulator()
                self.neural_md_available = True
                self.logger.info("Neural MD simulator initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Neural MD: {e}")
                self.neural_md_simulator = None
                self.neural_md_available = False
        else:
            self.neural_md_simulator = None
            self.neural_md_available = False
        
        # Fehlercode-Definitionen
        self.error_codes = {
            "ISV001": "Ungültiges Input-Format von HG erhalten",
            "ISV002": "MD-Simulation nicht konvergiert",
            "ISV003": "Prognosemodell-Fehler",
            "ISV004": "Ressourcen-Limit erreicht",
            "ISV005": "Timeout erreicht während MD-Simulation"
        }
    
    async def initialize(self):
        """Initialisiere den ISV-Agent"""
        self.logger.info("ISV-Agent wird initialisiert...")
        
        try:
            # Simulationsmodelle laden
            await self._load_simulation_models()
            
            # Prognosemodelle laden
            await self._load_prediction_models()
            
            self.is_initialized = True
            self.logger.info("ISV-Agent erfolgreich initialisiert")
            
        except Exception as e:
            self.logger.error(f"Fehler bei ISV-Initialisierung: {e}")
            raise
    
    async def process_task(self, input_data: HGOutput) -> ISVOutput:
        """
        Hauptverarbeitungsschleife für eine ISV-Aufgabe
        """
        self.logger.set_task_id(input_data.taskID)
        self.logger.set_hypothese_id(input_data.hypotheseID)
        self.logger.log_task_start("ISV_PROCESS", input_data.taskID)
        
        start_time = datetime.now()
        
        try:
            # Aufgabe 2.1: Input-Validierung & Parsing
            validation_result = await self._task_2_1_input_validation(input_data)
            if not validation_result.success:
                return self._create_error_output(input_data.taskID, input_data.hypotheseID, 
                                               "ISV001", validation_result.error_message)
            
            # Aufgabe 2.1a: Simulationsmethoden-Entscheidung & Resource-Locking
            sim_decision = await self._task_2_1a_simulation_decision(input_data)
            if not sim_decision.success:
                return self._create_error_output(input_data.taskID, input_data.hypotheseID,
                                               "ISV004", sim_decision.error_message)
            
            # Aufgabe 2.2: Adaptive MD-Simulation
            simulation_result = await self._task_2_2_adaptive_md_simulation(input_data, sim_decision)
            if not simulation_result.success:
                return self._create_error_output(input_data.taskID, input_data.hypotheseID,
                                               "ISV002", simulation_result.error_message)
            
            # Aufgabe 2.3: Aroma- & Textur-Prognose
            prediction_result = await self._task_2_3_aroma_texture_prediction(input_data)
            if not prediction_result.success:
                return self._create_error_output(input_data.taskID, input_data.hypotheseID,
                                               "ISV003", prediction_result.error_message)
            
            # Aufgabe 2.4: Aggregation und Output-Formatierung
            output = await self._task_2_4_aggregation_output(input_data, sim_decision, 
                                                           simulation_result, prediction_result)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_task_complete("ISV_PROCESS", duration)
            
            return output
            
        except asyncio.TimeoutError:
            self.logger.log_task_error("ISV_PROCESS", "ISV005", "Timeout erreicht")
            return self._create_error_output(input_data.taskID, input_data.hypotheseID,
                                           "ISV005", "Timeout erreicht")
        
        except Exception as e:
            self.logger.log_task_error("ISV_PROCESS", "ISV003", str(e))
            return self._create_error_output(input_data.taskID, input_data.hypotheseID,
                                           "ISV003", str(e))
        
        finally:
            # Ressourcen freigeben
            if hasattr(self, '_current_resource_allocation'):
                await self._release_resources(self._current_resource_allocation)
    
    async def _task_2_1_input_validation(self, input_data: HGOutput) -> 'ValidationResult':
        """
        Aufgabe 2.1: Input-Validierung & Parsing
        """
        self.logger.info("Aufgabe 2.1: Input-Validierung gestartet")
        
        try:
            # Prüfe ob HG-Output erfolgreich war
            if input_data.status != TaskStatus.SUCCESS:
                return ValidationResult(False, f"HG-Status nicht SUCCESS: {input_data.status}")
            
            # Prüfe ob Hypothese vorhanden ist
            if not input_data.hypothese:
                return ValidationResult(False, "Keine Hypothese im HG-Output")
            
            # Prüfe Hypothese-Format
            if not input_data.hypothese.komponenten:
                return ValidationResult(False, "Keine Komponenten in Hypothese")
            
            # Validiere Komponenten
            for komp in input_data.hypothese.komponenten:
                if not komp.name:
                    return ValidationResult(False, "Komponente ohne Namen")
                if komp.konzentration < 0 or komp.konzentration > 1:
                    return ValidationResult(False, f"Ungültige Konzentration: {komp.konzentration}")
            
            self.logger.info("Input-Validierung erfolgreich",
                           komponenten_count=len(input_data.hypothese.komponenten))
            
            return ValidationResult(True, "Input-Validierung OK")
            
        except Exception as e:
            return ValidationResult(False, f"Fehler bei Input-Validierung: {e}")
    
    async def _task_2_1a_simulation_decision(self, input_data: HGOutput) -> 'SimulationDecision':
        """
        Aufgabe 2.1a: Simulationsmethoden-Entscheidung & Resource-Locking
        """
        self.logger.info("Aufgabe 2.1a: Simulationsmethoden-Entscheidung gestartet")
        
        try:
            komponenten_count = len(input_data.hypothese.komponenten)
            
            # Entscheidungskriterien
            if komponenten_count < 3:
                # Weniger als 3 Komponenten -> Klassische MD bevorzugt
                preferred_method = SimulationMethod.CLASSIC_MD
                reason = "Weniger als 3 Komponenten - klassische MD präziser"
            else:
                # Mehr als 3 Komponenten -> Neuronale MD effizienter
                preferred_method = SimulationMethod.NEURAL_MD
                reason = "Mehr als 3 Komponenten - neuronale MD effizienter"
            
            # Prüfe Ressourcenverfügbarkeit
            if preferred_method == SimulationMethod.CLASSIC_MD:
                resources_needed = {
                    "cpu_cores": 4,
                    "memory_mb": 4096,
                    "gpu_slots": 1
                }
            else:
                resources_needed = {
                    "cpu_cores": 2,
                    "memory_mb": 2048,
                    "gpu_slots": 0  # Optional
                }
            
            # Versuche Ressourcen zu akquirieren
            allocation = await self._acquire_resources(resources_needed, preferred_method)
            if not allocation:
                # Fallback auf alternative Methode
                if preferred_method == SimulationMethod.CLASSIC_MD:
                    fallback_method = SimulationMethod.NEURAL_MD
                    fallback_resources = {
                        "cpu_cores": 2,
                        "memory_mb": 2048,
                        "gpu_slots": 0
                    }
                else:
                    fallback_method = SimulationMethod.CLASSIC_MD
                    fallback_resources = {
                        "cpu_cores": 4,
                        "memory_mb": 4096,
                        "gpu_slots": 1
                    }
                
                allocation = await self._acquire_resources(fallback_resources, fallback_method)
                if not allocation:
                    return SimulationDecision(False, None, None, "Keine Ressourcen verfügbar")
                
                chosen_method = fallback_method
                reason = f"Fallback zu {fallback_method.value} - {preferred_method.value} Ressourcen nicht verfügbar"
            else:
                chosen_method = preferred_method
            
            # Generiere Sub-Task-ID
            sub_task_id = f"{input_data.taskID}-SIM-{chosen_method.value}"
            
            self.logger.info(f"Simulationsmethode gewählt: {chosen_method.value}",
                           reason=reason,
                           sub_task_id=sub_task_id)
            
            # Speichere Allocation für späteren Cleanup
            self._current_resource_allocation = allocation
            
            return SimulationDecision(True, chosen_method, sub_task_id, reason, allocation)
            
        except Exception as e:
            return SimulationDecision(False, None, None, f"Fehler bei Simulationsentscheidung: {e}")
    
    async def _task_2_2_adaptive_md_simulation(self, input_data: HGOutput, 
                                             sim_decision: 'SimulationDecision') -> 'SimulationResult':
        """
        Aufgabe 2.2: Adaptive MD-Simulation
        """
        self.logger.info("Aufgabe 2.2: MD-Simulation gestartet")
        
        try:
            method = sim_decision.method
            
            if method == SimulationMethod.CLASSIC_MD:
                timeout = self.config.get_timeout("ISV", "mdSim_classic")
                result = await asyncio.wait_for(
                    self._run_classic_md_simulation(input_data),
                    timeout=timeout
                )
            else:
                timeout = self.config.get_timeout("ISV", "mdSim_neural")
                result = await asyncio.wait_for(
                    self._run_neural_md_simulation(input_data),
                    timeout=timeout
                )
            
            if result.converged:
                self.logger.log_simulation_result(result.simulation_id, method.value, True, result.duration)
                return SimulationResult(True, result)
            else:
                self.logger.log_simulation_result(result.simulation_id, method.value, False, result.duration)
                return SimulationResult(False, None, "Simulation nicht konvergiert")
            
        except asyncio.TimeoutError:
            self.logger.error("MD-Simulation Timeout erreicht")
            return SimulationResult(False, None, "Simulation Timeout")
        
        except Exception as e:
            self.logger.error(f"Fehler bei MD-Simulation: {e}")
            return SimulationResult(False, None, str(e))
    
    async def _task_2_3_aroma_texture_prediction(self, input_data: HGOutput) -> 'PredictionResult':
        """
        Aufgabe 2.3: Aroma- & Textur-Prognose
        """
        self.logger.info("Aufgabe 2.3: Aroma- & Textur-Prognose gestartet")
        
        try:
            timeout = self.config.get_timeout("ISV", "aroma_prediction")
            
            # Führe Aroma-Prognose aus
            aroma_result = await asyncio.wait_for(
                self._run_aroma_prediction(input_data),
                timeout=timeout
            )
            
            # Führe Textur-Prognose aus
            texture_result = await asyncio.wait_for(
                self._run_texture_prediction(input_data),
                timeout=timeout
            )
            
            self.logger.info("Aroma- & Textur-Prognose abgeschlossen")
            
            return PredictionResult(True, aroma_result, texture_result)
            
        except asyncio.TimeoutError:
            return PredictionResult(False, None, None, "Prognose Timeout")
        
        except Exception as e:
            return PredictionResult(False, None, None, str(e))
    
    async def _task_2_4_aggregation_output(self, input_data: HGOutput, sim_decision: 'SimulationDecision',
                                         simulation_result: 'SimulationResult', 
                                         prediction_result: 'PredictionResult') -> ISVOutput:
        """
        Aufgabe 2.4: Aggregation und Output-Formatierung
        """
        self.logger.info("Aufgabe 2.4: Output-Formatierung gestartet")
        
        # Aggregiere Simulationsergebnisse
        simulations_ergebnis = SimulationsErgebnis(
            grundgeschmack=simulation_result.data.grundgeschmack,
            aromaProfil=prediction_result.aroma_profil,
            texturProfil=prediction_result.textur_profil
        )
        
        # Erstelle Beweis-Objekt
        beweis = ISVBeweis(
            simulationMethod=sim_decision.method,
            confidenceLevel=simulation_result.data.confidence_level,
            mdSimID=simulation_result.data.simulation_id,
            mdSimProtokoll=simulation_result.data.protokoll,
            aromaModellVersion="GNN-v3.1.2",
            texturModellVersion="T-SIM-v1.4",
            resourceLock=ResourceLock(
                lockID=sim_decision.allocation.lock_id,
                acquiredResources=[f"CPU_cores_{sim_decision.allocation.cpu_cores}",
                                 f"Memory_{sim_decision.allocation.memory_mb}MB"],
                lockDuration=int((datetime.now() - sim_decision.allocation.acquired_at).total_seconds())
            )
        )
        
        # Erstelle finale Output
        output = ISVOutput(
            taskID=input_data.taskID,
            subTaskID=sim_decision.sub_task_id,
            status=TaskStatus.SUCCESS,
            hypotheseID=input_data.hypotheseID,
            simulationsErgebnis=simulations_ergebnis,
            beweis=beweis
        )
        
        self.logger.info("Output-Formatierung abgeschlossen")
        
        return output
    
    # === Hilfsmethoden ===
    
    async def _load_simulation_models(self):
        """Lade Simulationsmodelle"""
        self.logger.info("Simulationsmodelle werden geladen...")
        
        await asyncio.sleep(0.2)  # Simuliere Modell-Laden
        
        self.classic_md_model = {"loaded": True, "version": "ClassicMD-v2.1"}
        self.neural_md_model = {"loaded": True, "version": "NeuralMD-v2.1.3"}
        
        self.logger.info("Simulationsmodelle erfolgreich geladen")
    
    async def _load_prediction_models(self):
        """Lade Prognosemodelle"""
        self.logger.info("Prognosemodelle werden geladen...")
        
        await asyncio.sleep(0.2)  # Simuliere Modell-Laden
        
        self.aroma_model = {"loaded": True, "version": "GNN-v3.1.2"}
        self.texture_model = {"loaded": True, "version": "T-SIM-v1.4"}
        
        self.logger.info("Prognosemodelle erfolgreich geladen")
    
    async def _acquire_resources(self, resources_needed: Dict, method: SimulationMethod) -> Optional[ResourceAllocation]:
        """Akquiriere Ressourcen für Simulation"""
        
        # Dummy-Implementierung - in Realität würde hier ein Resource-Manager verwendet
        lock_id = f"LOCK-ISV-{uuid.uuid4().hex[:8]}"
        
        allocation = ResourceAllocation(
            cpu_cores=resources_needed["cpu_cores"],
            memory_mb=resources_needed["memory_mb"],
            gpu_slots=resources_needed["gpu_slots"],
            lock_id=lock_id,
            acquired_at=datetime.now()
        )
        
        self.resource_locks[lock_id] = allocation
        
        return allocation
    
    async def _release_resources(self, allocation: ResourceAllocation):
        """Gebe Ressourcen frei"""
        if allocation.lock_id in self.resource_locks:
            del self.resource_locks[allocation.lock_id]
            self.logger.info(f"Ressourcen freigegeben: {allocation.lock_id}")
    
    async def _run_classic_md_simulation(self, input_data: HGOutput) -> 'MDSimulationData':
        """Führe klassische MD-Simulation aus"""
        self.logger.info("Klassische MD-Simulation gestartet")
        
        # Simuliere längere Berechnung
        await asyncio.sleep(2.0)
        
        # Dummy-Ergebnisse
        grundgeschmack = Grundgeschmack(
            suess=GrundgeschmackScore(score=0.82, molekuel="Vanillin"),
            sauer=GrundgeschmackScore(score=0.05, molekuel=None),
            salzig=GrundgeschmackScore(score=0.01, molekuel=None),
            bitter=GrundgeschmackScore(score=0.15, molekuel="Geosmin"),
            umami=GrundgeschmackScore(score=0.11, molekuel=None)
        )
        
        return MDSimulationData(
            simulation_id=f"CLASSIC-MD-{uuid.uuid4().hex[:8]}",
            converged=True,
            confidence_level=0.95,
            grundgeschmack=grundgeschmack,
            protokoll="Klassische MD-Simulation erfolgreich konvergiert",
            duration=2.0
        )
    
    async def _run_neural_md_simulation(self, input_data: HGOutput) -> 'MDSimulationData':
        """Führe neuronale MD-Simulation aus"""
        self.logger.info("Neuronale MD-Simulation gestartet")
        
        start_time = datetime.now()
        
        try:
            if self.neural_md_available and self.neural_md_simulator:
                # Use real Neural MD simulator
                molecules = []
                for komponente in input_data.hypothese.komponenten:
                    molecules.append({
                        'name': komponente.name,
                        'concentration': komponente.konzentration
                    })
                
                # Run simulation
                simulation_id = f"NEURAL-MD-{uuid.uuid4().hex[:8]}"
                results = self.neural_md_simulator.simulate_interactions(molecules, simulation_id)
                
                # Convert results to expected format
                grundgeschmack = Grundgeschmack(
                    suess=GrundgeschmackScore(
                        score=results["grundgeschmack"]["süß"]["score"],
                        molekuel=results["grundgeschmack"]["süß"]["molekül"]
                    ),
                    sauer=GrundgeschmackScore(
                        score=results["grundgeschmack"]["sauer"]["score"],
                        molekuel=results["grundgeschmack"]["sauer"]["molekül"]
                    ),
                    salzig=GrundgeschmackScore(
                        score=results["grundgeschmack"]["salzig"]["score"],
                        molekuel=results["grundgeschmack"]["salzig"]["molekül"]
                    ),
                    bitter=GrundgeschmackScore(
                        score=results["grundgeschmack"]["bitter"]["score"],
                        molekuel=results["grundgeschmack"]["bitter"]["molekül"]
                    ),
                    umami=GrundgeschmackScore(
                        score=results["grundgeschmack"]["umami"]["score"],
                        molekuel=results["grundgeschmack"]["umami"]["molekül"]
                    )
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                return MDSimulationData(
                    simulation_id=simulation_id,
                    converged=True,
                    confidence_level=results["confidence"],
                    grundgeschmack=grundgeschmack,
                    protokoll=f"Neural MD simulation completed using {results['model_version']}",
                    duration=duration
                )
            
            else:
                # Fallback to mock implementation
                await asyncio.sleep(0.5)
                
                grundgeschmack = Grundgeschmack(
                    suess=GrundgeschmackScore(score=0.80, molekuel="Vanillin"),
                    sauer=GrundgeschmackScore(score=0.06, molekuel=None),
                    salzig=GrundgeschmackScore(score=0.02, molekuel=None),
                    bitter=GrundgeschmackScore(score=0.16, molekuel="Geosmin"),
                    umami=GrundgeschmackScore(score=0.12, molekuel=None)
                )
                
                return MDSimulationData(
                    simulation_id=f"NEURAL-MD-{uuid.uuid4().hex[:8]}",
                    converged=True,
                    confidence_level=0.85,
                    grundgeschmack=grundgeschmack,
                    protokoll="Mock neuronale MD-Simulation (Neural MD nicht verfügbar)",
                    duration=0.5
                )
                
        except Exception as e:
            self.logger.error(f"Neural MD simulation failed: {e}")
            raise
    
    async def _run_aroma_prediction(self, input_data: HGOutput) -> AromaProfil:
        """Führe Aroma-Prognose aus"""
        await asyncio.sleep(0.3)
        
        return AromaProfil(
            ERDIG=0.95,
            SUESSLICH=0.88,
            HOLZIG=0.21,
            FRUCHTIG=0.05
        )
    
    async def _run_texture_prediction(self, input_data: HGOutput) -> TexturProfil:
        """Führe Textur-Prognose aus"""
        await asyncio.sleep(0.2)
        
        return TexturProfil(
            viskositaet=0.1,
            kristallinitaet=0.0
        )
    
    def _create_error_output(self, task_id: str, hypothese_id: str, error_code: str, error_message: str) -> ISVOutput:
        """Erstelle Error-Output"""
        return ISVOutput(
            taskID=task_id,
            status=TaskStatus.FAILED,
            hypotheseID=hypothese_id,
            errorCode=error_code,
            errorMessage=self.error_codes.get(error_code, error_message)
        )

# === Hilfsklassen ===

@dataclass
class ValidationResult:
    """Resultat einer Validierung"""
    success: bool
    error_message: str = ""

@dataclass
class SimulationDecision:
    """Entscheidung über Simulationsmethode"""
    success: bool
    method: Optional[SimulationMethod] = None
    sub_task_id: Optional[str] = None
    reason: str = ""
    allocation: Optional[ResourceAllocation] = None

@dataclass
class MDSimulationData:
    """Daten einer MD-Simulation"""
    simulation_id: str
    converged: bool
    confidence_level: float
    grundgeschmack: Grundgeschmack
    protokoll: str
    duration: float

@dataclass
class SimulationResult:
    """Resultat einer Simulation"""
    success: bool
    data: Optional[MDSimulationData] = None
    error_message: str = ""

@dataclass
class PredictionResult:
    """Resultat einer Prognose"""
    success: bool
    aroma_profil: Optional[AromaProfil] = None
    textur_profil: Optional[TexturProfil] = None
    error_message: str = ""
