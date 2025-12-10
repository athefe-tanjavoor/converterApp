"""
Web interface routes for FileConverter Pro.
Renders HTML templates using Jinja2.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.storage import storage
from app.workers.celery_app import celery_app

router = APIRouter()

# Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """
    Render homepage with file upload interface.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
            "max_files": settings.MAX_FILES_PER_REQUEST,
            "supported_conversions": settings.SUPPORTED_CONVERSIONS,
            "allowed_extensions": sorted(settings.ALLOWED_EXTENSIONS),
        }
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """
    Render admin dashboard.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response
    """
    try:
        # Get Celery inspector
        inspector = celery_app.control.inspect()
        
        # Get active tasks
        active_tasks = inspector.active() or {}
        active_count = sum(len(tasks) for tasks in active_tasks.values())
        
        # Get scheduled tasks
        scheduled_tasks = inspector.scheduled() or {}
        scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values())
        
        # Get reserved tasks
        reserved_tasks = inspector.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved_tasks.values())
        
        # Get registered tasks
        registered_tasks = inspector.registered() or {}
        
        # Get worker stats
        stats = inspector.stats() or {}
        worker_count = len(stats)
        
        # Get storage usage
        storage_stats = storage.get_storage_usage()
        
        # Prepare worker details
        worker_details = []
        for worker_name, worker_stats in stats.items():
            worker_details.append({
                'name': worker_name,
                'pool': worker_stats.get('pool', {}).get('implementation', 'N/A'),
                'max_concurrency': worker_stats.get('pool', {}).get('max-concurrency', 'N/A'),
            })
        
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "app_name": settings.APP_NAME,
                "active_tasks": active_count,
                "scheduled_tasks": scheduled_count,
                "reserved_tasks": reserved_count,
                "pending_tasks": scheduled_count + reserved_count,
                "worker_count": worker_count,
                "worker_details": worker_details,
                "storage_stats": storage_stats,
                "registered_tasks": registered_tasks,
            }
        )
        
    except Exception as e:
        # Return error page with minimal info
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "app_name": settings.APP_NAME,
                "error": f"Error loading admin data: {str(e)}",
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "pending_tasks": 0,
                "worker_count": 0,
                "worker_details": [],
                "storage_stats": {},
            }
        )
