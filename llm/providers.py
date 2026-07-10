from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from config.loader import LLMConfig
from llm.base import LLMClient

LOGGER = logging.getLogger(__name__)


class OpenAICompatibleClient(LLMClient):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.api_key = os.getenv(config.api_key_env, "")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                f"Missing API key in environment variable {self.config.api_key_env}"
            )

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "")
        if not content.strip():
            finish_reason = choice.get("finish_reason", "unknown")
            message_keys = ", ".join(sorted(message.keys())) or "none"
            raise RuntimeError(
                "LLM returned empty message content "
                f"(provider={self.config.provider}, model={self.config.model}, "
                f"base_url={self.config.base_url}, finish_reason={finish_reason}, "
                f"message_keys={message_keys})"
            )
        return content


class DeepSeekClient(OpenAICompatibleClient):
    def __init__(self, config: LLMConfig) -> None:
        if not config.base_url or "api.openai.com" in config.base_url:
            config.base_url = "https://api.deepseek.com/v1"
        elif config.base_url.rstrip("/") == "https://api.deepseek.com":
            config.base_url = "https://api.deepseek.com/v1"
        if not config.api_key_env or config.api_key_env == "OPENAI_API_KEY":
            config.api_key_env = "DEEPSEEK_API_KEY"
        super().__init__(config)


class FallbackLLMClient(LLMClient):
    """A deterministic fallback so the pipeline can run without paid APIs."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        LOGGER.warning("Using fallback LLM client; output will be heuristic.")
        return ""


def build_llm_client(config: LLMConfig) -> LLMClient:
    provider = config.provider.lower()
    if provider in {"openai", "openai_compatible"}:
        return OpenAICompatibleClient(config)
    if provider == "deepseek":
        if not config.base_url or "api.openai.com" in config.base_url:
            config.base_url = "https://api.deepseek.com/v1"
        elif config.base_url.rstrip("/") == "https://api.deepseek.com":
            config.base_url = "https://api.deepseek.com/v1"
        if not config.api_key_env or config.api_key_env == "OPENAI_API_KEY":
            config.api_key_env = "DEEPSEEK_API_KEY"
        return DeepSeekClient(config)
    if provider in {"fallback", "mock", "none"}:
        return FallbackLLMClient()
    raise ValueError(f"Unknown LLM provider: {config.provider}")
