"""
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models import User


class TestAuthRegister:
    """Tests for POST /api/v1/auth/register"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert "hashed_password" not in data["user"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword123",
                "name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
                "name": "Test",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "short",
                "name": "Test",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_without_name(self, client: AsyncClient):
        """Test registration without name succeeds."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "noname@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["name"] is None


class TestAuthLogin:
    """Tests for POST /api/v1/auth/login"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepassword123",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session, test_user: User):
        """Test login with inactive user fails."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 401


class TestAuthMe:
    """Tests for GET /api/v1/auth/me"""

    @pytest.mark.asyncio
    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user info when authenticated."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user info without auth fails."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        """Test getting current user info with invalid token fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )

        assert response.status_code == 401


class TestAuthLogout:
    """Tests for POST /api/v1/auth/logout"""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Test logout without auth fails."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401
