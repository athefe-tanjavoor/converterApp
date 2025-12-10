"""
Configuration management for FileConverter Pro.
All settings can be overridden via environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "FileConverter Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL, either from REDIS_URL or construct from components."""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Celery Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_WORKER_CONCURRENCY: int = 2
    
    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL."""
        return self.CELERY_BROKER_URL or self.redis_url
    
    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL."""
        return self.CELERY_RESULT_BACKEND or self.redis_url
    
    # File Storage
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    TEMP_DIR: str = "/tmp/file_converter"
    INPUT_DIR: str = "/tmp/file_converter/input"
    OUTPUT_DIR: str = "/tmp/file_converter/output"
    
    # File Limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_FILES_PER_REQUEST: int = 10
    FILE_RETENTION_MINUTES: int = 60
    
    # Allowed File Types
    ALLOWED_MIME_TYPES: set = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    }
    
    ALLOWED_EXTENSIONS: set = {
        "jpg", "jpeg", "png", "webp", "pdf", "docx"
    }
    
    # Conversion Formats
    SUPPORTED_CONVERSIONS: dict = {
        "jpg": ["png", "webp", "pdf"],
        "jpeg": ["png", "webp", "pdf"],
        "png": ["jpg", "webp", "pdf"],
        "webp": ["jpg", "png", "pdf"],
        "pdf": ["docx", "jpg", "png"],
        "docx": ["pdf"],
    }
    
    # Security
    RATE_LIMIT_PER_HOUR: int = 50
    ENABLE_RATE_LIMITING: bool = True
    SECRET_KEY: str = "change-this-in-production-use-env-variable"
    
    # AWS S3 Configuration (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FORMAT: str = "json"  # "json" or "text"
    
    # LibreOffice Path
    LIBREOFFICE_PATH: str = "/usr/bin/soffice"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Ensure required directories exist
def ensure_directories():
    """Create required directories if they don't exist."""
    directories = [
        settings.TEMP_DIR,
        settings.INPUT_DIR,
        settings.OUTPUT_DIR,
        settings.LOG_DIR,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Initialize directories on import
ensure_directories()
