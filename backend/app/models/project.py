"""
Project model for audio transcription projects.
"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.model_config import ModelConfig
    from app.models.usage_log import UsageLog


class ProjectStatus(str, enum.Enum):
    """Status of a transcription project."""
    PENDING = "pending"
    UPLOADING = "uploading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Audio transcription project."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    transcription_model_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        nullable=True
    )
    summarization_model_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        nullable=True
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProjectStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    user: Mapped["User"] = relationship("User", back_populates="projects")
    transcription_model: Mapped["ModelConfig | None"] = relationship(
        "ModelConfig",
        foreign_keys=[transcription_model_id],
        back_populates="projects_transcription"
    )
    summarization_model: Mapped["ModelConfig | None"] = relationship(
        "ModelConfig",
        foreign_keys=[summarization_model_id],
        back_populates="projects_summarization"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        "UsageLog",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, title={self.title}, status={self.status})>"
