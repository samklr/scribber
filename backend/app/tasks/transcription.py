"""
Transcription background tasks.
"""
from app.worker import celery


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio(self, project_id: int, model_id: int):
    """
    Background task to transcribe audio file.

    Args:
        project_id: ID of the project to transcribe
        model_id: ID of the transcription model to use
    """
    # Import here to avoid circular imports
    from app.services.transcription import process_transcription

    try:
        process_transcription(project_id, model_id)
    except Exception as exc:
        # Retry on failure
        self.retry(exc=exc)
