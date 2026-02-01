"""
Tests for admin endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models import User, ModelConfig, Project


class TestAdminAccess:
    """Tests for admin access control."""

    @pytest.mark.asyncio
    async def test_admin_endpoint_as_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test admin can access admin endpoints."""
        response = await client.get("/api/v1/admin/users/stats", headers=admin_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_endpoint_as_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test regular user cannot access admin endpoints."""
        response = await client.get("/api/v1/admin/users/stats", headers=auth_headers)

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_endpoint_unauthenticated(self, client: AsyncClient):
        """Test unauthenticated user cannot access admin endpoints."""
        response = await client.get("/api/v1/admin/users/stats")

        assert response.status_code == 401


class TestAdminModels:
    """Tests for admin model management."""

    @pytest.mark.asyncio
    async def test_list_models_includes_inactive(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        transcription_model: ModelConfig,
    ):
        """Test admin can see inactive models."""
        # Create inactive model
        inactive = ModelConfig(
            name="inactive",
            display_name="Inactive",
            provider="openai",
            model_type="transcription",
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/models?include_inactive=true",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        names = [m["name"] for m in data]
        assert "inactive" in names

    @pytest.mark.asyncio
    async def test_create_model(self, client: AsyncClient, admin_headers: dict):
        """Test admin can create a model."""
        response = await client.post(
            "/api/v1/admin/models",
            headers=admin_headers,
            json={
                "name": "new-model",
                "display_name": "New Model",
                "provider": "openai",
                "model_type": "transcription",
                "is_active": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-model"
        assert data["display_name"] == "New Model"

    @pytest.mark.asyncio
    async def test_create_duplicate_model(
        self,
        client: AsyncClient,
        admin_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test creating model with duplicate name fails."""
        response = await client.post(
            "/api/v1/admin/models",
            headers=admin_headers,
            json={
                "name": transcription_model.name,
                "display_name": "Duplicate",
                "provider": "openai",
                "model_type": "transcription",
            },
        )

        assert response.status_code == 400
        assert "exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_model(
        self,
        client: AsyncClient,
        admin_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test admin can update a model."""
        response = await client.put(
            f"/api/v1/admin/models/{transcription_model.id}",
            headers=admin_headers,
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_toggle_model(
        self,
        client: AsyncClient,
        admin_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test admin can toggle model active status."""
        # Model starts active
        assert transcription_model.is_active is True

        response = await client.post(
            f"/api/v1/admin/models/{transcription_model.id}/toggle",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_model(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
    ):
        """Test admin can delete a model."""
        model = ModelConfig(
            name="to-delete",
            display_name="To Delete",
            provider="openai",
            model_type="transcription",
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        response = await client.delete(
            f"/api/v1/admin/models/{model.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()


class TestAdminUsers:
    """Tests for admin user management."""

    @pytest.mark.asyncio
    async def test_get_user_stats(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test getting user statistics."""
        response = await client.get("/api/v1/admin/users/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "admin_users" in data
        assert data["total_users"] >= 1

    @pytest.mark.asyncio
    async def test_list_users(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        admin_user: User,
    ):
        """Test listing users."""
        response = await client.get("/api/v1/admin/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_users_with_filter(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        admin_user: User,
    ):
        """Test listing users with admin filter."""
        response = await client.get(
            "/api/v1/admin/users?is_admin=true",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["is_admin"] is True

    @pytest.mark.asyncio
    async def test_list_users_with_search(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test listing users with search."""
        response = await client.get(
            f"/api/v1/admin/users?search={test_user.email}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) >= 1
        assert any(u["email"] == test_user.email for u in data["users"])

    @pytest.mark.asyncio
    async def test_get_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test getting a specific user."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test updating a user."""
        response = await client.put(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers,
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_toggle_user_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test toggling user admin status."""
        assert test_user.is_admin is False

        response = await client.post(
            f"/api/v1/admin/users/{test_user.id}/toggle-admin",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_admin"] is True

    @pytest.mark.asyncio
    async def test_cannot_remove_own_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
        admin_user: User,
    ):
        """Test admin cannot remove their own admin status."""
        response = await client.post(
            f"/api/v1/admin/users/{admin_user.id}/toggle-admin",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "own" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_toggle_user_active(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """Test toggling user active status."""
        assert test_user.is_active is True

        response = await client.post(
            f"/api/v1/admin/users/{test_user.id}/toggle-active",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_cannot_deactivate_self(
        self,
        client: AsyncClient,
        admin_headers: dict,
        admin_user: User,
    ):
        """Test admin cannot deactivate themselves."""
        response = await client.post(
            f"/api/v1/admin/users/{admin_user.id}/toggle-active",
            headers=admin_headers,
        )

        assert response.status_code == 400


class TestAdminUsage:
    """Tests for admin usage statistics."""

    @pytest.mark.asyncio
    async def test_get_usage_summary(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test getting usage summary."""
        response = await client.get("/api/v1/admin/usage/summary", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "total_transcriptions" in data
        assert "total_summaries" in data

    @pytest.mark.asyncio
    async def test_get_daily_usage(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test getting daily usage data."""
        response = await client.get(
            "/api/v1/admin/usage/daily?days=7",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 8  # 7 days + today

    @pytest.mark.asyncio
    async def test_get_usage_by_model(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test getting usage by model."""
        response = await client.get("/api/v1/admin/usage/by-model", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_top_users(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test getting top users."""
        response = await client.get("/api/v1/admin/usage/top-users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_usage_logs(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test getting usage logs."""
        response = await client.get("/api/v1/admin/usage/logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
