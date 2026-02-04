"""
Google Cloud Speech-to-Text V2 with Chirp model.

This service uses the newer V2 API which provides access to Chirp,
Google's most accurate speech recognition model based on the
Universal Speech Model (USM).

Chirp benefits:
- ~30% lower word error rate than V1
- Better punctuation and formatting
- Superior handling of accents and dialects
- Native long-form audio support
"""
import logging
from typing import Any

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from app.services.transcription.base import TranscriptionService, TranscriptionResult
from app.services.google_auth import get_google_credentials, get_project_id, SPEECH_SCOPES
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleSTTV2Service(TranscriptionService):
    """Google Cloud Speech-to-Text V2 with Chirp model."""

    # Available models in V2
    # Note: chirp_2 is only available in us-central1
    # chirp is available in more regions including europe-west1
    MODELS = {
        "chirp": "chirp",           # Best accuracy, 100+ languages, broad regional availability
        "chirp_2": "chirp_2",       # Latest Chirp version (us-central1 only)
        "short": "short",           # Optimized for short audio (<60s)
        "long": "long",             # Optimized for long audio
        "telephony": "telephony",   # Optimized for phone audio
    }

    # Models with limited regional availability
    US_ONLY_MODELS = {"chirp_2"}

    def __init__(
        self,
        credentials_path: str | None = None,
        credentials_json: str | dict | None = None,
        project_id: str | None = None,
        location: str | None = None,
        language_code: str = "en-US",
        model: str = "chirp",
    ):
        """
        Initialize Google Cloud Speech-to-Text V2 service.

        Args:
            credentials_path: Path to service account JSON file
            credentials_json: Service account JSON as string or dict
            project_id: Google Cloud project ID
            location: API location (us-central1, europe-west4, asia-southeast1 for Chirp)
            language_code: Default language code (e.g., 'en-US')
            model: Model to use ('chirp', 'chirp_2', 'short', 'long', 'telephony')
        """
        self.language_code = language_code
        # Use provided location or fall back to settings
        self.location = location or settings.GOOGLE_STT_LOCATION or "europe-west4"

        # Handle model selection with regional availability checks
        requested_model = self.MODELS.get(model, model)
        if requested_model in self.US_ONLY_MODELS and not location.startswith("us"):
            logger.warning(
                f"Model '{requested_model}' is only available in us-central1. "
                f"Falling back to 'chirp' for location '{location}'."
            )
            self.model = "chirp"
        else:
            self.model = requested_model

        # Get credentials
        credentials, creds_project = get_google_credentials(
            credentials_path=credentials_path,
            credentials_json=credentials_json,
            scopes=SPEECH_SCOPES,
        )

        # Determine project ID
        self.project_id = project_id or creds_project or settings.GOOGLE_CLOUD_PROJECT
        if not self.project_id:
            raise ValueError("Google Cloud project ID required")

        # Initialize V2 client with appropriate endpoint
        # Regional locations (non-global) require regional API endpoints
        if self.location != "global":
            client_options = ClientOptions(
                api_endpoint=f"{self.location}-speech.googleapis.com"
            )
            self.client = SpeechClient(
                credentials=credentials,
                client_options=client_options
            )
            logger.info(f"Using regional endpoint: {self.location}-speech.googleapis.com")
        else:
            self.client = SpeechClient(credentials=credentials)

        logger.info(
            f"Google STT V2 initialized with Chirp (project: {self.project_id}, "
            f"model: {self.model}, location: {self.location})"
        )

    @property
    def name(self) -> str:
        return f"google-stt-v2-{self.model}"

    @property
    def supported_formats(self) -> list[str]:
        return ["wav", "flac", "mp3", "ogg", "webm", "m4a", "mp4"]

    def _get_recognizer_path(self) -> str:
        """Get the recognizer resource path."""
        return f"projects/{self.project_id}/locations/{self.location}/recognizers/_"

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """
        Transcribe audio using Google Cloud Speech-to-Text V2 with Chirp.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en-US', 'es-ES')
            **kwargs: Additional options (word_timestamps, etc.)

        Returns:
            TranscriptionResult with transcribed text
        """
        import asyncio
        from pathlib import Path

        try:
            # Read audio file
            logger.info(f"Reading audio file from: {audio_path}")
            audio_path_obj = Path(audio_path)
            with open(audio_path_obj, "rb") as audio_file:
                content = audio_file.read()
            logger.info(f"Audio file read. Size: {len(content)} bytes")

            # Build recognition config
            lang = language or self.language_code

            # Auto-detect features for Chirp
            recognition_features = cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True,
                enable_word_time_offsets=kwargs.get("word_timestamps", True),
            )

            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=[lang],
                model=self.model,
                features=recognition_features,
            )

            # Determine if we need batch (long) or inline (short) recognition
            file_size_mb = len(content) / (1024 * 1024)

            if file_size_mb > 10:
                # Use batch recognition for large files
                result = await self._batch_recognize(content, config, audio_path_obj.name)
            else:
                # Use inline recognition for smaller files
                result = await self._recognize(content, config)

            return result

        except Exception as e:
            logger.error(f"Google STT V2 transcription failed: {e}", exc_info=True)
            raise RuntimeError(f"Transcription failed: {str(e)}")

    async def _recognize(
        self,
        content: bytes,
        config: cloud_speech.RecognitionConfig,
    ) -> TranscriptionResult:
        """Perform synchronous recognition for shorter audio."""
        import asyncio

        logger.info(f"Starting V2 recognize with model: {self.model}")

        request = cloud_speech.RecognizeRequest(
            recognizer=self._get_recognizer_path(),
            config=config,
            content=content,
        )

        # Run in thread to not block async loop
        response = await asyncio.to_thread(
            self.client.recognize,
            request=request,
        )

        logger.info("V2 recognize completed")
        return self._parse_response(response)

    async def _batch_recognize(
        self,
        content: bytes,
        config: cloud_speech.RecognitionConfig,
        filename: str,
    ) -> TranscriptionResult:
        """Perform batch recognition for longer audio."""
        import asyncio
        import tempfile
        import os

        logger.info(f"Starting V2 batch recognize with model: {self.model}")

        # For batch recognition, we need to use GCS or inline content
        # Using inline content for simplicity (up to ~480 minutes)

        request = cloud_speech.BatchRecognizeRequest(
            recognizer=self._get_recognizer_path(),
            config=config,
            files=[
                cloud_speech.BatchRecognizeFileMetadata(
                    content=content,
                )
            ],
            recognition_output_config=cloud_speech.RecognitionOutputConfig(
                inline_response_config=cloud_speech.InlineOutputConfig(),
            ),
        )

        # Start batch operation
        operation = self.client.batch_recognize(request=request)

        # Wait for completion
        logger.info("Waiting for batch recognize to complete...")
        response = await asyncio.to_thread(
            lambda: operation.result(timeout=3600)  # 1 hour timeout
        )

        logger.info("V2 batch recognize completed")

        # Parse batch response
        return self._parse_batch_response(response)

    def _parse_response(
        self,
        response: cloud_speech.RecognizeResponse,
    ) -> TranscriptionResult:
        """Parse V2 recognition response."""
        transcript_parts = []
        segments = []
        total_confidence = 0
        confidence_count = 0

        for i, result in enumerate(response.results):
            if not result.alternatives:
                continue

            alternative = result.alternatives[0]
            transcript_parts.append(alternative.transcript)

            segment = {
                "id": i,
                "text": alternative.transcript,
                "confidence": alternative.confidence,
            }

            if alternative.confidence:
                total_confidence += alternative.confidence
                confidence_count += 1

            # Add word timestamps if available
            if alternative.words:
                segment["words"] = [
                    {
                        "word": word.word,
                        "start": word.start_offset.total_seconds() if word.start_offset else 0,
                        "end": word.end_offset.total_seconds() if word.end_offset else 0,
                        "confidence": word.confidence,
                    }
                    for word in alternative.words
                ]

            segments.append(segment)

        full_transcript = " ".join(transcript_parts)

        # Calculate duration from last word timestamp
        duration = None
        if segments and segments[-1].get("words"):
            duration = segments[-1]["words"][-1]["end"]

        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else None

        return TranscriptionResult(
            text=full_transcript,
            duration_seconds=duration,
            language=self.language_code,
            confidence=avg_confidence,
            segments=segments,
            metadata={
                "provider": "google_v2",
                "model": self.model,
                "location": self.location,
            },
        )

    def _parse_batch_response(
        self,
        response: cloud_speech.BatchRecognizeResponse,
    ) -> TranscriptionResult:
        """Parse V2 batch recognition response."""
        transcript_parts = []
        segments = []
        total_confidence = 0
        confidence_count = 0
        segment_id = 0

        # Batch response contains results per file
        for file_result in response.results.values():
            if not file_result.transcript:
                continue

            for result in file_result.transcript.results:
                if not result.alternatives:
                    continue

                alternative = result.alternatives[0]
                transcript_parts.append(alternative.transcript)

                segment = {
                    "id": segment_id,
                    "text": alternative.transcript,
                    "confidence": alternative.confidence,
                }
                segment_id += 1

                if alternative.confidence:
                    total_confidence += alternative.confidence
                    confidence_count += 1

                if alternative.words:
                    segment["words"] = [
                        {
                            "word": word.word,
                            "start": word.start_offset.total_seconds() if word.start_offset else 0,
                            "end": word.end_offset.total_seconds() if word.end_offset else 0,
                            "confidence": word.confidence,
                        }
                        for word in alternative.words
                    ]

                segments.append(segment)

        full_transcript = " ".join(transcript_parts)

        # Calculate duration
        duration = None
        if segments and segments[-1].get("words"):
            duration = segments[-1]["words"][-1]["end"]

        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else None

        return TranscriptionResult(
            text=full_transcript,
            duration_seconds=duration,
            language=self.language_code,
            confidence=avg_confidence,
            segments=segments,
            metadata={
                "provider": "google_v2_batch",
                "model": self.model,
                "location": self.location,
            },
        )

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate cost for Google Cloud Speech-to-Text V2.

        Pricing (as of 2024):
        - Chirp: $0.016 per minute
        - Standard models: $0.024 per minute
        """
        minutes = duration_seconds / 60
        if self.model in ("chirp", "chirp_2"):
            return minutes * 0.016
        return minutes * 0.024
