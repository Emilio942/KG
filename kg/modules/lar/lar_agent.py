import asyncio
import logging
from typing import Dict, List, Any, Optional
import uuid

from kg.utils.config import Config
from kg.schemas import HGInput, HGOutput, TaskStatus, SignalType
from kg.modules.hg.hg_agent import HGAgent

logger = logging.getLogger(__name__)

class LARAgent:
    """
    Lern- und Anpassungs-Regulator (LAR) Agent 2.0
    Main orchestrator using the new mathematical framework.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.hg_agent = HGAgent(self.config)
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all underlying agents and models"""
        if self.is_initialized:
            return
            
        logger.info("LAR Agent: Initialisiere mathematische Module...")
        await self.hg_agent.initialize()
        
        # In the future, we would initialize ISV and KD here too
        self.is_initialized = True
        logger.info("LAR Agent: Gesamtsystem bereit.")

    async def process_signal(self, signal_data: Dict[str, Any]) -> HGOutput:
        """
        Processes an incoming signal and triggers the discovery pipeline.
        """
        if not self.is_initialized:
            await self.initialize()
            
        task_id = signal_data.get("taskID", f"LAR-{uuid.uuid4().hex[:6]}")
        logger.info(f"LAR Agent: Verarbeite Signal für Task {task_id}")
        
        # Create input for the discovery engine
        hg_input = HGInput(
            taskID=task_id,
            signal=signal_data.get("signal", "CREATE_NEW"),
            constraints=signal_data.get("constraints", {})
        )
        
        # Execute the discovery via HG Agent 2.0
        result = await self.hg_agent.process_task(hg_input)
        
        # Logic for further processing (ISV, KD) would follow here
        # For now, we return the generated hypothesis
        return result

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("LAR Agent: Herunterfahren...")
