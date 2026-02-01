"""
Admin Model Management Router.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ModelConfig, User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Admin Check Dependency ---


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# --- Request/Response Models ---


class ModelConfigCreate(BaseModel):
    """Request to create a model config."""
    name: str
    display_name: str
    provider: str
    model_type: str  # 'transcription' or 'summarization'
    api_endpoint: Optional[str] = None
    config_json: Optional[dict] = None
    is_active: bool = True
    is_default: bool = False


class ModelConfigUpdate(BaseModel):
    """Request to update a model config."""
    display_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    config_json: Optional[dict] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """Response with model config details."""
    id: int
    name: str
    display_name: str
    provider: str
    model_type: str
    api_endpoint: Optional[str]
    config_json: Optional[dict]
    is_active: bool
    is_default: bool
    created_at: str

    class Config:
        from_attributes = True


# --- Endpoints ---


@router.get("", response_model=List[ModelConfigResponse])
async def list_models(
    model_type: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    List all model configurations (admin only).
    """
    query = select(ModelConfig)

    if model_type:
        query = query.where(ModelConfig.model_type == model_type)

    if not include_inactive:
        query = query.where(ModelConfig.is_active == True)

    query = query.order_by(ModelConfig.model_type, ModelConfig.display_name)

    result = await db.execute(query)
    models = result.scalars().all()

    return [
        ModelConfigResponse(
            id=m.id,
            name=m.name,
            display_name=m.display_name,
            provider=m.provider,
            model_type=m.model_type,
            api_endpoint=m.api_endpoint,
            config_json=m.config_json,
            is_active=m.is_active,
            is_default=m.is_default,
            created_at=m.created_at.isoformat(),
        )
        for m in models
    ]


@router.post("", response_model=ModelConfigResponse)
async def create_model(
    request: ModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Create a new model configuration (admin only).
    """
    # Check if name already exists
    existing = await db.execute(
        select(ModelConfig).where(ModelConfig.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Model name already exists")

    # If setting as default, unset other defaults of same type
    if request.is_default:
        await db.execute(
            ModelConfig.__table__.update()
            .where(ModelConfig.model_type == request.model_type)
            .values(is_default=False)
        )

    model = ModelConfig(
        name=request.name,
        display_name=request.display_name,
        provider=request.provider,
        model_type=request.model_type,
        api_endpoint=request.api_endpoint,
        config_json=request.config_json,
        is_active=request.is_active,
        is_default=request.is_default,
    )

    db.add(model)
    await db.commit()
    await db.refresh(model)

    logger.info(f"Admin {admin.email} created model: {model.name}")

    return ModelConfigResponse(
        id=model.id,
        name=model.name,
        display_name=model.display_name,
        provider=model.provider,
        model_type=model.model_type,
        api_endpoint=model.api_endpoint,
        config_json=model.config_json,
        is_active=model.is_active,
        is_default=model.is_default,
        created_at=model.created_at.isoformat(),
    )


@router.get("/{model_id}", response_model=ModelConfigResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get a model configuration by ID (admin only).
    """
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == model_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return ModelConfigResponse(
        id=model.id,
        name=model.name,
        display_name=model.display_name,
        provider=model.provider,
        model_type=model.model_type,
        api_endpoint=model.api_endpoint,
        config_json=model.config_json,
        is_active=model.is_active,
        is_default=model.is_default,
        created_at=model.created_at.isoformat(),
    )


@router.put("/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    model_id: int,
    request: ModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Update a model configuration (admin only).
    """
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == model_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Update fields
    if request.display_name is not None:
        model.display_name = request.display_name
    if request.api_endpoint is not None:
        model.api_endpoint = request.api_endpoint
    if request.config_json is not None:
        model.config_json = request.config_json
    if request.is_active is not None:
        model.is_active = request.is_active
    if request.is_default is not None:
        # If setting as default, unset other defaults of same type
        if request.is_default:
            await db.execute(
                ModelConfig.__table__.update()
                .where(
                    ModelConfig.model_type == model.model_type,
                    ModelConfig.id != model_id,
                )
                .values(is_default=False)
            )
        model.is_default = request.is_default

    await db.commit()
    await db.refresh(model)

    logger.info(f"Admin {admin.email} updated model: {model.name}")

    return ModelConfigResponse(
        id=model.id,
        name=model.name,
        display_name=model.display_name,
        provider=model.provider,
        model_type=model.model_type,
        api_endpoint=model.api_endpoint,
        config_json=model.config_json,
        is_active=model.is_active,
        is_default=model.is_default,
        created_at=model.created_at.isoformat(),
    )


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Delete a model configuration (admin only).
    """
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == model_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    await db.delete(model)
    await db.commit()

    logger.info(f"Admin {admin.email} deleted model: {model.name}")

    return {"message": "Model deleted successfully"}


@router.post("/{model_id}/toggle")
async def toggle_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Toggle a model's active status (admin only).
    """
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.id == model_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = not model.is_active
    await db.commit()

    status = "activated" if model.is_active else "deactivated"
    logger.info(f"Admin {admin.email} {status} model: {model.name}")

    return {"message": f"Model {status}", "is_active": model.is_active}
