"""
API routes for FileConverter Pro.
Handles file conversion requests and task status.
"""
import os
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from celery.result import AsyncResult

from app.workers.celery_app import celery_app
from app.workers.celery_worker import process_conversion_task
from app.config import settings
from app.utils.security import (
    validate_upload_file,
    validate_file_extension,
    validate_conversion_format,
    check_rate_limit,
    check_malicious_filename,
    validate_mime_type,
)
from app.utils.file_utils import (
    generate_unique_filename,
    get_file_extension,
    sanitize_filename,
)
from app.utils.logger import app_logger, log_api_request
from app.services.storage import storage

router = APIRouter()


@router.post("/convert")
async def convert_files(
    request: Request,
    files: List[UploadFile] = File(...),
    target_format: str = Form(...),
):
    """
    Upload and convert files.
    
    Args:
        request: FastAPI request object
        files: List of uploaded files
        target_format: Target conversion format
        
    Returns:
        JSON with task ID and status
    """
    start_time = time.time()
    client_ip = request.client.host
    
    try:
        # Check rate limit
        check_rate_limit(client_ip)
        
        # Validate number of files
        if len(files) > settings.MAX_FILES_PER_REQUEST:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum: {settings.MAX_FILES_PER_REQUEST}"
            )
        
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        # Validate target format
        target_format = target_format.lower().strip()
        if target_format not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target format: {target_format}"
            )
        
        # Process uploaded files
        uploaded_files = []
        
        for file in files:
            # Validate filename
            check_malicious_filename(file.filename)
            
            # Validate file
            await validate_upload_file(file)
            
            # Get source format
            source_format = get_file_extension(file.filename)
            
            # Validate conversion
            validate_conversion_format(source_format, target_format)
            
            # Generate unique filename
            unique_filename = generate_unique_filename(file.filename)
            file_path = os.path.join(settings.INPUT_DIR, unique_filename)
            
            # Save file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Validate MIME type
            validate_mime_type(file_path)
            
            uploaded_files.append({
                'path': file_path,
                'filename': file.filename,
            })
            
            app_logger.info(f"Uploaded file: {file.filename} -> {unique_filename}")
        
        # Queue conversion task
        task = process_conversion_task.delay(
            uploaded_files,
            target_format,
            {'client_ip': client_ip}
        )
        
        duration_ms = (time.time() - start_time) * 1000
        log_api_request("POST", "/convert", 202, client_ip, duration_ms)
        
        app_logger.info(f"Queued conversion task {task.id} for {len(files)} file(s)")
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "task_id": task.id,
                "message": f"Conversion queued for {len(files)} file(s)",
                "files_count": len(files),
                "target_format": target_format,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Conversion request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/status/{task_id}")
async def get_task_status(request: Request, task_id: str):
    """
    Get conversion task status.
    
    Args:
        request: FastAPI request object
        task_id: Celery task ID
        
    Returns:
        JSON with task status
    """
    start_time = time.time()
    client_ip = request.client.host
    
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "status": task_result.state,
        }
        
        if task_result.state == "PENDING":
            response["message"] = "Task is pending"
        elif task_result.state == "STARTED":
            response["message"] = "Task is processing"
        elif task_result.state == "SUCCESS":
            result = task_result.result
            response["message"] = "Task completed successfully"
            response["result"] = result
            
            # Add download URL
            if result and result.get('status') == 'success':
                output = result.get('output', {})
                filename = output.get('filename')
                if filename:
                    response["download_url"] = f"/download/{task_id}"
        elif task_result.state == "FAILURE":
            response["message"] = "Task failed"
            response["error"] = str(task_result.info)
        else:
            response["message"] = f"Task state: {task_result.state}"
        
        duration_ms = (time.time() - start_time) * 1000
        log_api_request("GET", f"/status/{task_id}", 200, client_ip, duration_ms)
        
        return response
        
    except Exception as e:
        app_logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{task_id}")
async def download_converted_file(request: Request, task_id: str):
    """
    Download converted file.
    
    Args:
        request: FastAPI request object
        task_id: Celery task ID
        
    Returns:
        File download response
    """
    start_time = time.time()
    client_ip = request.client.host
    
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state != "SUCCESS":
            raise HTTPException(
                status_code=404,
                detail="Conversion not complete or task not found"
            )
        
        result = task_result.result
        
        if not result or result.get('status') != 'success':
            raise HTTPException(status_code=404, detail="Conversion failed")
        
        output = result.get('output', {})
        file_path = output.get('path')
        filename = output.get('filename')
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        duration_ms = (time.time() - start_time) * 1000
        log_api_request("GET", f"/download/{task_id}", 200, client_ip, duration_ms)
        
        # Determine media type
        if filename.endswith('.zip'):
            media_type = "application/zip"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename.endswith('.png'):
            media_type = "image/png"
        elif filename.endswith('.webp'):
            media_type = "image/webp"
        else:
            media_type = "application/octet-stream"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(request: Request):
    """
    System health check.
    
    Returns:
        JSON with system health status
    """
    try:
        # Check Redis connection
        redis_ok = False
        try:
            celery_app.backend.client.ping()
            redis_ok = True
        except:
            pass
        
        # Check Celery workers
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        workers_ok = active_workers is not None and len(active_workers) > 0
        
        # Get storage stats
        storage_stats = storage.get_storage_usage()
        
        overall_health = "healthy" if (redis_ok and workers_ok) else "degraded"
        
        return {
            "status": overall_health,
            "redis": "connected" if redis_ok else "disconnected",
            "workers": len(active_workers) if active_workers else 0,
            "storage": storage_stats,
            "app_version": settings.APP_VERSION,
        }
        
    except Exception as e:
        app_logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )
