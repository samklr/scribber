"""
Export Router - Endpoints for exporting transcriptions to external services.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, User
from app.routers.auth import get_current_user
from app.services.export import EmailService, GoogleDriveService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances
email_service = EmailService()
google_drive_service = GoogleDriveService()


# --- Request/Response Models ---


class EmailExportRequest(BaseModel):
    """Request to export via email."""
    project_id: int
    to_email: EmailStr
    include_summary: bool = True
    include_attachment: bool = True


class EmailExportResponse(BaseModel):
    """Response from email export."""
    success: bool
    message: str


class GoogleDriveAuthRequest(BaseModel):
    """Request to start Google Drive OAuth."""
    project_id: int
    redirect_uri: str


class GoogleDriveAuthResponse(BaseModel):
    """Response with OAuth URL."""
    authorization_url: str


class GoogleDriveCallbackRequest(BaseModel):
    """Request to complete Google Drive OAuth."""
    code: str
    state: str
    redirect_uri: str


class GoogleDriveUploadRequest(BaseModel):
    """Request to upload to Google Drive."""
    project_id: int
    access_token: str
    folder_name: Optional[str] = "Scribber"


class GoogleDriveUploadResponse(BaseModel):
    """Response from Google Drive upload."""
    success: bool
    file_id: Optional[str] = None
    web_view_link: Optional[str] = None
    message: str


class ExportStatusResponse(BaseModel):
    """Response with export service status."""
    email_configured: bool
    google_drive_configured: bool


# --- Endpoints ---


@router.get("/status", response_model=ExportStatusResponse)
async def get_export_status(
    current_user: User = Depends(get_current_user),
):
    """Get status of export services."""
    return ExportStatusResponse(
        email_configured=email_service.is_configured(),
        google_drive_configured=google_drive_service.is_configured(),
    )


@router.post("/email", response_model=EmailExportResponse)
async def export_to_email(
    request: EmailExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send transcription/summary to email via SendGrid.
    """
    # Get project
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.transcription:
        raise HTTPException(status_code=400, detail="Project has no transcription")

    # Send email
    result = await email_service.send_transcription(
        to_email=request.to_email,
        project_title=project.title,
        transcription=project.transcription,
        summary=project.summary if request.include_summary else None,
        include_attachment=request.include_attachment,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return EmailExportResponse(**result)


@router.post("/google-drive/auth", response_model=GoogleDriveAuthResponse)
async def start_google_drive_auth(
    request: GoogleDriveAuthRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Start Google Drive OAuth flow.
    Returns authorization URL to redirect user to.
    """
    if not google_drive_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google Drive export not configured. Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.",
        )

    # Create state with user and project info for callback
    state = f"{current_user.id}:{request.project_id}"

    authorization_url = google_drive_service.get_authorization_url(
        redirect_uri=request.redirect_uri,
        state=state,
    )

    return GoogleDriveAuthResponse(authorization_url=authorization_url)


@router.post("/google-drive/callback")
async def google_drive_callback(
    request: GoogleDriveCallbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Handle Google Drive OAuth callback and exchange code for token.
    """
    if not google_drive_service.is_configured():
        raise HTTPException(status_code=503, detail="Google Drive export not configured")

    # Verify state matches current user
    try:
        state_user_id, state_project_id = request.state.split(":")
        if int(state_user_id) != current_user.id:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        # Exchange code for tokens
        tokens = await google_drive_service.exchange_code(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )

        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
            "project_id": int(state_project_id),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/google-drive/upload", response_model=GoogleDriveUploadResponse)
async def upload_to_google_drive(
    request: GoogleDriveUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload transcription to Google Drive.
    Requires access_token from OAuth flow.
    """
    # Get project
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.transcription:
        raise HTTPException(status_code=400, detail="Project has no transcription")

    try:
        # Build document content
        content_lines = [
            f"# {project.title}",
            "",
            f"Transcribed: {project.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        if project.summary:
            content_lines.extend([
                "## Summary",
                "",
                project.summary,
                "",
            ])

        content_lines.extend([
            "## Full Transcription",
            "",
            project.transcription,
        ])

        content = "\n".join(content_lines)

        # Create folder if specified
        folder_id = None
        if request.folder_name:
            try:
                folder = await google_drive_service.create_folder(
                    access_token=request.access_token,
                    folder_name=request.folder_name,
                )
                folder_id = folder.get("id")
            except Exception as e:
                logger.warning(f"Could not create folder: {e}")
                # Continue without folder

        # Upload document
        result = await google_drive_service.upload_document(
            access_token=request.access_token,
            title=project.title,
            content=content,
            folder_id=folder_id,
        )

        return GoogleDriveUploadResponse(
            success=True,
            file_id=result.get("file_id"),
            web_view_link=result.get("web_view_link"),
            message="Successfully uploaded to Google Drive",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Google Drive upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/google-drive/refresh")
async def refresh_google_drive_token(
    refresh_token: str,
    current_user: User = Depends(get_current_user),
):
    """
    Refresh an expired Google Drive access token.
    """
    if not google_drive_service.is_configured():
        raise HTTPException(status_code=503, detail="Google Drive export not configured")

    try:
        tokens = await google_drive_service.refresh_access_token(refresh_token)
        return {
            "access_token": tokens.get("access_token"),
            "expires_in": tokens.get("expires_in"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
