"""
Tests for projects endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models import User, Project, ModelConfig


class TestListProjects:
    """Tests for GET /api/v1/projects"""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing projects when none exist."""
        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_projects_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test listing projects returns user's projects."""
        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_project.id
        assert data[0]["title"] == test_project.title

    @pytest.mark.asyncio
    async def test_list_projects_only_own(
        self,
        client: AsyncClient,
        db_session,
        auth_headers: dict,
        test_project: Project,
        admin_user: User,
        transcription_model: ModelConfig,
    ):
        """Test user only sees their own projects."""
        # Create a project for another user
        other_project = Project(
            user_id=admin_user.id,
            title="Admin's Project",
            status="pending",
            transcription_model_id=transcription_model.id,
        )
        db_session.add(other_project)
        await db_session.commit()

        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_project.id

    @pytest.mark.asyncio
    async def test_list_projects_unauthenticated(self, client: AsyncClient):
        """Test listing projects without auth fails."""
        response = await client.get("/api/v1/projects")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_projects_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_user: User,
        transcription_model: ModelConfig,
    ):
        """Test listing projects with pagination."""
        # Create 15 projects
        for i in range(15):
            project = Project(
                user_id=test_user.id,
                title=f"Project {i}",
                status="pending",
                transcription_model_id=transcription_model.id,
            )
            db_session.add(project)
        await db_session.commit()

        # Get first page
        response = await client.get(
            "/api/v1/projects?skip=0&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert len(response.json()) == 10

        # Get second page
        response = await client.get(
            "/api/v1/projects?skip=10&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert len(response.json()) == 5


class TestGetProject:
    """Tests for GET /api/v1/projects/{id}"""

    @pytest.mark.asyncio
    async def test_get_project_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test getting a specific project."""
        response = await client.get(
            f"/api/v1/projects/{test_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project.id
        assert data["title"] == test_project.title

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting nonexistent project fails."""
        response = await client.get("/api/v1/projects/99999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        admin_user: User,
        transcription_model: ModelConfig,
    ):
        """Test getting another user's project fails."""
        other_project = Project(
            user_id=admin_user.id,
            title="Admin's Project",
            status="pending",
            transcription_model_id=transcription_model.id,
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.get(
            f"/api/v1/projects/{other_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestCreateProject:
    """Tests for POST /api/v1/projects"""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test creating a project."""
        response = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "title": "My New Project",
                "transcription_model_id": transcription_model.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My New Project"
        assert data["status"] == "pending"
        assert data["transcription_model_id"] == transcription_model.id

    @pytest.mark.asyncio
    async def test_create_project_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        transcription_model: ModelConfig,
    ):
        """Test creating a project with minimal data."""
        response = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Minimal Project"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Project"

    @pytest.mark.asyncio
    async def test_create_project_unauthenticated(self, client: AsyncClient):
        """Test creating project without auth fails."""
        response = await client.post(
            "/api/v1/projects",
            json={"title": "Test"},
        )

        assert response.status_code == 401


class TestUpdateProject:
    """Tests for PUT /api/v1/projects/{id}"""

    @pytest.mark.asyncio
    async def test_update_project_title(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test updating project title."""
        response = await client.put(
            f"/api/v1/projects/{test_project.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_project_transcription(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test updating project transcription."""
        response = await client.put(
            f"/api/v1/projects/{test_project.id}",
            headers=auth_headers,
            json={"transcription": "Updated transcription text."},
        )

        assert response.status_code == 200
        assert response.json()["transcription"] == "Updated transcription text."

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test updating nonexistent project fails."""
        response = await client.put(
            "/api/v1/projects/99999",
            headers=auth_headers,
            json={"title": "Test"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        admin_user: User,
        transcription_model: ModelConfig,
    ):
        """Test updating another user's project fails."""
        other_project = Project(
            user_id=admin_user.id,
            title="Admin's Project",
            status="pending",
            transcription_model_id=transcription_model.id,
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.put(
            f"/api/v1/projects/{other_project.id}",
            headers=auth_headers,
            json={"title": "Hacked!"},
        )

        assert response.status_code == 404


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{id}"""

    @pytest.mark.asyncio
    async def test_delete_project_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test deleting a project."""
        response = await client.delete(
            f"/api/v1/projects/{test_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/v1/projects/{test_project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test deleting nonexistent project fails."""
        response = await client.delete("/api/v1/projects/99999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        admin_user: User,
        transcription_model: ModelConfig,
    ):
        """Test deleting another user's project fails."""
        other_project = Project(
            user_id=admin_user.id,
            title="Admin's Project",
            status="pending",
            transcription_model_id=transcription_model.id,
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.delete(
            f"/api/v1/projects/{other_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestProjectStatus:
    """Tests for GET /api/v1/projects/{id}/status"""

    @pytest.mark.asyncio
    async def test_get_project_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: Project,
    ):
        """Test getting project status."""
        response = await client.get(
            f"/api/v1/projects/{test_project.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == test_project.status
        assert "has_transcription" in data
        assert "has_summary" in data

    @pytest.mark.asyncio
    async def test_get_completed_project_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        completed_project: Project,
    ):
        """Test getting completed project status."""
        response = await client.get(
            f"/api/v1/projects/{completed_project.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["has_transcription"] is True
        assert data["has_summary"] is True
