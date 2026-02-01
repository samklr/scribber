"""
Summarization service factory.
"""
from app.models.model_config import ModelConfig, ModelProvider
from app.services.summarization.base import SummarizationService
from app.services.summarization.openai_service import OpenAISummarizationService
from app.services.summarization.anthropic_service import AnthropicSummarizationService


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
            model=config.get("model", "claude-3-5-sonnet-20241022"),
            max_tokens=config.get("max_tokens", 4000),
        )

    else:
        raise ValueError(f"Unsupported summarization provider: {provider}")
