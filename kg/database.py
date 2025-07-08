# KG Database Models
# SQLAlchemy-basierte Datenmodelle für das Knowledge Graph System

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from typing import Dict, List, Any
import uuid

Base = declarative_base()

class KGBaseModel(Base):
    """Basis-Modell für alle KG-Tabellen"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Hypothese(KGBaseModel):
    """Hypothesen-Tabelle"""
    __tablename__ = 'hypothesen'
    
    hypothese_id = Column(String(50), unique=True, nullable=False, index=True)
    task_id = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED, IN_PROGRESS
    
    # HG-spezifische Felder
    hg_novelty_score = Column(Float)
    hg_beweis = Column(JSON)
    komponenten = Column(JSON)  # Liste der Molekülkomponenten
    constraints = Column(JSON)  # Original-Constraints
    
    # ISV-spezifische Felder
    isv_simulation_method = Column(String(20))  # CLASSIC_MD, NEURAL_MD
    isv_confidence_level = Column(Float)
    isv_simulation_id = Column(String(100))
    grundgeschmack = Column(JSON)
    aroma_profil = Column(JSON)
    textur_profil = Column(JSON)
    
    # KD-spezifische Felder
    kd_verdict = Column(String(20))  # APPROVED, REJECTED
    kd_gesamt_score = Column(Float)
    kd_scoring_details = Column(JSON)
    kd_applied_rules = Column(JSON)
    
    # LAR-spezifische Felder
    lar_reward_signal = Column(Float)
    lar_cycle_number = Column(Integer)
    
    # Beziehungen
    komponenten_details = relationship("MolekuelKomponente", back_populates="hypothese")
    bewertungen = relationship("HarmonieBewertung", back_populates="hypothese")

class MolekuelKomponente(KGBaseModel):
    """Molekül-Komponenten einer Hypothese"""
    __tablename__ = 'molekuel_komponenten'
    
    hypothese_id = Column(String(50), ForeignKey('hypothesen.hypothese_id'), nullable=False)
    molekuel_name = Column(String(100), nullable=False)
    konzentration = Column(Float, nullable=False)
    molekuel_typ = Column(String(50))  # organic, aromatic, aliphatic
    
    # Beziehungen
    hypothese = relationship("Hypothese", back_populates="komponenten_details")

class WissensGraphKnoten(KGBaseModel):
    """Knoten im Wissensgraph"""
    __tablename__ = 'wissensgraph_knoten'
    
    knoten_id = Column(String(100), unique=True, nullable=False)
    knoten_typ = Column(String(50), nullable=False)  # hypothese, molekuel, geschmack, aroma
    name = Column(String(200), nullable=False)
    eigenschaften = Column(JSON)
    embedding_vector = Column(JSON)  # Für Ähnlichkeitsberechnungen
    
    # Beziehungen
    ausgehende_kanten = relationship("WissensGraphKante", foreign_keys="WissensGraphKante.von_knoten_id")
    eingehende_kanten = relationship("WissensGraphKante", foreign_keys="WissensGraphKante.zu_knoten_id")

class WissensGraphKante(KGBaseModel):
    """Kanten im Wissensgraph"""
    __tablename__ = 'wissensgraph_kanten'
    
    von_knoten_id = Column(String(100), ForeignKey('wissensgraph_knoten.knoten_id'), nullable=False)
    zu_knoten_id = Column(String(100), ForeignKey('wissensgraph_knoten.knoten_id'), nullable=False)
    beziehungs_typ = Column(String(100), nullable=False)  # contains, harmonizes_with, similar_to
    gewichtung = Column(Float, default=1.0)
    eigenschaften = Column(JSON)

class HarmonieBewertung(KGBaseModel):
    """Bewertungen der Harmonieregeln"""
    __tablename__ = 'harmonie_bewertungen'
    
    hypothese_id = Column(String(50), ForeignKey('hypothesen.hypothese_id'), nullable=False)
    regel_id = Column(String(100), nullable=False)
    regel_name = Column(String(200), nullable=False)
    passed = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    grund = Column(Text)
    
    # Beziehungen
    hypothese = relationship("Hypothese", back_populates="bewertungen")

class SimulationProtokoll(KGBaseModel):
    """Protokoll der MD-Simulationen"""
    __tablename__ = 'simulation_protokolle'
    
    simulation_id = Column(String(100), unique=True, nullable=False)
    hypothese_id = Column(String(50), ForeignKey('hypothesen.hypothese_id'), nullable=False)
    simulation_method = Column(String(20), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Ressourcen-Information
    cpu_cores_used = Column(Integer)
    memory_mb_used = Column(Integer)
    gpu_slots_used = Column(Integer)
    
    # Simulationsergebnisse
    converged = Column(Boolean)
    confidence_level = Column(Float)
    raw_output = Column(JSON)
    fehler_meldung = Column(Text)

class SystemMetrik(KGBaseModel):
    """System-Performance-Metriken"""
    __tablename__ = 'system_metriken'
    
    metrik_name = Column(String(100), nullable=False)
    metrik_wert = Column(Float, nullable=False)
    einheit = Column(String(50))
    modul = Column(String(10))  # HG, ISV, KD, LAR
    timestamp = Column(DateTime, default=datetime.utcnow)

class ResourceLock(KGBaseModel):
    """Aktive Ressourcen-Locks"""
    __tablename__ = 'resource_locks'
    
    lock_id = Column(String(100), unique=True, nullable=False)
    resource_type = Column(String(50), nullable=False)  # CPU, Memory, GPU, Database
    acquired_by = Column(String(100), nullable=False)  # Module oder Task-ID
    acquired_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    released = Column(Boolean, default=False)
    released_at = Column(DateTime)

class KonfigurationParameter(KGBaseModel):
    """System-Konfiguration in der Datenbank"""
    __tablename__ = 'konfiguration_parameter'
    
    parameter_name = Column(String(100), unique=True, nullable=False)
    parameter_wert = Column(String(500), nullable=False)
    parameter_typ = Column(String(20), nullable=False)  # string, int, float, bool, json
    modul = Column(String(10))  # HG, ISV, KD, LAR, SYSTEM
    beschreibung = Column(Text)

# === Database Engine und Session Management ===

class DatabaseManager:
    """Datenbank-Manager für das KG-System"""
    
    def __init__(self, database_url: str = "sqlite:///kg_system.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
    
    def initialize_database(self):
        """Initialisiere Datenbank und erstelle Tabellen"""
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True
        )
        
        # Erstelle alle Tabellen
        Base.metadata.create_all(bind=self.engine)
        
        # Session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        print(f"Datenbank initialisiert: {self.database_url}")
    
    def get_session(self):
        """Hole eine neue Datenbank-Session"""
        if not self.SessionLocal:
            self.initialize_database()
        
        return self.SessionLocal()
    
    def close(self):
        """Schließe Datenbankverbindung"""
        if self.engine:
            self.engine.dispose()

# === Repository-Pattern für Datenbank-Operationen ===

class HypotheseRepository:
    """Repository für Hypothesen-Operationen"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_hypothese(self, hypothese_data: Dict[str, Any]) -> Hypothese:
        """Erstelle neue Hypothese"""
        hypothese = Hypothese(
            hypothese_id=hypothese_data['hypotheseID'],
            task_id=hypothese_data['taskID'],
            status=hypothese_data['status'],
            hg_novelty_score=hypothese_data.get('novelty_score'),
            komponenten=hypothese_data.get('komponenten'),
            constraints=hypothese_data.get('constraints')
        )
        
        self.db.add(hypothese)
        self.db.commit()
        self.db.refresh(hypothese)
        
        return hypothese
    
    def update_isv_results(self, hypothese_id: str, isv_data: Dict[str, Any]):
        """Update ISV-Ergebnisse"""
        hypothese = self.db.query(Hypothese).filter(
            Hypothese.hypothese_id == hypothese_id
        ).first()
        
        if hypothese:
            hypothese.isv_simulation_method = isv_data.get('simulation_method')
            hypothese.isv_confidence_level = isv_data.get('confidence_level')
            hypothese.isv_simulation_id = isv_data.get('simulation_id')
            hypothese.grundgeschmack = isv_data.get('grundgeschmack')
            hypothese.aroma_profil = isv_data.get('aroma_profil')
            hypothese.textur_profil = isv_data.get('textur_profil')
            
            self.db.commit()
            self.db.refresh(hypothese)
        
        return hypothese
    
    def update_kd_results(self, hypothese_id: str, kd_data: Dict[str, Any]):
        """Update KD-Ergebnisse"""
        hypothese = self.db.query(Hypothese).filter(
            Hypothese.hypothese_id == hypothese_id
        ).first()
        
        if hypothese:
            hypothese.kd_verdict = kd_data.get('verdict')
            hypothese.kd_gesamt_score = kd_data.get('gesamt_score')
            hypothese.kd_scoring_details = kd_data.get('scoring_details')
            hypothese.kd_applied_rules = kd_data.get('applied_rules')
            
            self.db.commit()
            self.db.refresh(hypothese)
        
        return hypothese
    
    def update_lar_results(self, hypothese_id: str, lar_data: Dict[str, Any]):
        """Update LAR-Ergebnisse"""
        hypothese = self.db.query(Hypothese).filter(
            Hypothese.hypothese_id == hypothese_id
        ).first()
        
        if hypothese:
            hypothese.lar_reward_signal = lar_data.get('reward_signal')
            hypothese.lar_cycle_number = lar_data.get('cycle_number')
            
            self.db.commit()
            self.db.refresh(hypothese)
        
        return hypothese
    
    def get_approved_hypotheses(self) -> List[Hypothese]:
        """Hole alle genehmigten Hypothesen"""
        return self.db.query(Hypothese).filter(
            Hypothese.kd_verdict == "APPROVED"
        ).all()
    
    def get_hypothese_by_id(self, hypothese_id: str) -> Hypothese:
        """Hole Hypothese nach ID"""
        return self.db.query(Hypothese).filter(
            Hypothese.hypothese_id == hypothese_id
        ).first()

class WissensGraphRepository:
    """Repository für Wissensgraph-Operationen"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def add_approved_hypothese_to_graph(self, hypothese: Hypothese):
        """Füge genehmigte Hypothese zum Wissensgraphen hinzu"""
        # Erstelle Knoten für die Hypothese
        hypothese_knoten = WissensGraphKnoten(
            knoten_id=f"HYP_{hypothese.hypothese_id}",
            knoten_typ="hypothese",
            name=f"Hypothese {hypothese.hypothese_id}",
            eigenschaften={
                "novelty_score": hypothese.hg_novelty_score,
                "gesamt_score": hypothese.kd_gesamt_score,
                "grundgeschmack": hypothese.grundgeschmack,
                "aroma_profil": hypothese.aroma_profil
            }
        )
        
        self.db.add(hypothese_knoten)
        
        # Erstelle Knoten und Kanten für Moleküle
        if hypothese.komponenten:
            for komp in hypothese.komponenten:
                molekuel_knoten_id = f"MOL_{komp['name']}"
                
                # Prüfe ob Molekül-Knoten bereits existiert
                existing_mol = self.db.query(WissensGraphKnoten).filter(
                    WissensGraphKnoten.knoten_id == molekuel_knoten_id
                ).first()
                
                if not existing_mol:
                    molekuel_knoten = WissensGraphKnoten(
                        knoten_id=molekuel_knoten_id,
                        knoten_typ="molekuel",
                        name=komp['name'],
                        eigenschaften={"typ": "molekular"}
                    )
                    self.db.add(molekuel_knoten)
                
                # Erstelle Kante zwischen Hypothese und Molekül
                kante = WissensGraphKante(
                    von_knoten_id=f"HYP_{hypothese.hypothese_id}",
                    zu_knoten_id=molekuel_knoten_id,
                    beziehungs_typ="contains",
                    gewichtung=komp['konzentration'],
                    eigenschaften={"konzentration": komp['konzentration']}
                )
                self.db.add(kante)
        
        self.db.commit()
    
    def find_similar_hypotheses(self, target_profil: Dict[str, float], limit: int = 5) -> List[Dict]:
        """Finde ähnliche Hypothesen basierend auf Profil"""
        # Vereinfachte Ähnlichkeitssuche
        # In der Praxis würde hier ein Embedding-basierter Ansatz verwendet
        
        hypothesen = self.db.query(Hypothese).filter(
            Hypothese.kd_verdict == "APPROVED"
        ).all()
        
        similarities = []
        for hyp in hypothesen:
            if hyp.aroma_profil:
                # Berechne Ähnlichkeit (Cosinus-Ähnlichkeit vereinfacht)
                similarity = self._calculate_profile_similarity(target_profil, hyp.aroma_profil)
                similarities.append({
                    "hypothese_id": hyp.hypothese_id,
                    "similarity": similarity,
                    "aroma_profil": hyp.aroma_profil
                })
        
        # Sortiere nach Ähnlichkeit
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:limit]
    
    def _calculate_profile_similarity(self, prof1: Dict, prof2: Dict) -> float:
        """Berechne Ähnlichkeit zwischen zwei Aroma-Profilen"""
        if not prof1 or not prof2:
            return 0.0
        
        # Vereinfachte Berechnung
        common_keys = set(prof1.keys()) & set(prof2.keys())
        if not common_keys:
            return 0.0
        
        total_diff = sum(abs(prof1[key] - prof2[key]) for key in common_keys)
        max_possible_diff = len(common_keys) * 2.0  # Max Differenz wenn ein Profil 0, das andere 1 hat
        
        similarity = 1.0 - (total_diff / max_possible_diff)
        return max(0.0, similarity)

# === Initialisierungs-Hilfsfunktionen ===

def setup_database(database_url: str = "sqlite:///kg_system.db") -> DatabaseManager:
    """Setup und Initialisierung der Datenbank"""
    db_manager = DatabaseManager(database_url)
    db_manager.initialize_database()
    
    # Füge Standard-Konfiguration hinzu
    with db_manager.get_session() as session:
        _add_default_configuration(session)
    
    return db_manager

def _add_default_configuration(session):
    """Füge Standard-Konfigurationsparameter hinzu"""
    default_configs = [
        ("HG_total_timeout", "300", "int", "HG", "Gesamttimeout für HG in Sekunden"),
        ("ISV_mdSim_classic_timeout", "3600", "int", "ISV", "Timeout für klassische MD-Simulation"),
        ("ISV_mdSim_neural_timeout", "180", "int", "ISV", "Timeout für neuronale MD-Simulation"),
        ("KD_approval_threshold", "0.75", "float", "KD", "Mindest-Score für Approval"),
        ("LAR_max_parallel_cycles", "5", "int", "LAR", "Maximum parallele Zyklen"),
        ("SYSTEM_log_level", "INFO", "string", "SYSTEM", "Log-Level des Systems")
    ]
    
    for name, value, typ, modul, beschreibung in default_configs:
        existing = session.query(KonfigurationParameter).filter(
            KonfigurationParameter.parameter_name == name
        ).first()
        
        if not existing:
            config = KonfigurationParameter(
                parameter_name=name,
                parameter_wert=value,
                parameter_typ=typ,
                modul=modul,
                beschreibung=beschreibung
            )
            session.add(config)
    
    session.commit()

if __name__ == "__main__":
    # Test der Datenbank-Funktionalität
    db_manager = setup_database()
    
    with db_manager.get_session() as session:
        repo = HypotheseRepository(session)
        
        # Test: Erstelle eine Test-Hypothese
        test_data = {
            'hypotheseID': 'TEST-HYP-001',
            'taskID': 'TEST-TASK-001',
            'status': 'SUCCESS',
            'novelty_score': 0.85,
            'komponenten': [
                {'name': 'Vanillin', 'konzentration': 0.2},
                {'name': 'Geosmin', 'konzentration': 0.01}
            ],
            'constraints': {'targetProfile': ['SÜSS', 'ERDIG']}
        }
        
        hypothese = repo.create_hypothese(test_data)
        print(f"Test-Hypothese erstellt: {hypothese.hypothese_id}")
    
    db_manager.close()
    print("Datenbank-Test erfolgreich!")

# === Utility Functions for API Integration ===

# Global database manager instance
_db_manager = None

def get_db_manager():
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def get_db_session():
    """Get a database session for API use"""
    return get_db_manager().get_session()

# === Backwards Compatibility Aliases ===
Hypothesis = Hypothese
Validation = SimulationProtokoll
KnowledgeEntry = WissensGraphKnoten
LearningAction = HarmonieBewertung
