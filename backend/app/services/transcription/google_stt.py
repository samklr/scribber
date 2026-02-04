"""
Google Cloud Speech-to-Text transcription service.
"""
import logging
from typing import Any

from google.cloud import speech_v1 as speech
from google.api_core.client_options import ClientOptions

from app.services.transcription.base import TranscriptionService, TranscriptionResult
from app.services.google_auth import get_google_credentials, SPEECH_SCOPES
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleSTTService(TranscriptionService):
    """Google Cloud Speech-to-Text transcription service."""

    def __init__(
        self,
        credentials_path: str | None = None,
        credentials_json: str | dict | None = None,
        api_key: str | None = None,
        language_code: str = "en-US",
        model: str = "latest_long",
    ):
        """
        Initialize Google Cloud Speech-to-Text service.

        Args:
            credentials_path: Path to service account JSON file
            credentials_json: Service account JSON as string or dict
            api_key: Google Cloud API Key (alternative to service account)
            language_code: Default language code
            model: Speech recognition model ('latest_long', 'latest_short', etc.)
        """
        self.language_code = language_code
        self.model = model

        # Initialize client - prefer service account, fall back to API key
        if credentials_json or credentials_path or settings.GOOGLE_APPLICATION_CREDENTIALS or settings.GOOGLE_SERVICE_ACCOUNT_JSON:
            # Use service account authentication
            credentials, project_id = get_google_credentials(
                credentials_path=credentials_path,
                credentials_json=credentials_json,
                scopes=SPEECH_SCOPES,
            )
            self.client = speech.SpeechClient(credentials=credentials)
            logger.info(f"Google STT initialized with service account (project: {project_id})")
        elif api_key or settings.GOOGLE_API_KEY:
            # Use API key authentication
            key = api_key or settings.GOOGLE_API_KEY
            client_options = ClientOptions(api_key=key)
            self.client = speech.SpeechClient(client_options=client_options)
            logger.info("Google STT initialized with API key")
        else:
            # Use default credentials (e.g., from environment)
            self.client = speech.SpeechClient()
            logger.info("Google STT initialized with default credentials")

    @property
    def name(self) -> str:
        return "google-speech-to-text"

    @property
    def supported_formats(self) -> list[str]:
        return ["wav", "flac", "mp3", "ogg", "webm"]

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """
        Transcribe audio using Google Cloud Speech-to-Text.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en-US', 'es-ES')
            **kwargs: Additional options

        Returns:
            TranscriptionResult with transcribed text
        """
        import asyncio
        from pathlib import Path

        try:
            # Read audio file
            logger.info(f"Reading audio file from: {audio_path}")
            audio_path = Path(audio_path)
            with open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            logger.info(f"Audio file read. Size: {len(content)} bytes")

            # Determine encoding from file extension
            extension = audio_path.suffix.lower().lstrip(".")
            encoding_map = {
                "wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "flac": speech.RecognitionConfig.AudioEncoding.FLAC,
                "mp3": speech.RecognitionConfig.AudioEncoding.MP3,
                "ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                "webm": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            }
            encoding = encoding_map.get(
                extension,
                speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
            )

            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=encoding,
                language_code=language or self.language_code,
                model=kwargs.get("model", self.model),
                enable_automatic_punctuation=True,
                enable_word_time_offsets=kwargs.get("word_timestamps", False),
                enable_spoken_punctuation=True,
            )

            audio = speech.RecognitionAudio(content=content)

            # For longer audio (> 1 minute), use long running operation
            if len(content) > 10 * 1024 * 1024:  # > 10MB
                logger.info("Audio > 10MB, starting long_running_recognize...")
                operation = self.client.long_running_recognize(
                    config=config,
                    audio=audio,
                )
                # Wait for operation in async context
                # Timeout increased to 1800s (30m) for large files
                logger.info("Waiting for long_running_recognize to complete...")
                response = await asyncio.to_thread(
                    lambda: operation.result(timeout=1800)
                )
                logger.info("long_running_recognize completed.")
            else:
                # Synchronous for shorter audio
                logger.info("Audio <= 10MB, starting synchronous recognize...")
                response = await asyncio.to_thread(
                    self.client.recognize,
                    config=config,
                    audio=audio,
                )
                logger.info("Synchronous recognize completed.")

            # Extract transcription
            transcript_parts = []
            segments = []

            for i, result in enumerate(response.results):
                alternative = result.alternatives[0]
                transcript_parts.append(alternative.transcript)

                segment = {
                    "id": i,
                    "text": alternative.transcript,
                    "confidence": alternative.confidence,
                }

                # Add word timestamps if available
                if alternative.words:
                    segment["words"] = [
                        {
                            "word": word.word,
                            "start": word.start_time.total_seconds(),
                            "end": word.end_time.total_seconds(),
                        }
                        for word in alternative.words
                    ]

                segments.append(segment)

            full_transcript = " ".join(transcript_parts)

            # Calculate duration from last word timestamp if available
            duration = None
            if segments and segments[-1].get("words"):
                duration = segments[-1]["words"][-1]["end"]

            return TranscriptionResult(
                text=full_transcript,
                duration_seconds=duration,
                language=language or self.language_code,
                confidence=(
                    sum(s.get("confidence", 0) for s in segments) / len(segments)
                    if segments else None
                ),
                segments=segments if kwargs.get("word_timestamps") else None,
                metadata={
                    "provider": "google",
                    "model": self.model,
                },
            )

        except Exception as e:
            logger.error(f"Google STT transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate cost for Google Cloud Speech-to-Text.
        Pricing: ~$0.006 per 15 seconds (standard model)
        """
        # $0.024 per minute = $0.006 per 15 seconds
        minutes = duration_seconds / 60
        return minutes * 0.024
