from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
from typing import Any, Literal

import requests

from .config import ModelConfig


TokenKind = Literal["reasoning", "content"]


@dataclass(frozen=True)
class ChatToken:
    kind: TokenKind
    text: str


class ModelClientError(RuntimeError):
    """Raised when an OpenAI-compatible API request fails."""


class OpenAICompatibleClient:
    def iter_chat(self, messages: list[dict[str, Any]], config: ModelConfig) -> Iterator[str]:
        for token in self.iter_chat_events(messages, config):
            yield token.text

    def iter_chat_events(
        self, messages: list[dict[str, Any]], config: ModelConfig
    ) -> Iterator[ChatToken]:
        payload = self._payload(messages, config, stream=True)

        try:
            with requests.post(
                self._chat_url(config),
                headers=self._headers(config),
                json=payload,
                stream=True,
                timeout=(15, config.timeout_seconds),
            ) as response:
                self._raise_for_status(response)
                for raw_line in response.iter_lines(decode_unicode=False):
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8").strip()
                    if line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break

                    chunk = self._loads_json(line)
                    for token in self._tokens_from_chunk(chunk):
                        yield token
        except requests.RequestException as exc:
            raise ModelClientError(f"API stream request failed: {exc}") from exc

    def complete_chat(self, messages: list[dict[str, Any]], config: ModelConfig) -> str:
        payload = self._payload(messages, config, stream=False)

        try:
            response = requests.post(
                self._chat_url(config),
                headers=self._headers(config),
                json=payload,
                timeout=(15, config.timeout_seconds),
            )
            self._raise_for_status(response)
        except requests.RequestException as exc:
            raise ModelClientError(f"API request failed: {exc}") from exc

        data = self._loads_json(self._response_text(response))
        choices = data.get("choices") or []
        if not choices:
            raise ModelClientError("API response did not contain choices")

        message = choices[0].get("message") or {}
        content = message.get("content") or message.get("reasoning_content") or ""
        if isinstance(content, list):
            return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return str(content)

    def _payload(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "stream": stream,
        }
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens
        return payload

    def _chat_url(self, config: ModelConfig) -> str:
        if not config.base_url:
            raise ModelClientError("Missing base_url in config.toml")
        base_url = config.base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _headers(self, config: ModelConfig) -> dict[str, str]:
        if not config.api_key:
            raise ModelClientError("Missing api_key in config.toml")
        return {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return
        body = self._response_text(response)[:1000]
        raise ModelClientError(
            f"API returned HTTP {response.status_code}: {body or response.reason}"
        )

    def _response_text(self, response: requests.Response) -> str:
        return response.content.decode("utf-8", errors="replace")

    def _loads_json(self, text: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModelClientError(f"API returned invalid JSON: {text[:500]}") from exc
        if not isinstance(value, dict):
            raise ModelClientError("API returned a non-object JSON payload")
        return value

    def _tokens_from_chunk(self, chunk: dict[str, Any]) -> Iterator[ChatToken]:
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            for key in ("reasoning_content", "reasoning"):
                token = delta.get(key)
                if token:
                    yield ChatToken(kind="reasoning", text=str(token))
            token = delta.get("content")
            if token:
                yield ChatToken(kind="content", text=str(token))
