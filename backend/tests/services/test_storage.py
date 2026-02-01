"""
Tests for storage service.
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.services.storage import LocalStorageService


class TestLocalStorageService:
    """Tests for LocalStorageService."""

    @pytest.fixture
    def storage_dir(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage_service(self, storage_dir):
        """Create a storage service with temp directory."""
        return LocalStorageService(base_path=storage_dir)

    @pytest.fixture
    def sample_file(self):
        """Create a sample file for upload."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Hello, World!")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_save_file(self, storage_service, sample_file):
        """Test saving a file."""
        with open(sample_file, "rb") as f:
            content = f.read()

        url = await storage_service.save_file(
            content=content,
            filename="test.txt",
            user_id=1,
        )

        assert url is not None
        assert "test.txt" in url or "1" in url

    @pytest.mark.asyncio
    async def test_save_file_custom_folder(self, storage_service, sample_file):
        """Test saving a file to a custom folder."""
        with open(sample_file, "rb") as f:
            content = f.read()

        url = await storage_service.save_file(
            content=content,
            filename="test.txt",
            user_id=1,
            folder="custom",
        )

        assert url is not None
        assert "custom" in url

    @pytest.mark.asyncio
    async def test_get_file(self, storage_service, sample_file):
        """Test retrieving a saved file."""
        original_content = b"Test content for retrieval"

        url = await storage_service.save_file(
            content=original_content,
            filename="retrieve_test.txt",
            user_id=1,
        )

        retrieved_content = await storage_service.get_file(url)

        assert retrieved_content == original_content

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, storage_service):
        """Test retrieving nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            await storage_service.get_file("/nonexistent/path.txt")

    @pytest.mark.asyncio
    async def test_delete_file(self, storage_service, sample_file):
        """Test deleting a file."""
        with open(sample_file, "rb") as f:
            content = f.read()

        url = await storage_service.save_file(
            content=content,
            filename="delete_test.txt",
            user_id=1,
        )

        # Verify file exists
        local_path = storage_service.get_local_path(url)
        assert os.path.exists(local_path)

        # Delete file
        result = await storage_service.delete_file(url)
        assert result is True

        # Verify file is deleted
        assert not os.path.exists(local_path)

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, storage_service):
        """Test deleting nonexistent file returns False."""
        result = await storage_service.delete_file("/nonexistent/path.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists(self, storage_service, sample_file):
        """Test checking if file exists."""
        with open(sample_file, "rb") as f:
            content = f.read()

        url = await storage_service.save_file(
            content=content,
            filename="exists_test.txt",
            user_id=1,
        )

        assert await storage_service.file_exists(url) is True
        assert await storage_service.file_exists("/nonexistent/path.txt") is False

    def test_get_local_path(self, storage_service):
        """Test getting local path from URL."""
        url = "/uploads/1/test.txt"
        local_path = storage_service.get_local_path(url)

        assert local_path is not None
        assert "1" in local_path
        assert "test.txt" in local_path

    @pytest.mark.asyncio
    async def test_generate_unique_filename(self, storage_service):
        """Test that duplicate filenames get unique names."""
        content = b"Test content"

        # Save same filename twice
        url1 = await storage_service.save_file(
            content=content,
            filename="duplicate.txt",
            user_id=1,
        )
        url2 = await storage_service.save_file(
            content=content,
            filename="duplicate.txt",
            user_id=1,
        )

        # Both should exist but with different names
        assert url1 != url2
        assert await storage_service.file_exists(url1)
        assert await storage_service.file_exists(url2)

    @pytest.mark.asyncio
    async def test_save_audio_file(self, storage_service, temp_audio_file):
        """Test saving an audio file."""
        with open(temp_audio_file, "rb") as f:
            content = f.read()

        url = await storage_service.save_file(
            content=content,
            filename="audio.wav",
            user_id=1,
            folder="audio",
        )

        assert url is not None
        assert ".wav" in url

        # Verify we can retrieve it
        retrieved = await storage_service.get_file(url)
        assert retrieved == content


class TestStorageServiceValidation:
    """Tests for storage service validation."""

    @pytest.fixture
    def storage_service(self):
        """Create a storage service with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorageService(base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_empty_content(self, storage_service):
        """Test saving empty content."""
        # Should handle empty content gracefully
        url = await storage_service.save_file(
            content=b"",
            filename="empty.txt",
            user_id=1,
        )
        assert url is not None

    @pytest.mark.asyncio
    async def test_large_file(self, storage_service):
        """Test saving a larger file."""
        # Create 1MB of content
        content = b"x" * (1024 * 1024)

        url = await storage_service.save_file(
            content=content,
            filename="large.bin",
            user_id=1,
        )

        assert url is not None
        retrieved = await storage_service.get_file(url)
        assert len(retrieved) == len(content)

    @pytest.mark.asyncio
    async def test_special_characters_in_filename(self, storage_service):
        """Test handling special characters in filename."""
        content = b"Test content"

        # Filename with spaces and special chars
        url = await storage_service.save_file(
            content=content,
            filename="my file (copy) [1].txt",
            user_id=1,
        )

        assert url is not None
        assert await storage_service.file_exists(url)
