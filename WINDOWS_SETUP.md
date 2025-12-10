# Windows Startup Guide (Without Docker)

Since Docker is not installed, here's how to run FileConverter Pro locally on Windows.

## Prerequisites Installed ✅
- Python 3.13
- Virtual environment activated

## Step 1: Install Redis for Windows

**Option A: Using Memurai (Redis for Windows)**
1. Download from: https://www.memurai.com/get-memurai
2. Install and start the service
3. Redis will run on `localhost:6379`

**Option B: Using WSL2 (Recommended)**
```powershell
# Install WSL2 if not already installed
wsl --install

# Start WSL and install Redis
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
exit
```

**Option C: Run Redis in a separate PowerShell**
```powershell
# If you later install Docker, this is easiest:
docker run -p 6379:6379 redis:7-alpine
```

## Step 2: Verify Dependencies Installed

Check that installation completed:
```powershell
pip list | findstr "fastapi uvicorn celery"
```

You should see:
- fastapi 0.115.5
- uvicorn 0.32.1  
- celery 5.4.0

## Step 3: Update .env File

Make sure Redis is pointing to localhost:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Step 4: Install LibreOffice (For DOCX→PDF)

Download and install: https://www.libreoffice.org/download/download/

Then update `.env`:
```env
LIBREOFFICE_PATH=C:/Program Files/LibreOffice/program/soffice.exe
```

## Step 5: Start the Application

Open **3 separate PowerShell terminals** in the project directory.

**Terminal 1: Activate venv and start FastAPI**
```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Activate venv and start Celery Worker**
```powershell
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3 (Optional): Activate venv and start Flower**
```powershell
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app flower --port=5555
```

## Step 6: Access the Application

- **Main App**: http://localhost:8000
- **Admin Dashboard**: http://localhost:8000/admin
- **Health Check**: http://localhost:8000/health
- **Flower (if running)**: http://localhost:5555

## Troubleshooting

### "uvicorn: command not found"
Your venv is not activated. Run:
```powershell
.\venv\Scripts\Activate.ps1
```

### "ModuleNotFoundError"
Dependencies not installed. Run:
```powershell
pip install -r requirements.txt
```

### "Redis connection failed"
Redis is not running. Start Redis using one of the options in Step 1.

### LibreOffice conversions fail
1. Install LibreOffice
2. Update `LIBREOFFICE_PATH` in `.env`
3. Test: `& "C:/Program Files/LibreOffice/program/soffice.exe" --version`

## Quick Test

Once everything is running, test the conversion:
1. Go to http://localhost:8000
2. Upload a JPG image
3. Select "PNG" as target format
4. Click "Start Conversion"
5. Download the converted file

## Notes

- **Pool=solo** is required for Celery on Windows
- **Beat scheduler** is optional for local development
- Files are stored in `C:\tmp\file_converter\` by default
- Files auto-delete after 60 minutes
