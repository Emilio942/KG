# KG-System Web API
# FastAPI-basierte REST-API für das Geschmackshypothesen-System

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import uuid
import json

# KG-System Imports
from kg.modules.lar.lar_agent import LARAgent
from kg.utils.config import Config
from kg.utils.logging_config import setup_logging, KGLogger
from kg.schemas import HGInput, SignalType, TaskStatus

# Import authentication and analytics
from kg.auth import (
    auth_service, get_current_user, require_admin, require_user,
    rate_limit_dependency, User, AuthenticationService
)
from kg.analytics import analytics_engine

# Enhanced Validation Imports
from enhanced_validation import (
    EnhancedHypothesisRequest, ValidationLevel, RateLimiter,
    SecurityValidator, ValidationReport
)

# === Enhanced Rate Limiter Instance ===
rate_limiter = RateLimiter()

# === Pydantic Models für API ===

class HypotheseAnfrage(BaseModel):
    """Anfrage für neue Hypothese"""
    targetProfile: List[str] = Field(..., description="Gewünschte Geschmacksprofile")
    exclude: List[str] = Field(default=[], description="Auszuschließende Moleküle")
    signal: str = Field(default="CREATE_NEW", description="Art des Signals")
    priority: str = Field(default="NORMAL", description="Priorität der Anfrage")

class HypotheseResponse(BaseModel):
    """Response für Hypothese"""
    hypotheseID: str
    status: str
    komponenten: List[Dict[str, Any]]
    noveltyScore: float
    taskID: str
    timestamp: datetime

class SimulationResponse(BaseModel):
    """Response für Simulation"""
    simulationID: str
    method: str
    confidence: float
    grundgeschmack: Dict[str, Any]
    aromaProfil: Dict[str, float]
    texturProfil: Dict[str, float]
    duration: float

class BewertungResponse(BaseModel):
    """Response für Bewertung"""
    verdict: str
    gesamtScore: float
    geschmacksharmonie: float
    aromaharmonie: float
    bestaetigteNeuheit: float
    angewandteRegeln: List[str]

class VollstaendigeHypothese(BaseModel):
    """Vollständige Hypothese mit allen Ergebnissen"""
    hypothese: HypotheseResponse
    simulation: Optional[SimulationResponse] = None
    bewertung: Optional[BewertungResponse] = None
    status: str
    fehlercode: Optional[str] = None
    fehlermeldung: Optional[str] = None

class SystemStatus(BaseModel):
    """System-Status"""
    isRunning: bool
    activeModules: List[str]
    activeCycles: int
    totalProcessed: int
    successRate: float
    averageProcessingTime: float

class MetrikResponse(BaseModel):
    """Performance-Metriken"""
    module: str
    metrikName: str
    wert: float
    einheit: str
    timestamp: datetime

# Authentication endpoints
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Dict[str, Any]

class RefreshRequest(BaseModel):
    refresh_token: str

# === FastAPI App Setup ===

app = FastAPI(
    title="KG-System API",
    description="API für das Geschmackshypothesen-Generator System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion spezifischer konfigurieren
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Globale Variablen ===

kg_system = None
config = None
logger = None
active_tasks = {}  # Task-ID -> Task-Status
system_metrics = {
    "total_processed": 0,
    "successful": 0,
    "failed": 0,
    "start_time": datetime.now()
}

# === Dependency Functions ===

async def get_kg_system():
    """Dependency: Hole KG-System Instanz"""
    global kg_system
    if not kg_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KG-System ist nicht initialisiert"
        )
    return kg_system

async def validate_target_profile(target_profile: List[str]):
    """Validiere Target-Profile"""
    valid_profiles = ["ERDIG", "SÜSS", "SAUER", "SALZIG", "BITTER", "UMAMI", "FRUCHTIG", "HOLZIG"]
    
    for profile in target_profile:
        if profile not in valid_profiles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ungültiges Target-Profile: {profile}. Erlaubt: {valid_profiles}"
            )

# === API Endpoints ===

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root-Endpoint"""
    return {
        "message": "KG-System API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health-Check Endpoint"""
    global kg_system, system_metrics
    
    is_healthy = kg_system is not None and kg_system.is_initialized
    
    uptime = (datetime.now() - system_metrics["start_time"]).total_seconds()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "uptime_seconds": uptime,
        "kg_system_initialized": is_healthy,
        "active_tasks": len(active_tasks),
        "timestamp": datetime.now()
    }

@app.get("/status", response_model=SystemStatus)
async def get_system_status(kg_system=Depends(get_kg_system)):
    """Hole System-Status"""
    global system_metrics, active_tasks
    
    total = system_metrics["total_processed"]
    success_rate = (system_metrics["successful"] / total * 100) if total > 0 else 0
    
    avg_time = 2.5  # Mock - würde aus echten Metriken berechnet
    
    return SystemStatus(
        isRunning=kg_system.is_running,
        activeModules=["HG", "ISV", "KD", "LAR"],
        activeCycles=len(active_tasks),
        totalProcessed=total,
        successRate=success_rate,
        averageProcessingTime=avg_time
    )

@app.post("/hypothese/erstellen", response_model=Dict[str, str])
async def erstelle_hypothese(
    anfrage: HypotheseAnfrage,
    background_tasks: BackgroundTasks,
    kg_system=Depends(get_kg_system),
    user: User = Depends(get_current_user)
):
    """Erstelle neue Geschmackshypothese mit Enhanced Validation"""
    
    # === Enhanced Validation ===
    try:
        # Rate Limiting Check
        client_id = user.id if user else "anonymous"
        if not rate_limiter.check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Create Enhanced Request for Validation
        enhanced_request = EnhancedHypothesisRequest(
            targetProfile=anfrage.targetProfile,
            exclude=anfrage.exclude,
            signal=anfrage.signal,
            priority=anfrage.priority,
            userID=user.id if user else None,
            timestamp=datetime.now()
        )
        
        # Security Validation
        security_validator = SecurityValidator()
        security_report = security_validator.validate_request(enhanced_request)
        
        if not security_report.is_valid:
            logger.warning(f"Security validation failed: {security_report.errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security validation failed: {'; '.join(security_report.errors)}"
            )
        
        # Validate Target Profile (existing validation)
        await validate_target_profile(anfrage.targetProfile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal validation error"
        )
    
    # Generiere Task-ID
    task_id = f"API-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Erstelle Signal für KG-System
    signal = {
        "taskID": task_id,
        "signal": anfrage.signal,
        "constraints": {
            "targetProfile": anfrage.targetProfile,
            "exclude": anfrage.exclude
        },
        "userID": user.id if user else None,
        "priority": anfrage.priority
    }
    
    # Starte Verarbeitung im Hintergrund
    background_tasks.add_task(process_hypothese_request, task_id, signal)
    
    # Registriere Task
    active_tasks[task_id] = {
        "status": "IN_PROGRESS",
        "created_at": datetime.now(),
        "signal": signal,
        "user_id": user.id if user else None
    }
    
    logger.info(f"Neue Hypothese-Anfrage: {task_id}")
    
    return {
        "message": "Hypothese-Erstellung gestartet",
        "taskID": task_id,
        "status": "IN_PROGRESS",
        "polling_url": f"/hypothese/status/{task_id}"
    }

@app.get("/hypothese/status/{task_id}", response_model=Dict[str, Any])
async def get_hypothese_status(task_id: str):
    """Hole Status einer Hypothese-Anfrage"""
    
    if task_id not in active_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} nicht gefunden"
        )
    
    task_info = active_tasks[task_id]
    
    return {
        "taskID": task_id,
        "status": task_info["status"],
        "created_at": task_info["created_at"],
        "result": task_info.get("result"),
        "error": task_info.get("error")
    }

@app.get("/hypothese/ergebnis/{task_id}", response_model=VollstaendigeHypothese)
async def get_hypothese_ergebnis(task_id: str):
    """Hole vollständiges Ergebnis einer Hypothese"""
    
    if task_id not in active_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} nicht gefunden"
        )
    
    task_info = active_tasks[task_id]
    
    if task_info["status"] != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Task noch nicht abgeschlossen. Status: {task_info['status']}"
        )
    
    # Hole Ergebnis
    result = task_info.get("result")
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ergebnis nicht verfügbar"
        )
    
    return result

@app.get("/hypothesen/aktive", response_model=List[Dict[str, Any]])
async def get_aktive_hypothesen():
    """Hole alle aktiven Hypothesen-Anfragen"""
    
    aktive = []
    for task_id, task_info in active_tasks.items():
        aktive.append({
            "taskID": task_id,
            "status": task_info["status"],
            "created_at": task_info["created_at"],
            "signal": task_info["signal"]
        })
    
    return aktive

@app.get("/metriken", response_model=List[MetrikResponse])
async def get_system_metriken():
    """Hole System-Performance-Metriken"""
    
    metriken = []
    
    # Mock-Metriken
    modules = ["HG", "ISV", "KD", "LAR"]
    for module in modules:
        metriken.extend([
            MetrikResponse(
                module=module,
                metrikName="durchschnittliche_verarbeitungszeit",
                wert=1.5 if module != "ISV" else 3.2,
                einheit="sekunden",
                timestamp=datetime.now()
            ),
            MetrikResponse(
                module=module,
                metrikName="erfolgsrate",
                wert=95.0 if module != "ISV" else 88.0,
                einheit="prozent",
                timestamp=datetime.now()
            )
        ])
    
    return metriken

@app.delete("/hypothese/{task_id}")
async def cancel_hypothese(task_id: str):
    """Abbrechen einer Hypothese-Anfrage"""
    
    if task_id not in active_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} nicht gefunden"
        )
    
    task_info = active_tasks[task_id]
    
    if task_info["status"] in ["SUCCESS", "FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task bereits abgeschlossen: {task_info['status']}"
        )
    
    # Task als abgebrochen markieren
    active_tasks[task_id]["status"] = "CANCELLED"
    active_tasks[task_id]["cancelled_at"] = datetime.now()
    
    logger.info(f"Task abgebrochen: {task_id}")
    
    return {"message": f"Task {task_id} wurde abgebrochen"}

@app.post("/system/restart")
async def restart_system():
    """Starte KG-System neu"""
    global kg_system
    
    try:
        if kg_system:
            await kg_system.shutdown()
        
        # Neu initialisieren
        await initialize_kg_system()
        
        logger.info("KG-System neu gestartet")
        
        return {"message": "KG-System erfolgreich neu gestartet"}
        
    except Exception as e:
        logger.error(f"Fehler beim Neustart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neustart fehlgeschlagen: {str(e)}"
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Monitoring Dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KG-System Monitoring Dashboard</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; color: #27ae60; }
            .metric-label { color: #7f8c8d; font-size: 0.9em; }
            .status-running { color: #27ae60; }
            .status-stopped { color: #e74c3c; }
            .refresh-btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .refresh-btn:hover { background: #2980b9; }
        </style>
        <script>
            function refreshData() {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('system-status').innerText = data.isRunning ? 'RUNNING' : 'STOPPED';
                        document.getElementById('system-status').className = data.isRunning ? 'status-running' : 'status-stopped';
                        document.getElementById('active-cycles').innerText = data.activeCycles;
                        document.getElementById('total-processed').innerText = data.totalProcessed;
                        document.getElementById('success-rate').innerText = data.successRate.toFixed(1) + '%';
                        document.getElementById('avg-time').innerText = data.averageProcessingTime.toFixed(2) + 's';
                    })
                    .catch(error => console.error('Error:', error));
                
                fetch('/metriken')
                    .then(response => response.json())
                    .then(data => {
                        const metricsContainer = document.getElementById('module-metrics');
                        metricsContainer.innerHTML = '';
                        
                        const modules = {};
                        data.forEach(metric => {
                            if (!modules[metric.module]) {
                                modules[metric.module] = {};
                            }
                            modules[metric.module][metric.metrikName] = metric.wert;
                        });
                        
                        Object.keys(modules).forEach(module => {
                            const moduleDiv = document.createElement('div');
                            moduleDiv.className = 'metric-card';
                            moduleDiv.innerHTML = `
                                <h3>${module} Module</h3>
                                <div class="metric-value">${modules[module].erfolgsrate || 0}%</div>
                                <div class="metric-label">Erfolgsrate</div>
                                <div style="margin-top: 10px;">
                                    <span class="metric-label">Ø Verarbeitungszeit: ${modules[module].durchschnittliche_verarbeitungszeit || 0}s</span>
                                </div>
                            `;
                            metricsContainer.appendChild(moduleDiv);
                        });
                    })
                    .catch(error => console.error('Error:', error));
            }
            
            // Refresh every 5 seconds
            setInterval(refreshData, 5000);
            
            // Initial load
            document.addEventListener('DOMContentLoaded', refreshData);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧬 KG-System Monitoring Dashboard</h1>
                <p>Real-time monitoring of the Knowledge Graph Taste Hypothesis System</p>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <h3>System Status</h3>
                    <div class="metric-value" id="system-status">LOADING...</div>
                    <div class="metric-label">Current System State</div>
                </div>
                
                <div class="metric-card">
                    <h3>Active Cycles</h3>
                    <div class="metric-value" id="active-cycles">0</div>
                    <div class="metric-label">Currently Processing</div>
                </div>
                
                <div class="metric-card">
                    <h3>Total Processed</h3>
                    <div class="metric-value" id="total-processed">0</div>
                    <div class="metric-label">Hypotheses Processed</div>
                </div>
                
                <div class="metric-card">
                    <h3>Success Rate</h3>
                    <div class="metric-value" id="success-rate">0%</div>
                    <div class="metric-label">Overall Success</div>
                </div>
                
                <div class="metric-card">
                    <h3>Average Processing Time</h3>
                    <div class="metric-value" id="avg-time">0s</div>
                    <div class="metric-label">Per Hypothesis</div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <h2>Module Metrics</h2>
                <div class="metrics" id="module-metrics">
                    <!-- Module metrics will be populated here -->
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# === Background Task Functions ===

async def process_hypothese_request(task_id: str, signal: Dict[str, Any]):
    """Verarbeite Hypothese-Anfrage im Hintergrund"""
    global active_tasks, system_metrics
    
    try:
        logger.info(f"Starte Verarbeitung: {task_id}")
        
        # Simuliere vollständige KG-Pipeline
        result = await simulate_full_kg_pipeline(signal)
        
        # Aktualisiere Task-Status
        active_tasks[task_id]["status"] = "SUCCESS"
        active_tasks[task_id]["completed_at"] = datetime.now()
        active_tasks[task_id]["result"] = result
        
        # Update Metriken
        system_metrics["total_processed"] += 1
        system_metrics["successful"] += 1
        
        logger.info(f"Verarbeitung erfolgreich: {task_id}")
        
    except Exception as e:
        logger.error(f"Fehler bei Verarbeitung {task_id}: {e}")
        
        # Aktualisiere Task-Status
        active_tasks[task_id]["status"] = "FAILED"
        active_tasks[task_id]["completed_at"] = datetime.now()
        active_tasks[task_id]["error"] = str(e)
        
        # Update Metriken
        system_metrics["total_processed"] += 1
        system_metrics["failed"] += 1

async def simulate_full_kg_pipeline(signal: Dict[str, Any]) -> VollstaendigeHypothese:
    """Simuliere vollständige KG-Pipeline"""
    
    # Mock-Implementierung der vollständigen Pipeline
    await asyncio.sleep(2.0)  # Simuliere Verarbeitungszeit
    
    # Mock-Hypothese
    hypothese = HypotheseResponse(
        hypotheseID=f"HYP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        status="SUCCESS",
        komponenten=[
            {"name": "Vanillin", "konzentration": 0.2},
            {"name": "Geosmin", "konzentration": 0.01}
        ],
        noveltyScore=0.87,
        taskID=signal["taskID"],
        timestamp=datetime.now()
    )
    
    # Mock-Simulation
    simulation = SimulationResponse(
        simulationID=f"SIM-{uuid.uuid4().hex[:8]}",
        method="NEURAL_MD",
        confidence=0.85,
        grundgeschmack={
            "süß": {"score": 0.82, "molekül": "Vanillin"},
            "bitter": {"score": 0.15, "molekül": "Geosmin"}
        },
        aromaProfil={
            "ERDIG": 0.95,
            "SÜSSLICH": 0.88,
            "HOLZIG": 0.21,
            "FRUCHTIG": 0.05
        },
        texturProfil={
            "viskosität": 0.1,
            "kristallinität": 0.0
        },
        duration=1.8
    )
    
    # Mock-Bewertung
    bewertung = BewertungResponse(
        verdict="APPROVED",
        gesamtScore=0.89,
        geschmacksharmonie=0.92,
        aromaharmonie=0.95,
        bestaetigteNeuheit=0.87,
        angewandteRegeln=["Rule_G01_Süß-Bitter-Balance", "Rule_A04_Erde-Süße-Paarung"]
    )
    
    return VollstaendigeHypothese(
        hypothese=hypothese,
        simulation=simulation,
        bewertung=bewertung,
        status="SUCCESS"
    )

# === Startup/Shutdown Events ===

@app.on_event("startup")
async def startup_event():
    """Startup-Event"""
    global logger
    logger = setup_logging()
    logger.info("KG-System API wird gestartet...")
    
    await initialize_kg_system()
    
    logger.info("KG-System API erfolgreich gestartet")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown-Event"""
    global kg_system
    
    logger.info("KG-System API wird heruntergefahren...")
    
    if kg_system:
        await kg_system.shutdown()
    
    logger.info("KG-System API erfolgreich heruntergefahren")

async def initialize_kg_system():
    """Initialisiere KG-System"""
    global kg_system, config
    
    try:
        config = Config()
        kg_system = MockKGSystem(config)
        await kg_system.start()
        
        logger.info("KG-System erfolgreich initialisiert")
        
    except Exception as e:
        logger.error(f"Fehler bei KG-System-Initialisierung: {e}")
        raise

# === Mock KG-System für API-Tests ===

class MockKGSystem:
    """Mock-Implementierung des KG-Systems für API-Tests"""
    
    def __init__(self, config):
        self.config = config
        self.is_initialized = False
        self.is_running = False
    
    async def start(self):
        await asyncio.sleep(0.1)
        self.is_initialized = True
        self.is_running = True
    
    async def shutdown(self):
        await asyncio.sleep(0.1)
        self.is_running = False

# Authentication endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    rate_limit: bool = Depends(rate_limit_dependency)
):
    """Authenticate user and return tokens"""
    user = auth_service.authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        }
    )

@app.post("/auth/refresh")
async def refresh_token(
    request: RefreshRequest,
    rate_limit: bool = Depends(rate_limit_dependency)
):
    """Refresh access token"""
    # Implementation for token refresh
    return {"access_token": "new_token", "message": "Token refreshed successfully"}

@app.post("/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    current_user: User = Depends(get_current_user)
):
    """Logout user and revoke token"""
    token = credentials.credentials
    auth_service.revoke_token(token)
    
    return {"message": "Successfully logged out"}

@app.get("/auth/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

# Advanced Analytics endpoints
@app.get("/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(require_user)
):
    """Get system analytics overview"""
    try:
        overview = await analytics_engine.get_system_overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics overview")

@app.get("/analytics/hypotheses")
async def get_hypothesis_analytics(
    time_range: str = "24h",
    current_user: User = Depends(require_user)
):
    """Get detailed hypothesis analytics"""
    try:
        analytics = await analytics_engine.get_hypothesis_analytics(time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting hypothesis analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hypothesis analytics")

@app.get("/analytics/validations")
async def get_validation_analytics(
    time_range: str = "24h",
    current_user: User = Depends(require_user)
):
    """Get detailed validation analytics"""
    try:
        analytics = await analytics_engine.get_validation_analytics(time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting validation analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get validation analytics")

@app.get("/analytics/knowledge")
async def get_knowledge_analytics(
    time_range: str = "24h",
    current_user: User = Depends(require_user)
):
    """Get knowledge base analytics"""
    try:
        analytics = await analytics_engine.get_knowledge_analytics(time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting knowledge analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get knowledge analytics")

@app.get("/analytics/learning")
async def get_learning_analytics(
    time_range: str = "24h",
    current_user: User = Depends(require_user)
):
    """Get learning and adaptation analytics"""
    try:
        analytics = await analytics_engine.get_learning_analytics(time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting learning analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get learning analytics")

@app.get("/analytics/report")
async def generate_analytics_report(
    time_range: str = "24h",
    current_user: User = Depends(require_user)
):
    """Generate comprehensive analytics report"""
    try:
        report = await analytics_engine.generate_comprehensive_report(time_range)
        return report
    except Exception as e:
        logger.error(f"Error generating analytics report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics report")

# Admin endpoints
@app.get("/admin/system-health")
async def get_system_health(
    current_user: User = Depends(require_admin)
):
    """Get detailed system health information"""
    try:
        overview = await analytics_engine.get_system_overview()
        return {
            "system_health": overview.get("system_health", {}),
            "performance_metrics": overview.get("performance_trends", {}),
            "resource_usage": await get_resource_usage(),
            "active_connections": await get_active_connections(),
            "error_rates": await get_error_rates()
        }
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system health")

@app.post("/admin/system-maintenance")
async def system_maintenance(
    action: str,
    current_user: User = Depends(require_admin)
):
    """Perform system maintenance actions"""
    try:
        if action == "clear_cache":
            analytics_engine.cache.clear()
            return {"message": "Cache cleared successfully"}
        elif action == "restart_services":
            # Implementation for restarting services
            return {"message": "Services restarted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Invalid maintenance action")
    except Exception as e:
        logger.error(f"Error performing maintenance: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform maintenance")

# Enhanced status endpoints
@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        # Check critical dependencies
        await check_database_connection()
        await check_redis_connection()
        await check_ml_models()
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

# WebSocket endpoint for real-time updates
@app.websocket("/ws/analytics")
async def websocket_analytics(websocket):
    """WebSocket endpoint for real-time analytics updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send real-time analytics updates
            overview = await analytics_engine.get_system_overview()
            await websocket.send_json({
                "type": "analytics_update",
                "data": overview,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await asyncio.sleep(30)  # Update every 30 seconds
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Helper functions
async def get_resource_usage():
    """Get system resource usage"""
    return {
        "cpu_usage": "45%",
        "memory_usage": "60%",
        "disk_usage": "30%",
        "network_io": "150MB/s"
    }

async def get_active_connections():
    """Get active connections count"""
    return {
        "database_connections": 15,
        "redis_connections": 8,
        "api_connections": 25,
        "websocket_connections": 5
    }

async def get_error_rates():
    """Get error rates"""
    return {
        "api_error_rate": "0.5%",
        "database_error_rate": "0.1%",
        "ml_model_error_rate": "2.0%",
        "overall_error_rate": "0.8%"
    }

async def check_database_connection():
    """Check database connection"""
    # Implementation for database health check
    pass

async def check_redis_connection():
    """Check Redis connection"""
    # Implementation for Redis health check
    pass

async def check_ml_models():
    """Check ML models availability"""
    # Implementation for ML models health check
    pass

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "kg_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
