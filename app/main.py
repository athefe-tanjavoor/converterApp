"""
FileConverter Pro - Main Application
A production-ready SaaS platform for file conversions.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, ensure_directories
from app.routes import web, api
from app.utils.logger import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    app_logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    ensure_directories()
    app_logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready SaaS platform for file conversions",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(web.router, tags=["web"])
app.include_router(api.router, tags=["api"])


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint."""
    from fastapi.responses import Response
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
