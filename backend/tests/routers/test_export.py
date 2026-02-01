"""
Tests for export endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.models import User, Project


class TestExportStatus:
    """Tests for GET /api/v1/export/status"""

    @pytest.mark.asyncio
    async def test_get_export_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting export service status."""
        response = await client.get("/api/v1/export/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email_configured" in data
        assert "google_drive_configured" in data
        # Without env vars, both should be False
        assert isinstance(data["email_configured"], bool)
        assert isinstance(data["google_drive_configured"], bool)

    @pytest.mark.asyncio
    async def test_get_export_status_unauthenticated(self, client: AsyncClient):
        """Test getting export status without auth fails."""
        response = await client.get("/api/v1/export/status")

        assert response.status_code == 401


class TestEmailExport:
    """Tests for POST /api/v1/export/email"""

    @pytest.mark.asyncio
    async def test_email_export_no_transcription(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test email export fails if no transcription."""
        response = await client.post(
            "/api/v1/export/email",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "to_email": "recipient@example.com",
            },
        )

        assert response.status_code == 400
        assert "transcription" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_email_export_project_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test email export with nonexistent project fails."""
        response = await client.post(
            "/api/v1/export/email",
            headers=auth_headers,
            json={
                "project_id": 99999,
                "to_email": "recipient@example.com",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_email_export_invalid_email(
        self,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test email export with invalid email fails."""
        response = await client.post(
            "/api/v1/export/email",
            headers=auth_headers,
            json={
                "project_id": completed_project.id,
                "to_email": "not-an-email",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.routers.export.email_service")
    async def test_email_export_success(
        self,
        mock_email_service,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test successful email export."""
        mock_email_service.is_configured.return_value = True
        mock_email_service.send_transcription = AsyncMock(
            return_value={"success": True, "message": "Email sent"}
        )

        response = await client.post(
            "/api/v1/export/email",
            headers=auth_headers,
            json={
                "project_id": completed_project.id,
                "to_email": "recipient@example.com",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_email_export_other_user_project(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        admin_user: User,
        transcription_model,
        summarization_model,
    ):
        """Test email export fails for other user's project."""
        # Create a project for admin user
        admin_project = Project(
            user_id=admin_user.id,
            title="Admin Project",
            transcription="Some text",
            status="completed",
            transcription_model_id=transcription_model.id,
        )
        db_session.add(admin_project)
        await db_session.commit()
        await db_session.refresh(admin_project)

        response = await client.post(
            "/api/v1/export/email",
            headers=auth_headers,
            json={
                "project_id": admin_project.id,
                "to_email": "recipient@example.com",
            },
        )

        assert response.status_code == 404


class TestGoogleDriveExport:
    """Tests for Google Drive export endpoints."""

    @pytest.mark.asyncio
    async def test_google_drive_auth_not_configured(
        self,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test Google Drive auth fails when not configured."""
        response = await client.post(
            "/api/v1/export/google-drive/auth",
            headers=auth_headers,
            json={
                "project_id": completed_project.id,
                "redirect_uri": "http://localhost:5173/oauth/callback",
            },
        )

        # Should fail because Google OAuth is not configured
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.export.google_drive_service")
    async def test_google_drive_auth_success(
        self,
        mock_drive_service,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test Google Drive auth returns authorization URL."""
        mock_drive_service.is_configured.return_value = True
        mock_drive_service.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?..."
        )

        response = await client.post(
            "/api/v1/export/google-drive/auth",
            headers=auth_headers,
            json={
                "project_id": completed_project.id,
                "redirect_uri": "http://localhost:5173/oauth/callback",
            },
        )

        assert response.status_code == 200
        assert "authorization_url" in response.json()

    @pytest.mark.asyncio
    async def test_google_drive_callback_not_configured(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        completed_project: Project,
    ):
        """Test Google Drive callback fails when not configured."""
        response = await client.post(
            "/api/v1/export/google-drive/callback",
            headers=auth_headers,
            json={
                "code": "auth_code",
                "state": f"{test_user.id}:{completed_project.id}",
                "redirect_uri": "http://localhost:5173/oauth/callback",
            },
        )

        assert response.status_code == 503

    @pytest.mark.asyncio
    @patch("app.routers.export.google_drive_service")
    async def test_google_drive_callback_invalid_state(
        self,
        mock_drive_service,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test Google Drive callback fails with invalid state."""
        mock_drive_service.is_configured.return_value = True

        response = await client.post(
            "/api/v1/export/google-drive/callback",
            headers=auth_headers,
            json={
                "code": "auth_code",
                "state": "invalid_state",  # Not user_id:project_id format
                "redirect_uri": "http://localhost:5173/oauth/callback",
            },
        )

        assert response.status_code == 400
        assert "state" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_google_drive_upload_no_transcription(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test Google Drive upload fails without transcription."""
        response = await client.post(
            "/api/v1/export/google-drive/upload",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "access_token": "fake_token",
            },
        )

        assert response.status_code == 400
        assert "transcription" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.export.google_drive_service")
    async def test_google_drive_upload_success(
        self,
        mock_drive_service,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test successful Google Drive upload."""
        mock_drive_service.create_folder = AsyncMock(return_value={"id": "folder_id"})
        mock_drive_service.upload_document = AsyncMock(
            return_value={
                "file_id": "file_123",
                "web_view_link": "https://drive.google.com/file/d/file_123/view",
            }
        )

        response = await client.post(
            "/api/v1/export/google-drive/upload",
            headers=auth_headers,
            json={
                "project_id": completed_project.id,
                "access_token": "valid_token",
                "folder_name": "Scribber",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_id"] == "file_123"
        assert "web_view_link" in data
