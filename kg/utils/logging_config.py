# Logging-Konfiguration für das KG-System
import logging
import json
from datetime import datetime
from typing import Dict, Any
from pythonjsonlogger import jsonlogger

class KGJsonFormatter(jsonlogger.JsonFormatter):
    """Benutzerdefinierter JSON-Formatter für KG-System"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Füge KG-spezifische Felder hinzu
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['system'] = 'KG'
        
        # Füge Modul-Information hinzu, falls verfügbar
        if hasattr(record, 'kg_module'):
            log_record['module'] = record.kg_module
        
        # Füge Task-ID hinzu, falls verfügbar
        if hasattr(record, 'task_id'):
            log_record['task_id'] = record.task_id
            
        # Füge Hypothese-ID hinzu, falls verfügbar
        if hasattr(record, 'hypothese_id'):
            log_record['hypothese_id'] = record.hypothese_id

def setup_logging(log_level: str = "INFO", detailed_logging: bool = True) -> logging.Logger:
    """
    Einrichtung des Logging-Systems für das KG-System
    
    Args:
        log_level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        detailed_logging: Ob detailliertes JSON-Logging aktiviert werden soll
    
    Returns:
        Logger-Instanz
    """
    
    # Hauptlogger erstellen
    logger = logging.getLogger('KG')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Entferne alle existierenden Handler
    logger.handlers.clear()
    
    if detailed_logging:
        # JSON-Formatter für strukturierte Logs
        json_formatter = KGJsonFormatter(
            '%(timestamp)s %(system)s %(module)s %(levelname)s %(message)s'
        )
        
        # Console Handler mit JSON-Format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)
        
        # File Handler für persistente Logs
        file_handler = logging.FileHandler('kg_system.log', encoding='utf-8')
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
        
    else:
        # Einfacher Formatter für bessere Lesbarkeit
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    return logger

class KGLogger:
    """
    Wrapper-Klasse für modulspezifisches Logging
    Erleichtert das Hinzufügen von KG-spezifischen Kontext-Informationen
    """
    
    def __init__(self, module_name: str, logger: logging.Logger = None):
        self.module_name = module_name
        self.logger = logger or logging.getLogger('KG')
        self.task_id = None
        self.hypothese_id = None
    
    def set_task_id(self, task_id: str):
        """Setze Task-ID für nachfolgende Log-Einträge"""
        self.task_id = task_id
    
    def set_hypothese_id(self, hypothese_id: str):
        """Setze Hypothese-ID für nachfolgende Log-Einträge"""
        self.hypothese_id = hypothese_id
    
    def clear_context(self):
        """Lösche Kontext-Informationen"""
        self.task_id = None
        self.hypothese_id = None
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Internes Logging mit Kontext"""
        extra = {
            'kg_module': self.module_name,  # Changed from 'module' to 'kg_module'
            **kwargs
        }
        
        if self.task_id:
            extra['task_id'] = self.task_id
        
        if self.hypothese_id:
            extra['hypothese_id'] = self.hypothese_id
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Debug-Level Logging"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info-Level Logging"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning-Level Logging"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error-Level Logging"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical-Level Logging"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def log_task_start(self, task_name: str, task_id: str = None):
        """Spezifisches Logging für Task-Start"""
        if task_id:
            self.set_task_id(task_id)
        
        self.info(f"Task '{task_name}' gestartet", 
                 task_name=task_name, 
                 event_type="task_start")
    
    def log_task_complete(self, task_name: str, duration: float = None):
        """Spezifisches Logging für Task-Abschluss"""
        extra = {
            'task_name': task_name,
            'event_type': 'task_complete'
        }
        
        if duration is not None:
            extra['duration_seconds'] = duration
        
        self.info(f"Task '{task_name}' abgeschlossen", **extra)
    
    def log_task_error(self, task_name: str, error_code: str, error_message: str):
        """Spezifisches Logging für Task-Fehler"""
        self.error(f"Task '{task_name}' fehlgeschlagen: {error_message}",
                  task_name=task_name,
                  error_code=error_code,
                  event_type="task_error")
    
    def log_hypothesis_generated(self, hypothese_id: str, komponenten_count: int):
        """Spezifisches Logging für Hypothesen-Generierung"""
        self.set_hypothese_id(hypothese_id)
        self.info(f"Hypothese generiert: {hypothese_id}",
                 komponenten_count=komponenten_count,
                 event_type="hypothesis_generated")
    
    def log_simulation_result(self, simulation_id: str, method: str, success: bool, duration: float = None):
        """Spezifisches Logging für Simulationsergebnisse"""
        extra = {
            'simulation_id': simulation_id,
            'simulation_method': method,
            'success': success,
            'event_type': 'simulation_complete'
        }
        
        if duration is not None:
            extra['duration_seconds'] = duration
        
        if success:
            self.info(f"Simulation erfolgreich: {simulation_id}", **extra)
        else:
            self.error(f"Simulation fehlgeschlagen: {simulation_id}", **extra)
    
    def log_verdict(self, verdict: str, score: float, hypothese_id: str = None):
        """Spezifisches Logging für Kritiker-Urteile"""
        if hypothese_id:
            self.set_hypothese_id(hypothese_id)
        
        self.info(f"Urteil gefällt: {verdict} (Score: {score})",
                 verdict=verdict,
                 score=score,
                 event_type="verdict_issued")

def get_logger(module_name: str = "KG") -> KGLogger:
    """
    Erstelle einen Logger für ein spezifisches Modul
    
    Args:
        module_name: Name des Moduls
        
    Returns:
        KGLogger-Instanz
    """
    return KGLogger(module_name)

# Convenience-Funktion für schnellen Zugriff
def get_basic_logger(name: str = "KG") -> logging.Logger:
    """Erstelle einen einfachen Logger ohne KG-spezifische Features"""
    return logging.getLogger(name)
