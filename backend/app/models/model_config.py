"""
Model configuration for transcription and summarization models.
"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.usage_log import UsageLog


class ModelProvider(str, enum.Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    ELEVENLABS = "elevenlabs"
    QWEN = "qwen"
    LOCAL = "local"


class ModelType(str, enum.Enum):
    """Type of AI model."""
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"


class ModelConfig(Base):
    """Configuration for AI models (transcription and summarization)."""

    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[ModelProvider] = mapped_column(
        Enum(ModelProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    model_type: Mapped[ModelType] = mapped_column(
        Enum(ModelType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    projects_transcription: Mapped[list["Project"]] = relationship(
        "Project",
        foreign_keys="Project.transcription_model_id",
        back_populates="transcription_model"
    )
    projects_summarization: Mapped[list["Project"]] = relationship(
        "Project",
        foreign_keys="Project.summarization_model_id",
        back_populates="summarization_model"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        "UsageLog",
        back_populates="model"
    )

    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, name={self.name}, type={self.model_type})>"
