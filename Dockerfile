# FileConverter Pro - Multi-stage Production Dockerfile

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies and LibreOffice
RUN apt-get update && apt-get install -y --no-install-recommends \
    # LibreOffice for DOCX to PDF conversion (headless only)
    libreoffice-writer-nogui \
    libreoffice-core-nogui \
    # Poppler utilities for PDF processing
    poppler-utils \
    # Image processing dependencies
    libmagic1 \
    # General utilities
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /tmp/file_converter/input /tmp/file_converter/output /app/logs && \
    chown -R appuser:appuser /tmp/file_converter /app

# Copy application code
COPY --chown=appuser:appuser ./app ./app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
