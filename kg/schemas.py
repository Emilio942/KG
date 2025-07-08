# JSON-Schemas für alle KG-Module
# Definiert die exakten Input/Output-Formate

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# === Enums ===

class TaskStatus(str, Enum):
    """Status eines Tasks"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"

class SignalType(str, Enum):
    """Arten von Signalen für den HG"""
    CREATE_NEW = "CREATE_NEW"
    EXPLORE_NEARBY = "EXPLORE_NEARBY"
    CREATE_NEW_DIFFERENT_SECTOR = "CREATE_NEW_DIFFERENT_SECTOR"
    BOOTSTRAP_COMPLETE = "BOOTSTRAP_COMPLETE"

class Verdict(str, Enum):
    """Urteil des Kritikers"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class SimulationMethod(str, Enum):
    """MD-Simulationsmethoden"""
    CLASSIC_MD = "CLASSIC_MD"
    NEURAL_MD = "NEURAL_MD"

# === HG (Hypothesen-Generator) Schemas ===

class HGInput(BaseModel):
    """Input für den Hypothesen-Generator"""
    taskID: str = Field(..., description="Eindeutige Task-ID")
    signal: SignalType = Field(..., description="Art des Signals")
    constraints: Dict[str, Any] = Field(..., description="Constraints für die Generierung")

class MolekuelKomponente(BaseModel):
    """Molekülkomponente einer Hypothese"""
    name: str = Field(..., description="Name des Moleküls")
    konzentration: float = Field(..., ge=0, le=1, description="Konzentration zwischen 0 und 1")

class Hypothese(BaseModel):
    """Eine Geschmackshypothese"""
    komponenten: List[MolekuelKomponente] = Field(..., description="Liste der Molekülkomponenten")
    typ: str = Field(default="molekular", description="Typ der Hypothese")

class HGBeweis(BaseModel):
    """Beweis/Dokumentation für HG-Entscheidung"""
    herleitung: str = Field(..., description="Herleitung der Hypothese")
    filterProtokoll: str = Field(..., description="Protokoll der angewandten Filter")
    noveltyScore: float = Field(..., ge=0, le=1, description="Neuigkeitswert")
    constraintsPropagation: Dict[str, Any] = Field(..., description="Weitergegebene Constraints")

class HGOutput(BaseModel):
    """Output des Hypothesen-Generators"""
    taskID: str = Field(..., description="Task-ID")
    status: TaskStatus = Field(..., description="Status des Tasks")
    hypotheseID: Optional[str] = Field(None, description="ID der generierten Hypothese")
    hypothese: Optional[Hypothese] = Field(None, description="Die generierte Hypothese")
    beweis: Optional[HGBeweis] = Field(None, description="Beweis für die Entscheidung")
    errorCode: Optional[str] = Field(None, description="Fehlercode bei Fehlschlag")
    errorMessage: Optional[str] = Field(None, description="Fehlermeldung bei Fehlschlag")

# === ISV (In-Silico-Validator) Schemas ===

class GrundgeschmackScore(BaseModel):
    """Score für einen Grundgeschmack"""
    score: float = Field(..., ge=0, le=1, description="Score zwischen 0 und 1")
    molekuel: Optional[str] = Field(None, description="Verantwortliches Molekül")

class Grundgeschmack(BaseModel):
    """Grundgeschmack-Profil"""
    suess: GrundgeschmackScore
    sauer: GrundgeschmackScore
    salzig: GrundgeschmackScore
    bitter: GrundgeschmackScore
    umami: GrundgeschmackScore

class AromaProfil(BaseModel):
    """Aroma-Profil"""
    ERDIG: float = Field(..., ge=0, le=1)
    SUESSLICH: float = Field(..., ge=0, le=1)
    HOLZIG: float = Field(..., ge=0, le=1)
    FRUCHTIG: float = Field(..., ge=0, le=1)

class TexturProfil(BaseModel):
    """Textur-Profil"""
    viskositaet: float = Field(..., ge=0, le=1)
    kristallinitaet: float = Field(..., ge=0, le=1)

class ResourceLock(BaseModel):
    """Resource-Lock-Information"""
    lockID: str = Field(..., description="Lock-ID")
    acquiredResources: List[str] = Field(..., description="Erworbene Ressourcen")
    lockDuration: int = Field(..., description="Lock-Dauer in Sekunden")

class ISVBeweis(BaseModel):
    """Beweis für ISV-Simulation"""
    simulationMethod: SimulationMethod = Field(..., description="Verwendete Simulationsmethode")
    confidenceLevel: float = Field(..., ge=0, le=1, description="Konfidenz-Level")
    mdSimID: str = Field(..., description="MD-Simulation-ID")
    mdSimProtokoll: str = Field(..., description="Protokoll der MD-Simulation")
    aromaModellVersion: str = Field(..., description="Version des Aroma-Modells")
    texturModellVersion: str = Field(..., description="Version des Textur-Modells")
    resourceLock: ResourceLock = Field(..., description="Resource-Lock-Information")

class SimulationsErgebnis(BaseModel):
    """Ergebnis der Simulation"""
    grundgeschmack: Grundgeschmack
    aromaProfil: AromaProfil
    texturProfil: TexturProfil

class ISVOutput(BaseModel):
    """Output des In-Silico-Validators"""
    taskID: str = Field(..., description="Task-ID")
    subTaskID: Optional[str] = Field(None, description="Sub-Task-ID für spezifische Simulationen")
    status: TaskStatus = Field(..., description="Status des Tasks")
    hypotheseID: str = Field(..., description="Hypothese-ID")
    simulationsErgebnis: Optional[SimulationsErgebnis] = Field(None, description="Simulationsergebnis")
    beweis: Optional[ISVBeweis] = Field(None, description="Beweis für die Simulation")
    errorCode: Optional[str] = Field(None, description="Fehlercode bei Fehlschlag")
    errorMessage: Optional[str] = Field(None, description="Fehlermeldung bei Fehlschlag")

# === KD (Kritiker/Diskriminator) Schemas ===

class RegelErgebnis(BaseModel):
    """Ergebnis einer Regel-Anwendung"""
    pass_status: bool = Field(..., description="Ob die Regel erfolgreich war")
    score: float = Field(..., ge=0, le=1, description="Score der Regel")

class KDScoring(BaseModel):
    """Scoring-Ergebnisse des Kritikers"""
    geschmacksharmonie: float = Field(..., ge=0, le=1)
    aromaharmonie: float = Field(..., ge=0, le=1)
    texturkomplexitaet: float = Field(..., ge=0, le=1)
    bestaetigteNeuheit: float = Field(..., ge=0, le=1)

class KDUrteil(BaseModel):
    """Urteil des Kritikers"""
    verdict: Verdict = Field(..., description="Endgültiges Urteil")
    gesamtScore: float = Field(..., ge=0, le=1, description="Gesamtscore")
    scoring: KDScoring = Field(..., description="Detaillierte Scores")

class KDBeweis(BaseModel):
    """Beweis für KD-Entscheidung"""
    angewandteRegeln: List[str] = Field(..., description="Liste der angewandten Regeln")
    regelErgebnisse: Dict[str, RegelErgebnis] = Field(..., description="Ergebnisse aller Regeln")
    naechsterNachbarID: Optional[str] = Field(None, description="ID des nächsten Nachbarn")
    abstandZumNachbarn: Optional[float] = Field(None, description="Abstand zum nächsten Nachbarn")

class KDOutput(BaseModel):
    """Output des Kritikers"""
    taskID: str = Field(..., description="Task-ID")
    status: TaskStatus = Field(..., description="Status des Tasks")
    hypotheseID: str = Field(..., description="Hypothese-ID")
    urteil: Optional[KDUrteil] = Field(None, description="Urteil des Kritikers")
    beweis: Optional[KDBeweis] = Field(None, description="Beweis für die Entscheidung")
    errorCode: Optional[str] = Field(None, description="Fehlercode bei Fehlschlag")
    errorMessage: Optional[str] = Field(None, description="Fehlermeldung bei Fehlschlag")

# === LAR (Lern- und Anpassungs-Regulator) Schemas ===

class LARAction(BaseModel):
    """Dokumentiert eine vom LAR ausgeführte Aktion"""
    action_type: str = Field(..., description="Art der Aktion (z.B. 'PARAMETER_UPDATE', 'GRAPH_UPDATE')")
    target_module: str = Field(..., description="Zielmodul der Aktion (z.B. 'HG', 'Wissensgraph')")
    parameters: Dict[str, Any] = Field(..., description="Parameter der Aktion")

class LAROutput(BaseModel):
    """Output des LAR (interne Dokumentation des Zyklusabschlusses)"""
    taskID: str = Field(..., description="Abgeschlossene Task-ID")
    status: TaskStatus = Field(..., description="Status des Zyklus")
    rewardSignal: float = Field(..., description="Berechnetes Reward-Signal")
    actions: List[LARAction] = Field(..., description="Durchgeführte Aktionen")
    nextTaskID: Optional[str] = Field(None, description="ID des nächsten Tasks, falls gestartet")
    errorCode: Optional[str] = Field(None, description="Fehlercode bei Fehlschlag im LAR selbst")
    errorMessage: Optional[str] = Field(None, description="Fehlermeldung bei Fehlschlag im LAR")

# === Allgemeine Schemas ===

class ErrorOutput(BaseModel):
    """Standardisierter Fehleroutput für alle Module"""
    taskID: str = Field(..., description="Task-ID")
    status: TaskStatus = Field(default=TaskStatus.FAILED, description="Status (immer FAILED)")
    hypotheseID: Optional[str] = Field(None, description="Hypothese-ID, falls zutreffend")
    errorCode: str = Field(..., description="Eindeutiger Fehlercode")
    errorMessage: str = Field(..., description="Menschlich lesbare Fehlermeldung")
    module: str = Field(..., description="Modul, das den Fehler verursacht hat")
    timestamp: datetime = Field(default_factory=datetime.now, description="Zeitstempel des Fehlers")

# === System Konfigurations-Schemas ===

class TimeoutConfig(BaseModel):
    """Timeout-Konfiguration für alle Module"""
    HG_total: int = Field(300, description="Gesamttimeout für HG in Sekunden")
    HG_vae_generation: int = Field(60, description="Timeout für VAE-Kandidaten-Generierung")
    ISV_total: int = Field(7200, description="Gesamttimeout für ISV")
    ISV_mdSim_classic: int = Field(3600, description="Timeout für klassische MD-Simulation")
    ISV_mdSim_neural: int = Field(180, description="Timeout für neuronale MD-Simulation")
    ISV_aroma_prediction: int = Field(300, description="Timeout für Aroma-Prognose")
    KD_analysis: int = Field(180, description="Timeout für Kritiker-Analyse")
    LAR_update: int = Field(60, description="Timeout für LAR-Updates")

class ResourceLimits(BaseModel):
    """Ressourcen-Limits für das System"""
    ISV_parallelSims_classic: int = Field(3, description="Max parallele klassische MD-Sims")
    ISV_parallelSims_neural: int = Field(10, description="Max parallele neuronale MD-Sims")
    maxMemoryMB: int = Field(8192, description="Max RAM in MB")
    maxGPUSlots: int = Field(2, description="Max GPU-Slots")
    maxCPUCores: int = Field(8, description="Max CPU-Kerne")
    diskSpaceGB: int = Field(100, description="Max Festplattenspeicher in GB")

class ErrorCodeDetail(BaseModel):
    """Details für einen spezifischen Fehlercode."""
    message: str = Field(..., description="Standard-Fehlermeldung")
    severity: str = Field(..., description="Schweregrad (z.B. HIGH, CRITICAL)")
    retryable: bool = Field(..., description="Gibt an, ob der Task wiederholt werden kann")
    suggestedAction: str = Field(..., description="Vorgeschlagene Aktion zur Behebung")

class BootstrapConfig(BaseModel):
    """Konfiguration für den initialen Systemstart (Bootstrap)."""
    step1: str = Field("Lade Basis-Wissensgraph mit Seed-Hypothesen")
    step2: str = Field("Initialisiere VAE-Modell mit Trainingsdaten")
    step3: str = Field("Validiere alle Modell-Versionen")
    step4: str = Field("Erste LAR-Nachricht mit signal: 'BOOTSTRAP_COMPLETE'")
    initialConstraints: Dict[str, Any] = Field(default_factory=lambda: {"targetProfile": ["SÜSS", "FRUCHTIG"], "exclude": []})

class DeadlockPreventionConfig(BaseModel):
    """Konfiguration für Deadlock-Prävention."""
    lockHierarchy: List[str] = Field(default_factory=lambda: ["KD_read", "LAR_write"])
    maxWaitTime: int = Field(300, description="Maximale Wartezeit in Sekunden")
    deadlockDetection: bool = Field(True)

class TransactionSafetyConfig(BaseModel):
    """Konfiguration für Transaktionssicherheit."""
    atomicUpdates: bool = Field(True)
    rollbackOnFailure: bool = Field(True)
    checkpointInterval: str = Field("per_cycle")
    recoveryMechanism: str = Field("last_known_good_state")

class MoleculeValidationConfig(BaseModel):
    """Konfiguration für die Validierung von Molekülen."""
    whitelist: List[str] = Field(default_factory=lambda: ["organic", "aromatic", "aliphatic"])
    blacklist: List[str] = Field(default_factory=lambda: ["toxic", "radioactive"])
    validationRequired: bool = Field(True)

class BatchControlConfig(BaseModel):
    """Konfiguration für die Batch-Steuerung."""
    maxParallelCycles: int = Field(5, description="Maximale Anzahl paralleler Zyklen")
    queueManagement: bool = Field(True)
    loadBalancing: str = Field("round_robin")

class ModelCompatibilityConfig(BaseModel):
    """Konfiguration für die Modellkompatibilität."""
    neuralMD_supportedMolecules: List[str] = Field(default_factory=lambda: ["organic", "aromatic", "aliphatic"])
    preflightCheck: bool = Field(True)
    fallbackStrategy: str = Field("force_classic_MD")

class AdvancedSecurityConfig(BaseModel):
    """Sammlung von erweiterten Sicherheits- und Steuerungskonfigurationen."""
    deadlockPrevention: DeadlockPreventionConfig = Field(default_factory=DeadlockPreventionConfig)
    transactionSafety: TransactionSafetyConfig = Field(default_factory=TransactionSafetyConfig)
    moleculeValidation: MoleculeValidationConfig = Field(default_factory=MoleculeValidationConfig)
    batchControl: BatchControlConfig = Field(default_factory=BatchControlConfig)
    modelCompatibility: ModelCompatibilityConfig = Field(default_factory=ModelCompatibilityConfig)

class SystemConfig(BaseModel):
    """Zentrale System-Konfigurations-Klasse"""
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    resources: ResourceLimits = Field(default_factory=ResourceLimits)
    bootstrap: BootstrapConfig = Field(default_factory=BootstrapConfig)
    security: AdvancedSecurityConfig = Field(default_factory=AdvancedSecurityConfig)
    error_codes: Dict[str, ErrorCodeDetail] = Field(..., description="Definition aller System-Fehlercodes")
    logLevel: str = Field("INFO", description="Log-Level (z.B. DEBUG, INFO, WARNING, ERROR)")
    enableDetailedLogging: bool = Field(True, description="Aktiviert detaillierte Log-Ausgaben")

# Type Aliases für einfachere Verwendung
TaskRequest = HGInput
HGResult = HGOutput
ISVResult = ISVOutput
KDResult = KDOutput
LARResult = LAROutput
ErrorResponse = ErrorOutput
TaskConstraints = Dict[str, Any]