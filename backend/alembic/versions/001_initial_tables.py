"""Initial tables for Scribber

Revision ID: 001_initial
Revises:
Create Date: 2024-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE modelprovider AS ENUM ('openai', 'anthropic', 'google', 'elevenlabs', 'qwen', 'local')")
    op.execute("CREATE TYPE modeltype AS ENUM ('transcription', 'summarization')")
    op.execute("CREATE TYPE projectstatus AS ENUM ('pending', 'uploading', 'transcribing', 'summarizing', 'completed', 'failed')")
    op.execute("CREATE TYPE operationtype AS ENUM ('transcription', 'summarization')")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # Create model_configs table
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.Enum("openai", "anthropic", "google", "elevenlabs", "qwen", "local", name="modelprovider"), nullable=False),
        sa.Column("model_type", sa.Enum("transcription", "summarization", name="modeltype"), nullable=False),
        sa.Column("api_endpoint", sa.String(length=500), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_configs_id"), "model_configs", ["id"], unique=False)
    op.create_index(op.f("ix_model_configs_name"), "model_configs", ["name"], unique=True)
    op.create_index(op.f("ix_model_configs_provider"), "model_configs", ["provider"], unique=False)
    op.create_index(op.f("ix_model_configs_model_type"), "model_configs", ["model_type"], unique=False)

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("audio_url", sa.String(length=1000), nullable=True),
        sa.Column("audio_filename", sa.String(length=255), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("audio_size_bytes", sa.Integer(), nullable=True),
        sa.Column("transcription", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("transcription_model_id", sa.Integer(), nullable=True),
        sa.Column("summarization_model_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("pending", "uploading", "transcribing", "summarizing", "completed", "failed", name="projectstatus"), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcription_model_id"], ["model_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["summarization_model_id"], ["model_configs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"], unique=False)
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)

    # Create usage_logs table
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.Enum("transcription", "summarization", name="operationtype"), nullable=False),
        sa.Column("input_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_id"], ["model_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_logs_id"), "usage_logs", ["id"], unique=False)
    op.create_index(op.f("ix_usage_logs_user_id"), "usage_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_usage_logs_project_id"), "usage_logs", ["project_id"], unique=False)
    op.create_index(op.f("ix_usage_logs_model_id"), "usage_logs", ["model_id"], unique=False)
    op.create_index(op.f("ix_usage_logs_operation"), "usage_logs", ["operation"], unique=False)
    op.create_index(op.f("ix_usage_logs_created_at"), "usage_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("usage_logs")
    op.drop_table("projects")
    op.drop_table("model_configs")
    op.drop_table("users")

    op.execute("DROP TYPE operationtype")
    op.execute("DROP TYPE projectstatus")
    op.execute("DROP TYPE modeltype")
    op.execute("DROP TYPE modelprovider")
