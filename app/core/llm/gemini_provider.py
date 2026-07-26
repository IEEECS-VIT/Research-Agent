import json
from typing import Any
from google import genai
from google.genai import types

from app.core.llm.base import LLMProvider, EmbeddingResult, GenerateResult


class GeminiProvider(LLMProvider):

    def __init__(self, api_key: str, default_model: str = "gemini-2.5-flash-lite"):
        self.client = genai.Client(api_key=api_key)
        self.default_model = default_model

    async def embed_content(self, text: str, model: str | None = None) -> EmbeddingResult:
        response = await self.client.aio.models.embed_content(
            model=model or "gemini-embedding-2",
            contents=text,
        )
        if not response.embeddings:
            raise ValueError("API returned an empty embeddings list.")
        return EmbeddingResult(values=[float(v) for v in response.embeddings[0].values])

    async def generate_content(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> GenerateResult:
        config_kwargs = {}
        if "response_schema" in kwargs:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = kwargs.pop("response_schema")
        if "temperature" in kwargs:
            config_kwargs["temperature"] = kwargs.pop("temperature")
        if "max_output_tokens" in kwargs:
            config_kwargs["max_output_tokens"] = kwargs.pop("max_output_tokens")

        response = await self.client.aio.models.generate_content(
            model=model or self.default_model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
        )
        return GenerateResult(text=response.text or "")

    async def generate_content_with_image(
        self, prompt: str, image_bytes: bytes, mime_type: str,
        model: str | None = None, **kwargs: Any,
    ) -> GenerateResult:
        config_kwargs = {}
        if "temperature" in kwargs:
            config_kwargs["temperature"] = kwargs.pop("temperature")
        if "max_output_tokens" in kwargs:
            config_kwargs["max_output_tokens"] = kwargs.pop("max_output_tokens")

        response = await self.client.aio.models.generate_content(
            model=model or self.default_model,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
        )
        return GenerateResult(text=response.text or "")
