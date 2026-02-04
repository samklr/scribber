"""
OpenAI GPT summarization service.
"""
import logging
from openai import OpenAI

from app.config import settings
from app.services.summarization.base import SummarizationService, SummaryResult

logger = logging.getLogger(__name__)


class OpenAISummarizationService(SummarizationService):
    """OpenAI GPT API summarization service."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    @property
    def name(self) -> str:
        return self.model

    async def summarize(
        self,
        text: str,
        style: str = "professional",
        max_length: int | None = None,
        **kwargs
    ) -> SummaryResult:
        """
        Generate a summary using OpenAI GPT.

        Args:
            text: The text to summarize
            style: Summary style
            max_length: Optional maximum summary length
            **kwargs: Additional options

        Returns:
            SummaryResult with generated summary
        """
        # Get prompt template
        prompt = self.get_prompt_template(style).format(text=text)

        if max_length:
            prompt += f"\n\nKeep the summary under {max_length} words."

        # Call OpenAI API
        logger.info(f"Calling OpenAI GPT API with model: {self.model}")
        logger.info(f"Text length: {len(text)} chars, style: {style}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at summarizing transcriptions and meeting notes. "
                    "Provide clear, actionable summaries."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
        )

        # Extract summary
        summary = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else None
        logger.info(f"OpenAI GPT API call completed. Tokens used: {tokens_used}")

        return SummaryResult(
            summary=summary,
            tokens_used=tokens_used,
            model=self.model,
            metadata={
                "provider": "openai",
                "style": style,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
            }
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for OpenAI summarization.

        Pricing (as of 2024):
        - GPT-4o-mini: $0.15/1M input, $0.60/1M output
        - GPT-4o: $2.50/1M input, $10.00/1M output
        """
        if self.model.startswith("gpt-4o-mini"):
            input_cost = (input_tokens / 1_000_000) * 0.15
            output_cost = (output_tokens / 1_000_000) * 0.60
        elif self.model.startswith("gpt-4o"):
            input_cost = (input_tokens / 1_000_000) * 2.50
            output_cost = (output_tokens / 1_000_000) * 10.00
        else:
            # Default pricing
            input_cost = (input_tokens / 1_000_000) * 0.50
            output_cost = (output_tokens / 1_000_000) * 1.50

        return input_cost + output_cost
