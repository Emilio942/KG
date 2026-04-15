from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

from kg.modules.lar.lar_agent import LARAgent
from kg.schemas import HGInput, TaskStatus

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="KG-System API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
lar_agent = LARAgent()
active_tasks = {}

class HypothesisRequest(BaseModel):
    targetProfile: List[str]
    exclude: List[str] = []
    signal: str = "CREATE_NEW"
    priority: str = "NORMAL"

@app.on_event("startup")
async def startup():
    await lar_agent.initialize()
    logger.info("KG-System initialized.")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/hypothese/erstellen")
async def create_hypothesis(request: HypothesisRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    active_tasks[task_id] = {
        "status": "IN_PROGRESS",
        "created_at": datetime.now(),
        "request": request.dict()
    }
    
    background_tasks.add_task(run_pipeline, task_id, request)
    
    return {"taskID": task_id, "status": "IN_PROGRESS"}

@app.get("/hypothese/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return active_tasks[task_id]

async def run_pipeline(task_id: str, request: HypothesisRequest):
    try:
        # Hier wird die echte LAR-Logik aufgerufen
        result = await lar_agent.process_signal({
            "taskID": task_id,
            "signal": request.signal,
            "constraints": {
                "targetProfile": request.targetProfile,
                "exclude": request.exclude
            }
        })
        active_tasks[task_id]["status"] = "SUCCESS"
        active_tasks[task_id]["result"] = result
    except Exception as e:
        logger.error(f"Pipeline error for {task_id}: {e}")
        active_tasks[task_id]["status"] = "FAILED"
        active_tasks[task_id]["error"] = str(e)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
