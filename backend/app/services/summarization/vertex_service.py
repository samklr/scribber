"""
Google Vertex AI (Gemini) summarization service.

Supports Gemini models via Vertex AI with service account authentication.
"""
import logging
from typing import Any

from app.config import settings
from app.services.google_auth import get_google_credentials, get_project_id
from app.services.summarization.base import SummarizationService, SummaryResult

logger = logging.getLogger(__name__)


class VertexAISummarizationService(SummarizationService):
    """Google Vertex AI (Gemini) summarization service."""

    # Available Gemini models on Vertex AI
    SUPPORTED_MODELS = [
        "gemini-1.5-flash-002",
        "gemini-1.5-pro-002",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
    ]

    def __init__(
        self,
        credentials_path: str | None = None,
        credentials_json: str | dict | None = None,
        project_id: str | None = None,
        location: str | None = None,
        model: str = "gemini-1.5-flash-002",
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ):
        """
        Initialize Vertex AI summarization service.

        Args:
            credentials_path: Path to service account JSON file
            credentials_json: Service account JSON as string or dict
            project_id: Google Cloud project ID (optional, extracted from credentials)
            location: Vertex AI location (default: us-central1)
            model: Gemini model name
            max_tokens: Maximum output tokens
            temperature: Generation temperature (0-1)
        """
        self.model_name = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.location = location or settings.VERTEX_AI_LOCATION or "us-central1"

        # Get credentials
        credentials, creds_project = get_google_credentials(
            credentials_path=credentials_path,
            credentials_json=credentials_json,
        )

        # Determine project ID
        self.project_id = project_id or creds_project or settings.GOOGLE_CLOUD_PROJECT
        if not self.project_id:
            raise ValueError(
                "Google Cloud project ID required. Set GOOGLE_CLOUD_PROJECT or include in credentials."
            )

        self._credentials = credentials
        self._model = None

    def _get_model(self):
        """Lazy initialization of Vertex AI model."""
        if self._model is None:
            # Import here to avoid loading at module level
            import vertexai
            from vertexai.preview.generative_models import GenerativeModel

            # Initialize Vertex AI
            vertexai.init(
                project=self.project_id,
                location=self.location,
                credentials=self._credentials,
            )

            self._model = GenerativeModel(self.model_name)
            logger.info(
                f"Initialized Vertex AI model: {self.model_name} "
                f"(project: {self.project_id}, location: {self.location})"
            )

        return self._model

    @property
    def name(self) -> str:
        return self.model_name

    async def summarize(
        self,
        text: str,
        style: str = "professional",
        max_length: int | None = None,
        **kwargs: Any,
    ) -> SummaryResult:
        """
        Generate a summary using Vertex AI Gemini.

        Args:
            text: The text to summarize
            style: Summary style (professional, casual, technical, etc.)
            max_length: Optional maximum summary length in words
            **kwargs: Additional generation options

        Returns:
            SummaryResult with generated summary
        """
        import asyncio

        # Build prompt
        prompt = self.get_prompt_template(style).format(text=text)

        if max_length:
            prompt += f"\n\nKeep the summary under {max_length} words."

        # Configure generation
        generation_config = {
            "max_output_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", 0.95),
        }

        logger.info(f"Calling Vertex AI Gemini with model: {self.model_name}")
        logger.info(f"Text length: {len(text)} chars, style: {style}")

        try:
            # Get model (lazy init)
            model = self._get_model()

            # Generate content (run in thread to not block async loop)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=generation_config,
            )

            # Extract response
            summary = response.text.strip()

            # Get token counts
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count if usage else None
            output_tokens = usage.candidates_token_count if usage else None
            total_tokens = usage.total_token_count if usage else None

            logger.info(
                f"Vertex AI Gemini call completed. Tokens: {input_tokens} input, {output_tokens} output"
            )

            return SummaryResult(
                summary=summary,
                tokens_used=total_tokens,
                model=self.model_name,
                metadata={
                    "provider": "google_vertex",
                    "style": style,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "project_id": self.project_id,
                    "location": self.location,
                },
            )

        except Exception as e:
            logger.error(f"Vertex AI summarization failed: {e}")
            raise RuntimeError(f"Vertex AI summarization failed: {str(e)}")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for Vertex AI Gemini summarization.

        Pricing (as of 2024, per 1M tokens):
        - Gemini 1.5 Flash: $0.075 input, $0.30 output (< 128K context)
        - Gemini 1.5 Pro: $1.25 input, $5.00 output (< 128K context)
        """
        if "flash" in self.model_name.lower():
            input_cost = (input_tokens / 1_000_000) * 0.075
            output_cost = (output_tokens / 1_000_000) * 0.30
        elif "pro" in self.model_name.lower():
            input_cost = (input_tokens / 1_000_000) * 1.25
            output_cost = (output_tokens / 1_000_000) * 5.00
        else:
            # Default to Flash pricing
            input_cost = (input_tokens / 1_000_000) * 0.075
            output_cost = (output_tokens / 1_000_000) * 0.30

        return input_cost + output_cost
