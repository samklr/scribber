"""
Qwen Audio transcription service.
Qwen Audio can be used via Alibaba Cloud DashScope API or local deployment.
"""
import logging
from typing import Any

import httpx

from app.services.transcription.base import TranscriptionService, TranscriptionResult
from app.config import settings

logger = logging.getLogger(__name__)

# DashScope API endpoint for Qwen Audio
DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/api/v1"


class QwenAudioTranscriptionService(TranscriptionService):
    """Qwen Audio transcription service via Alibaba Cloud DashScope."""

    def __init__(
        self,
        api_key: str | None = None,
        api_endpoint: str | None = None,
        model: str = "qwen-audio-turbo",
    ):
        """
        Initialize Qwen Audio transcription service.

        Args:
            api_key: DashScope API key (or custom endpoint API key)
            api_endpoint: Custom API endpoint URL (for self-hosted)
            model: Model name (qwen-audio-turbo, qwen-audio-chat, etc.)
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint or DASHSCOPE_API_BASE
        self.model = model

        if not self.api_key:
            raise ValueError("Qwen Audio API key is required")

    @property
    def name(self) -> str:
        return "qwen-audio"

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3", "wav", "m4a", "flac", "ogg", "webm"]

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """
        Transcribe audio using Qwen Audio.

        Args:
            audio_path: Path to audio file
            language: Language code (optional)
            **kwargs: Additional options

        Returns:
            TranscriptionResult with transcribed text
        """
        from pathlib import Path
        import base64

        try:
            audio_path = Path(audio_path)

            # Read and encode audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # Encode to base64 for API
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            # Determine audio format from extension
            extension = audio_path.suffix.lower().lstrip(".")
            format_map = {
                "mp3": "mp3",
                "wav": "wav",
                "m4a": "m4a",
                "flac": "flac",
                "ogg": "ogg",
                "webm": "webm",
            }
            audio_format = format_map.get(extension, "mp3")

            # Build request payload for DashScope API
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "audio": f"data:audio/{audio_format};base64,{audio_base64}",
                                },
                                {
                                    "text": "Please transcribe this audio accurately.",
                                },
                            ],
                        }
                    ],
                },
                "parameters": {
                    "result_format": "message",
                },
            }

            # Add language hint if provided
            if language:
                payload["input"]["messages"][0]["content"][1]["text"] = (
                    f"Please transcribe this audio accurately in {language}."
                )

            # Make API request
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_endpoint}/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Qwen Audio API error: {response.status_code} - {error_detail}"
                    )
                    raise RuntimeError(
                        f"Qwen Audio API error: {response.status_code}"
                    )

                result = response.json()

            # Extract transcription from response
            output = result.get("output", {})
            choices = output.get("choices", [])

            if not choices:
                raise RuntimeError("No transcription result returned")

            # Get the assistant's response
            message = choices[0].get("message", {})
            content = message.get("content", [])

            # Extract text from content
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)

            full_text = " ".join(text_parts).strip()

            # Get usage info if available
            usage = result.get("usage", {})

            return TranscriptionResult(
                text=full_text,
                duration_seconds=None,  # Not provided by Qwen
                language=language,
                metadata={
                    "provider": "qwen",
                    "model": self.model,
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                },
            )

        except httpx.TimeoutException:
            logger.error("Qwen Audio API timeout")
            raise RuntimeError("Transcription timed out")
        except Exception as e:
            logger.error(f"Qwen Audio transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    def estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate cost for Qwen Audio transcription.
        Pricing based on DashScope rates.
        """
        # Approximate: $0.0004 per audio second
        return duration_seconds * 0.0004
