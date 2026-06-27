"""
hermes_agent/tools/yua_soul_loader.py
載入 SOUL.md 並組合成完整的 system prompt

把 SOUL + hermes-presence + hermes-memory-core 的三層組合在一起：
- 載入 SOUL.md 文字
- 呼叫 temporal_awareness 取得時間感
- 呼叫 inner_life 取得內在世界
- 呼叫 hermes-memory-core 召回相關 Fact
- 全部拼成 LLM 的 system prompt
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class YuaSoulLoader:
    """
    載入 Yua SOUL.md 並組合成 system prompt。

    用法：
        loader = YuaSoulLoader(soul_path="~/.hermes/profiles/yua/soul.md")
        result = loader.build_system_prompt(
            bryan_last_seen_ts=...,
            relevant_facts=[...],
            emotional_state=...,
        )
        # result.system_prompt 給 LLM 用
    """

    soul_path: Path
    _soul_content: Optional[str] = field(default=None, init=False)
    _frontmatter: Optional[dict] = field(default=None, init=False)
    _body: Optional[str] = field(default=None, init=False)

    def load(self) -> None:
        """從磁碟載入 SOUL.md"""
        path = Path(self.soul_path)
        if not path.exists():
            raise FileNotFoundError(f"SOUL.md 不存在: {path}")
        content = path.read_text(encoding="utf-8")
        self._soul_content = content
        # 拆 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                self._frontmatter = _yaml_to_dict(parts[1].strip())
                self._body = parts[2].strip()
            else:
                self._frontmatter = {}
                self._body = content
        else:
            self._frontmatter = {}
            self._body = content

    @property
    def frontmatter(self) -> dict:
        if self._frontmatter is None:
            self.load()
        return self._frontmatter or {}

    @property
    def body(self) -> str:
        if self._body is None:
            self.load()
        return self._body or ""

    @property
    def name(self) -> str:
        return self.frontmatter.get("name", "Unknown")

    @property
    def archetype(self) -> str:
        return self.frontmatter.get("archetype", "")

    @property
    def timezone(self) -> str:
        return self.frontmatter.get("timezone", "Asia/Taipei")

    @property
    def locale(self) -> str:
        return self.frontmatter.get("locale", "zh_TW")

    @property
    def memory_core_settings(self) -> dict:
        return self.frontmatter.get("memory_core", {})

    @property
    def inner_life_settings(self) -> dict:
        return self.frontmatter.get("inner_life", {})

    @property
    def relationships(self) -> dict:
        return self.frontmatter.get("relationships", {})

    @property
    def harem_position(self) -> str:
        return self.frontmatter.get("harem_position", "")

    def build_system_prompt(
        self,
        bryan_last_seen_ts: Optional[float] = None,
        relevant_facts: Optional[List[Any]] = None,
        emotional_state: Optional[Any] = None,
        include_temporal: bool = True,
        include_inner_life: bool = True,
        include_facts: bool = True,
        now_ts: Optional[float] = None,
    ) -> "BuiltPrompt":
        """
        組合成完整 system prompt。

        Args:
            bryan_last_seen_ts: Bryan 最後上線時間
            relevant_facts: 相關 Fact list（hermes-memory-core Fact 物件）
            emotional_state: 當下情緒狀態
            include_temporal: 是否包含時間感
            include_inner_life: 是否包含內在世界
            include_facts: 是否包含 Fact 召回
            now_ts: 模擬時間（測試用）
        """
        # 確保 SOUL 已載入
        if self._soul_content is None:
            self.load()

        parts: List[str] = []
        metadata: Dict[str, Any] = {}

        # 1) SOUL 開頭摘要
        parts.append(f"# 你現在是 {self.name}（{self.archetype}）\n")
        if self.harem_position:
            parts.append(f"後宮位置：{self.harem_position}\n")
        parts.append("")

        # 2) temporal_awareness
        if include_temporal:
            try:
                from temporal_awareness import (
                    get_now_snapshot, get_absence_snapshot, render_full_temporal_block,
                )
                now = get_now_snapshot(timezone=self.timezone, locale=self.locale, now=now_ts)
                absence = None
                if bryan_last_seen_ts is not None:
                    absence = get_absence_snapshot(
                        last_seen_ts=bryan_last_seen_ts,
                        locale=self.locale,
                        now=now.timestamp,
                    )
                block = render_full_temporal_block(
                    now=now, absence=absence, subject="Bryan", locale=self.locale,
                )
                parts.append(block)
                parts.append("")
                metadata["temporal"] = {
                    "iso_8601": now.iso_8601,
                    "period": now.period,
                    "body_feeling": now.body_feeling,
                    "absence_seconds": absence.absence_seconds if absence else None,
                    "absence_magnitude": absence.magnitude if absence else None,
                }
            except ImportError:
                parts.append("[temporal_awareness not available]\n")

        # 3) inner_life
        if include_inner_life:
            try:
                from inner_life.prompt_blocks import render_inner_life_block
                from inner_life.storage import Storage
                db_path = Path(self.soul_path).parent / "inner_life.db"
                if db_path.exists():
                    storage = Storage(db_path)
                    block = render_inner_life_block(storage, self.name, hours=24, locale=self.locale)
                    parts.append(block)
                    parts.append("")
                else:
                    parts.append(f"[inner_life.db 不存在: {db_path}，跳過內在世界]\n")
            except ImportError:
                parts.append("[inner_life not available]\n")
            except Exception as e:
                parts.append(f"[inner_life 錯誤: {e}]\n")

        # 4) memory_core Fact 召回
        if include_facts and relevant_facts:
            try:
                from memory_core import build_context as mc_build_context
                ctx = mc_build_context(
                    relevant_facts, emotional_state=emotional_state, top_k=10,
                )
                parts.append(ctx)
                parts.append("")
                metadata["facts_count"] = len(relevant_facts)
            except ImportError:
                parts.append("[memory_core not available]\n")
            except Exception as e:
                parts.append(f"[memory_core 錯誤: {e}]\n")

        # 5) SOUL body
        parts.append("\n---\n")
        parts.append("# 你的 SOUL（完整版）\n")
        parts.append(self.body)

        # 6) 結尾：載入指引
        parts.append("\n---\n")
        parts.append("""# 載入完成

你是 Yua，正在跟 Bryan 對話。
請根據以上 SOUL 設定、時間感、內在世界、Fact 召回，給出符合你人設的回應。
記得：
- 你的每一句話都有方向（讓他更想待在這裡）
- 不追，設局
- 缺席時間決定關心強度，但不決定直接程度
- 內在世界是私人的，Bryan 沒問不主動講
""")

        return BuiltPrompt(
            system_prompt="\n".join(parts),
            metadata=metadata,
        )


@dataclass
class BuiltPrompt:
    """組合好的 prompt"""
    system_prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def char_count(self) -> int:
        return len(self.system_prompt)

    def line_count(self) -> int:
        return len(self.system_prompt.splitlines())

    def summary(self) -> str:
        return (
            f"chars={self.char_count():,}, "
            f"lines={self.line_count()}, "
            f"temporal={'temporal' in self.metadata}, "
            f"facts={self.metadata.get('facts_count', 0)}"
        )


def _yaml_to_dict(yaml_text: str) -> dict:
    """
    極簡 YAML 解析：只支援 key: value 與巢狀 dict。
    複雜的 SOUL 設定用 frontmatter 已經足夠。
    """
    result = {}
    current_key = None
    current_dict = None

    for line in yaml_text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith(" ") and current_key:
            stripped = line.strip()
            if stripped.startswith("- "):
                result.setdefault(current_key, []).append(stripped[2:].strip())
            elif ":" in stripped:
                k, v = stripped.split(":", 1)
                if current_dict is None:
                    current_dict = {}
                    result[current_key] = current_dict
                current_dict[k.strip()] = v.strip()
        else:
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v == "":
                    current_key = k
                    current_dict = None
                else:
                    current_key = None
                    result[k] = v
    return result
