from app.core.config import get_settings
from app.core.llm.base import LLMProvider
from app.core.llm.gemini_provider import GeminiProvider


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        if settings.gemini_api_key:
            _provider = GeminiProvider(api_key=settings.gemini_api_key)
        else:
            raise RuntimeError("No LLM provider configured. Set GEMINI_API_KEY.")
    return _provider


def reset_provider():
    global _provider
    _provider = None
