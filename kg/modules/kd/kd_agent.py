"""
KD (Kritiker/Diskriminator) Agent

Gesamtziel: Bewerte das vom ISV gelieferte, simulierte sensorische Profil auf Basis 
einer erlernten Harmonielehre und eines Neuigkeits-Algorithmus. Fälle ein endgültiges, 
begründetes Urteil ("APPROVED" oder "REJECTED") und erstelle einen detaillierten 
Bewertungs-Score als Output für den Lern-Regulator.

Atomare Aufgabenkette:
1. Input-Validierung & Daten-Extraktion
2. Harmonie-Analyse (Regelabgleich)
3. Neuheits-Bestätigung (Novelty-Abgleich)
4. Gesamturteil und Score-Aggregation
5. Finale Output-Formatierung
"""

import time
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from ...schemas import (
    ISVResult, KDResult, KDUrteil, KDScoring, KDBeweis,
    ErrorResponse
)
from ...utils.config import get_config
from ...utils.logging_config import get_logger
from ...utils.resource_manager import ResourceManager

logger = get_logger("KD")

@dataclass
class HarmonieRegel:
    """Harmonieregel für Geschmacks- und Aromaanalyse"""
    regel_id: str
    name: str
    beschreibung: str
    typ: str  # "geschmack", "aroma", "textur"
    gewichtung: float
    schwellenwert: float
    
    def evaluate(self, profil: Dict[str, Any]) -> Dict[str, Any]:
        """Bewerte ein Profil basierend auf dieser Regel"""
        # Vereinfachte Regelbewertung - in Produktion würde hier komplexe Logik stehen
        score = 0.0
        passed = False
        
        if self.typ == "geschmack":
            # Beispiel: Süß-Bitter-Balance
            if "süß" in profil and "bitter" in profil:
                sweet_score = profil["süß"].get("score", 0.0)
                bitter_score = profil["bitter"].get("score", 0.0)
                # Wenn süß >= bitter * 3, dann ist die Balance gut
                if sweet_score >= bitter_score * 3:
                    score = min(0.95, sweet_score / (bitter_score + 0.1))
                    passed = True
                else:
                    score = max(0.3, sweet_score / (bitter_score + 0.1))
                    passed = False
        
        elif self.typ == "aroma":
            # Beispiel: Erdige und süße Aromen harmonieren gut
            if "ERDIG" in profil and "SÜßLICH" in profil:
                earth_score = profil.get("ERDIG", 0.0)
                sweet_score = profil.get("SÜßLICH", 0.0)
                # Beide Scores sollten hoch sein
                if earth_score > 0.7 and sweet_score > 0.7:
                    score = (earth_score + sweet_score) / 2
                    passed = True
                else:
                    score = max(0.4, (earth_score + sweet_score) / 2)
                    passed = False
        
        return {
            "score": score,
            "pass": passed,
            "details": f"Regel {self.regel_id}: {score:.2f}"
        }

class KDAgent:
    """
    Kritiker/Diskriminator Agent
    
    Führt die atomare Aufgabenkette für kritische Bewertung durch:
    1. Input-Validierung & Daten-Extraktion
    2. Harmonie-Analyse (Regelabgleich)
    3. Neuheits-Bestätigung (Novelty-Abgleich)
    4. Gesamturteil und Score-Aggregation
    5. Finale Output-Formatierung
    """
    
    def __init__(self):
        self.config = get_config()
        self.resource_manager = ResourceManager()
        
        # Lade Harmonieregeln
        self.harmonieregeln = self._load_harmonieregeln()
        
        # Wissensgraph-Simulation (vereinfacht)
        self.wissensgraph = self._init_wissensgraph()
        
        logger.info("KD-Agent erfolgreich initialisiert")
    
    def _load_harmonieregeln(self) -> List[HarmonieRegel]:
        """Lade Harmonieregeln aus dem Wissensgraph"""
        # In der Produktion würde hier aus einer Datenbank geladen
        regeln = [
            HarmonieRegel(
                regel_id="Rule_G01",
                name="Süß-Bitter-Balance",
                beschreibung="Süße sollte bittere Komponenten ausbalancieren",
                typ="geschmack",
                gewichtung=0.8,
                schwellenwert=0.6
            ),
            HarmonieRegel(
                regel_id="Rule_A04",
                name="Erde-Süße-Paarung",
                beschreibung="Erdige und süße Aromen harmonieren gut",
                typ="aroma",
                gewichtung=0.9,
                schwellenwert=0.7
            ),
            HarmonieRegel(
                regel_id="Rule_T01",
                name="Textur-Komplexität",
                beschreibung="Textur sollte moderate Komplexität haben",
                typ="textur",
                gewichtung=0.6,
                schwellenwert=0.5
            )
        ]
        return regeln
    
    def _init_wissensgraph(self) -> Dict[str, Any]:
        """Initialisiere Wissensgraph (vereinfachte Version)"""
        return {
            "approved_hypotheses": [
                {
                    "id": "HYP-REF-001",
                    "profil": {
                        "grundgeschmack": {"süß": 0.8, "bitter": 0.2},
                        "aromaProfil": {"ERDIG": 0.7, "SÜßLICH": 0.8}
                    }
                }
            ],
            "threshold_approved": 0.75
        }
    
    def process_task(self, isv_result: ISVResult) -> KDResult:
        """
        Führe die vollständige atomare Aufgabenkette für KD durch
        
        Args:
            isv_result: Ergebnis vom ISV-Agent
            
        Returns:
            KDResult: Bewertungsergebnis mit Urteil und Beweis
        """
        task_id = f"KD-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:3]}"
        
        logger.set_task_id(task_id)
        logger.log_task_start("KD_PROCESS", task_id)
        
        start_time = time.time()
        
        try:
            # Aufgabe 3.1: Input-Validierung & Daten-Extraktion
            validated_data = self._validate_input(isv_result)
            
            # Aufgabe 3.2: Harmonie-Analyse (Regelabgleich)
            harmonie_ergebnis = self._analyze_harmony(validated_data)
            
            # Aufgabe 3.3: Neuheits-Bestätigung (Novelty-Abgleich)
            novelty_ergebnis = self._verify_novelty(validated_data)
            
            # Aufgabe 3.4: Gesamturteil und Score-Aggregation
            urteil_data = self._aggregate_judgment(harmonie_ergebnis, novelty_ergebnis)
            
            # Aufgabe 3.5: Finale Output-Formatierung
            result = self._format_output(task_id, isv_result.hypotheseID, urteil_data, 
                                       harmonie_ergebnis, novelty_ergebnis)
            
            duration = time.time() - start_time
            logger.log_task_complete("KD_PROCESS", duration)
            
            # Spezifisches Logging für Urteil
            logger.log_verdict(
                result.urteil.verdict,
                result.urteil.gesamtScore,
                result.hypotheseID
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.log_task_error("KD_PROCESS", "KD001", str(e))
            
            return KDResult(
                taskID=task_id,
                status="FAILED",
                hypotheseID=isv_result.hypotheseID,
                errorCode="KD001",
                errorMessage=f"Unerwarteter Fehler in KD-Verarbeitung: {str(e)}",
                urteil=None,
                beweis=None
            )
    
    def _validate_input(self, isv_result: ISVResult) -> Dict[str, Any]:
        """
        Aufgabe 3.1: Input-Validierung & Daten-Extraktion
        
        Args:
            isv_result: ISV-Ergebnis
            
        Returns:
            Dict mit extrahierten Daten
            
        Raises:
            ValueError: Bei ungültigem Input
        """
        if not isv_result or isv_result.status != "SUCCESS":
            raise ValueError("Ungültiges ISV-Ergebnis erhalten")
        
        if not isv_result.simulationsErgebnis:
            raise ValueError("Keine Simulationsergebnisse verfügbar")
        
        # Extrahiere relevante Daten
        validated_data = {
            "hypotheseID": isv_result.hypotheseID,
            "grundgeschmack": isv_result.simulationsErgebnis.grundgeschmack,
            "aromaProfil": isv_result.simulationsErgebnis.aromaProfil,
            "texturProfil": isv_result.simulationsErgebnis.texturProfil,
            "simulation_confidence": isv_result.beweis.confidenceLevel
        }
        
        logger.info("Input-Validierung erfolgreich abgeschlossen")
        return validated_data
    
    def _analyze_harmony(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aufgabe 3.2: Harmonie-Analyse (Regelabgleich)
        
        Args:
            validated_data: Validierte Eingabedaten
            
        Returns:
            Dict mit Harmonie-Analyse-Ergebnissen
        """
        angewandte_regeln = []
        regel_ergebnisse = {}
        
        for regel in self.harmonieregeln:
            if regel.typ == "geschmack":
                ergebnis = regel.evaluate(validated_data["grundgeschmack"])
            elif regel.typ == "aroma":
                ergebnis = regel.evaluate(validated_data["aromaProfil"])
            elif regel.typ == "textur":
                ergebnis = regel.evaluate(validated_data["texturProfil"])
            else:
                continue
            
            angewandte_regeln.append(regel.name)
            regel_ergebnisse[regel.regel_id] = ergebnis
        
        # Berechne Harmonie-Scores
        geschmacksharmonie = self._calculate_harmony_score(regel_ergebnisse, "geschmack")
        aromaharmonie = self._calculate_harmony_score(regel_ergebnisse, "aroma")
        texturkomplexität = self._calculate_complexity_score(validated_data["texturProfil"])
        
        return {
            "angewandte_regeln": angewandte_regeln,
            "regel_ergebnisse": regel_ergebnisse,
            "geschmacksharmonie": geschmacksharmonie,
            "aromaharmonie": aromaharmonie,
            "texturkomplexität": texturkomplexität
        }
    
    def _calculate_harmony_score(self, regel_ergebnisse: Dict[str, Any], typ: str) -> float:
        """Berechne Harmonie-Score für einen bestimmten Typ"""
        relevante_regeln = [r for r in self.harmonieregeln if r.typ == typ]
        if not relevante_regeln:
            return 0.6  # Neutral score
        
        total_score = 0.0
        total_weight = 0.0
        
        for regel in relevante_regeln:
            if regel.regel_id in regel_ergebnisse:
                ergebnis = regel_ergebnisse[regel.regel_id]
                total_score += ergebnis["score"] * regel.gewichtung
                total_weight += regel.gewichtung
        
        return total_score / total_weight if total_weight > 0 else 0.6
    
    def _calculate_complexity_score(self, textur_profil: Dict[str, Any]) -> float:
        """Berechne Textur-Komplexitäts-Score"""
        # Einfache Berechnung basierend auf Viskosität und Kristallinität
        viskosität = textur_profil.get("viskosität", 0.0)
        kristallinität = textur_profil.get("kristallinität", 0.0)
        
        # Moderate Komplexität ist gewünscht
        komplexität = (viskosität + kristallinität) / 2
        if 0.3 <= komplexität <= 0.7:
            return 0.8  # Gute Komplexität
        else:
            return max(0.4, 1.0 - abs(komplexität - 0.5))
    
    def _verify_novelty(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aufgabe 3.3: Neuheits-Bestätigung (Novelty-Abgleich)
        
        Args:
            validated_data: Validierte Eingabedaten
            
        Returns:
            Dict mit Novelty-Analyse-Ergebnissen
        """
        # Vergleiche mit bekannten Hypothesen im Wissensgraph
        min_abstand = float('inf')
        nächster_nachbar = None
        
        for approved_hyp in self.wissensgraph["approved_hypotheses"]:
            abstand = self._calculate_profile_distance(
                validated_data, approved_hyp["profil"]
            )
            if abstand < min_abstand:
                min_abstand = abstand
                nächster_nachbar = approved_hyp["id"]
        
        # Berechne bestätigte Neuheit
        bestätigte_neuheit = min(0.95, max(0.1, min_abstand))
        
        return {
            "nächster_nachbar": nächster_nachbar,
            "abstand": min_abstand,
            "bestätigte_neuheit": bestätigte_neuheit
        }
    
    def _calculate_profile_distance(self, profil1: Dict[str, Any], profil2: Dict[str, Any]) -> float:
        """Berechne Abstand zwischen zwei Profilen"""
        # Vereinfachte Distanzberechnung
        distance = 0.0
        
        # Geschmacks-Distanz
        for taste in ["süß", "bitter", "sauer", "salzig", "umami"]:
            score1 = profil1.get("grundgeschmack", {}).get(taste, {}).get("score", 0.0)
            score2 = profil2.get("grundgeschmack", {}).get(taste, 0.0)
            distance += abs(score1 - score2)
        
        # Aroma-Distanz
        all_aromas = set(profil1.get("aromaProfil", {}).keys()) | set(profil2.get("aromaProfil", {}).keys())
        for aroma in all_aromas:
            score1 = profil1.get("aromaProfil", {}).get(aroma, 0.0)
            score2 = profil2.get("aromaProfil", {}).get(aroma, 0.0)
            distance += abs(score1 - score2)
        
        return distance / (len(all_aromas) + 5)  # Normalisiert
    
    def _aggregate_judgment(self, harmonie_ergebnis: Dict[str, Any], 
                           novelty_ergebnis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aufgabe 3.4: Gesamturteil und Score-Aggregation
        
        Args:
            harmonie_ergebnis: Harmonie-Analyse-Ergebnisse
            novelty_ergebnis: Novelty-Analyse-Ergebnisse
            
        Returns:
            Dict mit Gesamturteil
        """
        # Gewichtete Formel für Gesamtscore
        weights = {
            "geschmacksharmonie": 0.3,
            "aromaharmonie": 0.3,
            "texturkomplexität": 0.2,
            "bestätigte_neuheit": 0.2
        }
        
        gesamt_score = (
            harmonie_ergebnis["geschmacksharmonie"] * weights["geschmacksharmonie"] +
            harmonie_ergebnis["aromaharmonie"] * weights["aromaharmonie"] +
            harmonie_ergebnis["texturkomplexität"] * weights["texturkomplexität"] +
            novelty_ergebnis["bestätigte_neuheit"] * weights["bestätigte_neuheit"]
        )
        
        # Schwellenwert für Genehmigung
        schwellenwert = self.wissensgraph["threshold_approved"]
        verdict = "APPROVED" if gesamt_score >= schwellenwert else "REJECTED"
        
        return {
            "verdict": verdict,
            "gesamt_score": gesamt_score,
            "schwellenwert": schwellenwert,
            "weights": weights
        }
    
    def _format_output(self, task_id: str, hypothese_id: str, urteil_data: Dict[str, Any],
                      harmonie_ergebnis: Dict[str, Any], novelty_ergebnis: Dict[str, Any]) -> KDResult:
        """
        Aufgabe 3.5: Finale Output-Formatierung
        
        Args:
            task_id: Task-ID
            hypothese_id: Hypothese-ID
            urteil_data: Urteilsdaten
            harmonie_ergebnis: Harmonie-Ergebnisse
            novelty_ergebnis: Novelty-Ergebnisse
            
        Returns:
            KDResult: Formatiertes Ergebnis
        """
        # Erstelle Urteil-Objekt
        urteil = KDUrteil(
            verdict=urteil_data["verdict"],
            gesamtScore=urteil_data["gesamt_score"],
            scoring=KDScoring(
                geschmacksharmonie=harmonie_ergebnis["geschmacksharmonie"],
                aromaharmonie=harmonie_ergebnis["aromaharmonie"],
                texturkomplexität=harmonie_ergebnis["texturkomplexität"],
                bestätigteNeuheit=novelty_ergebnis["bestätigte_neuheit"]
            )
        )
        
        # Erstelle Beweis-Objekt
        beweis = KDBeweis(
            angewandteRegeln=harmonie_ergebnis["angewandte_regeln"],
            regelErgebnisse=harmonie_ergebnis["regel_ergebnisse"],
            nächsterNachbarID=novelty_ergebnis["nächster_nachbar"],
            abstandZumNachbarn=novelty_ergebnis["abstand"]
        )
        
        return KDResult(
            taskID=task_id,
            status="SUCCESS",
            hypotheseID=hypothese_id,
            urteil=urteil,
            beweis=beweis
        )
