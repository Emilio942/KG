from kg.schemas import (ISVOutput, KDOutput, KDUrteil, KDScoring, KDBeweis, 
                        RegelErgebnis, Verdict, TaskStatus, ErrorResponse)
from typing import Union, Dict, List, Tuple
import logging
import random
import uuid

logger = logging.getLogger(__name__)

class KDAgent:
    """
    Kritiker/Diskriminator Agent.
    Bewertet ein simuliertes sensorisches Profil.
    """

    def __init__(self, config):
        self.config = config
        # In a real scenario, this would connect to a knowledge graph to get harmony rules.
        logger.info("KD Agent initialisiert.")

    def _apply_harmony_rules(self, sim_ergebnis: ISVOutput) -> Tuple[Dict[str, RegelErgebnis], float, float]:
        """Simuliert die Anwendung von Harmonieregeln."""
        logger.debug("Aufgabe 3.2: Harmonie-Analyse gestartet.")
        rules_applied = {}
        
        # Regel 1: Süß-Bitter-Balance
        sweet_score = sim_ergebnis.simulationsErgebnis.grundgeschmack.suess.score
        bitter_score = sim_ergebnis.simulationsErgebnis.grundgeschmack.bitter.score
        geschmack_harmony = 1.0 - abs(sweet_score - (4 * bitter_score)) # Ideal: sweet = 4 * bitter
        geschmack_harmony = max(0, min(1, geschmack_harmony)) # clamp between 0 and 1
        rules_applied["Rule_G01_Süß-Bitter-Balance"] = RegelErgebnis(pass_status=geschmack_harmony > 0.5, score=round(geschmack_harmony, 2))

        # Regel 2: Aroma-Paarung (Erde-Süße)
        erdig_score = sim_ergebnis.simulationsErgebnis.aromaProfil.ERDIG
        suesslich_score = sim_ergebnis.simulationsErgebnis.aromaProfil.SUESSLICH
        aroma_harmony = 1.0 - abs(erdig_score - suesslich_score)
        aroma_harmony = max(0, min(1, aroma_harmony))
        rules_applied["Rule_A04_Erde-Süße-Paarung"] = RegelErgebnis(pass_status=aroma_harmony > 0.6, score=round(aroma_harmony, 2))

        logger.info(f"Harmonieregeln angewendet. Geschmack: {geschmack_harmony:.2f}, Aroma: {aroma_harmony:.2f}")
        return rules_applied, geschmack_harmony, aroma_harmony

    def _confirm_novelty(self, sim_ergebnis: ISVOutput) -> Tuple[float, str, float]:
        """Simuliert die Neuheits-Bestätigung gegen einen Wissensgraphen."""
        logger.debug("Aufgabe 3.3: Neuheits-Bestätigung gestartet.")
        # This simulates comparing the profile to all known approved profiles.
        confirmed_novelty = round(random.uniform(0.6, 0.99), 2)
        nearest_neighbor_id = f"HYP-{str(uuid.uuid4())[:8].upper()}"
        distance = round(1.0 - confirmed_novelty, 2)
        logger.info(f"Neuheit bestätigt: {confirmed_novelty:.2f}. Nächster Nachbar: {nearest_neighbor_id} (Abstand: {distance})")
        return confirmed_novelty, nearest_neighbor_id, distance

    async def process_task(self, isv_output: ISVOutput) -> Union[KDOutput, ErrorResponse]:
        """
        Verarbeitet eine einzelne Aufgabe zur Kritik und Diskriminierung.
        """
        logger.info(f"KD Agent startet Task: {isv_output.taskID} für Hypothese: {isv_output.hypotheseID}")

        try:
            # Aufgabe 3.1: Input-Validierung (implizit durch Pydantic)
            logger.debug("Aufgabe 3.1: Input-Validierung erfolgreich.")

            # Aufgabe 3.2: Harmonie-Analyse
            regel_ergebnisse, geschmack_score, aroma_score = self._apply_harmony_rules(isv_output)

            # Aufgabe 3.3: Neuheits-Bestätigung
            novelty_score, neighbor_id, distance = self._confirm_novelty(isv_output)

            # Aufgabe 3.4: Gesamturteil und Score-Aggregation
            logger.debug("Aufgabe 3.4: Gesamturteil und Score-Aggregation.")
            # Gewichtete Formel
            gesamt_score = (0.4 * geschmack_score) + (0.4 * aroma_score) + (0.2 * novelty_score)
            gesamt_score = round(gesamt_score, 2)

            # Schwellenwert für Urteil
            verdict = Verdict.APPROVED if gesamt_score > 0.7 else Verdict.REJECTED
            logger.info(f"Gesamtscore: {gesamt_score:.2f}. Urteil: {verdict.value}")

            # Aufgabe 3.5: Finale Output-Formatierung
            logger.debug("Aufgabe 3.5: Finale Output-Formatierung.")
            urteil = KDUrteil(
                verdict=verdict,
                gesamtScore=gesamt_score,
                scoring=KDScoring(
                    geschmacksharmonie=round(geschmack_score, 2),
                    aromaharmonie=round(aroma_score, 2),
                    texturkomplexitaet=round(random.uniform(0.3, 0.7), 2), # Placeholder
                    bestaetigteNeuheit=novelty_score
                )
            )
            beweis = KDBeweis(
                angewandteRegeln=list(regel_ergebnisse.keys()),
                regelErgebnisse=regel_ergebnisse,
                naechsterNachbarID=neighbor_id,
                abstandZumNachbarn=distance
            )

            output = KDOutput(
                taskID=isv_output.taskID,
                status=TaskStatus.SUCCESS,
                hypotheseID=isv_output.hypotheseID,
                urteil=urteil,
                beweis=beweis
            )
            logger.info(f"KD Agent hat Urteil für Hypothese {isv_output.hypotheseID} gefällt: {urteil.verdict.value}")
            return output

        except Exception as e:
            logger.error(f"Fehler im KD Agent bei Task {isv_output.taskID}: {e}", exc_info=True)
            return ErrorResponse(
                taskID=isv_output.taskID,
                hypotheseID=isv_output.hypotheseID,
                errorCode="KD999", # Allgemeiner Fehler
                errorMessage=f"Ein unerwarteter Fehler ist aufgetreten: {e}",
                module="KD"
            )