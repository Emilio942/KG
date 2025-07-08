from kg.schemas import (KDOutput, LAROutput, LARAction, TaskStatus, ErrorResponse, 
                        SignalType, ISVOutput, HGOutput)
from typing import Union
import logging
import datetime
import uuid

logger = logging.getLogger(__name__)

class LARAgent:
    """
    Lern- und Anpassungs-Regulator Agent.
    Verarbeitet das finale Urteil, generiert Rewards und steuert den nächsten Zyklus.
    """

    def __init__(self, config):
        self.config = config
        logger.info("LAR Agent initialisiert.")

    def _calculate_reward(self, final_output: Union[KDOutput, ErrorResponse]) -> float:
        """Definiert das Reward-Signal basierend auf dem finalen Output des Zyklus."""
        logger.debug("Aufgabe 4.1: Input-Analyse & Reward-Definition gestartet.")
        
        if isinstance(final_output, ErrorResponse):
            error_code = final_output.errorCode
            # Spezifische Bestrafungen basierend auf Fehlerquelle
            if error_code == "HG001": return -1.0  # Starke Bestrafung für fehlende Hypothese
            if error_code == "ISV002": return -0.8  # Bestrafung für nicht simulierbare Hypothese
            if error_code == "ISV004": return -0.6  # Bestrafung für Ressourcen-Limit
            if error_code == "ISV005": return -0.5  # Bestrafung für Timeout
            return -0.7 # Generische Bestrafung für andere Fehler

        # Belohnung/Bestrafung basierend auf KD-Urteil
        if final_output.urteil.verdict == "APPROVED":
            reward = final_output.urteil.gesamtScore
        else: # REJECTED
            # Der Score ist bereits niedrig, eine zusätzliche Bestrafung macht ihn stark negativ
            reward = final_output.urteil.gesamtScore - 0.5 
        
        # Berücksichtigung des ISV-Beweises (Fallback-Event)
        if isinstance(final_output, KDOutput) and final_output.beweis and hasattr(final_output.beweis, 'simulationMethod'):
             # This part is tricky as KDOutput doesn't directly contain ISV's beweis.
             # In a real system, the full context would be passed to LAR.
             # We simulate this by checking a hypothetical field.
             pass

        return round(reward, 2)

    def _determine_next_signal(self, reward: float) -> SignalType:
        """Bestimmt das Signal für den nächsten Zyklus basierend auf dem Reward."""
        if reward > 0.8:
            return SignalType.EXPLORE_NEARBY
        elif reward < -0.5:
            return SignalType.CREATE_NEW_DIFFERENT_SECTOR
        else:
            return SignalType.CREATE_NEW

    async def process_task(self, final_output: Union[KDOutput, ErrorResponse]) -> LAROutput:
        """
        Verarbeitet das finale Ergebnis eines Zyklus (von KD oder einem Fehler).
        """
        task_id = final_output.taskID
        logger.info(f"LAR Agent startet Verarbeitung für abgeschlossenen Zyklus: {task_id}")

        try:
            # Aufgabe 4.1: Reward berechnen
            reward = self._calculate_reward(final_output)
            logger.info(f"Reward für Task {task_id} berechnet: {reward}")

            actions = []
            # Aufgabe 4.2: Parameter-Update des HG (simuliert)
            hg_update_action = LARAction(
                action_type="PARAMETER_UPDATE",
                target_module="HG",
                parameters={"reward": reward, "learning_rate": 0.01, "hypotheseID": getattr(final_output, 'hypotheseID', None)}
            )
            actions.append(hg_update_action)
            logger.debug("Aktion für HG-Parameter-Update erstellt.")

            # Aufgabe 4.3: Update des Wissensgraphen (simuliert)
            if isinstance(final_output, KDOutput) and final_output.urteil.verdict == "APPROVED":
                wg_update_action = LARAction(
                    action_type="GRAPH_UPDATE_ADD_NODE",
                    target_module="Wissensgraph",
                    parameters={"hypotheseID": final_output.hypotheseID, "node_data": final_output.urteil.dict()}
                )
                actions.append(wg_update_action)
                logger.info(f"Wissensgraph-Update für approvte Hypothese {final_output.hypotheseID} wird erstellt.")

            # Aufgabe 4.4: Konsistenz-Validierung & Lock-Release (simuliert)
            logger.debug("Aufgabe 4.4: Konsistenz-Validierung & Lock-Release werden simuliert.")

            # Aufgabe 4.5: Initiierung des nächsten Zyklus
            logger.debug("Aufgabe 4.5: Nächster Zyklus wird initiiert.")
            # Erzeuge eine neue, eindeutige TaskID
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            next_task_id = f"HG-{timestamp}-{str(uuid.uuid4())[:4]}"
            next_signal = self._determine_next_signal(reward)
            logger.info(f"Nächster Task wird initiiert: {next_task_id} mit Signal: {next_signal.value}")

            output = LAROutput(
                taskID=task_id,
                status=TaskStatus.SUCCESS,
                rewardSignal=reward,
                actions=actions,
                nextTaskID=next_task_id
            )

            return output

        except Exception as e:
            logger.critical(f"Kritischer Fehler im LAR Agent bei Task {task_id}: {e}", exc_info=True)
            # Dies ist ein kritischer Fehler, der das System anhalten könnte
            return LAROutput(
                taskID=task_id,
                status=TaskStatus.FAILED,
                rewardSignal=0,
                actions=[],
                errorCode="LAR001",
                errorMessage=f"Update-Mechanismus fehlgeschlagen: {e}"
            )