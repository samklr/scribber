"""
Google Cloud authentication helper supporting multiple credential sources.

Supports:
1. JSON content from database/environment (for multi-tenant)
2. File path to service account JSON
3. GOOGLE_APPLICATION_CREDENTIALS environment variable
4. Application Default Credentials (ADC)
"""
import json
import logging
from typing import Any

from google.oauth2 import service_account
from google.auth import default as default_credentials
from google.auth.credentials import Credentials

from app.config import settings

logger = logging.getLogger(__name__)

# Default scopes for Google Cloud services
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]

# Scopes for specific services
SPEECH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]

VERTEX_AI_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]


def get_google_credentials(
    credentials_path: str | None = None,
    credentials_json: str | dict | None = None,
    scopes: list[str] | None = None,
) -> tuple[Credentials, str | None]:
    """
    Get Google Cloud credentials from multiple sources.

    Priority order:
    1. credentials_json (JSON string or dict from DB/env)
    2. credentials_path (explicit file path)
    3. GOOGLE_SERVICE_ACCOUNT_JSON env var
    4. GOOGLE_APPLICATION_CREDENTIALS env var (file path)
    5. Application Default Credentials (ADC)

    Args:
        credentials_path: Path to service account JSON file
        credentials_json: Service account JSON as string or dict
        scopes: OAuth scopes to request

    Returns:
        Tuple of (credentials, project_id)
    """
    target_scopes = scopes or DEFAULT_SCOPES
    project_id = None

    # 1. Try credentials_json parameter (string or dict)
    if credentials_json:
        try:
            if isinstance(credentials_json, str):
                info = json.loads(credentials_json)
            else:
                info = credentials_json

            project_id = info.get("project_id")
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=target_scopes
            )
            logger.info(f"Using service account credentials from JSON (project: {project_id})")
            return credentials, project_id
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse credentials JSON: {e}")
        except Exception as e:
            logger.warning(f"Failed to create credentials from JSON: {e}")

    # 2. Try explicit credentials_path parameter
    if credentials_path:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=target_scopes
            )
            # Read project_id from file
            with open(credentials_path) as f:
                info = json.load(f)
                project_id = info.get("project_id")
            logger.info(f"Using service account credentials from file: {credentials_path}")
            return credentials, project_id
        except Exception as e:
            logger.warning(f"Failed to load credentials from {credentials_path}: {e}")

    # 3. Try GOOGLE_SERVICE_ACCOUNT_JSON env var
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            project_id = info.get("project_id")
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=target_scopes
            )
            logger.info(f"Using service account from GOOGLE_SERVICE_ACCOUNT_JSON env var")
            return credentials, project_id
        except Exception as e:
            logger.warning(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

    # 4. Try GOOGLE_APPLICATION_CREDENTIALS env var (file path)
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=target_scopes
            )
            with open(settings.GOOGLE_APPLICATION_CREDENTIALS) as f:
                info = json.load(f)
                project_id = info.get("project_id")
            logger.info(f"Using service account from GOOGLE_APPLICATION_CREDENTIALS")
            return credentials, project_id
        except Exception as e:
            logger.warning(f"Failed to load GOOGLE_APPLICATION_CREDENTIALS: {e}")

    # 5. Fall back to Application Default Credentials
    try:
        credentials, project = default_credentials(scopes=target_scopes)
        project_id = project or settings.GOOGLE_CLOUD_PROJECT
        logger.info("Using Application Default Credentials (ADC)")
        return credentials, project_id
    except Exception as e:
        logger.error(f"Failed to get default credentials: {e}")
        raise RuntimeError(
            "No Google Cloud credentials found. Please provide one of:\n"
            "- credentials_json parameter\n"
            "- credentials_path parameter\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
            "- GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
            "- Application Default Credentials (gcloud auth application-default login)"
        )


def get_project_id(credentials_json: str | dict | None = None) -> str:
    """
    Get Google Cloud project ID from credentials or settings.

    Args:
        credentials_json: Optional credentials JSON to extract project from

    Returns:
        Project ID string
    """
    # Try to extract from credentials JSON
    if credentials_json:
        try:
            if isinstance(credentials_json, str):
                info = json.loads(credentials_json)
            else:
                info = credentials_json
            if info.get("project_id"):
                return info["project_id"]
        except Exception:
            pass

    # Fall back to settings
    if settings.GOOGLE_CLOUD_PROJECT:
        return settings.GOOGLE_CLOUD_PROJECT

    raise ValueError(
        "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT or include in credentials."
    )
