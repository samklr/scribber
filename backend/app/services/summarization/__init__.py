"""
Summarization services for generating text summaries.
"""
from app.services.summarization.base import SummarizationService, SummaryResult
from app.services.summarization.factory import get_summarization_service
from app.services.summarization.processor import process_summarization

__all__ = [
    "SummarizationService",
    "SummaryResult",
    "get_summarization_service",
    "process_summarization",
]
