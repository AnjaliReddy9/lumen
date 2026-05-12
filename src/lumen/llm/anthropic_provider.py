import os
from typing import Any

import anthropic
from anthropic.types import TextBlock


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-5") -> None:
        key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set and no api_key was passed")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model

    def generate(self, prompt: str, system: str | None = None) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        parts: list[str] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
        out = "".join(parts)
        if not out:
            raise RuntimeError(
                f"Anthropic returned no text content (stop_reason={message.stop_reason!r})"
            )
        return out
