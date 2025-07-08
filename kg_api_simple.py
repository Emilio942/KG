# Simplified KG-System API for Enhanced Validation Testing
# This version removes complex dependencies to focus on validation testing

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

# Enhanced Validation Imports
from enhanced_validation import (
    EnhancedHypothesisRequest, ValidationLevel, RateLimiter,
    SecurityValidator, ValidationReport
)

# === Simplified Models ===

class HypotheseAnfrage(BaseModel):
    """Anfrage für neue Hypothese"""
    targetProfile: List[str] = Field(..., description="Gewünschte Geschmacksprofile")
    exclude: List[str] = Field(default=[], description="Auszuschließende Moleküle")
    signal: str = Field(default="CREATE_NEW", description="Art des Signals")
    priority: str = Field(default="NORMAL", description="Priorität der Anfrage")

class User(BaseModel):
    """Simplified User model"""
    id: str
    username: str
    role: str = "user"

# === FastAPI App Setup ===

app = FastAPI(
    title="KG-System API - Enhanced Validation Test",
    description="API für das Geschmackshypothesen-Generator System mit Enhanced Validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Global Variables ===
rate_limiter = RateLimiter()
active_tasks = {}
system_metrics = {
    "total_processed": 0,
    "successful": 0,
    "failed": 0,
    "start_time": datetime.now()
}

# Mock logger
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

logger = MockLogger()

# === Authentication Stubs ===

async def get_current_user() -> Optional[User]:
    """Mock authentication - returns test user"""
    return User(id="test-user", username="testuser", role="user")

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
        "message": "KG-System API - Enhanced Validation Test",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health-Check Endpoint"""
    uptime = (datetime.now() - system_metrics["start_time"]).total_seconds()
    
    return {
        "status": "healthy",
        "uptime_seconds": uptime,
        "kg_system_initialized": True,
        "active_tasks": len(active_tasks),
        "timestamp": datetime.now()
    }

@app.post("/hypothese/erstellen", response_model=Dict[str, str])
async def erstelle_hypothese(
    anfrage: HypotheseAnfrage,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Erstelle neue Geschmackshypothese mit Enhanced Validation"""
    
    # === Enhanced Validation ===
    try:
        # Rate Limiting Check
        client_id = user.id if user else "anonymous"
        rate_check = rate_limiter.check_rate_limit(client_id, "/hypothese/erstellen")
        if not rate_check.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=rate_check.get("reason", "Rate limit exceeded. Please try again later.")
            )
        
        # Create Enhanced Request for Validation
        try:
            enhanced_request = EnhancedHypothesisRequest(
                targetProfile=anfrage.targetProfile,
                constraints={"maxComponents": 5, "noveltyThreshold": 0.8},
                context="Test hypothesis request",
                validation_level=ValidationLevel.STRICT,
                exclude=anfrage.exclude,
                signal=anfrage.signal,
                priority=anfrage.priority
            )
        except Exception as validation_error:
            # Handle validation errors (e.g., invalid target profiles)
            logger.warning(f"Request validation failed: {str(validation_error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request: {str(validation_error)}"
            )
        
        # Security Validation
        security_validator = SecurityValidator()
        security_report = security_validator.validate_request(enhanced_request)
        
        # Debug logging
        logger.info(f"Security validation result: valid={security_report.is_valid}, errors={security_report.errors}")
        
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

# === Background Task Functions ===

async def process_hypothese_request(task_id: str, signal: Dict[str, Any]):
    """Verarbeite Hypothese-Anfrage im Hintergrund"""
    global active_tasks, system_metrics
    
    try:
        logger.info(f"Starte Verarbeitung: {task_id}")
        
        # Simuliere Verarbeitung
        await asyncio.sleep(2.0)
        
        # Mock result
        result = {
            "hypotheseID": f"HYP-{uuid.uuid4().hex[:8]}",
            "status": "SUCCESS",
            "komponenten": [
                {"name": "Vanillin", "concentration": 0.5},
                {"name": "Citral", "concentration": 0.3}
            ],
            "noveltyScore": 0.85,
            "taskID": task_id,
            "timestamp": datetime.now()
        }
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
