# Quick Start - Windows (No Docker)

✅ **Fixed Windows compatibility issues!**

## Current Status
- ✅ Dependencies installed
- ✅ MIME validation made optional (works without libmagic)
- ⚠️ Still need Redis

## Start the App (No Redis Required for Testing)

The app will start even without Redis, but conversions won't work until Redis is running.

### Terminal 1: FastAPI (Already Running!)
The server should auto-reload with the fix. Check for:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Visit: http://localhost:8000

### To Enable Conversions: Install Redis

**Option 1: Memurai (Easiest)**
1. Download: https://www.memurai.com/get-memurai
2. Install (runs as Windows service automatically)
3. Start Celery worker (Terminal 2 below)

**Option 2: WSL2**
```powershell
wsl
sudo apt update && sudo apt install redis-server -y
sudo service redis-server start
exit
```

### Terminal 2: Celery Worker (After Redis is running)
```powershell
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

## Test Without Conversions

You can still test the UI:
1. Visit http://localhost:8000
2. See the beautiful interface ✨
3. Upload files (will show in queue but won't convert without Redis)

## Full Test With Redis

Once Redis + Celery worker are running:
1. Upload a JPG → convert to PNG
2. Watch progress bar
3. Download converted file!

## Troubleshooting

### "Application startup complete" but page doesn't load
- Check firewall
- Try http://127.0.0.1:8000 instead

### Conversions hang
- Redis not running
- Celery worker not started

### LibreOffice conversions fail
- Download: https://www.libreoffice.org/download/download/
- Update `.env`: `LIBREOFFICE_PATH=C:/Program Files/LibreOffice/program/soffice.exe`
