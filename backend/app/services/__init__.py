"""
Scribber services for file storage, transcription, and summarization.
"""
from app.services.storage import StorageService, get_storage_service

__all__ = ["StorageService", "get_storage_service"]
