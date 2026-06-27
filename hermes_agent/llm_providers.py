"""
llm_providers.py — 真實 LLM provider

支援：
- MinimaxM3Provider (Anthropic Messages API 相容)
- 直接 REST 呼叫，不依賴 anthropic SDK（更輕量）
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import List, Optional

from .agent import LLMProvider


class MinimaxM3Provider(LLMProvider):
    """
    minimax M3 (Anthropic Messages API 相容)。

    從環境變數讀 API key：
    - MINIMAX_API_KEY
    - ANTHROPIC_API_KEY
    - 或從 ~/.hermes/config.yaml 讀 base_url

    用法：
        provider = MinimaxM3Provider(
            api_key=os.environ["MINIMAX_API_KEY"],
            model="MiniMax-M3",
        )
        response = provider.chat("system", "user")
    """

    BASE_URL = "https://api.minimax.io/anthropic"
    DEFAULT_MODEL = "MiniMax-M3"
    MAX_TOKENS = 1000

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: str = BASE_URL,
        max_tokens: int = MAX_TOKENS,
        temperature: float = 0.8,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or self._find_api_key()
        if not self.api_key:
            raise ValueError(
                "找不到 API key。請設定 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY 環境變數"
            )
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    @staticmethod
    def _find_api_key() -> Optional[str]:
        for var in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            v = os.environ.get(var)
            if v:
                return v
        return None

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        max_tokens: int = MAX_TOKENS,
    ) -> str:
        """
        呼叫 minimax Messages API。

        格式是 Anthropic Messages API：
        POST {base_url}/v1/messages
        """
        url = f"{self.base_url}/v1/messages"

        # 組合 messages
        messages = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        # 最後一條 user message（如果沒有）
        if not messages or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": user_message})
        else:
            # 已經有 user 訊息了，把當前 user_message 加到最後
            messages.append({"role": "user", "content": user_message})

        body = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": messages,
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "hermes-presence/0.1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"minimax API error {e.code}: {error_body[:500]}"
            )
        except urllib.error.URLError as e:
            raise RuntimeError(f"minimax API connection error: {e.reason}")

        # 解析回應
        # 格式: {"content": [{"type": "text", "text": "..."}], ...}
        if "content" not in response_data:
            raise RuntimeError(f"minimax API unexpected response: {response_data}")

        content_blocks = response_data["content"]
        text_parts = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "".join(text_parts).strip()


class CachedLLMProvider(LLMProvider):
    """
    給 demo / 測試用的 cache provider。
    第一次呼叫真實 LLM，之後回 cache 內容。
    """
    def __init__(self, real_provider: LLMProvider, cache_path: Optional[str] = None):
        self.real = real_provider
        self.cache: dict = {}
        self.cache_path = cache_path
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                self.cache = json.load(f)

    def _key(self, system: str, user: str) -> str:
        return f"{hash(system)}::{hash(user)}"

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        max_tokens: int = 1000,
    ) -> str:
        key = self._key(system_prompt, user_message)
        if key in self.cache:
            return self.cache[key]

        # 沒 cache 就呼叫真實 LLM
        response = self.real.chat(system_prompt, user_message, conversation_history, max_tokens)
        self.cache[key] = response

        if self.cache_path:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)

        return response
