"""
Base transcription service interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    text: str
    duration_seconds: float | None = None
    language: str | None = None
    confidence: float | None = None
    segments: list[dict] | None = None
    metadata: dict | None = None


class TranscriptionService(ABC):
    """Abstract base class for transcription services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the service name."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Get list of supported audio formats."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs: Any
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio file
            language: Optional language code (e.g., 'en', 'es', 'fr')
            **kwargs: Additional provider-specific options

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        pass

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate the cost for transcribing audio of given duration.

        Args:
            duration_seconds: Duration of audio in seconds

        Returns:
            Estimated cost in USD
        """
        return 0.0  # Override in subclasses with pricing info
