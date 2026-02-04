"""
Summarization service factory.
"""
from app.models.model_config import ModelConfig, ModelProvider
from app.services.summarization.base import SummarizationService
from app.services.summarization.openai_service import OpenAISummarizationService
from app.services.summarization.anthropic_service import AnthropicSummarizationService
from app.services.summarization.vertex_service import VertexAISummarizationService


def get_summarization_service(model_config: ModelConfig) -> SummarizationService:
    """
    Get a summarization service instance based on model configuration.

    Args:
        model_config: Database model configuration

    Returns:
        Configured summarization service instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = model_config.provider
    config = model_config.config_json or {}

    if provider == ModelProvider.OPENAI:
        return OpenAISummarizationService(
            api_key=model_config.api_key_encrypted,  # Will be decrypted in production
            model=config.get("model", "gpt-4o-mini"),
            max_tokens=config.get("max_tokens", 2000),
            temperature=config.get("temperature", 0.3),
        )

    elif provider == ModelProvider.ANTHROPIC:
        return AnthropicSummarizationService(
            api_key=model_config.api_key_encrypted,
            model=config.get("model", "claude-sonnet-4-20250514"),
            max_tokens=config.get("max_tokens", 4000),
        )

    elif provider == ModelProvider.GOOGLE:
        return VertexAISummarizationService(
            credentials_path=config.get("credentials_path"),
            credentials_json=config.get("credentials_json"),
            project_id=config.get("project_id"),
            location=config.get("location", "us-central1"),
            model=config.get("model", "gemini-1.5-flash-002"),
            max_tokens=config.get("max_tokens", 4000),
            temperature=config.get("temperature", 0.3),
        )

    else:
        raise ValueError(f"Unsupported summarization provider: {provider}")
