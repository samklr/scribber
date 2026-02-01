"""
File storage service with local and GCS support.
"""
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import aiofiles
import aiofiles.os

from app.config import settings


class StorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        user_id: int,
        project_id: int,
    ) -> str:
        """Upload a file and return its URL/path."""
        pass

    @abstractmethod
    async def get_file_path(self, url: str) -> str:
        """Get the local file path for a URL."""
        pass

    @abstractmethod
    async def delete_file(self, url: str) -> bool:
        """Delete a file by its URL."""
        pass

    @abstractmethod
    async def file_exists(self, url: str) -> bool:
        """Check if a file exists."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage service."""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_project_dir(self, user_id: int, project_id: int) -> Path:
        """Get the directory path for a user's project."""
        return self.base_dir / str(user_id) / str(project_id)

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension."""
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4().hex[:12]
        return f"{unique_id}{ext}"

    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        user_id: int,
        project_id: int,
    ) -> str:
        """
        Upload a file to local storage.

        Returns the relative path that can be used to retrieve the file.
        """
        # Create directory structure
        project_dir = self._get_user_project_dir(user_id, project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_filename = self._generate_unique_filename(filename)
        file_path = project_dir / unique_filename

        # Write file asynchronously
        content = file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Return relative path as URL
        relative_path = str(file_path.relative_to(self.base_dir))
        return f"/uploads/{relative_path}"

    async def get_file_path(self, url: str) -> str:
        """Get the absolute file path for a URL."""
        # Remove /uploads/ prefix if present
        if url.startswith("/uploads/"):
            relative_path = url[9:]  # len("/uploads/") = 9
        else:
            relative_path = url

        return str(self.base_dir / relative_path)

    async def delete_file(self, url: str) -> bool:
        """Delete a file by its URL."""
        try:
            file_path = await self.get_file_path(url)
            if await aiofiles.os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    async def file_exists(self, url: str) -> bool:
        """Check if a file exists."""
        try:
            file_path = await self.get_file_path(url)
            return await aiofiles.os.path.exists(file_path)
        except Exception:
            return False

    async def get_file_size(self, url: str) -> int | None:
        """Get file size in bytes."""
        try:
            file_path = await self.get_file_path(url)
            stat = await aiofiles.os.stat(file_path)
            return stat.st_size
        except Exception:
            return None


# GCS Storage Service (for future implementation)
class GCSStorageService(StorageService):
    """Google Cloud Storage service (placeholder for future implementation)."""

    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        # TODO: Initialize GCS client
        # from google.cloud import storage
        # self.client = storage.Client()
        # self.bucket = self.client.bucket(self.bucket_name)

    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        user_id: int,
        project_id: int,
    ) -> str:
        """Upload a file to GCS."""
        raise NotImplementedError("GCS storage not yet implemented")

    async def get_file_path(self, url: str) -> str:
        """Get signed URL for GCS file."""
        raise NotImplementedError("GCS storage not yet implemented")

    async def delete_file(self, url: str) -> bool:
        """Delete a file from GCS."""
        raise NotImplementedError("GCS storage not yet implemented")

    async def file_exists(self, url: str) -> bool:
        """Check if a file exists in GCS."""
        raise NotImplementedError("GCS storage not yet implemented")


# Singleton storage service instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the configured storage service instance."""
    global _storage_service

    if _storage_service is None:
        # Use GCS if bucket is configured, otherwise local storage
        if settings.GCS_BUCKET_NAME:
            _storage_service = GCSStorageService(settings.GCS_BUCKET_NAME)
        else:
            _storage_service = LocalStorageService(settings.UPLOAD_DIR)

    return _storage_service
