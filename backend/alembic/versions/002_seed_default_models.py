"""Seed default models

Revision ID: 002_seed_models
Revises: 001_initial
Create Date: 2024-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_seed_models"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed default transcription models
    op.execute("""
        INSERT INTO model_configs (name, display_name, provider, model_type, is_active, is_default, description, config_json)
        VALUES
        (
            'whisper-large-v3',
            'Whisper Large V3',
            'openai',
            'transcription',
            true,
            true,
            'OpenAI Whisper Large V3 - High accuracy transcription with support for 99+ languages',
            '{"model": "whisper-1", "response_format": "verbose_json"}'
        ),
        (
            'google-speech-to-text',
            'Google Cloud Speech-to-Text',
            'google',
            'transcription',
            true,
            false,
            'Google Cloud Speech-to-Text - Real-time speech recognition with excellent accuracy',
            '{"model": "latest_long", "language_code": "en-US"}'
        ),
        (
            'elevenlabs-speech-to-text',
            'Eleven Labs Speech-to-Text',
            'elevenlabs',
            'transcription',
            true,
            false,
            'Eleven Labs Speech-to-Text - High-quality transcription optimized for voice cloning',
            '{}'
        ),
        (
            'qwen-audio',
            'Qwen Audio',
            'qwen',
            'transcription',
            true,
            false,
            'Qwen Audio - Open-source audio understanding model with transcription capabilities',
            '{"model": "qwen-audio-chat"}'
        )
    """)

    # Seed default summarization models
    op.execute("""
        INSERT INTO model_configs (name, display_name, provider, model_type, is_active, is_default, description, config_json)
        VALUES
        (
            'gpt-4o-mini',
            'GPT-4o Mini',
            'openai',
            'summarization',
            true,
            true,
            'OpenAI GPT-4o Mini - Fast and cost-effective summarization',
            '{"model": "gpt-4o-mini", "max_tokens": 2000, "temperature": 0.3}'
        ),
        (
            'gpt-4o',
            'GPT-4o',
            'openai',
            'summarization',
            true,
            false,
            'OpenAI GPT-4o - Most capable model for complex summarization tasks',
            '{"model": "gpt-4o", "max_tokens": 4000, "temperature": 0.3}'
        ),
        (
            'claude-3-5-sonnet',
            'Claude 3.5 Sonnet',
            'anthropic',
            'summarization',
            true,
            false,
            'Anthropic Claude 3.5 Sonnet - Excellent at understanding context and nuance',
            '{"model": "claude-3-5-sonnet-20241022", "max_tokens": 4000}'
        ),
        (
            'claude-3-5-haiku',
            'Claude 3.5 Haiku',
            'anthropic',
            'summarization',
            true,
            false,
            'Anthropic Claude 3.5 Haiku - Fast and efficient summarization',
            '{"model": "claude-3-5-haiku-20241022", "max_tokens": 2000}'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model_configs WHERE name IN ('whisper-large-v3', 'google-speech-to-text', 'elevenlabs-speech-to-text', 'qwen-audio', 'gpt-4o-mini', 'gpt-4o', 'claude-3-5-sonnet', 'claude-3-5-haiku')")
