"""
Model endpoints for listing available AI models.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.model_config import ModelConfig, ModelType, ModelProvider

router = APIRouter(prefix="/models", tags=["Models"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ModelResponse(BaseModel):
    """Model configuration response."""
    id: int
    name: str
    display_name: str
    provider: str
    model_type: str
    description: str | None
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ModelsListResponse(BaseModel):
    """Response containing lists of available models."""
    transcription: list[ModelResponse]
    summarization: list[ModelResponse]


# =============================================================================
# Helper Functions
# =============================================================================


def model_to_response(model: ModelConfig) -> ModelResponse:
    """Convert model config to response."""
    return ModelResponse(
        id=model.id,
        name=model.name,
        display_name=model.display_name,
        provider=model.provider.value,
        model_type=model.model_type.value,
        description=model.description,
        is_default=model.is_default,
        is_active=model.is_active,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ModelsListResponse,
    summary="List Models",
    description="Get all active transcription and summarization models",
)
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all active models grouped by type."""
    # Fetch transcription models
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.model_type == ModelType.TRANSCRIPTION,
            ModelConfig.is_active == True,
        )
        .order_by(ModelConfig.is_default.desc(), ModelConfig.display_name)
    )
    transcription_models = result.scalars().all()

    # Fetch summarization models
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.model_type == ModelType.SUMMARIZATION,
            ModelConfig.is_active == True,
        )
        .order_by(ModelConfig.is_default.desc(), ModelConfig.display_name)
    )
    summarization_models = result.scalars().all()

    return ModelsListResponse(
        transcription=[model_to_response(m) for m in transcription_models],
        summarization=[model_to_response(m) for m in summarization_models],
    )


@router.get(
    "/transcription",
    response_model=list[ModelResponse],
    summary="List Transcription Models",
    description="Get all active transcription models",
)
async def list_transcription_models(db: AsyncSession = Depends(get_db)):
    """List active transcription models."""
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.model_type == ModelType.TRANSCRIPTION,
            ModelConfig.is_active == True,
        )
        .order_by(ModelConfig.is_default.desc(), ModelConfig.display_name)
    )
    models = result.scalars().all()
    return [model_to_response(m) for m in models]


@router.get(
    "/summarization",
    response_model=list[ModelResponse],
    summary="List Summarization Models",
    description="Get all active summarization models",
)
async def list_summarization_models(db: AsyncSession = Depends(get_db)):
    """List active summarization models."""
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.model_type == ModelType.SUMMARIZATION,
            ModelConfig.is_active == True,
        )
        .order_by(ModelConfig.is_default.desc(), ModelConfig.display_name)
    )
    models = result.scalars().all()
    return [model_to_response(m) for m in models]


@router.get(
    "/{model_id}",
    response_model=ModelResponse,
    summary="Get Model",
    description="Get details of a specific model",
)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a model by ID."""
    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.id == model_id, ModelConfig.is_active == True)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return model_to_response(model)
