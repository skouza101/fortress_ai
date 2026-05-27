import os
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from celery.result import AsyncResult
from app.tasks.document_tasks import process_document
from app.core.config import settings
from app.core.auth import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user)
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch.")
    
    tasks = []
    for file in files:
        safe_filename = os.path.basename(file.filename) if file.filename else "upload.bin"
        file_path = os.path.join(settings.upload_path, safe_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Enqueue task with priority (0 is highest, let's just use 0 for now)
        task = process_document.apply_async(args=[file_path, user_id], priority=0)
        
        # In reality, you'd create a DB record here for DocumentTask using prisma
        
        tasks.append({"filename": file.filename, "task_id": task.id})
    
    return {"message": f"Successfully queued {len(files)} files.", "tasks": tasks}

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, user_id: str = Depends(get_current_user)):
    task = AsyncResult(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Revoke task, terminate if it's already running
    task.revoke(terminate=True)
    
    # Also update DB status to cancelled
    # store.db.documenttask.update(...)
    
    return {"message": f"Task {task_id} has been cancelled."}
