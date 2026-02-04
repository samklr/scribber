"""
Transcription service factory.
"""
from app.models.model_config import ModelConfig, ModelProvider
from app.services.transcription.base import TranscriptionService
from app.services.transcription.whisper import WhisperTranscriptionService
from app.services.transcription.google_stt import GoogleSTTService
from app.services.transcription.google_stt_v2 import GoogleSTTV2Service
from app.services.transcription.elevenlabs import ElevenLabsTranscriptionService
from app.services.transcription.qwen import QwenAudioTranscriptionService

# Models that use the V2 API (Chirp)
# Note: chirp_2 is only available in us-central1
GOOGLE_V2_MODELS = {"chirp", "chirp_2", "short", "long", "telephony"}


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
        model = config.get("model", "latest_long")

        # Use V2 API for Chirp and other V2 models
        if model in GOOGLE_V2_MODELS:
            return GoogleSTTV2Service(
                credentials_path=config.get("credentials_path"),
                credentials_json=config.get("credentials_json"),
                project_id=config.get("project_id"),
                location=config.get("location"),  # Will use GOOGLE_STT_LOCATION if not specified
                language_code=config.get("language_code", "en-US"),
                model=model,
            )

        # Use V1 API for legacy models
        return GoogleSTTService(
            credentials_path=config.get("credentials_path"),
            credentials_json=config.get("credentials_json"),
            api_key=model_config.api_key_encrypted,
            language_code=config.get("language_code", "en-US"),
            model=model,
        )

    elif provider == ModelProvider.ELEVENLABS:
        return ElevenLabsTranscriptionService(
            api_key=model_config.api_key_encrypted,
            model=config.get("model", "scribe_v1"),
        )

    elif provider == ModelProvider.QWEN:
        return QwenAudioTranscriptionService(
            api_key=model_config.api_key_encrypted,
            api_endpoint=model_config.api_endpoint,
            model=config.get("model", "qwen-audio-turbo"),
        )

    else:
        raise ValueError(f"Unsupported transcription provider: {provider}")
