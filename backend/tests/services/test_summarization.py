"""
Tests for summarization services.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.summarization.base import SummarizationResult
from app.services.summarization.openai_service import OpenAISummarizationService
from app.services.summarization.anthropic_service import AnthropicSummarizationService
from app.services.summarization.factory import get_summarization_service
from app.models import ModelConfig


class TestSummarizationResult:
    """Tests for SummarizationResult dataclass."""

    def test_result_creation(self):
        """Test creating a summarization result."""
        result = SummarizationResult(
            summary="This is a summary.",
            input_tokens=100,
            output_tokens=20,
        )

        assert result.summary == "This is a summary."
        assert result.input_tokens == 100
        assert result.output_tokens == 20

    def test_result_with_key_points(self):
        """Test creating a result with key points."""
        result = SummarizationResult(
            summary="This is a summary.",
            key_points=["Point 1", "Point 2", "Point 3"],
        )

        assert result.key_points is not None
        assert len(result.key_points) == 3

    def test_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = SummarizationResult(
            summary="Test",
            metadata={"model": "gpt-4o-mini", "temperature": 0.3},
        )

        assert result.metadata is not None
        assert result.metadata["model"] == "gpt-4o-mini"


class TestOpenAISummarizationService:
    """Tests for OpenAISummarizationService."""

    @pytest.fixture
    def openai_service(self):
        """Create an OpenAI service with mock API key."""
        return OpenAISummarizationService(
            api_key="test-api-key",
            model="gpt-4o-mini",
        )

    def test_service_properties(self, openai_service):
        """Test service properties."""
        assert openai_service.name == "openai"
        assert openai_service.model == "gpt-4o-mini"

    def test_estimate_cost(self, openai_service):
        """Test cost estimation."""
        # gpt-4o-mini: $0.00015/1K input, $0.0006/1K output
        cost = openai_service.estimate_cost(1000, 200)

        expected = (1000 * 0.00015 / 1000) + (200 * 0.0006 / 1000)
        assert cost == pytest.approx(expected, rel=0.01)

    @pytest.mark.asyncio
    @patch("app.services.summarization.openai_service.AsyncOpenAI")
    async def test_summarize_success(self, mock_openai_class, openai_service):
        """Test successful summarization."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="This is a summary."))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20)

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await openai_service.summarize("Long text to summarize...")

        assert result.summary == "This is a summary."
        assert result.input_tokens == 100
        assert result.output_tokens == 20

    @pytest.mark.asyncio
    @patch("app.services.summarization.openai_service.AsyncOpenAI")
    async def test_summarize_with_custom_prompt(self, mock_openai_class, openai_service):
        """Test summarization with custom prompt."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Custom summary"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=10)

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await openai_service.summarize(
            "Text to summarize",
            custom_prompt="Summarize in bullet points:",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert any("bullet points" in msg["content"].lower() for msg in messages if msg["role"] == "user")

    @pytest.mark.asyncio
    @patch("app.services.summarization.openai_service.AsyncOpenAI")
    async def test_summarize_api_error(self, mock_openai_class, openai_service):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await openai_service.summarize("Test text")

        assert "Summarization failed" in str(exc_info.value)


class TestAnthropicSummarizationService:
    """Tests for AnthropicSummarizationService."""

    @pytest.fixture
    def anthropic_service(self):
        """Create an Anthropic service with mock API key."""
        return AnthropicSummarizationService(
            api_key="test-api-key",
            model="claude-3-5-sonnet-20241022",
        )

    def test_service_properties(self, anthropic_service):
        """Test service properties."""
        assert anthropic_service.name == "anthropic"
        assert "claude" in anthropic_service.model.lower()

    def test_estimate_cost(self, anthropic_service):
        """Test cost estimation."""
        cost = anthropic_service.estimate_cost(1000, 200)

        # Should return some positive value
        assert cost > 0

    @pytest.mark.asyncio
    @patch("app.services.summarization.anthropic_service.AsyncAnthropic")
    async def test_summarize_success(self, mock_anthropic_class, anthropic_service):
        """Test successful summarization."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is Claude's summary.")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=25)

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await anthropic_service.summarize("Long text to summarize...")

        assert result.summary == "This is Claude's summary."
        assert result.input_tokens == 100
        assert result.output_tokens == 25

    @pytest.mark.asyncio
    @patch("app.services.summarization.anthropic_service.AsyncAnthropic")
    async def test_summarize_api_error(self, mock_anthropic_class, anthropic_service):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await anthropic_service.summarize("Test text")

        assert "Summarization failed" in str(exc_info.value)


class TestSummarizationFactory:
    """Tests for summarization service factory."""

    def test_get_openai_service(self):
        """Test getting OpenAI service."""
        model_config = ModelConfig(
            name="gpt-4o-mini",
            display_name="GPT-4o Mini",
            provider="openai",
            model_type="summarization",
            config_json={"model": "gpt-4o-mini", "max_tokens": 2000},
        )

        with patch.object(model_config, "api_key_encrypted", "test-key"):
            service = get_summarization_service(model_config)

        assert service is not None
        assert isinstance(service, OpenAISummarizationService)

    def test_get_anthropic_service(self):
        """Test getting Anthropic service."""
        model_config = ModelConfig(
            name="claude-3-5-sonnet",
            display_name="Claude 3.5 Sonnet",
            provider="anthropic",
            model_type="summarization",
            config_json={"model": "claude-3-5-sonnet-20241022"},
        )

        with patch.object(model_config, "api_key_encrypted", "test-key"):
            service = get_summarization_service(model_config)

        assert service is not None
        assert isinstance(service, AnthropicSummarizationService)

    def test_unsupported_provider(self):
        """Test error for unsupported provider."""
        model_config = ModelConfig(
            name="unknown",
            display_name="Unknown",
            provider="unknown_provider",
            model_type="summarization",
        )

        with pytest.raises(ValueError) as exc_info:
            get_summarization_service(model_config)

        assert "unsupported" in str(exc_info.value).lower()


class TestSummarizationServiceInterface:
    """Tests to verify all services implement the interface correctly."""

    @pytest.fixture(params=["openai", "anthropic"])
    def service(self, request):
        """Parameterized fixture for different service types."""
        if request.param == "openai":
            return OpenAISummarizationService(api_key="test")
        else:
            return AnthropicSummarizationService(api_key="test")

    def test_service_has_required_properties(self, service):
        """Test that all services have required properties."""
        assert hasattr(service, "name")
        assert hasattr(service, "summarize")
        assert hasattr(service, "estimate_cost")

        # Check types
        assert isinstance(service.name, str)

    def test_estimate_cost_returns_float(self, service):
        """Test that estimate_cost returns a float."""
        cost = service.estimate_cost(1000, 100)
        assert isinstance(cost, float)
        assert cost >= 0
