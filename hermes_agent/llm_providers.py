"""
llm_providers.py — LLM providers for hermes-presence

包含：
- MinimaxM3Provider  (Anthropic Messages API, api.minimax.io)
- LocalLLMProvider   (本地 server, http://192.168.0.37:8080, 不需要 key)
- CachedLLMProvider  (包裝任何 provider，第一次呼叫真實 LLM，之後用 cache)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Optional

from hermes_agent.agent import LLMProvider


# ─────────────────────────────────────────────────────────────
# MinimaxM3Provider
# ─────────────────────────────────────────────────────────────

class MinimaxM3Provider:
    """Minimax M3（Anthropic Messages API 相容）"""

    BASE_URL = "https://api.minimax.io/anthropic"
    DEFAULT_MODEL = "MiniMax-M3"
    MAX_TOKENS = 1000

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: str = BASE_URL,
        timeout: int = 120,
    ):
        if api_key is None:
            for var in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
                api_key = os.environ.get(var)
                if api_key:
                    break
        if not api_key:
            raise ValueError(
                "找不到 API key。請設定 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY 環境變數，"
                "或直接傳入 api_key 參數。"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._history: list[dict] = []

    def _find_api_key(self) -> str:
        """從環境變數找 API key"""
        for var in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            v = os.environ.get(var)
            if v:
                return v
        raise ValueError("找不到 API key")

    def chat(self, system_prompt: str, user_message: str, conversation_history=None) -> str:
        """發送對話到 Minimax M3，回覆 assistant 回應文字"""
        url = f"{self.base_url}/v1/messages"

        body = {
            "model": self.model,
            "max_tokens": self.MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")

        result = json.loads(raw)

        # Anthropic Messages API
        if result.get("type") == "message":
            texts = [
                block.get("text", "")
                for block in result.get("content", [])
                if block.get("type") == "text"
            ]
            response_text = "\n".join(texts)
        else:
            # OpenAI fallback
            choices = result.get("choices", [])
            response_text = choices[0]["message"]["content"] if choices else str(result)

        self._history.append({
            "system": system_prompt,
            "user": user_message,
            "assistant": response_text,
        })
        return response_text

    @property
    def name(self) -> str:
        return f"MinimaxM3({self.model})"

    def reset_history(self):
        self._history.clear()


# ─────────────────────────────────────────────────────────────
# LocalLLMProvider
# ─────────────────────────────────────────────────────────────

class LocalLLMProvider:
    """
    對接本地 LLM server (http://192.168.0.37:8080/v1/messages)

    - 不需要 API key
    - 使用 Anthropic Messages API 格式
    - 目標模型由 server 決定
    """

    BASE_URL = "http://192.168.0.37:8080"
    ENDPOINT = "/v1/messages"

    def __init__(
        self,
        base_url: str = BASE_URL,
        endpoint: str = ENDPOINT,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.timeout = timeout
        self._history: list[dict] = []

    def chat(self, system_prompt: str, user_message: str, conversation_history=None) -> str:
        """發送對話到本地 LLM server，回傳 assistant 回應文字

        Args:
            system_prompt: 系統提示（含 SOUL + 時間感 + 內在世界）
            user_message: 使用者訊息
            conversation_history: 對話歷史（目前未使用，保留介面相容性）
        """
        url = f"{self.base_url}{self.endpoint}"

        body = {
            "model": "M2.7",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")

        result = json.loads(raw)

        # Anthropic Messages API 格式
        if result.get("type") == "message":
            texts = []
            for block in result.get("content", []):
                if block.get("type") == "text":
                    raw = block.get("text", "")
                    # M2.7 有時會在 text block 裡摻雜 tool: / JSON / ```python 等機器的輸出
                    # Block-level cleaning：把包含機器輸出特徵的行拿掉
                    lines = raw.splitlines()
                    natural = []
                    for line in lines:
                        stripped = line.strip()
                        # 包含這些關鍵字的行視為機器輸出，跳過
                        if any(tag in stripped for tag in [
                            "render_", "full_temporal_block", "inner_life_block",
                            "Fact(", "FactType.", "Visibility.",
                            "add_fact", "memory_core.",
                            "tool_call", "tool_code", "<tool_",
                            "```python", "```",
                            "subject=", "predicate=", "object=",
                            '"type":', '"subject":', '"predicate":', '"object":',
                        ]):
                            continue
                        natural.append(line)
                    texts.append("\n".join(natural).strip())
            response_text = "\n".join(texts)
        else:
            # OpenAI chat/completions fallback
            choices = result.get("choices", [])
            response_text = choices[0]["message"]["content"] if choices else str(result)

        # M2.7 有時會輸出 <tool_call>...</tool_call> 標籤或 ```python...``` code blocks
        #（不是真的 tool call，只是模型的想像）— 過濾掉這些，只留純文字回覆
        import re
        response_text = re.sub(r"<tool_call>.*?</tool_call>", "", response_text, flags=re.DOTALL).strip()
        response_text = re.sub(r"```python.*?```", "", response_text, flags=re.DOTALL).strip()
        response_text = re.sub(r"```.*?```", "", response_text, flags=re.DOTALL).strip()

        self._history.append({
            "system": system_prompt,
            "user": user_message,
            "assistant": response_text,
        })
        return response_text

    @property
    def model(self) -> str:
        return "M2.7"

    def reset_history(self):
        self._history.clear()

    def __repr__(self):
        return f"LocalLLMProvider(url={self.base_url}{self.endpoint})"


# ─────────────────────────────────────────────────────────────
# CachedLLMProvider
# ─────────────────────────────────────────────────────────────

class CachedLLMProvider:
    """
    包裝任意 LLMProvider：
    - 第一次呼叫真實 LLM，結果快取到磁碟
    - 之後相同 (system, user) 的組合直接回傳快取
    """

    def __init__(self, delegate: LLMProvider, cache_path: str = ".llm_cache.jsonl"):
        self.delegate = delegate
        self.cache_path = cache_path
        self._memory: dict[tuple[str, str], str] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    for line in f:
                        entry = json.loads(line)
                        key = (entry["system"], entry["user"])
                        self._memory[key] = entry["assistant"]
            except Exception:
                pass

    def _save(self, system: str, user: str, assistant: str):
        self._memory[(system, user)] = assistant
        try:
            with open(self.cache_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"system": system, "user": user, "assistant": assistant}, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def chat(self, system_prompt: str, user_message: str, conversation_history=None) -> str:
        key = (system_prompt, user_message)
        if key in self._memory:
            return self._memory[key]
        response = self.delegate.chat(system_prompt, user_message, conversation_history)
        self._save(system_prompt, user_message, response)
        return response

    @property
    def model(self) -> str:
        return getattr(self.delegate, "model", "cached")

    def reset_history(self):
        self._memory.clear()
