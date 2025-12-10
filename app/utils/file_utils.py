"""
File utility functions for FileConverter Pro.
Handles file operations, sanitization, and cleanup.
"""
import os
import re
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from app.config import settings
from app.utils.logger import app_logger


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Remove multiple dots (except extension)
    name, ext = os.path.splitext(filename)
    name = name.replace('.', '_')
    
    # Limit length
    max_length = 200
    if len(name) > max_length:
        name = name[:max_length]
    
    # Ensure not empty
    if not name:
        name = "file"
    
    return f"{name}{ext}"


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename using UUID.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Unique filename with UUID prefix
    """
    sanitized = sanitize_filename(original_filename)
    name, ext = os.path.splitext(sanitized)
    unique_id = uuid.uuid4().hex[:12]
    return f"{unique_id}_{name}{ext}"


def get_file_extension(filename: str) -> str:
    """
    Extract file extension in lowercase.
    
    Args:
        filename: Filename
        
    Returns:
        Lowercase extension without dot
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext.lstrip('.')


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hex digest of SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def cleanup_old_files(directory: str, max_age_minutes: int = None) -> int:
    """
    Delete files older than specified age.
    
    Args:
        directory: Directory to clean
        max_age_minutes: Maximum file age in minutes (default from settings)
        
    Returns:
        Number of files deleted
    """
    if max_age_minutes is None:
        max_age_minutes = settings.FILE_RETENTION_MINUTES
    
    if not os.path.exists(directory):
        return 0
    
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=max_age_minutes)
    deleted_count = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    # Get file modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        app_logger.debug(f"Deleted old file: {file_path}")
                        
                except Exception as e:
                    app_logger.error(f"Error deleting file {file_path}: {e}")
        
        app_logger.info(f"Cleanup completed: {deleted_count} files deleted from {directory}")
        
    except Exception as e:
        app_logger.error(f"Error during cleanup of {directory}: {e}")
    
    return deleted_count


def secure_delete_file(file_path: str) -> bool:
    """
    Securely delete a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if deleted successfully
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            app_logger.debug(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as e:
        app_logger.error(f"Error deleting file {file_path}: {e}")
        return False


def get_directory_size(directory: str) -> int:
    """
    Calculate total size of directory in bytes.
    
    Args:
        directory: Directory path
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception as e:
        app_logger.error(f"Error calculating directory size for {directory}: {e}")
    
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def ensure_directory(directory: str) -> None:
    """
    Ensure directory exists, create if not.
    
    Args:
        directory: Directory path
    """
    os.makedirs(directory, exist_ok=True)


def list_files_in_directory(directory: str, extension: Optional[str] = None) -> List[str]:
    """
    List all files in directory, optionally filtered by extension.
    
    Args:
        directory: Directory path
        extension: Optional file extension filter (without dot)
        
    Returns:
        List of file paths
    """
    if not os.path.exists(directory):
        return []
    
    files = []
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        if os.path.isfile(file_path):
            if extension is None or get_file_extension(filename) == extension.lower():
                files.append(file_path)
    
    return files


def get_conversion_output_filename(input_filename: str, target_format: str) -> str:
    """
    Generate output filename for conversion.
    
    Args:
        input_filename: Original input filename
        target_format: Target file format (extension)
        
    Returns:
        Output filename with new extension
    """
    name = os.path.splitext(input_filename)[0]
    return f"{name}.{target_format}"
