"""
Tests for export services.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.export.email import EmailService
from app.services.export.google_drive import GoogleDriveService


class TestEmailService:
    """Tests for EmailService."""

    @pytest.fixture
    def email_service_configured(self):
        """Create an email service with API key."""
        with patch("app.services.export.email.settings") as mock_settings:
            mock_settings.SENDGRID_API_KEY = "test-api-key"
            service = EmailService()
            service.api_key = "test-api-key"
            service.client = MagicMock()
            yield service

    @pytest.fixture
    def email_service_unconfigured(self):
        """Create an email service without API key."""
        with patch("app.services.export.email.settings") as mock_settings:
            mock_settings.SENDGRID_API_KEY = ""
            service = EmailService()
            service.api_key = ""
            service.client = None
            yield service

    def test_is_configured_true(self, email_service_configured):
        """Test is_configured returns True when configured."""
        assert email_service_configured.is_configured() is True

    def test_is_configured_false(self, email_service_unconfigured):
        """Test is_configured returns False when not configured."""
        assert email_service_unconfigured.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_transcription_not_configured(self, email_service_unconfigured):
        """Test send fails when not configured."""
        result = await email_service_unconfigured.send_transcription(
            to_email="test@example.com",
            project_title="Test",
            transcription="Test transcription",
        )

        assert result["success"] is False
        assert "not configured" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_send_transcription_success(self, email_service_configured):
        """Test successful email send."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        email_service_configured.client.send.return_value = mock_response

        result = await email_service_configured.send_transcription(
            to_email="test@example.com",
            project_title="Test Project",
            transcription="This is the transcription text.",
            summary="This is the summary.",
        )

        assert result["success"] is True
        email_service_configured.client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_transcription_failure(self, email_service_configured):
        """Test email send failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        email_service_configured.client.send.return_value = mock_response

        result = await email_service_configured.send_transcription(
            to_email="test@example.com",
            project_title="Test",
            transcription="Test",
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_transcription_exception(self, email_service_configured):
        """Test email send with exception."""
        email_service_configured.client.send.side_effect = Exception("Network error")

        result = await email_service_configured.send_transcription(
            to_email="test@example.com",
            project_title="Test",
            transcription="Test",
        )

        assert result["success"] is False
        assert "failed" in result["message"].lower()

    def test_build_html_content(self, email_service_configured):
        """Test HTML content building."""
        html = email_service_configured._build_html_content(
            title="Test Title",
            transcription="Test transcription content",
            summary="Test summary content",
        )

        assert "Test Title" in html
        assert "Test transcription content" in html
        assert "Test summary content" in html
        assert "<html>" in html

    def test_build_plain_content(self, email_service_configured):
        """Test plain text content building."""
        plain = email_service_configured._build_plain_content(
            title="Test Title",
            transcription="Test transcription",
            summary="Test summary",
        )

        assert "Test Title" in plain
        assert "Test transcription" in plain
        assert "Test summary" in plain
        assert "SUMMARY" in plain
        assert "TRANSCRIPTION" in plain

    def test_build_plain_content_no_summary(self, email_service_configured):
        """Test plain text content without summary."""
        plain = email_service_configured._build_plain_content(
            title="Test Title",
            transcription="Test transcription",
            summary=None,
        )

        assert "Test transcription" in plain
        assert "SUMMARY" not in plain


class TestGoogleDriveService:
    """Tests for GoogleDriveService."""

    @pytest.fixture
    def drive_service_configured(self):
        """Create a Google Drive service with credentials."""
        with patch("app.services.export.google_drive.settings") as mock_settings:
            mock_settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
            service = GoogleDriveService()
            yield service

    @pytest.fixture
    def drive_service_unconfigured(self):
        """Create a Google Drive service without credentials."""
        with patch("app.services.export.google_drive.settings") as mock_settings:
            mock_settings.GOOGLE_OAUTH_CLIENT_ID = ""
            mock_settings.GOOGLE_OAUTH_CLIENT_SECRET = ""
            service = GoogleDriveService()
            yield service

    def test_is_configured_true(self, drive_service_configured):
        """Test is_configured returns True when configured."""
        assert drive_service_configured.is_configured() is True

    def test_is_configured_false(self, drive_service_unconfigured):
        """Test is_configured returns False when not configured."""
        assert drive_service_unconfigured.is_configured() is False

    def test_get_authorization_url(self, drive_service_configured):
        """Test authorization URL generation."""
        url = drive_service_configured.get_authorization_url(
            redirect_uri="http://localhost:5173/oauth/callback",
            state="1:2",
        )

        assert "accounts.google.com" in url
        assert "client_id=test-client-id" in url
        assert "redirect_uri=" in url
        assert "state=1%3A2" in url  # URL encoded colon

    def test_get_authorization_url_not_configured(self, drive_service_unconfigured):
        """Test authorization URL fails when not configured."""
        with pytest.raises(ValueError) as exc_info:
            drive_service_unconfigured.get_authorization_url(
                redirect_uri="http://localhost:5173/oauth/callback",
                state="1:2",
            )

        assert "not configured" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("app.services.export.google_drive.httpx.AsyncClient")
    async def test_exchange_code_success(self, mock_client_class, drive_service_configured):
        """Test successful code exchange."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
        }
        mock_client.post.return_value = mock_response

        result = await drive_service_configured.exchange_code(
            code="test-auth-code",
            redirect_uri="http://localhost:5173/oauth/callback",
        )

        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"

    @pytest.mark.asyncio
    @patch("app.services.export.google_drive.httpx.AsyncClient")
    async def test_exchange_code_failure(self, mock_client_class, drive_service_configured):
        """Test code exchange failure."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        mock_client.post.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await drive_service_configured.exchange_code(
                code="invalid-code",
                redirect_uri="http://localhost:5173/oauth/callback",
            )

        assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("app.services.export.google_drive.httpx.AsyncClient")
    async def test_upload_document_success(self, mock_client_class, drive_service_configured):
        """Test successful document upload."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "file123",
            "name": "test.txt",
        }
        mock_client.post.return_value = mock_response

        result = await drive_service_configured.upload_document(
            access_token="test-token",
            title="Test Document",
            content="Test content here",
        )

        assert result["file_id"] == "file123"
        assert "web_view_link" in result
        assert "file123" in result["web_view_link"]

    @pytest.mark.asyncio
    @patch("app.services.export.google_drive.httpx.AsyncClient")
    async def test_upload_document_with_folder(self, mock_client_class, drive_service_configured):
        """Test document upload to specific folder."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "file123", "name": "test.txt"}
        mock_client.post.return_value = mock_response

        result = await drive_service_configured.upload_document(
            access_token="test-token",
            title="Test Document",
            content="Test content",
            folder_id="folder123",
        )

        assert result["file_id"] == "file123"
        # Verify folder_id was included in request
        call_args = mock_client.post.call_args
        assert "folder123" in str(call_args)

    @pytest.mark.asyncio
    @patch("app.services.export.google_drive.httpx.AsyncClient")
    async def test_create_folder_success(self, mock_client_class, drive_service_configured):
        """Test successful folder creation."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "folder123", "name": "Scribber"}
        mock_client.post.return_value = mock_response

        result = await drive_service_configured.create_folder(
            access_token="test-token",
            folder_name="Scribber",
        )

        assert result["id"] == "folder123"

    def test_build_multipart_body(self, drive_service_configured):
        """Test multipart body building."""
        body = drive_service_configured._build_multipart_body(
            metadata={"name": "test.txt", "mimeType": "text/plain"},
            content="Test content",
            boundary="test_boundary",
        )

        assert b"test_boundary" in body
        assert b"test.txt" in body
        assert b"Test content" in body
