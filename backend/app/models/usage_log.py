"""
Usage log model for tracking API usage and costs.
"""
import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.model_config import ModelConfig


class OperationType(str, enum.Enum):
    """Type of operation logged."""
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"


class UsageLog(Base):
    """Log of API usage for billing and analytics."""

    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    operation: Mapped[OperationType] = mapped_column(
        Enum(OperationType),
        nullable=False,
        index=True
    )
    input_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_logs")
    project: Mapped["Project | None"] = relationship("Project", back_populates="usage_logs")
    model: Mapped["ModelConfig"] = relationship("ModelConfig", back_populates="usage_logs")

    def __repr__(self) -> str:
        return f"<UsageLog(id={self.id}, user_id={self.user_id}, operation={self.operation})>"
