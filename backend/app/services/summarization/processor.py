"""
Summarization processing logic for Celery tasks.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.project import Project, ProjectStatus
from app.models.model_config import ModelConfig
from app.models.usage_log import UsageLog, OperationType
from app.services.summarization.factory import get_summarization_service


def process_summarization(project_id: int, model_id: int) -> None:
    """
    Process summarization for a project (sync wrapper for Celery).

    Args:
        project_id: ID of the project to summarize
        model_id: ID of the summarization model to use
    """
    asyncio.run(_process_summarization_async(project_id, model_id))


async def _process_summarization_async(project_id: int, model_id: int) -> None:
    """
    Async implementation of summarization processing.

    Args:
        project_id: ID of the project to summarize
        model_id: ID of the summarization model to use
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

            if not project.transcription:
                raise ValueError(f"Project {project_id} has no transcription to summarize")

            # Fetch model configuration
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.id == model_id)
            )
            model_config = result.scalar_one_or_none()

            if not model_config:
                raise ValueError(f"Model {model_id} not found")

            # Update project status
            project.status = ProjectStatus.SUMMARIZING
            project.summarization_model_id = model_id
            await db.commit()

            # Get summarization service
            service = get_summarization_service(model_config)

            # Perform summarization
            result = await service.summarize(project.transcription)

            # Update project with summary
            project.summary = result.summary
            project.status = ProjectStatus.COMPLETED
            project.error_message = None

            # Log usage
            metadata = result.metadata or {}
            input_tokens = metadata.get("input_tokens") or metadata.get("prompt_tokens") or 0
            output_tokens = metadata.get("output_tokens") or metadata.get("completion_tokens") or 0

            usage_log = UsageLog(
                user_id=project.user_id,
                project_id=project.id,
                model_id=model_id,
                operation=OperationType.SUMMARIZATION,
                tokens_used=result.tokens_used,
                estimated_cost=Decimal(str(service.estimate_cost(input_tokens, output_tokens))),
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
