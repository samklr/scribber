"""
Anthropic Claude summarization service.
"""
from anthropic import Anthropic

from app.config import settings
from app.services.summarization.base import SummarizationService, SummaryResult


class AnthropicSummarizationService(SummarizationService):
    """Anthropic Claude API summarization service."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4000,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model
        self.max_tokens = max_tokens
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key)
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
        Generate a summary using Anthropic Claude.

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

        # Call Anthropic API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            system="You are an expert at summarizing transcriptions and meeting notes. "
            "Provide clear, actionable summaries that capture the essence of the discussion.",
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        # Extract summary
        summary = response.content[0].text.strip()
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return SummaryResult(
            summary=summary,
            tokens_used=input_tokens + output_tokens,
            model=self.model,
            metadata={
                "provider": "anthropic",
                "style": style,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "stop_reason": response.stop_reason,
            }
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for Anthropic Claude summarization.

        Pricing (as of 2024):
        - Claude 3.5 Sonnet: $3/1M input, $15/1M output
        - Claude 3.5 Haiku: $0.25/1M input, $1.25/1M output
        """
        if "haiku" in self.model.lower():
            input_cost = (input_tokens / 1_000_000) * 0.25
            output_cost = (output_tokens / 1_000_000) * 1.25
        elif "sonnet" in self.model.lower():
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00
        else:
            # Default to Sonnet pricing
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00

        return input_cost + output_cost
