"""
Scribber - Audio Transcription & Summarization API
Main FastAPI application entry point with comprehensive OpenAPI documentation.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.database import engine
from app.routers import auth, health, projects, models, websocket, export
from app.routers.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"Upload directory: {settings.UPLOAD_DIR}")

    yield

    # Shutdown
    print("Shutting down...")
    await engine.dispose()


# Define API tags with descriptions for better organization
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check endpoints for monitoring and container orchestration. "
        "These endpoints are used by load balancers and orchestrators to determine service health.",
    },
    {
        "name": "Authentication",
        "description": "Self-hosted authentication system with JWT tokens. "
        "Register new users, login to get access tokens, and manage user sessions. "
        "All protected endpoints require a valid Bearer token.",
    },
    {
        "name": "Projects",
        "description": "Audio transcription project management. "
        "Create projects, upload audio files, start transcription and summarization.",
    },
    {
        "name": "Models",
        "description": "Available AI models for transcription and summarization. "
        "List active models and their capabilities.",
    },
    {
        "name": "Export",
        "description": "Export transcriptions and summaries to external services. "
        "Google Drive, Email, WhatsApp.",
    },
    {
        "name": "Admin",
        "description": "Administrative endpoints for managing models, users, and usage statistics. "
        "Requires admin privileges.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 🎙️ Scribber - Audio Transcription & Summarization API

A professional-grade API for transcribing audio files and generating intelligent summaries.

### Features

* 🎤 **Multi-model transcription** - Whisper, Google STT, Eleven Labs, Qwen Audio
* 📝 **AI Summarization** - GPT-4o, Claude 3.5 for intelligent summaries
* 🔐 **Self-hosted authentication** - JWT tokens with bcrypt password hashing
* 📤 **Export options** - Google Drive, Email, WhatsApp
* 🏥 **Health checks** - Liveness and readiness probes for container orchestration
* 🐳 **Docker-ready** - Multi-stage builds for development and production

### Quick Start

1. Register a new account at `/api/v1/auth/register`
2. Login at `/api/v1/auth/login` to get your access token
3. Click the **Authorize** button (🔓) and enter your token as `Bearer <your_token>`
4. Create a project and upload an audio file
5. Start transcription with your preferred model
6. Generate a summary and export!

### Documentation

* **Swagger UI**: `/docs` (you are here)
* **ReDoc**: `/redoc`
* **OpenAPI Schema**: `/openapi.json`
    """,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "Scribber Support",
        "url": "https://github.com/scribber/scribber",
        "email": "support@scribber.app",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.scribber.app",
            "description": "Production server",
        },
    ],
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "persistAuthorization": True,
        "deepLinking": True,
        "displayOperationId": False,
    },
)


# Custom OpenAPI schema to add security schemes
def custom_openapi():
    """Generate custom OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from `/api/v1/auth/login` or `/api/v1/auth/register`",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(admin_router, prefix="/api/v1/admin")


@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Get basic information about the API",
    response_description="API information including name, version, and status",
)
async def root():
    """
    Get API information and status.

    Returns basic metadata about the running API instance.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }
