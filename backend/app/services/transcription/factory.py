"""
Transcription service factory.
"""
from app.models.model_config import ModelConfig, ModelProvider
from app.services.transcription.base import TranscriptionService
from app.services.transcription.whisper import WhisperTranscriptionService
from app.services.transcription.google_stt import GoogleSTTService
from app.services.transcription.elevenlabs import ElevenLabsTranscriptionService
from app.services.transcription.qwen import QwenAudioTranscriptionService


def get_transcription_service(model_config: ModelConfig) -> TranscriptionService:
    """
    Get a transcription service instance based on model configuration.

    Args:
        model_config: Database model configuration

    Returns:
        Configured transcription service instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = model_config.provider
    config = model_config.config_json or {}

    if provider == ModelProvider.OPENAI:
        return WhisperTranscriptionService(
            api_key=model_config.api_key_encrypted,  # Will be decrypted in production
            model=config.get("model", "whisper-1"),
        )

    elif provider == ModelProvider.GOOGLE:
        return GoogleSTTService(
            credentials_path=config.get("credentials_path"),
            language_code=config.get("language_code", "en-US"),
            model=config.get("model", "latest_long"),
        )

    elif provider == ModelProvider.ELEVENLABS:
        return ElevenLabsTranscriptionService(
            api_key=model_config.api_key_encrypted,
        )

    elif provider == ModelProvider.QWEN:
        return QwenAudioTranscriptionService(
            api_key=model_config.api_key_encrypted,
            api_endpoint=model_config.api_endpoint,
            model=config.get("model", "qwen-audio-turbo"),
        )

    else:
        raise ValueError(f"Unsupported transcription provider: {provider}")
