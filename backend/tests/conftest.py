"""
Pytest configuration and fixtures for Scribber tests.
"""
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Project, ModelConfig, UsageLog
from app.routers.auth import get_password_hash, create_access_token

# Use SQLite for tests (async via aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create an access token for the test user."""
    return create_access_token({"sub": test_user.email})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create an access token for the admin user."""
    return create_access_token({"sub": admin_user.email})


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """Get authorization headers for a regular user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Get authorization headers for an admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def transcription_model(db_session: AsyncSession) -> ModelConfig:
    """Create a test transcription model."""
    model = ModelConfig(
        name="test-whisper",
        display_name="Test Whisper",
        provider="openai",
        model_type="transcription",
        is_active=True,
        is_default=True,
        config_json={"model": "whisper-1"},
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def summarization_model(db_session: AsyncSession) -> ModelConfig:
    """Create a test summarization model."""
    model = ModelConfig(
        name="test-gpt",
        display_name="Test GPT",
        provider="openai",
        model_type="summarization",
        is_active=True,
        is_default=True,
        config_json={"model": "gpt-4o-mini"},
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def test_project(
    db_session: AsyncSession,
    test_user: User,
    transcription_model: ModelConfig,
) -> Project:
    """Create a test project."""
    project = Project(
        user_id=test_user.id,
        title="Test Project",
        status="pending",
        transcription_model_id=transcription_model.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def completed_project(
    db_session: AsyncSession,
    test_user: User,
    transcription_model: ModelConfig,
    summarization_model: ModelConfig,
) -> Project:
    """Create a completed test project with transcription and summary."""
    project = Project(
        user_id=test_user.id,
        title="Completed Project",
        audio_filename="test.mp3",
        audio_url="/uploads/test.mp3",
        transcription="This is a test transcription. It contains multiple sentences.",
        summary="This is a test summary.",
        status="completed",
        transcription_model_id=transcription_model.id,
        summarization_model_id=summarization_model.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def temp_audio_file() -> Generator[str, None, None]:
    """Create a temporary audio file for testing."""
    # Create a minimal valid audio file header (WAV format)
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk1Size (16 for PCM)
        0x01, 0x00,              # AudioFormat (1 = PCM)
        0x01, 0x00,              # NumChannels (1 = mono)
        0x44, 0xAC, 0x00, 0x00,  # SampleRate (44100)
        0x88, 0x58, 0x01, 0x00,  # ByteRate
        0x02, 0x00,              # BlockAlign
        0x10, 0x00,              # BitsPerSample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Subchunk2Size
    ])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_header)
        f.write(b"\x00" * 1000)  # Add some silence
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def upload_dir() -> Generator[str, None, None]:
    """Create a temporary upload directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch settings to use temp directory
        original_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = tmpdir
        yield tmpdir
        if original_upload_dir:
            os.environ["UPLOAD_DIR"] = original_upload_dir
        elif "UPLOAD_DIR" in os.environ:
            del os.environ["UPLOAD_DIR"]
