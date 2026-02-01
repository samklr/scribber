"""
Tests for transcription services.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.transcription.base import TranscriptionResult
from app.services.transcription.whisper import WhisperTranscriptionService
from app.services.transcription.factory import get_transcription_service
from app.models import ModelConfig


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_result_creation(self):
        """Test creating a transcription result."""
        result = TranscriptionResult(
            text="Hello, world!",
            duration_seconds=5.0,
            language="en",
            confidence=0.95,
        )

        assert result.text == "Hello, world!"
        assert result.duration_seconds == 5.0
        assert result.language == "en"
        assert result.confidence == 0.95

    def test_result_with_segments(self):
        """Test creating a result with segments."""
        segments = [
            {"id": 0, "text": "Hello", "start": 0.0, "end": 1.0},
            {"id": 1, "text": "world", "start": 1.0, "end": 2.0},
        ]

        result = TranscriptionResult(
            text="Hello world",
            segments=segments,
        )

        assert result.segments is not None
        assert len(result.segments) == 2
        assert result.segments[0]["text"] == "Hello"

    def test_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = TranscriptionResult(
            text="Test",
            metadata={"provider": "whisper", "model": "large-v3"},
        )

        assert result.metadata is not None
        assert result.metadata["provider"] == "whisper"


class TestWhisperTranscriptionService:
    """Tests for WhisperTranscriptionService."""

    @pytest.fixture
    def whisper_service(self):
        """Create a Whisper service with mock API key."""
        return WhisperTranscriptionService(
            api_key="test-api-key",
            model="whisper-1",
        )

    def test_service_properties(self, whisper_service):
        """Test service properties."""
        assert whisper_service.name == "whisper"
        assert "mp3" in whisper_service.supported_formats
        assert "wav" in whisper_service.supported_formats
        assert "webm" in whisper_service.supported_formats

    def test_estimate_cost(self, whisper_service):
        """Test cost estimation."""
        # 60 seconds = 1 minute
        cost = whisper_service.estimate_cost(60)

        # Whisper costs $0.006 per minute
        assert cost == pytest.approx(0.006, rel=0.01)

        # 300 seconds = 5 minutes
        cost = whisper_service.estimate_cost(300)
        assert cost == pytest.approx(0.03, rel=0.01)

    @pytest.mark.asyncio
    @patch("app.services.transcription.whisper.AsyncOpenAI")
    async def test_transcribe_success(self, mock_openai_class, whisper_service, temp_audio_file):
        """Test successful transcription."""
        # Set up mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "This is the transcribed text."
        mock_response.language = "en"
        mock_response.duration = 10.5
        mock_response.segments = [
            MagicMock(id=0, text="This is", start=0.0, end=1.0, avg_logprob=-0.3),
            MagicMock(id=1, text="the transcribed text.", start=1.0, end=2.0, avg_logprob=-0.2),
        ]

        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        # Call transcribe
        result = await whisper_service.transcribe(temp_audio_file)

        assert result.text == "This is the transcribed text."
        assert result.language == "en"
        assert result.duration_seconds == 10.5

    @pytest.mark.asyncio
    @patch("app.services.transcription.whisper.AsyncOpenAI")
    async def test_transcribe_with_language(self, mock_openai_class, whisper_service, temp_audio_file):
        """Test transcription with specified language."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Hola mundo"
        mock_response.language = "es"
        mock_response.duration = 5.0
        mock_response.segments = []

        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        result = await whisper_service.transcribe(temp_audio_file, language="es")

        # Verify language was passed
        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs[1].get("language") == "es"

    @pytest.mark.asyncio
    @patch("app.services.transcription.whisper.AsyncOpenAI")
    async def test_transcribe_api_error(self, mock_openai_class, whisper_service, temp_audio_file):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await whisper_service.transcribe(temp_audio_file)

        assert "Transcription failed" in str(exc_info.value)


class TestTranscriptionFactory:
    """Tests for transcription service factory."""

    def test_get_openai_service(self):
        """Test getting OpenAI/Whisper service."""
        model_config = ModelConfig(
            name="whisper",
            display_name="Whisper",
            provider="openai",
            model_type="transcription",
            config_json={"model": "whisper-1"},
        )

        # Mock the API key
        with patch.object(model_config, "api_key_encrypted", "test-key"):
            service = get_transcription_service(model_config)

        assert service is not None
        assert isinstance(service, WhisperTranscriptionService)
        assert service.name == "whisper"

    def test_get_google_service(self):
        """Test getting Google STT service."""
        from app.services.transcription.google_stt import GoogleSTTService

        model_config = ModelConfig(
            name="google-stt",
            display_name="Google STT",
            provider="google",
            model_type="transcription",
            config_json={"language_code": "en-US"},
        )

        # This will require proper Google credentials, so we patch the client
        with patch("app.services.transcription.google_stt.speech.SpeechClient"):
            service = get_transcription_service(model_config)

        assert service is not None
        assert isinstance(service, GoogleSTTService)

    def test_get_elevenlabs_service(self):
        """Test getting ElevenLabs service."""
        from app.services.transcription.elevenlabs import ElevenLabsTranscriptionService

        model_config = ModelConfig(
            name="elevenlabs",
            display_name="ElevenLabs",
            provider="elevenlabs",
            model_type="transcription",
        )

        with patch.object(model_config, "api_key_encrypted", "test-key"):
            service = get_transcription_service(model_config)

        assert service is not None
        assert isinstance(service, ElevenLabsTranscriptionService)

    def test_get_qwen_service(self):
        """Test getting Qwen Audio service."""
        from app.services.transcription.qwen import QwenAudioTranscriptionService

        model_config = ModelConfig(
            name="qwen-audio",
            display_name="Qwen Audio",
            provider="qwen",
            model_type="transcription",
            config_json={"model": "qwen-audio-chat"},
        )

        with patch.object(model_config, "api_key_encrypted", "test-key"):
            service = get_transcription_service(model_config)

        assert service is not None
        assert isinstance(service, QwenAudioTranscriptionService)

    def test_unsupported_provider(self):
        """Test error for unsupported provider."""
        model_config = ModelConfig(
            name="unknown",
            display_name="Unknown",
            provider="unknown_provider",
            model_type="transcription",
        )

        with pytest.raises(ValueError) as exc_info:
            get_transcription_service(model_config)

        assert "unsupported" in str(exc_info.value).lower()


class TestTranscriptionServiceInterface:
    """Tests to verify all services implement the interface correctly."""

    @pytest.fixture(params=["whisper", "google", "elevenlabs", "qwen"])
    def service_type(self, request):
        """Parameterized fixture for different service types."""
        return request.param

    def test_service_has_required_properties(self, service_type):
        """Test that all services have required properties."""
        from app.services.transcription.whisper import WhisperTranscriptionService
        from app.services.transcription.google_stt import GoogleSTTService
        from app.services.transcription.elevenlabs import ElevenLabsTranscriptionService
        from app.services.transcription.qwen import QwenAudioTranscriptionService

        services = {
            "whisper": lambda: WhisperTranscriptionService(api_key="test"),
            "google": lambda: GoogleSTTService.__new__(GoogleSTTService),
            "elevenlabs": lambda: ElevenLabsTranscriptionService(api_key="test"),
            "qwen": lambda: QwenAudioTranscriptionService(api_key="test"),
        }

        if service_type == "google":
            # GoogleSTTService requires credentials, skip property test
            pytest.skip("Google service requires credentials")

        service = services[service_type]()

        # Check required properties exist
        assert hasattr(service, "name")
        assert hasattr(service, "supported_formats")
        assert hasattr(service, "transcribe")
        assert hasattr(service, "estimate_cost")

        # Check types
        assert isinstance(service.name, str)
        assert isinstance(service.supported_formats, list)
