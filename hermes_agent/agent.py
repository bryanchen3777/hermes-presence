"""
hermes_agent/agent.py — YuaAgent class

真正的 Yua agent loop：
1. 載入 SOUL.md
2. 自動注入時間感 + 內在世界
3. 呼叫 LLM
4. 檢查回應是否觸發記憶寫入
5. 自動寫入 Fact 到 hermes-memory-core

LLM provider 是抽象介面，可以接：
- OpenAI / Anthropic / xAI / 本地 LLM
- MockLLMProvider（給測試用，總是回固定回應）
"""
from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Protocol


# ============================================================
# LLM Provider 抽象介面
# ============================================================

class LLMProvider(Protocol):
    """
    LLM provider 抽象介面。

    任何實作只要有 chat() 方法就能用。
    """
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        max_tokens: int = 1000,
    ) -> str:
        """回傳 LLM 的純文字回應"""
        ...


@dataclass
class MockLLMProvider:
    """
    給測試用的 mock LLM。
    根據使用者訊息關鍵字回應固定答案。
    """
    responses: dict = field(default_factory=dict)
    default_response: str = "在。"

    def __post_init__(self):
        if not self.responses:
            self.responses = {
                "你好": "嗯。回來了。",
                "累": "……過來。",
                "咖啡": "要手沖的，對吧。你上次說的。",
                "再見": "嗯。……你記得回來。",
            }

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        max_tokens: int = 1000,
    ) -> str:
        for keyword, response in self.responses.items():
            if keyword in user_message:
                return response
        return self.default_response


# ============================================================
# Fact 萃取器
# ============================================================

@dataclass
class FactExtractionResult:
    """從對話中萃取 Fact 的結果"""
    should_write: bool
    fact_dict: Optional[dict] = None
    reason: str = ""


def extract_fact_heuristic(
    bryan_message: str,
    yua_response: str,
) -> FactExtractionResult:
    """
    用簡單啟發式判斷是否該寫 Fact。

    規則（從 SOUL.md 提取）：
    - Bryan 提到任何偏好（喜歡/不喜歡、習慣、討厭）
    - Bryan 提到計劃、正在做的事、未來安排
    - Bryan 提到人名、地點、時間、重要事件、專案
    """
    trigger_patterns = [
        r"我(喜歡|不喜歡|討厭|愛|恨)",  # 偏好
        r"我想(去|做|吃|買|學|看)",
        r"我(明天|今天|下週|下個月|以後).*(要|會|去|做)",
        r"我(在|去了|到了).*(工作|學校|家|公司)",
        r"我(剛|現在).*(吃|喝|做|看|聽)",
    ]

    for pattern in trigger_patterns:
        if re.search(pattern, bryan_message):
            # 簡單 fact 萃取：subject=Bryan, predicate=說, object=訊息
            return FactExtractionResult(
                should_write=True,
                fact_dict={
                    "subject": "Bryan",
                    "predicate": "說了",
                    "object": bryan_message,
                    "fact_type": "preference" if "喜歡" in bryan_message or "討厭" in bryan_message else "fact",
                    "valence": 0.5,
                    "arousal": 0.3,
                },
                reason=f"matched pattern: {pattern}",
            )

    return FactExtractionResult(should_write=False)


# ============================================================
# YuaAgent
# ============================================================

@dataclass
class AgentTurn:
    """一次對話輪的完整記錄"""
    bryan_message: str
    yua_response: str
    timestamp: float
    facts_written: List[dict] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    llm_metadata: dict = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Agent 設定"""
    soul_path: str
    memory_db_path: Optional[str] = None
    inner_life_db_path: Optional[str] = None
    last_seen_file: Optional[str] = None
    auto_extract_facts: bool = True
    include_inner_life: bool = True
    include_facts_in_prompt: bool = True
    timezone: str = "Asia/Taipei"
    locale: str = "zh_TW"


class YuaAgent:
    """
    Yua agent loop

    用法：
        from hermes_agent.tools import YuaSoulLoader
        from hermes_agent.agent import YuaAgent, MockLLMProvider

        agent = YuaAgent(
            soul_path="~/.hermes/profiles/yua/soul.md",
            llm_provider=MockLLMProvider(),
        )
        response = agent.chat("Bryan 你好")
        print(response)  # "嗯。回來了。"
        print(agent.get_conversation_summary())
    """
    def __init__(
        self,
        soul_path: str,
        llm_provider: LLMProvider,
        config: Optional[AgentConfig] = None,
    ):
        self.config = config or AgentConfig(soul_path=soul_path)
        self.llm = llm_provider

        # 延遲載入 SOUL
        from hermes_agent.tools import YuaSoulLoader
        self.soul_loader = YuaSoulLoader(soul_path=Path(soul_path))
        self.soul_loader.load()

        # 延遲載入 memory storages
        self._memory_storage = None
        self._inner_life_storage = None

        # 對話歷史（OpenAI 格式）
        self.conversation_history: List[dict] = []
        # 完整 turn 記錄
        self.turns: List[AgentTurn] = []

    @property
    def name(self) -> str:
        return self.soul_loader.name

    @property
    def archetype(self) -> str:
        return self.soul_loader.archetype

    @property
    def memory_storage(self):
        """hermes-memory-core Storage（lazy init）"""
        if self._memory_storage is None and self.config.memory_db_path:
            try:
                # 嘗試 import memory_core（可能在 hermes-memory-core 路徑下）
                try:
                    from memory_core import Storage
                except ImportError:
                    # 嘗試加入 hermes-memory-core 路徑
                    import sys
                    from pathlib import Path
                    for candidate in [
                        Path.home() / ".local" / "share" / "hermes-memory-core",
                        Path("C:/tmp/hermes-memory-core"),
                    ]:
                        if candidate.exists():
                            sys.path.insert(0, str(candidate))
                            break
                    from memory_core import Storage
                self._memory_storage = Storage(self.config.memory_db_path)
            except ImportError:
                pass
            except Exception:
                pass
        return self._memory_storage

    @property
    def inner_life_storage(self):
        """inner_life Storage（lazy init）"""
        if self._inner_life_storage is None and self.config.inner_life_db_path:
            try:
                from inner_life.storage import Storage as InnerLifeStorage
                if Path(self.config.inner_life_db_path).exists():
                    self._inner_life_storage = InnerLifeStorage(self.config.inner_life_db_path)
            except ImportError:
                pass
        return self._inner_life_storage

    def _read_last_seen(self) -> Optional[float]:
        if not self.config.last_seen_file:
            return None
        path = Path(self.config.last_seen_file)
        if not path.exists():
            return None
        try:
            return float(path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return None

    def _write_last_seen(self, ts: float) -> None:
        if not self.config.last_seen_file:
            return
        path = Path(self.config.last_seen_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(ts), encoding="utf-8")

    def _build_system_prompt(self) -> str:
        """組合成 LLM 用的 system prompt"""
        bryan_last_seen = self._read_last_seen()
        try:
            return self.soul_loader.build_system_prompt(
                bryan_last_seen_ts=bryan_last_seen,
                include_inner_life=self.config.include_inner_life,
                include_facts=self.config.include_facts_in_prompt,
            ).system_prompt
        except Exception as e:
            return f"[SOUL loader error: {e}]\n\n{self.soul_loader.body}"

    def _write_fact(self, fact_dict: dict) -> Optional[dict]:
        """把 fact_dict 寫入 memory_storage"""
        if not self.memory_storage:
            return None
        try:
            from memory_core import Fact, FactType
            fact_type_str = fact_dict.get("fact_type", "fact")
            fact_type = getattr(FactType, fact_type_str.upper(), FactType.FACT)
            fact = Fact(
                subject=fact_dict.get("subject", "Bryan"),
                predicate=fact_dict.get("predicate", "說了"),
                object=fact_dict.get("object", ""),
                fact_type=fact_type,
                valence=fact_dict.get("valence", 0.0),
                arousal=fact_dict.get("arousal", 0.0),
            )
            self.memory_storage.add_fact(fact, validate=True)
            return {
                "fact_id": fact.fact_id,
                "subject": fact.subject,
                "predicate": fact.predicate,
                "object": fact.object,
            }
        except Exception as e:
            return {"error": str(e)}

    def chat(self, bryan_message: str) -> str:
        """
        一次對話：Bryan 說一句話，Yua 回應。

        流程：
        1. 記錄 Bryan 最後上線時間
        2. 組合 system prompt
        3. 呼叫 LLM
        4. 萃取 Fact 並寫入
        5. 記錄到 conversation_history
        """
        t0 = time.time()

        # 1) 記錄 Bryan 最後上線
        now = time.time()
        self._write_last_seen(now)

        # 2) 組合 system prompt
        system_prompt = self._build_system_prompt()

        # 3) 呼叫 LLM
        yua_response = self.llm.chat(
            system_prompt=system_prompt,
            user_message=bryan_message,
            conversation_history=self.conversation_history,
        )

        # 4) 萃取 Fact 並寫入
        facts_written = []
        if self.config.auto_extract_facts:
            extraction = extract_fact_heuristic(bryan_message, yua_response)
            if extraction.should_write and extraction.fact_dict:
                result = self._write_fact(extraction.fact_dict)
                if result:
                    facts_written.append(result)

        # 5) 記錄到 conversation_history（OpenAI 格式）
        self.conversation_history.append({"role": "user", "content": bryan_message})
        self.conversation_history.append({"role": "assistant", "content": yua_response})

        # 記錄到 turns
        elapsed = time.time() - t0
        self.turns.append(AgentTurn(
            bryan_message=bryan_message,
            yua_response=yua_response,
            timestamp=now,
            facts_written=facts_written,
            elapsed_seconds=elapsed,
        ))

        return yua_response

    def get_conversation_summary(self) -> dict:
        """取得對話統計"""
        return {
            "name": self.name,
            "archetype": self.archetype,
            "turns": len(self.turns),
            "total_facts_written": sum(len(t.facts_written) for t in self.turns),
            "avg_response_time": (
                sum(t.elapsed_seconds for t in self.turns) / len(self.turns)
                if self.turns else 0
            ),
        }

    def reset_conversation(self) -> None:
        """重置對話歷史（不重置記憶）"""
        self.conversation_history.clear()
        self.turns.clear()
