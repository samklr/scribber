"""
Project endpoints for audio transcription management.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.model_config import ModelConfig, ModelType
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.storage import get_storage_service
from app.tasks.transcription import transcribe_audio
from app.tasks.summarization import summarize_text

router = APIRouter(prefix="/projects", tags=["Projects"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ProjectCreate(BaseModel):
    """Project creation request."""
    title: str = Field(..., min_length=1, max_length=255, description="Project title")


class ProjectUpdate(BaseModel):
    """Project update request."""
    title: str | None = Field(None, max_length=255, description="New project title")
    transcription: str | None = Field(None, description="Updated transcription text")
    summary: str | None = Field(None, description="Updated summary text")


class ProjectResponse(BaseModel):
    """Project response model."""
    id: int
    title: str
    audio_url: str | None
    audio_filename: str | None
    audio_duration_seconds: float | None
    transcription: str | None
    summary: str | None
    status: str
    error_message: str | None
    transcription_model_name: str | None = None
    summarization_model_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Project list item response."""
    id: int
    title: str
    status: str
    audio_filename: str | None
    has_transcription: bool
    has_summary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscribeRequest(BaseModel):
    """Transcription request."""
    model_id: int = Field(..., description="ID of the transcription model to use")


class SummarizeRequest(BaseModel):
    """Summarization request."""
    model_id: int = Field(..., description="ID of the summarization model to use")


# =============================================================================
# Helper Functions
# =============================================================================


def project_to_response(project: Project) -> ProjectResponse:
    """Convert project model to response."""
    return ProjectResponse(
        id=project.id,
        title=project.title,
        audio_url=project.audio_url,
        audio_filename=project.audio_filename,
        audio_duration_seconds=project.audio_duration_seconds,
        transcription=project.transcription,
        summary=project.summary,
        status=project.status.value,
        error_message=project.error_message,
        transcription_model_name=project.transcription_model.display_name if project.transcription_model else None,
        summarization_model_name=project.summarization_model.display_name if project.summarization_model else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def project_to_list_response(project: Project) -> ProjectListResponse:
    """Convert project model to list response."""
    return ProjectListResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        audio_filename=project.audio_filename,
        has_transcription=project.transcription is not None,
        has_summary=project.summary is not None,
        created_at=project.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[ProjectListResponse],
    summary="List Projects",
    description="Get all projects for the current user",
)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """List all projects for the authenticated user."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    projects = result.scalars().all()
    return [project_to_list_response(p) for p in projects]


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a new transcription project",
)
async def create_project(
    current_user: Annotated[User, Depends(get_current_user)],
    title: str = Form(..., description="Project title"),
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project and upload audio file."""
    # Validate file extension
    if audio_file.filename:
        ext = audio_file.filename.rsplit(".", 1)[-1].lower()
        if ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {ext}. Supported: {', '.join(settings.allowed_extensions_list)}"
            )

    # Create project first to get ID
    project = Project(
        user_id=current_user.id,
        title=title,
        status=ProjectStatus.UPLOADING,
    )
    db.add(project)
    await db.flush()

    try:
        # Upload file to storage
        storage = get_storage_service()
        audio_url = await storage.upload_file(
            file=audio_file.file,
            filename=audio_file.filename or "audio",
            user_id=current_user.id,
            project_id=project.id,
        )

        # Update project with file info
        project.audio_url = audio_url
        project.audio_filename = audio_file.filename
        project.audio_size_bytes = audio_file.size
        project.status = ProjectStatus.PENDING

        await db.commit()
        await db.refresh(project)

        return project_to_response(project)

    except Exception as e:
        project.status = ProjectStatus.FAILED
        project.error_message = f"Upload failed: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio file: {str(e)}"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project",
    description="Get a specific project by ID",
)
async def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get a project by ID."""
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.transcription_model),
            selectinload(Project.summarization_model),
        )
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project_to_response(project)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project",
    description="Update a project's title, transcription, or summary",
)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.transcription_model),
            selectinload(Project.summarization_model),
        )
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Update fields
    if data.title is not None:
        project.title = data.title
    if data.transcription is not None:
        project.transcription = data.transcription
    if data.summary is not None:
        project.summary = data.summary

    await db.commit()
    await db.refresh(project)

    return project_to_response(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Delete a project and its associated files",
)
async def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Delete a project."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Delete file from storage
    if project.audio_url:
        storage = get_storage_service()
        await storage.delete_file(project.audio_url)

    # Delete project
    await db.delete(project)
    await db.commit()


@router.post(
    "/{project_id}/transcribe",
    response_model=ProjectResponse,
    summary="Start Transcription",
    description="Start transcription for a project",
)
async def start_transcription(
    project_id: int,
    request: TranscribeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Start transcription for a project."""
    # Fetch project
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.transcription_model),
            selectinload(Project.summarization_model),
        )
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not project.audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no audio file"
        )

    # Verify model exists and is active
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.id == request.model_id,
            ModelConfig.model_type == ModelType.TRANSCRIPTION,
            ModelConfig.is_active == True,
        )
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive transcription model"
        )

    # Update project status
    project.status = ProjectStatus.TRANSCRIBING
    project.transcription_model_id = request.model_id
    project.error_message = None
    await db.commit()

    # Queue transcription task
    transcribe_audio.delay(project_id, request.model_id)

    await db.refresh(project)
    return project_to_response(project)


@router.post(
    "/{project_id}/summarize",
    response_model=ProjectResponse,
    summary="Start Summarization",
    description="Generate a summary from the transcription",
)
async def start_summarization(
    project_id: int,
    request: SummarizeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Start summarization for a project."""
    # Fetch project
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.transcription_model),
            selectinload(Project.summarization_model),
        )
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not project.transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no transcription to summarize"
        )

    # Verify model exists and is active
    result = await db.execute(
        select(ModelConfig)
        .where(
            ModelConfig.id == request.model_id,
            ModelConfig.model_type == ModelType.SUMMARIZATION,
            ModelConfig.is_active == True,
        )
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive summarization model"
        )

    # Update project status
    project.status = ProjectStatus.SUMMARIZING
    project.summarization_model_id = request.model_id
    project.error_message = None
    await db.commit()

    # Queue summarization task
    summarize_text.delay(project_id, request.model_id)

    await db.refresh(project)
    return project_to_response(project)


@router.get(
    "/{project_id}/status",
    summary="Get Project Status",
    description="Get the current status of a project",
)
async def get_project_status(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get project status for polling."""
    result = await db.execute(
        select(Project.status, Project.error_message)
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return {
        "status": row.status.value,
        "error_message": row.error_message,
    }
