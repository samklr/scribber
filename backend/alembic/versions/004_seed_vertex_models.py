"""Seed Vertex AI Gemini models

Revision ID: 004_seed_vertex
Revises: 003_seed_users
Create Date: 2024-02-03

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_seed_vertex"
down_revision: Union[str, None] = "003_seed_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert Vertex AI Gemini models for summarization using raw SQL
    # to properly handle PostgreSQL ENUM types
    op.execute("""
        INSERT INTO model_configs (id, name, display_name, provider, model_type, is_active, is_default, config_json, description)
        VALUES
        (
            9,
            'gemini-1.5-flash',
            'Gemini 1.5 Flash',
            'google'::modelprovider,
            'summarization'::modeltype,
            true,
            false,
            '{"model": "gemini-1.5-flash-002", "max_tokens": 4000, "temperature": 0.3, "location": "us-central1"}'::jsonb,
            'Fast and efficient Gemini model for summarization. Best for quick summaries.'
        ),
        (
            10,
            'gemini-1.5-pro',
            'Gemini 1.5 Pro',
            'google'::modelprovider,
            'summarization'::modeltype,
            true,
            false,
            '{"model": "gemini-1.5-pro-002", "max_tokens": 8000, "temperature": 0.3, "location": "us-central1"}'::jsonb,
            'Most capable Gemini model for complex summarization tasks.'
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model_configs WHERE name IN ('gemini-1.5-flash', 'gemini-1.5-pro')")
