# Konfiguration für das KG-System
import json
import os
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class Config:
    """Konfigurationsklasse für das KG-System"""
    
    # Timeouts (in Sekunden)
    HG_total_timeout: int = 300
    HG_vae_generation_timeout: int = 60
    ISV_total_timeout: int = 7200
    ISV_mdSim_classic_timeout: int = 3600
    ISV_mdSim_neural_timeout: int = 180
    ISV_aroma_prediction_timeout: int = 300
    KD_analysis_timeout: int = 180
    LAR_update_timeout: int = 60
    
    # Ressourcen-Limits
    ISV_parallelSims_classic: int = 3
    ISV_parallelSims_neural: int = 10
    maxMemoryMB: int = 8192
    maxGPUSlots: int = 2
    maxCPUCores: int = 8
    diskSpaceGB: int = 100
    
    # System-Einstellungen
    maxParallelCycles: int = 5
    logLevel: str = "INFO"
    enableDetailedLogging: bool = True
    
    # Datenbankeinstellungen
    knowledge_graph_db: str = "kg_database.db"
    redis_host: str = "localhost"
    redis_port: int = 6379
    
    # Modell-Pfade
    vae_model_path: str = "models/vae_model.pkl"
    neural_md_model_path: str = "models/neural_md_model.pkl"
    aroma_model_path: str = "models/aroma_model.pkl"
    texture_model_path: str = "models/texture_model.pkl"
    
    def __init__(self, config_file: str = None):
        """Initialisierung der Konfiguration"""
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file: str):
        """Lade Konfiguration aus Datei"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Setze Attribute aus der Konfigurationsdatei
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warnung: Konnte Konfigurationsdatei nicht laden: {e}")
            print("Verwende Standard-Konfiguration")
    
    def save_to_file(self, config_file: str):
        """Speichere Konfiguration in Datei"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Konfiguration: {e}")
    
    def get_timeout(self, module: str, task: str = None) -> int:
        """Hole Timeout für spezifisches Modul/Task"""
        if task:
            attr_name = f"{module}_{task}_timeout"
        else:
            attr_name = f"{module}_total_timeout"
        
        return getattr(self, attr_name, 300)  # Standard: 5 Minuten
    
    def get_resource_limit(self, resource: str) -> int:
        """Hole Ressourcen-Limit"""
        return getattr(self, resource, 1)

# Globale Konfigurationsinstanz
_config_instance = None

def get_config() -> Config:
    """Singleton-Zugriff auf die Konfiguration"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def set_config(config: Config):
    """Setze globale Konfiguration"""
    global _config_instance
    _config_instance = config
