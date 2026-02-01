"""
Tests for models endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models import User, ModelConfig


class TestListModels:
    """Tests for GET /api/v1/models"""

    @pytest.mark.asyncio
    async def test_list_models_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing models when none exist."""
        response = await client.get("/api/v1/models", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["transcription"] == []
        assert data["summarization"] == []

    @pytest.mark.asyncio
    async def test_list_models_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        transcription_model: ModelConfig,
        summarization_model: ModelConfig,
    ):
        """Test listing models returns active models."""
        response = await client.get("/api/v1/models", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert len(data["transcription"]) == 1
        assert data["transcription"][0]["id"] == transcription_model.id
        assert data["transcription"][0]["display_name"] == transcription_model.display_name

        assert len(data["summarization"]) == 1
        assert data["summarization"][0]["id"] == summarization_model.id

    @pytest.mark.asyncio
    async def test_list_models_excludes_inactive(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        transcription_model: ModelConfig,
    ):
        """Test listing models excludes inactive models."""
        # Create an inactive model
        inactive_model = ModelConfig(
            name="inactive-model",
            display_name="Inactive Model",
            provider="openai",
            model_type="transcription",
            is_active=False,
            is_default=False,
        )
        db_session.add(inactive_model)
        await db_session.commit()

        response = await client.get("/api/v1/models", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["transcription"]) == 1
        assert data["transcription"][0]["id"] == transcription_model.id

    @pytest.mark.asyncio
    async def test_list_models_unauthenticated(self, client: AsyncClient):
        """Test listing models without auth fails."""
        response = await client.get("/api/v1/models")

        assert response.status_code == 401


class TestGetModel:
    """Tests for GET /api/v1/models/{id}"""

    @pytest.mark.asyncio
    async def test_get_model_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test getting a specific model."""
        response = await client.get(
            f"/api/v1/models/{transcription_model.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transcription_model.id
        assert data["name"] == transcription_model.name
        assert data["display_name"] == transcription_model.display_name
        assert data["provider"] == transcription_model.provider
        assert data["model_type"] == transcription_model.model_type

    @pytest.mark.asyncio
    async def test_get_model_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting nonexistent model fails."""
        response = await client.get("/api/v1/models/99999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_inactive_model(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
    ):
        """Test getting inactive model still works (for existing projects)."""
        inactive_model = ModelConfig(
            name="inactive-model",
            display_name="Inactive Model",
            provider="openai",
            model_type="transcription",
            is_active=False,
            is_default=False,
        )
        db_session.add(inactive_model)
        await db_session.commit()
        await db_session.refresh(inactive_model)

        response = await client.get(
            f"/api/v1/models/{inactive_model.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestModelDefaults:
    """Tests for default model functionality."""

    @pytest.mark.asyncio
    async def test_default_models_marked(
        self,
        client: AsyncClient,
        auth_headers: dict,
        transcription_model: ModelConfig,
        summarization_model: ModelConfig,
    ):
        """Test that default models are properly marked."""
        response = await client.get("/api/v1/models", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Check transcription default
        trans_model = data["transcription"][0]
        assert trans_model["is_default"] is True

        # Check summarization default
        sum_model = data["summarization"][0]
        assert sum_model["is_default"] is True

    @pytest.mark.asyncio
    async def test_multiple_models_one_default(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        transcription_model: ModelConfig,
    ):
        """Test that only one model per type is default."""
        # Create another transcription model (not default)
        other_model = ModelConfig(
            name="other-whisper",
            display_name="Other Whisper",
            provider="openai",
            model_type="transcription",
            is_active=True,
            is_default=False,
        )
        db_session.add(other_model)
        await db_session.commit()

        response = await client.get("/api/v1/models", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        defaults = [m for m in data["transcription"] if m["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["id"] == transcription_model.id
