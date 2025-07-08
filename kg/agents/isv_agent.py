from kg.schemas import (HGOutput, ISVOutput, SimulationsErgebnis, Grundgeschmack, 
                        GrundgeschmackScore, AromaProfil, TexturProfil, ISVBeweis, 
                        ResourceLock, TaskStatus, SimulationMethod, ErrorResponse)
from typing import Union
import logging
import random
import uuid

logger = logging.getLogger(__name__)

class ISVAgent:
    """
    In-Silico-Validator Agent.
    Führt biophysikalische und chemoinformatische Analysen durch.
    """

    def __init__(self, config):
        self.config = config
        logger.info("ISV Agent initialisiert.")

    def _decide_simulation_method(self, hypothese: HGOutput) -> (SimulationMethod, str):
        """Entscheidet über die Simulationsmethode basierend auf Komplexität."""
        logger.debug("Aufgabe 2.1a: Simulationsmethoden-Entscheidung gestartet.")
        # Entscheidungskriterium: Anzahl der Komponenten
        if len(hypothese.hypothese.komponenten) > 2:
            logger.info("Entscheidung: Neuronale MD-Simulation (effizient). Hypothese zu komplex.")
            return SimulationMethod.NEURAL_MD, "HG_hypothesis_too_complex"
        else:
            logger.info("Entscheidung: Klassische MD-Simulation (präzise).")
            return SimulationMethod.CLASSIC_MD, "precision_required"

    def _acquire_resources(self, method: SimulationMethod) -> ResourceLock:
        """Simuliert die Akquise von Rechenressourcen."""
        logger.debug("Resource-Locking wird simuliert.")
        if method == SimulationMethod.CLASSIC_MD:
            resources = ["GPU_slot_1", "CPU_cores_8", "Memory_16GB"]
            duration = self.config.timeouts.ISV_mdSim_classic
        else:
            resources = ["CPU_cores_4", "Memory_4GB"]
            duration = self.config.timeouts.ISV_mdSim_neural
        
        lock_id = f"LOCK-{str(uuid.uuid4())[:8].upper()}"
        logger.info(f"Ressourcen für {method.value} gesperrt. Lock-ID: {lock_id}")
        return ResourceLock(lockID=lock_id, acquiredResources=resources, lockDuration=duration)

    async def process_task(self, hg_output: HGOutput) -> Union[ISVOutput, ErrorResponse]:
        """
        Verarbeitet eine einzelne Aufgabe zur In-Silico-Validierung.
        """
        logger.info(f"ISV Agent startet Task: {hg_output.taskID} für Hypothese: {hg_output.hypotheseID}")

        try:
            # Aufgabe 2.1: Input-Validierung (implizit durch Pydantic)
            logger.debug("Aufgabe 2.1: Input-Validierung erfolgreich.")

            # Aufgabe 2.1a: Simulationsmethoden-Entscheidung & Resource-Locking
            simulation_method, reason = self._decide_simulation_method(hg_output)
            resource_lock = self._acquire_resources(simulation_method)

            # Aufgabe 2.2 & 2.3: Adaptive Simulation & Prognose (simuliert)
            logger.debug(f"Aufgabe 2.2 & 2.3: Simulation ({simulation_method.value}) und Prognose werden ausgeführt.")
            # Die Ergebnisse werden hier noch zufällig generiert, könnten aber von der Methode abhängen
            simulations_ergebnis = SimulationsErgebnis(
                grundgeschmack=Grundgeschmack(
                    suess=GrundgeschmackScore(score=round(random.uniform(0,1),2), molekuel="Vanillin"),
                    sauer=GrundgeschmackScore(score=round(random.uniform(0,1),2), molekuel=None),
                    salzig=GrundgeschmackScore(score=round(random.uniform(0,1),2), molekuel=None),
                    bitter=GrundgeschmackScore(score=round(random.uniform(0,1),2), molekuel="Geosmin"),
                    umami=GrundgeschmackScore(score=round(random.uniform(0,1),2), molekuel=None)
                ),
                aromaProfil=AromaProfil(
                    ERDIG=round(random.uniform(0,1),2),
                    SUESSLICH=round(random.uniform(0,1),2),
                    HOLZIG=round(random.uniform(0,1),2),
                    FRUCHTIG=round(random.uniform(0,1),2)
                ),
                texturProfil=TexturProfil(
                    viskositaet=round(random.uniform(0,1),2),
                    kristallinitaet=round(random.uniform(0,1),2)
                )
            )

            confidence = 0.95 if simulation_method == SimulationMethod.CLASSIC_MD else 0.85

            # Aufgabe 2.4: Aggregation und finale Output-Formatierung
            logger.debug("Aufgabe 2.4: Aggregation und finale Output-Formatierung.")
            beweis = ISVBeweis(
                simulationMethod=simulation_method,
                confidenceLevel=confidence,
                mdSimID=f"MDSIM-{str(uuid.uuid4())[:8].upper()}",
                mdSimProtokoll=f"Simulation ({simulation_method.value}) erfolgreich konvergiert.",
                aromaModellVersion="GNN-v3.1.2",
                texturModellVersion="T-SIM-v1.4",
                resourceLock=resource_lock
            )

            output = ISVOutput(
                taskID=hg_output.taskID,
                subTaskID=f"{hg_output.taskID}-SIM-{simulation_method.value}",
                status=TaskStatus.SUCCESS,
                hypotheseID=hg_output.hypotheseID,
                simulationsErgebnis=simulations_ergebnis,
                beweis=beweis
            )
            logger.info(f"ISV Agent hat Simulation für Hypothese {hg_output.hypotheseID} abgeschlossen.")
            return output

        except Exception as e:
            logger.error(f"Fehler im ISV Agent bei Task {hg_output.taskID}: {e}", exc_info=True)
            return ErrorResponse(
                taskID=hg_output.taskID,
                hypotheseID=hg_output.hypotheseID,
                errorCode="ISV999", # Allgemeiner Fehler
                errorMessage=f"Ein unerwarteter Fehler ist aufgetreten: {e}",
                module="ISV"
            )