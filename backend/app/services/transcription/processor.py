"""
Transcription processing logic for Celery tasks.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.project import Project, ProjectStatus
from app.models.model_config import ModelConfig
from app.models.usage_log import UsageLog, OperationType
from app.services.storage import get_storage_service
from app.services.transcription.factory import get_transcription_service


def process_transcription(project_id: int, model_id: int) -> None:
    """
    Process transcription for a project (sync wrapper for Celery).

    Args:
        project_id: ID of the project to transcribe
        model_id: ID of the transcription model to use
    """
    asyncio.run(_process_transcription_async(project_id, model_id))


async def _process_transcription_async(project_id: int, model_id: int) -> None:
    """
    Async implementation of transcription processing.

    Args:
        project_id: ID of the project to transcribe
        model_id: ID of the transcription model to use
    """
    # Create a new database session for this task
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Fetch project
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            if not project.audio_url:
                raise ValueError(f"Project {project_id} has no audio file")

            # Fetch model configuration
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.id == model_id)
            )
            model_config = result.scalar_one_or_none()

            if not model_config:
                raise ValueError(f"Model {model_id} not found")

            # Update project status
            project.status = ProjectStatus.TRANSCRIBING
            project.transcription_model_id = model_id
            await db.commit()

            # Get storage service and file path
            storage = get_storage_service()
            audio_path = await storage.get_file_path(project.audio_url)

            # Get transcription service
            service = get_transcription_service(model_config)

            # Perform transcription
            result = await service.transcribe(audio_path)

            # Update project with transcription
            project.transcription = result.text
            project.audio_duration_seconds = result.duration_seconds
            project.status = ProjectStatus.COMPLETED
            project.error_message = None

            # Log usage
            usage_log = UsageLog(
                user_id=project.user_id,
                project_id=project.id,
                model_id=model_id,
                operation=OperationType.TRANSCRIPTION,
                input_size_bytes=project.audio_size_bytes,
                duration_seconds=result.duration_seconds,
                estimated_cost=Decimal(str(service.estimate_cost(result.duration_seconds or 0))),
            )
            db.add(usage_log)

            await db.commit()

        except Exception as e:
            # Update project with error
            if project:
                project.status = ProjectStatus.FAILED
                project.error_message = str(e)
                await db.commit()
            raise

        finally:
            await engine.dispose()
