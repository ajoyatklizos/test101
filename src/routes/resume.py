import os
import uuid
import json
import shutil
from fastapi import (
    APIRouter, 
    UploadFile, 
    File,
    HTTPException, 
    Depends, 
    BackgroundTasks
)
from fastapi.responses import JSONResponse
from config.settings import settings,conn

router = APIRouter()

# Redis connection



@router.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}_{file.filename}")

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Push job metadata into Redis (queue + status)
    job_data = {
        "task_id": task_id,
        "filename": file.filename,
        "file_path": file_path,
        "status": "queued",
        "result": None
    }
    conn.redis_conn.set(f"task:{task_id}", json.dumps(job_data))
    conn.redis_conn.lpush("task_queue", task_id)  # push into queue for worker

    return {"task_id": task_id, "status": "queued"}

@router.post("/job/{task_id}")
async def get_job_status(task_id: str):
    job_raw = conn.redis_conn.get(f"task:{task_id}")
    if not job_raw:
        raise HTTPException(status_code=404, detail="Task not found")

    job_data = json.loads(job_raw)
    return JSONResponse(content=job_data)


