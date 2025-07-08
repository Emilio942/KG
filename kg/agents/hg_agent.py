from kg.schemas import HGInput, HGOutput, Hypothese, HGBeweis, MolekuelKomponente, TaskStatus, ErrorResponse
from typing import Union, List
import logging
import random
import uuid

logger = logging.getLogger(__name__)

class HGAgent:
    """
    Hypothesen-Generator Agent.
    Generiert neuartige Geschmackshypothesen basierend auf einem Startsignal.
    """

    def __init__(self, config):
        self.config = config
        # In a real scenario, this would load a trained VAE model.
        logger.info("HG Agent initialisiert.")

    def _generate_candidates(self, constraints: dict) -> List[Hypothese]:
        """Simuliert die VAE-Kandidaten-Generierung."""
        logger.debug("Aufgabe 1.2: Kandidaten-Generierung gestartet.")
        candidates = []
        for _ in range(10):
            # Create more varied candidates
            konzentration1 = round(random.uniform(0.01, 0.5), 4)
            konzentration2 = round(random.uniform(0.01, 0.5), 4)
            molekuel1 = random.choice(["Geosmin", "Linalool", "Furfural", "Damascone"])
            molekuel2 = random.choice(["Vanillin", "Ethyl-Maltol", "Menthol", "Citral"])
            candidate = Hypothese(
                komponenten=[
                    MolekuelKomponente(name=molekuel1, konzentration=konzentration1),
                    MolekuelKomponente(name=molekuel2, konzentration=konzentration2)
                ],
                typ="molekular"
            )
            candidates.append(candidate)
        logger.info(f"{len(candidates)} Kandidaten generiert.")
        return candidates

    def _filter_candidates(self, candidates: List[Hypothese], constraints: dict) -> (List[Hypothese], str):
        """Simuliert die Regel-Filterung."""
        logger.debug("Aufgabe 1.3: Regel-Filterung gestartet.")
        exclude_list = constraints.get("exclude", [])
        passed_candidates = []
        filter_protocol = ""

        for i, candidate in enumerate(candidates):
            passes = True
            reasons = []
            for komp in candidate.komponenten:
                if komp.name in exclude_list:
                    passes = False
                    reasons.append(f"enthält ausgeschlossenes Molekül {komp.name}")
            
            if passes:
                passed_candidates.append(candidate)
                filter_protocol += f"Kandidat {i+1}: PASSED\n"
            else:
                filter_protocol += f"Kandidat {i+1}: FAILED - Gründe: {', '.join(reasons)}\n"
        
        logger.info(f"{len(passed_candidates)} von {len(candidates)} Kandidaten haben den Filter passiert.")
        return passed_candidates, filter_protocol.strip()

    def _select_and_score(self, candidates: List[Hypothese]) -> (Hypothese, float):
        """Simuliert Auswahl und Novelty-Scoring."""
        logger.debug("Aufgabe 1.4: Auswahl & Novelty-Scoring gestartet.")
        if not candidates:
            return None, 0

        # Assign a random novelty score to each and find the best one
        scored_candidates = [(cand, random.uniform(0.5, 0.99)) for cand in candidates]
        
        winner, novelty_score = max(scored_candidates, key=lambda item: item[1])
        logger.info(f"Kandidat mit höchstem Novelty-Score ({novelty_score:.2f}) ausgewählt.")
        return winner, round(novelty_score, 2)

    async def process_task(self, hg_input: HGInput) -> Union[HGOutput, ErrorResponse]:
        """
        Verarbeitet eine einzelne Aufgabe zur Hypothesengenerierung mit voller Logik.
        """
        logger.info(f"HG Agent startet Task: {hg_input.taskID}")

        try:
            # Aufgabe 1.1: Input-Validierung (implizit durch Pydantic)
            logger.debug("Aufgabe 1.1: Input-Validierung erfolgreich.")

            # Aufgabe 1.2: Kandidaten-Generierung
            candidates = self._generate_candidates(hg_input.constraints)

            # Aufgabe 1.3: Regel-Filterung
            passed_candidates, filter_protocol = self._filter_candidates(candidates, hg_input.constraints)

            # Aufgabe 1.4: Auswahl & Novelty-Scoring
            selected_hypothesis, novelty_score = self._select_and_score(passed_candidates)

            # Fehlerbehandlung: Wenn kein Kandidat die Filter besteht
            if not selected_hypothesis:
                logger.warning(f"Keine gültige Hypothese für Task {hg_input.taskID} gefunden.")
                return ErrorResponse(
                    taskID=hg_input.taskID,
                    errorCode="HG001",
                    errorMessage="Keine Hypothese gefunden, die die Constraints und internen Filter passiert.",
                    module="HG"
                )

            # Aufgabe 1.5: Finale Output-Formatierung
            logger.debug("Aufgabe 1.5: Finale Output-Formatierung.")
            hypothese_id = f"HYP-{str(uuid.uuid4())[:8].upper()}"
            beweis = HGBeweis(
                herleitung="Hypothese wurde aus simuliertem VAE-Raum generiert und nach Novelty-Score ausgewählt.",
                filterProtokoll=filter_protocol,
                noveltyScore=novelty_score,
                constraintsPropagation={
                    "targetProfile": hg_input.constraints.get("targetProfile", []),
                    "precisionRequired": "MEDIUM"
                }
            )
            output = HGOutput(
                taskID=hg_input.taskID,
                status=TaskStatus.SUCCESS,
                hypotheseID=hypothese_id,
                hypothese=selected_hypothesis,
                beweis=beweis
            )
            logger.info(f"HG Agent hat Hypothese {output.hypotheseID} für Task {hg_input.taskID} generiert.")
            return output

        except Exception as e:
            logger.error(f"Fehler im HG Agent bei Task {hg_input.taskID}: {e}", exc_info=True)
            return ErrorResponse(
                taskID=hg_input.taskID,
                errorCode="HG999", # Allgemeiner Fehler
                errorMessage=f"Ein unerwarteter Fehler ist aufgetreten: {e}",
                module="HG"
            )