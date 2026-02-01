"""
Admin Routers for Scribber.
"""
from fastapi import APIRouter

from app.routers.admin import models, users, usage

router = APIRouter()

# Include all admin routers
router.include_router(models.router, prefix="/models", tags=["Admin - Models"])
router.include_router(users.router, prefix="/users", tags=["Admin - Users"])
router.include_router(usage.router, prefix="/usage", tags=["Admin - Usage"])

__all__ = ["router", "models", "users", "usage"]
