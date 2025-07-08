# Hypothesen-Generator (HG) - Hauptmodul
# Implementiert die atomare Aufgabenstruktur aus der Spezifikation

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass

from kg.utils.config import Config
from kg.utils.logging_config import KGLogger
from kg.schemas import (
    HGInput, HGOutput, HGBeweis, Hypothese, MolekuelKomponente,
    TaskStatus, SignalType, ErrorOutput
)
from kg.utils.resource_manager import resource_manager, ResourceType, LockPriority

# ML Model imports
try:
    from kg.ml_models.vae_model import HypothesisGenerator
    ML_MODELS_AVAILABLE = True
except ImportError:
    ML_MODELS_AVAILABLE = False

@dataclass
class VAEKandidat:
    """Kandidat aus dem VAE-Modell"""
    id: str
    komponenten: List[MolekuelKomponente]
    vae_koordinaten: List[float]
    novelty_score: float

class HGAgent:
    """
    Hypothesen-Generator Agent
    Implementiert die atomare Aufgabenstruktur:
    1.1 Input-Validierung
    1.2 Kandidaten-Generierung
    1.3 Regel-Filterung
    1.4 Auswahl & Novelty-Scoring
    1.5 Finale Output-Formatierung
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = KGLogger("HG")
        
        # Initialize ML model if available
        if ML_MODELS_AVAILABLE:
            try:
                model_path = config.get("modules.hg.model_path", None)
                self.ml_generator = HypothesisGenerator(model_path)
                self.use_ml_model = True
                self.logger.info("Real ML model initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize ML model: {e}, falling back to mock")
                self.ml_generator = None
                self.use_ml_model = False
        else:
            self.ml_generator = None
            self.use_ml_model = False
            self.logger.info("ML models not available, using mock implementation")
        
        # Performance tracking
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "average_time": 0.0
        }
        
        # Known hypotheses for novelty calculation
        self.known_hypotheses = []
        
        # Agent state
        self.is_initialized = False
        self.vae_model = None
        self.filter_rules = []
        self.knowledge_graph = None
        self.is_initialized = False
        
        # Fehlercode-Definitionen
        self.error_codes = {
            "HG001": "Keine Hypothese gefunden, die Constraints und Filter passiert",
            "HG002": "Input-Signal oder Constraints ungültig/unvollständig",
            "HG003": "VAE-Modell nicht verfügbar oder korrupt",
            "HG004": "Timeout erreicht während Kandidaten-Generierung"
        }
    
    async def initialize(self):
        """Initialisiere den HG-Agent"""
        self.logger.info("HG-Agent wird initialisiert...")
        
        try:
            # VAE-Modell laden (Dummy-Implementierung)
            await self._load_vae_model()
            
            # Filter-Regeln laden
            await self._load_filter_rules()
            
            # Knowledge Graph Verbindung
            await self._connect_knowledge_graph()
            
            self.is_initialized = True
            self.logger.info("HG-Agent erfolgreich initialisiert")
            
        except Exception as e:
            self.logger.error(f"Fehler bei HG-Initialisierung: {e}")
            raise
    
    async def process_task(self, input_data: HGInput) -> HGOutput:
        """
        Hauptverarbeitungsschleife für eine HG-Aufgabe
        Implementiert die atomare Aufgabenstruktur
        """
        self.logger.set_task_id(input_data.taskID)
        self.logger.log_task_start("HG_PROCESS", input_data.taskID)
        
        start_time = datetime.now()
        
        try:
            # Aufgabe 1.1: Input-Validierung
            validation_result = await self._task_1_1_input_validation(input_data)
            if not validation_result.success:
                return self._create_error_output(input_data.taskID, "HG002", validation_result.error_message)
            
            # Aufgabe 1.2: Kandidaten-Generierung
            kandidaten = await self._task_1_2_candidate_generation(input_data)
            if not kandidaten:
                return self._create_error_output(input_data.taskID, "HG001", "Keine Kandidaten generiert")
            
            # Aufgabe 1.3: Regel-Filterung
            filtered_kandidaten = await self._task_1_3_rule_filtering(kandidaten)
            if not filtered_kandidaten:
                return self._create_error_output(input_data.taskID, "HG001", "Keine Kandidaten nach Filterung")
            
            # Aufgabe 1.4: Auswahl & Novelty-Scoring
            selected_candidate = await self._task_1_4_selection_novelty_scoring(filtered_kandidaten)
            if not selected_candidate:
                return self._create_error_output(input_data.taskID, "HG001", "Keine Auswahl möglich")
            
            # Aufgabe 1.5: Finale Output-Formatierung
            output = await self._task_1_5_output_formatting(input_data, selected_candidate, filtered_kandidaten)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_task_complete("HG_PROCESS", duration)
            
            return output
            
        except asyncio.TimeoutError:
            self.logger.log_task_error("HG_PROCESS", "HG004", "Timeout erreicht")
            return self._create_error_output(input_data.taskID, "HG004", "Timeout erreicht")
        
        except Exception as e:
            self.logger.log_task_error("HG_PROCESS", "HG003", str(e))
            return self._create_error_output(input_data.taskID, "HG003", str(e))
    
    async def _task_1_1_input_validation(self, input_data: HGInput) -> 'ValidationResult':
        """
        Aufgabe 1.1: Input-Validierung
        Prüfe Input-Format und Constraints
        """
        self.logger.info("Aufgabe 1.1: Input-Validierung gestartet")
        
        try:
            # Prüfe ob alle erforderlichen Felder vorhanden sind
            if not input_data.taskID:
                return ValidationResult(False, "Task-ID fehlt")
            
            if not input_data.signal:
                return ValidationResult(False, "Signal fehlt")
            
            if not input_data.constraints:
                return ValidationResult(False, "Constraints fehlen")
            
            # Prüfe Constraints-Format
            constraints = input_data.constraints
            
            if "targetProfile" not in constraints:
                return ValidationResult(False, "targetProfile in Constraints fehlt")
            
            if "exclude" not in constraints:
                constraints["exclude"] = []
            
            # Validiere targetProfile
            valid_profiles = ["ERDIG", "SÜSS", "SAUER", "SALZIG", "BITTER", "UMAMI", "FRUCHTIG", "HOLZIG"]
            for profile in constraints["targetProfile"]:
                if profile not in valid_profiles:
                    return ValidationResult(False, f"Ungültiges targetProfile: {profile}")
            
            self.logger.info("Input-Validierung erfolgreich", 
                           target_profiles=constraints["targetProfile"],
                           exclude_count=len(constraints["exclude"]))
            
            return ValidationResult(True, "Input-Validierung OK")
            
        except Exception as e:
            return ValidationResult(False, f"Fehler bei Input-Validierung: {e}")
    
    async def _task_1_2_candidate_generation(self, input_data: HGInput) -> List[VAEKandidat]:
        """
        Aufgabe 1.2: Kandidaten-Generierung
        Generiere 10 Kandidaten mit dem VAE-Modell oder ML-Model
        """
        self.logger.info("Aufgabe 1.2: Kandidaten-Generierung gestartet")
        
        try:
            # Acquire resources for generation
            resource_lock = await resource_manager.acquire_lock(
                task_id=input_data.taskID,
                module="HG_generation",
                resources={
                    ResourceType.CPU_CORE: 2,
                    ResourceType.MEMORY_GB: 4
                },
                timeout_seconds=300,
                priority=LockPriority.NORMAL
            )
            
            try:
                # Timeout für diese Aufgabe
                timeout = self.config.get_timeout("HG", "vae_generation")
                
                if self.use_ml_model and self.ml_generator:
                    # Use real ML model
                    kandidaten = await asyncio.wait_for(
                        self._generate_ml_candidates(input_data),
                        timeout=timeout
                    )
                else:
                    # Use mock implementation
                    kandidaten = await asyncio.wait_for(
                        self._generate_vae_candidates(input_data),
                        timeout=timeout
                    )
                
                self.logger.info(f"Kandidaten-Generierung abgeschlossen: {len(kandidaten)} Kandidaten generiert")
                
                return kandidaten
                
            finally:
                # Release resources
                if resource_lock:
                    resource_manager.release_lock(resource_lock)
                    
        except asyncio.TimeoutError:
            self.logger.error("Timeout bei Kandidaten-Generierung")
            raise
        except Exception as e:
            self.logger.error(f"Fehler bei Kandidaten-Generierung: {e}")
            raise
    
    async def _task_1_3_rule_filtering(self, kandidaten: List[VAEKandidat]) -> List[VAEKandidat]:
        """
        Aufgabe 1.3: Regel-Filterung
        Wende Filter-Regeln auf alle Kandidaten an
        """
        self.logger.info("Aufgabe 1.3: Regel-Filterung gestartet")
        
        filtered_kandidaten = []
        filter_protokoll = {}
        
        for kandidat in kandidaten:
            passed_filters = True
            kandidat_protokoll = {}
            
            # Wende alle Filter-Regeln an
            for filter_rule in self.filter_rules:
                result = await self._apply_filter_rule(filter_rule, kandidat)
                kandidat_protokoll[filter_rule["id"]] = result
                
                if not result["passed"]:
                    passed_filters = False
                    break
            
            filter_protokoll[kandidat.id] = kandidat_protokoll
            
            if passed_filters:
                filtered_kandidaten.append(kandidat)
        
        self.logger.info(f"Regel-Filterung abgeschlossen: {len(filtered_kandidaten)}/{len(kandidaten)} Kandidaten bestanden",
                        filter_protokoll=filter_protokoll)
        
        return filtered_kandidaten
    
    async def _task_1_4_selection_novelty_scoring(self, kandidaten: List[VAEKandidat]) -> Optional[VAEKandidat]:
        """
        Aufgabe 1.4: Auswahl & Novelty-Scoring
        Wähle den besten Kandidaten basierend auf Novelty-Score
        """
        self.logger.info("Aufgabe 1.4: Auswahl & Novelty-Scoring gestartet")
        
        if not kandidaten:
            return None
        
        # Berechne Novelty-Scores für alle Kandidaten
        for kandidat in kandidaten:
            kandidat.novelty_score = await self._calculate_novelty_score(kandidat)
        
        # Sortiere nach Novelty-Score (höchster zuerst)
        kandidaten.sort(key=lambda k: k.novelty_score, reverse=True)
        
        selected = kandidaten[0]
        
        self.logger.info(f"Kandidat ausgewählt: {selected.id}",
                        novelty_score=selected.novelty_score,
                        komponenten_count=len(selected.komponenten))
        
        # Dokumentiere Top-3 für Beweis
        top_3_scores = [k.novelty_score for k in kandidaten[:3]]
        self.logger.debug(f"Top-3 Novelty-Scores: {top_3_scores}")
        
        return selected
    
    async def _task_1_5_output_formatting(self, input_data: HGInput, selected_candidate: VAEKandidat, 
                                        all_filtered: List[VAEKandidat]) -> HGOutput:
        """
        Aufgabe 1.5: Finale Output-Formatierung
        Erstelle das finale Output-JSON mit allen Beweisen
        """
        self.logger.info("Aufgabe 1.5: Output-Formatierung gestartet")
        
        # Generiere eindeutige Hypothese-ID
        hypothese_id = f"HYP-{uuid.uuid4().hex[:8].upper()}-{datetime.now().strftime('%Y%m%d')}"
        
        # Erstelle Hypothese-Objekt
        hypothese = Hypothese(
            komponenten=selected_candidate.komponenten,
            typ="molekular"
        )
        
        # Erstelle Beweis-Objekt
        beweis = HGBeweis(
            herleitung=f"Hypothese wurde aus VAE-Raum {selected_candidate.vae_koordinaten} generiert",
            filterProtokoll=f"Alle Filter-Regeln erfolgreich passiert. {len(all_filtered)} Kandidaten bestanden Filter",
            noveltyScore=selected_candidate.novelty_score,
            constraintsPropagation=input_data.constraints
        )
        
        # Erstelle finale Output
        output = HGOutput(
            taskID=input_data.taskID,
            status=TaskStatus.SUCCESS,
            hypotheseID=hypothese_id,
            hypothese=hypothese,
            beweis=beweis
        )
        
        self.logger.log_hypothesis_generated(hypothese_id, len(selected_candidate.komponenten))
        self.logger.info("Output-Formatierung abgeschlossen")
        
        return output
    
    async def _generate_ml_candidates(self, input_data: HGInput) -> List[VAEKandidat]:
        """
        Generate candidates using real ML model
        """
        try:
            # Extract target profiles and constraints
            target_profiles = input_data.constraints.get("targetProfile", [])
            exclude_molecules = input_data.constraints.get("exclude", [])
            
            # Generate candidates using ML model
            candidates = self.ml_generator.generate_candidates(
                target_profiles=target_profiles,
                exclude_molecules=exclude_molecules,
                num_candidates=10
            )
            
            # Convert to VAEKandidat format
            vae_kandidaten = []
            for i, candidate in enumerate(candidates):
                vae_kandidat = VAEKandidat(
                    id=f"ML-{input_data.taskID}-{i+1:03d}",
                    komponenten=[
                        MolekuelKomponente(
                            name=mol["name"],
                            konzentration=mol["concentration"]
                        ) for mol in candidate["molecules"]
                    ],
                    vae_koordinaten=candidate.get("activation_scores", []),
                    novelty_score=self.ml_generator.calculate_novelty_score(
                        candidate, self.known_hypotheses
                    )
                )
                vae_kandidaten.append(vae_kandidat)
            
            return vae_kandidaten
            
        except Exception as e:
            self.logger.error(f"ML candidate generation failed: {e}")
            # Fallback to mock implementation
            return await self._generate_vae_candidates(input_data)

    # === Hilfsmethoden ===
    
    async def _load_vae_model(self):
        """Lade VAE-Modell (Dummy-Implementierung)"""
        self.logger.info("VAE-Modell wird geladen...")
        
        # Simuliere Modell-Laden
        await asyncio.sleep(0.1)
        
        # Dummy-VAE-Modell
        self.vae_model = {
            "loaded": True,
            "version": "VAE-v1.0.0",
            "latent_dimensions": 128
        }
        
        self.logger.info("VAE-Modell erfolgreich geladen", model_version=self.vae_model["version"])
    
    async def _load_filter_rules(self):
        """Lade Filter-Regeln"""
        self.logger.info("Filter-Regeln werden geladen...")
        
        # Standard-Filter-Regeln
        self.filter_rules = [
            {
                "id": "RF-01",
                "name": "Konzentrations-Plausibilität",
                "description": "Prüfe ob Konzentrationen im plausiblen Bereich liegen"
            },
            {
                "id": "RF-02", 
                "name": "Toxizitäts-Check",
                "description": "Prüfe auf bekannte toxische Kombinationen"
            },
            {
                "id": "RF-03",
                "name": "Chemische Kompatibilität",
                "description": "Prüfe chemische Kompatibilität der Komponenten"
            }
        ]
        
        self.logger.info(f"Filter-Regeln geladen: {len(self.filter_rules)} Regeln")
    
    async def _connect_knowledge_graph(self):
        """Verbinde mit Knowledge Graph (Dummy-Implementierung)"""
        self.logger.info("Knowledge Graph-Verbindung wird hergestellt...")
        
        # Simuliere DB-Verbindung
        await asyncio.sleep(0.1)
        
        # Dummy-Knowledge-Graph
        self.knowledge_graph = {
            "connected": True,
            "entries": 1000,
            "last_updated": datetime.now()
        }
        
        self.logger.info("Knowledge Graph-Verbindung hergestellt")
    
    async def _generate_vae_candidates(self, input_data: HGInput) -> List[VAEKandidat]:
        """Generiere VAE-Kandidaten (Dummy-Implementierung)"""
        kandidaten = []
        
        # Simuliere VAE-Generierung
        await asyncio.sleep(0.5)
        
        # Basis-Moleküle für die Generierung
        basis_molekuele = [
            ("Geosmin", 0.01, "erdig"),
            ("Vanillin", 0.2, "süß"),
            ("Citral", 0.1, "fruchtig"),
            ("Eugenol", 0.05, "holzig"),
            ("Menthol", 0.03, "kühl"),
            ("Limonene", 0.15, "zitrusartig"),
            ("Linalool", 0.08, "blumig")
        ]
        
        # Generiere 10 Kandidaten
        for i in range(10):
            kandidat_id = f"VAE-KAND-{i+1:03d}"
            
            # Wähle 2-4 Komponenten zufällig
            komponenten_count = np.random.randint(2, 5)
            selected_molecules = np.random.choice(len(basis_molekuele), komponenten_count, replace=False)
            
            komponenten = []
            for mol_idx in selected_molecules:
                mol_name, base_conc, _ = basis_molekuele[mol_idx]
                # Variiere Konzentration um ±50%
                variation = np.random.uniform(0.5, 1.5)
                final_conc = min(1.0, base_conc * variation)
                
                komponenten.append(MolekuelKomponente(
                    name=mol_name,
                    konzentration=final_conc
                ))
            
            # Zufällige VAE-Koordinaten
            vae_coords = np.random.normal(0, 1, 128).tolist()
            
            kandidat = VAEKandidat(
                id=kandidat_id,
                komponenten=komponenten,
                vae_koordinaten=vae_coords,
                novelty_score=0.0  # Wird später berechnet
            )
            
            kandidaten.append(kandidat)
        
        return kandidaten
    
    async def _apply_filter_rule(self, filter_rule: Dict, kandidat: VAEKandidat) -> Dict:
        """Wende eine Filter-Regel auf einen Kandidaten an"""
        rule_id = filter_rule["id"]
        
        # Dummy-Implementierung der Filter-Logik
        if rule_id == "RF-01":  # Konzentrations-Plausibilität
            for komponente in kandidat.komponenten:
                if komponente.konzentration > 0.5:  # Sehr hohe Konzentration
                    return {"passed": False, "reason": f"Konzentration zu hoch: {komponente.konzentration}"}
            return {"passed": True, "reason": "Konzentrationen plausibel"}
        
        elif rule_id == "RF-02":  # Toxizitäts-Check
            # Prüfe auf bekannte toxische Kombinationen
            molekuel_namen = [k.name for k in kandidat.komponenten]
            if "Geosmin" in molekuel_namen and "Citral" in molekuel_namen:
                return {"passed": False, "reason": "Toxische Kombination: Geosmin + Citral"}
            return {"passed": True, "reason": "Keine toxischen Kombinationen"}
        
        elif rule_id == "RF-03":  # Chemische Kompatibilität
            # Dummy-Kompatibilitätsprüfung
            if len(kandidat.komponenten) > 4:
                return {"passed": False, "reason": "Zu viele Komponenten für stabile Kombination"}
            return {"passed": True, "reason": "Chemisch kompatibel"}
        
        return {"passed": True, "reason": "Filter nicht implementiert"}
    
    async def _calculate_novelty_score(self, kandidat: VAEKandidat) -> float:
        """Berechne Novelty-Score für einen Kandidaten"""
        
        # Simuliere Knowledge Graph-Abfrage
        await asyncio.sleep(0.1)
        
        # Dummy-Berechnung basierend auf Komponenten
        base_score = 0.5
        
        # Bonuspunkte für seltene Moleküle
        rare_molecules = ["Geosmin", "Eugenol"]
        for komponente in kandidat.komponenten:
            if komponente.name in rare_molecules:
                base_score += 0.2
        
        # Bonuspunkte für ungewöhnliche Konzentrationen
        for komponente in kandidat.komponenten:
            if komponente.konzentration < 0.05 or komponente.konzentration > 0.3:
                base_score += 0.1
        
        # Sicherstellen, dass Score im Bereich [0,1] liegt
        return min(1.0, base_score)
    
    def _create_error_output(self, task_id: str, error_code: str, error_message: str) -> HGOutput:
        """Erstelle Error-Output"""
        return HGOutput(
            taskID=task_id,
            status=TaskStatus.FAILED,
            errorCode=error_code,
            errorMessage=self.error_codes.get(error_code, error_message)
        )

@dataclass
class ValidationResult:
    """Resultat einer Validierung"""
    success: bool
    error_message: str = ""
