"""
Base summarization service interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SummaryResult:
    """Result of a summarization operation."""
    summary: str
    tokens_used: int | None = None
    model: str | None = None
    metadata: dict | None = None


class SummarizationService(ABC):
    """Abstract base class for summarization services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the service name."""
        pass

    @abstractmethod
    async def summarize(
        self,
        text: str,
        style: str = "professional",
        max_length: int | None = None,
        **kwargs: Any
    ) -> SummaryResult:
        """
        Generate a summary of the given text.

        Args:
            text: The text to summarize
            style: Summary style ('professional', 'bullet_points', 'brief', 'detailed')
            max_length: Optional maximum summary length in words
            **kwargs: Additional provider-specific options

        Returns:
            SummaryResult with generated summary
        """
        pass

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate the cost for summarization.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        return 0.0  # Override in subclasses with pricing info

    @staticmethod
    def get_prompt_template(style: str = "professional") -> str:
        """Get the prompt template for a given style."""
        templates = {
            "professional": """You are a professional transcription summarizer. Create a clear,
well-structured summary of the following transcription.

Focus on:
- Key discussion points and main topics
- Important decisions or conclusions reached
- Action items or next steps mentioned
- Names of speakers and their main contributions (if identifiable)

Transcription:
{text}

Please provide a professional summary:""",

            "bullet_points": """Summarize the following transcription into clear bullet points.

Focus on:
- Main topics discussed
- Key decisions or outcomes
- Action items with owners (if mentioned)
- Important quotes or statements

Transcription:
{text}

Bullet point summary:""",

            "brief": """Provide a brief 2-3 sentence summary of the following transcription,
capturing only the most essential points.

Transcription:
{text}

Brief summary:""",

            "detailed": """Create a comprehensive, detailed summary of the following transcription.

Include:
- Executive summary (2-3 sentences)
- Main discussion topics with details
- Decisions made and their rationale
- Action items with deadlines (if mentioned)
- Key quotes or important statements
- Any unresolved issues or follow-up items

Transcription:
{text}

Detailed summary:""",
        }

        return templates.get(style, templates["professional"])
