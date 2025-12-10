"""
Celery worker tasks for FileConverter Pro.
Handles background file conversions and maintenance tasks.
"""
import os
import time
from typing import List, Dict
from datetime import datetime

from celery import Task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.services.conversions import converter, ConversionError
from app.services.storage import storage
from app.config import settings
from app.utils.file_utils import (
    generate_unique_filename,
    get_file_extension,
    cleanup_old_files,
    secure_delete_file,
    get_conversion_output_filename,
)
from app.utils.logger import log_task_execution

# Celery task logger
logger = get_task_logger(__name__)


class ConversionTask(Task):
    """Base class for conversion tasks with error handling."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        log_task_execution(task_id, self.name, 0, False)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} succeeded")


@celery_app.task(
    base=ConversionTask,
    bind=True,
    name='app.workers.celery_worker.process_conversion_task',
    max_retries=3,
    default_retry_delay=60
)
def process_conversion_task(
    self,
    input_files: List[Dict[str, str]],
    target_format: str,
    task_metadata: Dict[str, any] = None
) -> Dict[str, any]:
    """
    Process file conversion task.
    
    Args:
        input_files: List of dicts with 'path' and 'filename' keys
        target_format: Target conversion format
        task_metadata: Optional metadata
        
    Returns:
        Dict with conversion results
    """
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(f"Starting conversion task {task_id}: {len(input_files)} file(s) to {target_format}")
    
    try:
        output_files = []
        errors = []
        
        # Process each file
        for file_info in input_files:
            input_path = file_info['path']
            original_filename = file_info['filename']
            
            try:
                # Get source format
                source_format = get_file_extension(original_filename)
                
                # Generate output filename
                output_filename = get_conversion_output_filename(
                    original_filename,
                    target_format
                )
                output_filename = generate_unique_filename(output_filename)
                output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
                
                # Convert file
                logger.info(f"Converting {original_filename} ({source_format} -> {target_format})")
                
                result_path = converter.convert_file(
                    input_path,
                    output_path,
                    source_format,
                    target_format
                )
                
                # Handle PDF to images (multiple outputs)
                if source_format == 'pdf' and target_format in ['jpg', 'jpeg', 'png']:
                    # PDF to images returns list, but we stored first page earlier
                    # For multiple pages, we need to handle differently
                    output_files.append({
                        'path': result_path,
                        'filename': os.path.basename(result_path),
                        'original_filename': original_filename,
                    })
                else:
                    output_files.append({
                        'path': result_path,
                        'filename': output_filename,
                        'original_filename': original_filename,
                    })
                
            except ConversionError as e:
                error_msg = f"Conversion failed for {original_filename}: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    'filename': original_filename,
                    'error': str(e)
                })
            except Exception as e:
                error_msg = f"Unexpected error for {original_filename}: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    'filename': original_filename,
                    'error': str(e)
                })
        
        # If no files were successfully converted
        if not output_files:
            raise ConversionError("All conversions failed")
        
        # Create ZIP if multiple output files
        final_output = None
        if len(output_files) > 1:
            zip_filename = f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(settings.OUTPUT_DIR, zip_filename)
            
            output_paths = [f['path'] for f in output_files]
            converter.create_zip_archive(output_paths, zip_path)
            
            final_output = {
                'type': 'zip',
                'filename': zip_filename,
                'path': zip_path,
                'files_count': len(output_files),
            }
            
            # Clean up individual files
            for output_file in output_files:
                secure_delete_file(output_file['path'])
        else:
            final_output = {
                'type': 'single',
                'filename': output_files[0]['filename'],
                'path': output_files[0]['path'],
            }
        
        # Calculate execution time
        duration_ms = (time.time() - start_time) * 1000
        log_task_execution(task_id, 'process_conversion_task', duration_ms, True)
        
        logger.info(f"Conversion task {task_id} completed in {duration_ms:.2f}ms")
        
        return {
            'status': 'success',
            'task_id': task_id,
            'output': final_output,
            'errors': errors if errors else None,
            'duration_ms': duration_ms,
            'processed_files': len(input_files),
            'successful_files': len(output_files),
        }
        
    except ConversionError as e:
        logger.error(f"Conversion task {task_id} failed: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_task_execution(task_id, 'process_conversion_task', duration_ms, False)
        
        return {
            'status': 'failed',
            'task_id': task_id,
            'error': str(e),
            'duration_ms': duration_ms,
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in task {task_id}: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_task_execution(task_id, 'process_conversion_task', duration_ms, False)
        
        # Retry on unexpected errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            'status': 'failed',
            'task_id': task_id,
            'error': f"Unexpected error: {str(e)}",
            'duration_ms': duration_ms,
        }


@celery_app.task(name='app.workers.celery_worker.cleanup_old_files_task')
def cleanup_old_files_task():
    """
    Scheduled task to clean up old files.
    Runs every 30 minutes via Celery Beat.
    """
    logger.info("Starting scheduled file cleanup")
    
    try:
        # Clean input directory
        input_deleted = cleanup_old_files(
            settings.INPUT_DIR,
            settings.FILE_RETENTION_MINUTES
        )
        
        # Clean output directory
        output_deleted = cleanup_old_files(
            settings.OUTPUT_DIR,
            settings.FILE_RETENTION_MINUTES
        )
        
        total_deleted = input_deleted + output_deleted
        
        logger.info(f"Cleanup completed: {total_deleted} files deleted")
        
        return {
            'status': 'success',
            'input_deleted': input_deleted,
            'output_deleted': output_deleted,
            'total_deleted': total_deleted,
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {
            'status': 'failed',
            'error': str(e),
        }


@celery_app.task(name='app.workers.celery_worker.worker_heartbeat_task')
def worker_heartbeat_task():
    """
    Scheduled task to log worker heartbeat.
    Runs every 60 seconds via Celery Beat.
    """
    logger.debug("Worker heartbeat")
    
    return {
        'status': 'alive',
        'timestamp': datetime.now().isoformat(),
    }


@celery_app.task(name='app.workers.celery_worker.get_storage_stats_task')
def get_storage_stats_task():
    """Get current storage statistics."""
    try:
        stats = storage.get_storage_usage()
        logger.info(f"Storage stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return {'error': str(e)}
