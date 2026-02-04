"""
Eleven Labs transcription service.
Note: ElevenLabs is primarily a TTS service but has speech recognition capabilities.
"""
import logging
from typing import Any

import httpx

from app.services.transcription.base import TranscriptionService, TranscriptionResult
from app.config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsTranscriptionService(TranscriptionService):
    """Eleven Labs transcription service using their speech-to-text API."""

    # Available speech-to-text models
    MODELS = {
        "scribe_v1": "scribe_v1",                      # Standard transcription model
        "scribe_v1_experimental": "scribe_v1_experimental",  # Experimental version
        "scribe_v2": "scribe_v2",                      # Latest version
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "scribe_v1",
    ):
        """
        Initialize Eleven Labs transcription service.

        Args:
            api_key: Eleven Labs API key
            model: Model to use (scribe_v1 or turbo)
        """
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.model_id = self.MODELS.get(model, "scribe_v1")

        if not self.api_key:
            raise ValueError("Eleven Labs API key is required")

    @property
    def name(self) -> str:
        return "elevenlabs"

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3", "wav", "m4a", "webm", "ogg", "flac"]

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """
        Transcribe audio using Eleven Labs Speech-to-Text.

        Args:
            audio_path: Path to audio file
            language: Language code (optional)
            **kwargs: Additional options

        Returns:
            TranscriptionResult with transcribed text
        """
        from pathlib import Path
        import mimetypes

        try:
            audio_path = Path(audio_path)

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(audio_path))
            if not mime_type:
                mime_type = "audio/mpeg"  # Default to mp3

            # Read audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # Make API request
            logger.info(f"Sending audio to ElevenLabs API ({ELEVENLABS_API_BASE}), model: {self.model_id}...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{ELEVENLABS_API_BASE}/speech-to-text",
                    headers={
                        "xi-api-key": self.api_key,
                    },
                    files={
                        "file": (audio_path.name, audio_data, mime_type),
                    },
                    data={
                        "model_id": self.model_id,
                        "language_code": language or "en",
                    },
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Eleven Labs API error: {response.status_code} - {error_detail}"
                    )
                    raise RuntimeError(
                        f"Eleven Labs API error: {response.status_code}"
                    )
                
                logger.info("ElevenLabs API request successful.")
                result = response.json()

            # Extract transcription
            text = result.get("text", "")
            words = result.get("words", [])

            # Build segments from words
            segments = []
            if words:
                # Group words into segments (by sentence or time chunks)
                current_segment = {"id": 0, "text": "", "words": []}
                for word in words:
                    current_segment["words"].append({
                        "word": word.get("text", ""),
                        "start": word.get("start", 0),
                        "end": word.get("end", 0),
                    })
                    current_segment["text"] += word.get("text", "") + " "

                if current_segment["words"]:
                    current_segment["text"] = current_segment["text"].strip()
                    segments.append(current_segment)

            # Calculate duration
            duration = None
            if words:
                duration = max(w.get("end", 0) for w in words)

            return TranscriptionResult(
                text=text,
                duration_seconds=duration,
                language=language,
                segments=segments if kwargs.get("word_timestamps") else None,
                metadata={
                    "provider": "elevenlabs",
                    "word_count": len(words),
                },
            )

        except httpx.TimeoutException:
            logger.error("Eleven Labs API timeout")
            raise RuntimeError("Transcription timed out")
        except Exception as e:
            logger.error(f"Eleven Labs transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate cost for Eleven Labs transcription.
        Pricing varies by plan - using approximate values.
        """
        # Approximate: $0.0001 per character, assuming ~150 words/minute, 5 chars/word
        minutes = duration_seconds / 60
        estimated_chars = minutes * 150 * 5
        return estimated_chars * 0.0001
