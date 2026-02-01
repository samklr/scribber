"""
Celery tasks for Scribber.
"""
from app.tasks.transcription import transcribe_audio
from app.tasks.summarization import summarize_text

__all__ = ["transcribe_audio", "summarize_text"]
