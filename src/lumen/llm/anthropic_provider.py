import os
from typing import Any, cast

import anthropic
from anthropic.types import TextBlock, ToolParam, ToolUseBlock

from lumen.llm.pricing import estimate_cost


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-5") -> None:
        key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set and no api_key was passed")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model
        self._pending_cost_usd = 0.0

    @property
    def model_name(self) -> str:
        return self._model

    def take_pending_cost_usd(self) -> float:
        """Return accumulated USD cost from API calls since last take, then reset."""
        out = self._pending_cost_usd
        self._pending_cost_usd = 0.0
        return out

    def _record_message_usage(self, message: Any) -> None:
        usage = getattr(message, "usage", None)
        if usage is None:
            return
        inp = int(getattr(usage, "input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        self._pending_cost_usd += estimate_cost(inp, out, self._model)

    def generate(self, prompt: str, system: str | None = None) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        self._record_message_usage(message)
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
        self._record_message_usage(message)
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == name:
                return cast(dict[str, Any], block.input)
        raise RuntimeError(
            f"Anthropic returned no matching tool_use for {name!r} "
            f"(stop_reason={message.stop_reason!r})"
        )
