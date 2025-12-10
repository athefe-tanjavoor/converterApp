"""
Logging configuration for FileConverter Pro.
Provides structured logging with file and console handlers.
"""
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        if hasattr(record, "user_ip"):
            log_data["user_ip"] = record.user_ip
            
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Standard text formatter for human-readable logs."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Optional log file path (relative to LOG_DIR)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Choose formatter
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = log_dir / log_file
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Application loggers
app_logger = setup_logger("fileconverter.app", "app.log")
access_logger = setup_logger("fileconverter.access", "access.log")
error_logger = setup_logger("fileconverter.error", "error.log", "ERROR")
task_logger = setup_logger("fileconverter.tasks", "tasks.log")
celery_logger = setup_logger("celery", "celery.log")


def log_task_execution(task_id: str, task_name: str, duration_ms: float, success: bool):
    """
    Log task execution metrics.
    
    Args:
        task_id: Celery task ID
        task_name: Task function name
        duration_ms: Execution duration in milliseconds
        success: Whether task succeeded
    """
    log_record = {
        "task_id": task_id,
        "task_name": task_name,
        "duration_ms": duration_ms,
        "success": success,
    }
    
    if success:
        task_logger.info(f"Task completed: {task_name}", extra=log_record)
    else:
        task_logger.error(f"Task failed: {task_name}", extra=log_record)


def log_api_request(method: str, path: str, status_code: int, user_ip: str, duration_ms: float):
    """
    Log API request details.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        user_ip: Client IP address
        duration_ms: Request duration in milliseconds
    """
    access_logger.info(
        f"{method} {path} - {status_code}",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "user_ip": user_ip,
            "duration_ms": duration_ms,
        }
    )
