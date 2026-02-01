"""
Transcription services for audio-to-text conversion.
"""
from app.services.transcription.base import TranscriptionService, TranscriptionResult
from app.services.transcription.factory import get_transcription_service
from app.services.transcription.processor import process_transcription

__all__ = [
    "TranscriptionService",
    "TranscriptionResult",
    "get_transcription_service",
    "process_transcription",
]
