"""
OpenAI Whisper transcription service.
"""
import logging
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.services.transcription.base import TranscriptionService, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperTranscriptionService(TranscriptionService):
    """OpenAI Whisper API transcription service."""

    def __init__(self, api_key: str | None = None, model: str = "whisper-1"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    @property
    def name(self) -> str:
        return "whisper-large-v3"

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "flac", "ogg"]

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_path: Path to the audio file
            language: Optional language code (e.g., 'en')
            **kwargs: Additional options like response_format, temperature

        Returns:
            TranscriptionResult with transcribed text
        """
        # Prepare transcription options
        options = {
            "model": self.model,
            "response_format": kwargs.get("response_format", "verbose_json"),
        }

        if language:
            options["language"] = language

        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]

        if "prompt" in kwargs:
            options["prompt"] = kwargs["prompt"]

        # Read and send the audio file
        logger.info(f"Calling OpenAI Whisper API for file: {audio_path}")
        logger.info(f"Options: {options}")
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                file=audio_file,
                **options
            )
        logger.info(f"Whisper API call completed successfully")

        # Parse response based on format
        if options["response_format"] == "verbose_json":
            # Handle segments - can be dicts or objects depending on SDK version
            segments = None
            raw_segments = getattr(response, "segments", None)
            if raw_segments:
                segments = []
                for seg in raw_segments:
                    if isinstance(seg, dict):
                        segments.append({
                            "start": seg.get("start"),
                            "end": seg.get("end"),
                            "text": seg.get("text"),
                        })
                    else:
                        segments.append({
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                        })

            return TranscriptionResult(
                text=response.text,
                duration_seconds=getattr(response, "duration", None),
                language=getattr(response, "language", language),
                segments=segments,
                metadata={
                    "model": self.model,
                    "provider": "openai",
                }
            )
        else:
            # Simple text response
            return TranscriptionResult(
                text=response if isinstance(response, str) else response.text,
                language=language,
                metadata={
                    "model": self.model,
                    "provider": "openai",
                }
            )

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate cost for Whisper transcription.

        Pricing: $0.006 per minute (as of 2024)
        """
        minutes = duration_seconds / 60.0
        return minutes * 0.006
