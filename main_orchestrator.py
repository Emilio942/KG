
import asyncio
import logging
from typing import Union

from kg.agents.hg_agent import HGAgent
from kg.agents.isv_agent import ISVAgent
from kg.agents.kd_agent import KDAgent
from kg.agents.lar_agent import LARAgent
from kg.schemas import (SystemConfig, HGInput, HGOutput, ISVOutput, KDOutput,
                        ErrorResponse, SignalType, TaskStatus)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainOrchestrator:
    """
    The main orchestrator for the KG system.
    Initializes all agents and runs the main processing loop.
    """

    def __init__(self):
        # In a real application, this would be loaded from a file (e.g., config.json)
        # For now, we create a default config.
        # Note: The full error code mapping needs to be added here.
        error_codes = {
            "HG001": {"message": "Keine Hypothese gefunden", "severity": "HIGH", "retryable": True, "suggestedAction": "Lockere Constraints"},
            "HG002": {"message": "Input ungültig", "severity": "CRITICAL", "retryable": False, "suggestedAction": "Überprüfe LAR-Output"},
            "ISV002": {"message": "MD-Simulation nicht konvergiert", "severity": "HIGH", "retryable": True, "suggestedAction": "Verwende alternative MD-Parameter"},
            # ... add all other error codes here
        }
        self.config = SystemConfig(error_codes=error_codes)
        
        logger.info("System Konfiguration geladen.")
        
        self.hg_agent = HGAgent(self.config)
        self.isv_agent = ISVAgent(self.config)
        self.kd_agent = KDAgent(self.config)
        self.lar_agent = LARAgent(self.config)
        
        logger.info("Alle Agenten wurden initialisiert.")

    async def run_cycle(self, hg_input: HGInput) -> Union[KDOutput, ErrorResponse]:
        """
        Runs a single, complete processing cycle from HG to KD.
        """
        logger.info(f"Starte Zyklus für Task: {hg_input.taskID}")

        # 1. Hypothesen-Generator
        hg_result = await self.hg_agent.process_task(hg_input)
        if hg_result.status == TaskStatus.FAILED:
            logger.error(f"HG Agent fehlgeschlagen: {hg_result.errorMessage}")
            return hg_result

        # 2. In-Silico-Validator
        isv_result = await self.isv_agent.process_task(hg_result)
        if isv_result.status == TaskStatus.FAILED:
            logger.error(f"ISV Agent fehlgeschlagen: {isv_result.errorMessage}")
            return isv_result

        # 3. Kritiker/Diskriminator
        kd_result = await self.kd_agent.process_task(isv_result)
        if kd_result.status == TaskStatus.FAILED:
            logger.error(f"KD Agent fehlgeschlagen: {kd_result.errorMessage}")
            return kd_result
            
        logger.info(f"Zyklus für Task {hg_input.taskID} erfolgreich abgeschlossen. Urteil: {kd_result.urteil.verdict.value}")
        return kd_result

    async def start_simulation(self, num_cycles: int = 5):
        """
        Starts the main simulation loop.
        """
        logger.info(f"Starte Simulation mit {num_cycles} Zyklen.")
        
        # Initialen Task erstellen
        current_task_id = "HG-20250708-001"
        next_hg_input = HGInput(
            taskID=current_task_id,
            signal=SignalType.CREATE_NEW,
            constraints=self.config.bootstrap.initialConstraints
        )

        for i in range(num_cycles):
            logger.info(f"--- Zyklus {i + 1}/{num_cycles} ---")
            
            # Den Zyklus ausführen
            final_result = await self.run_cycle(next_hg_input)

            # LAR verarbeitet das Ergebnis und bereitet den nächsten Zyklus vor
            lar_result = await self.lar_agent.process_task(final_result)

            if lar_result.status == TaskStatus.FAILED:
                logger.critical(f"LAR Agent fehlgeschlagen: {lar_result.errorMessage}. System wird angehalten.")
                break

            # Den Input für den nächsten Zyklus vorbereiten
            next_hg_input = HGInput(
                taskID=lar_result.nextTaskID,
                signal=SignalType.CREATE_NEW, # Dies könnte vom LAR intelligenter gesteuert werden
                constraints=self.config.bootstrap.initialConstraints # Ebenso
            )
            
            logger.info(f"Nächster Zyklus wird vorbereitet mit TaskID: {lar_result.nextTaskID}")
            await asyncio.sleep(1) # Kurze Pause zwischen den Zyklen

        logger.info("Simulation beendet.")

if __name__ == "__main__":
    orchestrator = MainOrchestrator()
    asyncio.run(orchestrator.start_simulation())
