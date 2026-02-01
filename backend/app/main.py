"""
Main FastAPI application entry point with comprehensive OpenAPI documentation.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.routers import auth, health, items


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    print("Shutting down...")


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
        "name": "Items",
        "description": "Example CRUD operations for managing items. "
        "Demonstrates basic create, read, update, and delete patterns.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 🚀 Project Template API

A production-ready FastAPI template with self-hosted authentication, designed for rapid deployment.

### Features

* 🔐 **Self-hosted authentication** - JWT tokens with bcrypt password hashing
* 🏥 **Health checks** - Liveness and readiness probes for container orchestration
* 📦 **CRUD examples** - Fully documented item management endpoints
* 🐳 **Docker-ready** - Multi-stage builds for development and production
* 🔒 **Security** - CORS configuration, secure password handling, token-based auth

### Quick Start

1. Register a new account at `/api/v1/auth/register`
2. Login at `/api/v1/auth/login` to get your access token
3. Click the **Authorize** button (🔓) and enter your token as `Bearer <your_token>`
4. Try the protected endpoints!

### Documentation

* **Swagger UI**: `/docs` (you are here)
* **ReDoc**: `/redoc`
* **OpenAPI Schema**: `/openapi.json`
    """,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "API Support",
        "url": "https://github.com/yourusername/project-template",
        "email": "support@example.com",
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
            "url": "https://api.yourdomain.com",
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
app.include_router(items.router, prefix="/api/v1")


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
