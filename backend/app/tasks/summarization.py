"""
Summarization background tasks.
"""
from app.worker import celery


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def summarize_text(self, project_id: int, model_id: int):
    """
    Background task to summarize transcription.

    Args:
        project_id: ID of the project to summarize
        model_id: ID of the summarization model to use
    """
    # Import here to avoid circular imports
    from app.services.summarization import process_summarization

    try:
        process_summarization(project_id, model_id)
    except Exception as exc:
        # Retry on failure
        self.retry(exc=exc)
