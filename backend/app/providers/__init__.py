from .base import BaseProvider, ProviderResult
from .mock_provider import MockProvider
from .openai_provider import OpenAICompatibleProvider
from .anthropic_provider import AnthropicCompatibleProvider


def get_provider(card: dict, api_key: str = "") -> BaseProvider:
    """Build an adapter for a registry card. The api_key is decrypted by the
    caller at call time and never stored inside the card."""
    ptype = card.get("provider", "mock")
    if ptype == "mock":
        return MockProvider(card)
    if not api_key:
        raise RuntimeError(f"missing API key for provider {ptype}")
    if ptype == "anthropic":
        return AnthropicCompatibleProvider(
            card, card.get("base_url") or "https://api.anthropic.com", api_key)
    # openai, deepseek, qwen, gemini, openrouter, custom_openai — all
    # chat-completions compatible
    return OpenAICompatibleProvider(
        card, card.get("base_url") or "https://api.openai.com/v1", api_key)
