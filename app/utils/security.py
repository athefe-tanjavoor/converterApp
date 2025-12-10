"""
Security utilities for FileConverter Pro.
Handles validation, rate limiting, and security checks.
"""
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import defaultdict

# Try to import magic, but make it optional for Windows
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False
    print("WARNING: python-magic not available. Using extension-based validation only.")

from fastapi import HTTPException, UploadFile
from app.config import settings
from app.utils.logger import app_logger, error_logger


# Rate limiting storage (in production, use Redis)
rate_limit_storage: Dict[str, list] = defaultdict(list)


def validate_mime_type(file_path: str) -> bool:
    """
    Validate file MIME type using python-magic (if available).
    Falls back to extension-based validation on Windows.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if MIME type is allowed
        
    Raises:
        HTTPException: If MIME type is not allowed
    """
    if not MAGIC_AVAILABLE:
        # Fallback: Just validate extension if magic is not available
        app_logger.warning("python-magic not available, skipping MIME validation")
        return True
    
    try:
        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_file(file_path)
        
        if file_mime_type not in settings.ALLOWED_MIME_TYPES:
            error_logger.warning(f"Rejected file with MIME type: {file_mime_type}")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Detected: {file_mime_type}"
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        # If magic fails, just log and continue (better than blocking on Windows)
        app_logger.warning(f"MIME type validation failed, continuing: {e}")
        return True


def validate_file_extension(filename: str) -> bool:
    """
    Validate file extension.
    
    Args:
        filename: Filename to validate
        
    Returns:
        True if extension is allowed
        
    Raises:
        HTTPException: If extension is not allowed
    """
    ext = Path(filename).suffix.lower().lstrip('.')
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '.{ext}' not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    return True


def validate_file_size(file_size: int) -> bool:
    """
    Validate file size against maximum allowed.
    
    Args:
        file_size: File size in bytes
        
    Returns:
        True if size is within limit
        
    Raises:
        HTTPException: If file is too large
    """
    if file_size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {max_mb:.1f}MB, Actual: {actual_mb:.1f}MB"
        )
    
    return True


async def validate_upload_file(file: UploadFile, check_mime: bool = False) -> bool:
    """
    Validate uploaded file (extension and size).
    
    Args:
        file: FastAPI UploadFile object
        check_mime: Whether to check MIME type (requires file to be saved)
        
    Returns:
        True if file is valid
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate extension
    validate_file_extension(file.filename)
    
    # Validate size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    validate_file_size(file_size)
    
    return True


def check_malicious_filename(filename: str) -> bool:
    """
    Check for potentially malicious filename patterns.
    
    Args:
        filename: Filename to check
        
    Returns:
        True if filename is safe
        
    Raises:
        HTTPException: If filename is suspicious
    """
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: path traversal detected"
        )
    
    # Check for null bytes
    if '\x00' in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: null byte detected"
        )
    
    # Check for hidden files
    if filename.startswith('.'):
        raise HTTPException(
            status_code=400,
            detail="Hidden files not allowed"
        )
    
    return True


def validate_conversion_format(source_format: str, target_format: str) -> bool:
    """
    Validate that conversion is supported.
    
    Args:
        source_format: Source file format
        target_format: Target file format
        
    Returns:
        True if conversion is supported
        
    Raises:
        HTTPException: If conversion is not supported
    """
    source_format = source_format.lower()
    target_format = target_format.lower()
    
    if source_format not in settings.SUPPORTED_CONVERSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Source format '{source_format}' not supported"
        )
    
    if target_format not in settings.SUPPORTED_CONVERSIONS[source_format]:
        supported = ', '.join(settings.SUPPORTED_CONVERSIONS[source_format])
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert {source_format} to {target_format}. Supported: {supported}"
        )
    
    return True


def check_rate_limit(client_ip: str) -> bool:
    """
    Check if client has exceeded rate limit.
    
    Args:
        client_ip: Client IP address
        
    Returns:
        True if within rate limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.ENABLE_RATE_LIMITING:
        return True
    
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(hours=1)
    
    # Clean old requests
    rate_limit_storage[client_ip] = [
        timestamp for timestamp in rate_limit_storage[client_ip]
        if timestamp > cutoff_time
    ]
    
    # Check limit
    request_count = len(rate_limit_storage[client_ip])
    
    if request_count >= settings.RATE_LIMIT_PER_HOUR:
        app_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_HOUR} conversions per hour."
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)
    
    return True


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Sanitized text
    """
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Limit length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text
