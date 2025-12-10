"""
Storage abstraction layer for FileConverter Pro.
Supports local temporary storage and AWS S3.
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict
import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.utils.logger import app_logger
from app.utils.file_utils import get_directory_size, format_file_size


class StorageProvider(ABC):
    """Abstract base class for storage providers."""
    
    @abstractmethod
    def upload_file(self, local_path: str, storage_key: str) -> str:
        """Upload file to storage."""
        pass
    
    @abstractmethod
    def get_file_path(self, storage_key: str) -> str:
        """Get file path or URL."""
        pass
    
    @abstractmethod
    def get_download_url(self, storage_key: str, expiration: int = 3600) -> str:
        """Get download URL."""
        pass
    
    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def get_storage_usage(self) -> Dict[str, any]:
        """Get storage usage statistics."""
        pass


class LocalTempStorage(StorageProvider):
    """Local temporary storage provider."""
    
    def __init__(self):
        """Initialize local storage."""
        self.input_dir = settings.INPUT_DIR
        self.output_dir = settings.OUTPUT_DIR
        
        # Ensure directories exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        app_logger.info("Initialized LocalTempStorage")
    
    def upload_file(self, local_path: str, storage_key: str) -> str:
        """
        Upload file (copy to output directory).
        
        Args:
            local_path: Source file path
            storage_key: Destination filename
            
        Returns:
            Destination file path
        """
        dest_path = os.path.join(self.output_dir, storage_key)
        
        # If file is already in output dir, no need to copy
        if os.path.abspath(local_path) == os.path.abspath(dest_path):
            return dest_path
        
        # Copy file
        import shutil
        shutil.copy2(local_path, dest_path)
        
        app_logger.debug(f"Uploaded file to local storage: {storage_key}")
        return dest_path
    
    def get_file_path(self, storage_key: str) -> str:
        """
        Get file path.
        
        Args:
            storage_key: Filename
            
        Returns:
            Full file path
        """
        # Check output directory first
        output_path = os.path.join(self.output_dir, storage_key)
        if os.path.exists(output_path):
            return output_path
        
        # Check input directory
        input_path = os.path.join(self.input_dir, storage_key)
        if os.path.exists(input_path):
            return input_path
        
        # Return output path anyway (might be created later)
        return output_path
    
    def get_download_url(self, storage_key: str, expiration: int = 3600) -> str:
        """
        Get download URL (returns relative path for local storage).
        
        Args:
            storage_key: Filename
            expiration: Not used for local storage
            
        Returns:
            Download path
        """
        return f"/download/{storage_key}"
    
    def delete_file(self, storage_key: str) -> bool:
        """
        Delete file from local storage.
        
        Args:
            storage_key: Filename
            
        Returns:
            True if deleted successfully
        """
        try:
            file_path = self.get_file_path(storage_key)
            if os.path.exists(file_path):
                os.remove(file_path)
                app_logger.debug(f"Deleted file from local storage: {storage_key}")
                return True
            return False
        except Exception as e:
            app_logger.error(f"Error deleting file {storage_key}: {e}")
            return False
    
    def get_storage_usage(self) -> Dict[str, any]:
        """
        Get storage usage statistics.
        
        Returns:
            Dict with usage stats
        """
        input_size = get_directory_size(self.input_dir)
        output_size = get_directory_size(self.output_dir)
        total_size = input_size + output_size
        
        # Count files
        input_files = len([f for f in os.listdir(self.input_dir) if os.path.isfile(os.path.join(self.input_dir, f))]) if os.path.exists(self.input_dir) else 0
        output_files = len([f for f in os.listdir(self.output_dir) if os.path.isfile(os.path.join(self.output_dir, f))]) if os.path.exists(self.output_dir) else 0
        
        return {
            "input_size_bytes": input_size,
            "output_size_bytes": output_size,
            "total_size_bytes": total_size,
            "input_size_formatted": format_file_size(input_size),
            "output_size_formatted": format_file_size(output_size),
            "total_size_formatted": format_file_size(total_size),
            "input_files": input_files,
            "output_files": output_files,
            "total_files": input_files + output_files,
        }


class S3Storage(StorageProvider):
    """AWS S3 storage provider."""
    
    def __init__(self):
        """Initialize S3 storage."""
        if not all([
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_S3_BUCKET
        ]):
            raise ValueError("S3 credentials not configured")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION
        )
        
        self.bucket = settings.AWS_S3_BUCKET
        app_logger.info(f"Initialized S3Storage with bucket: {self.bucket}")
    
    def upload_file(self, local_path: str, storage_key: str) -> str:
        """
        Upload file to S3.
        
        Args:
            local_path: Source file path
            storage_key: S3 key
            
        Returns:
            S3 URL
        """
        try:
            self.s3_client.upload_file(local_path, self.bucket, storage_key)
            app_logger.info(f"Uploaded file to S3: {storage_key}")
            return f"s3://{self.bucket}/{storage_key}"
        except ClientError as e:
            app_logger.error(f"Error uploading to S3: {e}")
            raise
    
    def get_file_path(self, storage_key: str) -> str:
        """
        Get S3 URL.
        
        Args:
            storage_key: S3 key
            
        Returns:
            S3 URL
        """
        return f"s3://{self.bucket}/{storage_key}"
    
    def get_download_url(self, storage_key: str, expiration: int = 3600) -> str:
        """
        Generate pre-signed download URL.
        
        Args:
            storage_key: S3 key
            expiration: URL expiration in seconds
            
        Returns:
            Pre-signed URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': storage_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            app_logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def delete_file(self, storage_key: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            storage_key: S3 key
            
        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_key)
            app_logger.info(f"Deleted file from S3: {storage_key}")
            return True
        except ClientError as e:
            app_logger.error(f"Error deleting from S3: {e}")
            return False
    
    def get_storage_usage(self) -> Dict[str, any]:
        """
        Get S3 bucket usage statistics.
        
        Returns:
            Dict with usage stats
        """
        # Note: This is a simplified version. For production,
        # consider using CloudWatch metrics for better performance
        try:
            total_size = 0
            object_count = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_formatted": format_file_size(total_size),
                "total_files": object_count,
            }
        except ClientError as e:
            app_logger.error(f"Error getting S3 usage: {e}")
            return {"error": str(e)}


def get_storage_provider() -> StorageProvider:
    """
    Get configured storage provider.
    
    Returns:
        StorageProvider instance
    """
    if settings.STORAGE_TYPE == "s3":
        return S3Storage()
    else:
        return LocalTempStorage()


# Global storage provider instance
storage = get_storage_provider()
