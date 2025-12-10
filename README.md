# FileConverter Pro ⚡

A production-ready SaaS platform for professional file conversions, built with FastAPI, Celery, and Redis.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Features

### Core Capabilities
- **Image Conversions**: JPG ↔ PNG ↔ WEBP
- **PDF Operations**: PDF → DOCX, PDF → Images (multi-page support)
- **Document Conversion**: DOCX → PDF (using LibreOffice headless)
- **Batch Processing**: Convert multiple files at once with ZIP output
- **Images to PDF**: Combine multiple images into a single PDF

### Technical Features
- ⚡ **Asynchronous Processing**: Background task handling with Celery
- 🔒 **Secure**: File validation, MIME type checking, rate limiting
- 📦 **Scalable**: Docker-based deployment with multiple workers
- 💾 **Flexible Storage**: Local temp storage or AWS S3
- 📊 **Monitoring**: Admin dashboard + Flower for Celery tasks
- 🎨 **Modern UI**: Responsive dark-mode interface with drag-and-drop
- 🧹 **Auto-cleanup**: Files auto-delete after 60 minutes

## 📋 Prerequisites

- Docker and Docker Compose
- (Optional) AWS account for S3 storage

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│    Redis     │◀────│   Celery    │
│  (Web App)  │     │  (Broker)    │     │   Worker    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                                          │
      │                                          │
      ▼                                          ▼
┌─────────────┐                         ┌─────────────┐
│  Templates  │                         │ Conversions │
│   Static    │                         │   Service   │
└─────────────┘                         └─────────────┘
                                                │
                                                ▼
                                        ┌─────────────┐
                                        │  Storage    │
                                        │ Local / S3  │
                                        └─────────────┘
```

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone and setup**
   ```bash
   cd converterApp
   cp .env.example .env
   ```

2. **Edit `.env` file** (optional)
   ```env
   SECRET_KEY=your-secret-key-here
   RATE_LIMIT_PER_HOUR=50
   MAX_FILE_SIZE=104857600  # 100MB
   ```

3. **Build and run**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Application: http://localhost:8000
   - Admin Dashboard: http://localhost:8000/admin
   - Flower (Celery Monitor): http://localhost:5555
   - Health Check: http://localhost:8000/health

### Local Development (Without Docker)

1. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y libreoffice libreoffice-writer-nogui poppler-utils libmagic1

   # macOS
   brew install libreoffice poppler libmagic
   ```

2. **Install Python dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start Redis**
   ```bash
   docker run -p 6379:6379 redis:7-alpine
   ```

4. **Run the application**
   ```bash
   # Terminal 1: FastAPI
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2: Celery Worker
   celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

   # Terminal 3: Celery Beat
   celery -A app.workers.celery_app beat --loglevel=info

   # Terminal 4: Flower (optional)
   celery -A app.workers.celery_app flower --port=5555
   ```

## 📡 API Documentation

### Endpoints

#### `POST /convert`
Upload and convert files.

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `files`: File(s) to convert (max 10)
  - `target_format`: Target format (jpg, png, webp, pdf, docx)

**Response (202):**
```json
{
  "status": "queued",
  "task_id": "abc123...",
  "message": "Conversion queued for 2 file(s)",
  "files_count": 2,
  "target_format": "pdf"
}
```

#### `GET /status/{task_id}`
Check conversion status.

**Response:**
```json
{
  "task_id": "abc123...",
  "status": "SUCCESS",
  "message": "Task completed successfully",
  "result": {
    "status": "success",
    "output": {
      "type": "single",
      "filename": "converted.pdf",
      "path": "/tmp/..."
    }
  },
  "download_url": "/download/abc123..."
}
```

#### `GET /download/{task_id}`
Download converted file.

**Response:** File download

#### `GET /health`
System health check.

**Response:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "workers": 1,
  "storage": {...},
  "app_version": "1.0.0"
}
```

## 🔐 Security Features

- **MIME Type Validation**: Files are validated by actual content, not just extension
- **File Size Limits**: Configurable maximum file size (default 100MB)
- **Rate Limiting**: 50 conversions per hour per IP (configurable)
- **Path Traversal Prevention**: Filename sanitization
- **Auto-cleanup**: Files older than 60 minutes are automatically deleted

## ⚙️ Configuration

All settings can be configured via environment variables. See `.env.example` for available options.

### Important Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE` | `104857600` | Maximum file size in bytes (100MB) |
| `MAX_FILES_PER_REQUEST` | `10` | Maximum files per conversion |
| `FILE_RETENTION_MINUTES` | `60` | File auto-delete age |
| `RATE_LIMIT_PER_HOUR` | `50` | Conversions per hour per IP |
| `CELERY_WORKER_CONCURRENCY` | `2` | Number of concurrent workers |

### Storage Configuration

**Local Storage (Default):**
```env
STORAGE_TYPE=local
```

**AWS S3 Storage:**
```env
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_S3_BUCKET=your-bucket
AWS_S3_REGION=us-east-1
```

## 📊 Monitoring

### Admin Dashboard
Access at `/admin` to view:
- Active tasks
- System storage usage
- Worker status
- Registered tasks

### Flower Dashboard
Access at `http://localhost:5555` for detailed Celery monitoring:
- Task history
- Worker performance
- Task execution times
- Queue statistics

## 🐳 Docker Services

The application runs 5 Docker services:

1. **fastapi**: Web application (port 8000)
2. **redis**: Message broker and result backend (port 6379)
3. **celery-worker**: Background task processor
4. **celery-beat**: Scheduled task scheduler
5. **flower**: Celery monitoring dashboard (port 5555)

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Scale workers
docker-compose up -d --scale celery-worker=4
```

## 🌐 Deployment

### Render.com Deployment

1. **Create Web Service**
   - Connect your repository
   - Build Command: `docker build -t fileconverter .`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Add Redis Instance**
   - Create a Redis service on Render
   - Add `REDIS_URL` environment variable to your web service

3. **Add Background Worker**
   - Create a new Background Worker service
   - Start Command: `celery -A app.workers.celery_app worker --loglevel=info`

4. **Environment Variables**
   Set these in Render dashboard:
   ```
   REDIS_URL=<your-redis-url>
   SECRET_KEY=<random-string>
   STORAGE_TYPE=local
   ```

### Other Platforms

The application is compatible with:
- **Heroku**: Add Redis add-on, scale worker dynos
- **AWS ECS**: Use task definitions for each service
- **DigitalOcean App Platform**: Deploy as Docker container
- **Railway**: Automatic Docker deployment

## 📁 Project Structure

```
converterApp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── routes/
│   │   ├── web.py              # Web interface routes
│   │   └── api.py              # API endpoints
│   ├── services/
│   │   ├── conversions.py      # Conversion logic
│   │   └── storage.py          # Storage abstraction
│   ├── workers/
│   │   ├── celery_app.py       # Celery configuration
│   │   └── celery_worker.py    # Background tasks
│   ├── utils/
│   │   ├── logger.py           # Logging utilities
│   │   ├── security.py         # Security utilities
│   │   └── file_utils.py       # File utilities
│   ├── templates/
│   │   ├── index.html          # Homepage
│   │   └── admin.html          # Admin dashboard
│   └── static/
│       ├── css/
│       │   └── style.css       # Styles
│       └── js/
│           └── main.js         # Client-side JS
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-service setup
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # Documentation
```

## 🔧 Troubleshooting

### LibreOffice Conversion Fails
- Ensure LibreOffice is installed: `soffice --version`
- Check permissions on temp directories
- Increase worker memory if handling large files

### Redis Connection Issues
- Verify Redis is running: `redis-cli ping`
- Check REDIS_HOST and REDIS_PORT in environment
- Ensure firewall allows connection to Redis port

### Worker Not Processing Tasks
- Check worker logs: `docker-compose logs celery-worker`
- Verify Redis connection
- Restart workers: `docker-compose restart celery-worker`

### File Upload Fails
- Check file size against MAX_FILE_SIZE
- Verify MIME type is in ALLOWED_MIME_TYPES
- Check disk space in temp directories

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [Pillow](https://pillow.readthedocs.io/) - Image processing
- [LibreOffice](https://www.libreoffice.org/) - Document conversion
- [Redis](https://redis.io/) - In-memory data store

## 📧 Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review logs for error messages

---

**Built with ⚡ by the FileConverter Pro team**
