from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class EmbeddingResult:
    values: list[float]


@dataclass
class GenerateResult:
    text: str


class LLMProvider(ABC):
    @abstractmethod
    async def embed_content(self, text: str, model: str | None = None) -> EmbeddingResult: ...

    @abstractmethod
    async def generate_content(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> GenerateResult: ...

    @abstractmethod
    async def generate_content_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult: ...
