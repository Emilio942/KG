# KG System - Geschmackshypothesen-Generator
# Hauptinitialisierung und Systemstart

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from kg.modules.lar.lar_agent import LARAgent
from kg.utils.config import Config
from kg.utils.logging_config import setup_logging

class KGSystem:
    """
    Hauptsystem-Klasse für das Geschmackshypothesen-Generator System
    Koordiniert alle vier Module: HG, ISV, KD, LAR
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config = Config(config_path)
        self.logger = setup_logging()
        self.lar_agent = LARAgent(self.config)
        self.is_running = False
        
    async def start(self):
        """Startet das KG-System"""
        self.logger.info("=== KG System wird gestartet ===")
        
        # Bootstrap-Prozess
        await self._bootstrap()
        
        # Hauptschleife starten
        self.is_running = True
        await self._main_loop()
        
    async def _bootstrap(self):
        """Bootstrap-Prozess für Systemstart"""
        self.logger.info("Bootstrap-Prozess gestartet...")
        
        # Schritt 1: Basis-Wissensgraph laden
        await self.lar_agent.load_base_knowledge_graph()
        
        # Schritt 2: Alle Module initialisieren
        await self.lar_agent.initialize_all_modules()
        
        # Schritt 3: Erste LAR-Nachricht senden
        bootstrap_signal = {
            "taskID": f"BOOTSTRAP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-001",
            "signal": "BOOTSTRAP_COMPLETE",
            "constraints": {
                "targetProfile": ["SÜSS", "FRUCHTIG"],
                "exclude": []
            }
        }
        
        await self.lar_agent.send_first_signal(bootstrap_signal)
        self.logger.info("Bootstrap-Prozess abgeschlossen")
        
    async def _main_loop(self):
        """Hauptschleife des Systems"""
        self.logger.info("Hauptschleife gestartet...")
        
        while self.is_running:
            try:
                # LAR-Agent übernimmt die Hauptsteuerung
                await self.lar_agent.process_cycle()
                
                # Kurze Pause zwischen Zyklen
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Shutdown-Signal erhalten...")
                await self.shutdown()
                break
            except Exception as e:
                self.logger.error(f"Fehler in der Hauptschleife: {e}")
                await asyncio.sleep(5)  # Warte 5 Sekunden bei Fehlern
                
    async def shutdown(self):
        """Sauberes Herunterfahren des Systems"""
        self.logger.info("System wird heruntergefahren...")
        self.is_running = False
        
        # Alle Module herunterfahren
        await self.lar_agent.shutdown()
        
        self.logger.info("System erfolgreich heruntergefahren")

async def main():
    """Haupteinstiegspunkt"""
    system = KGSystem()
    await system.start()

if __name__ == "__main__":
    asyncio.run(main())
