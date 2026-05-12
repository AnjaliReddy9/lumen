import os
from typing import Any, cast

import anthropic
from anthropic.types import TextBlock, ToolParam, ToolUseBlock


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

    def call_tool_use(
        self,
        *,
        system: str,
        user: str,
        tool: ToolParam,
    ) -> dict[str, Any]:
        name = tool["name"]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": name},
        }
        message = self._client.messages.create(**kwargs)
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == name:
                return cast(dict[str, Any], block.input)
        raise RuntimeError(
            f"Anthropic returned no matching tool_use for {name!r} "
            f"(stop_reason={message.stop_reason!r})"
        )
