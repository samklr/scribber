"""
Google Drive Export Service.
"""
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

# Scopes needed for Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveService:
    """Service for exporting to Google Drive."""

    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET

    def is_configured(self) -> bool:
        """Check if Google Drive service is properly configured."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URL
            state: State parameter for CSRF protection (e.g., user_id:project_id)

        Returns:
            Authorization URL to redirect user to
        """
        if not self.is_configured():
            raise ValueError("Google Drive service not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        if not self.is_configured():
            raise ValueError("Google Drive service not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authorization

        Returns:
            New token response with access_token
        """
        if not self.is_configured():
            raise ValueError("Google Drive service not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.status_code}")

            return response.json()

    async def upload_document(
        self,
        access_token: str,
        title: str,
        content: str,
        folder_id: Optional[str] = None,
        mime_type: str = "text/plain",
    ) -> dict:
        """
        Upload a document to Google Drive.

        Args:
            access_token: Valid OAuth access token
            title: Document title/filename
            content: Document content
            folder_id: Optional folder ID to upload to
            mime_type: MIME type of the document

        Returns:
            dict with file id and web view link
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        # Create file metadata
        metadata = {
            "name": f"{title}.txt",
            "mimeType": mime_type,
        }

        if folder_id:
            metadata["parents"] = [folder_id]

        async with httpx.AsyncClient() as client:
            # Multipart upload
            boundary = "scribber_boundary"
            body = self._build_multipart_body(metadata, content, boundary)

            response = await client.post(
                f"{GOOGLE_DRIVE_UPLOAD_URL}?uploadType=multipart",
                headers={
                    **headers,
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                content=body,
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Drive upload failed: {response.text}")
                raise ValueError(f"Drive upload failed: {response.status_code}")

            file_data = response.json()

            # Get web view link
            file_id = file_data.get("id")
            web_link = f"https://drive.google.com/file/d/{file_id}/view"

            return {
                "file_id": file_id,
                "name": file_data.get("name"),
                "web_view_link": web_link,
            }

    def _build_multipart_body(
        self,
        metadata: dict,
        content: str,
        boundary: str,
    ) -> bytes:
        """Build multipart body for Drive upload."""
        import json

        parts = [
            f"--{boundary}",
            "Content-Type: application/json; charset=UTF-8",
            "",
            json.dumps(metadata),
            f"--{boundary}",
            "Content-Type: text/plain",
            "",
            content,
            f"--{boundary}--",
        ]

        return "\r\n".join(parts).encode("utf-8")

    async def create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_id: Optional[str] = None,
    ) -> dict:
        """
        Create a folder in Google Drive.

        Args:
            access_token: Valid OAuth access token
            folder_name: Name for the new folder
            parent_id: Optional parent folder ID

        Returns:
            dict with folder id
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            metadata["parents"] = [parent_id]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_DRIVE_FILES_URL,
                headers=headers,
                json=metadata,
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Folder creation failed: {response.text}")
                raise ValueError(f"Folder creation failed: {response.status_code}")

            return response.json()
