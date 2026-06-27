"""
inner_life/monologue.py — 內心獨白

agent 自己的「想法」。可以被 LLM 生成，也可以由 trigger 自動產生。

trigger 範例：
- idle_3hr   — 沉默 3 小時
- after_meal — 吃完飯
- saw_post   — 看到其他 agent 的訊息
- woke_up    — 剛起床
- bedtime    — 準備睡了
- manual     — 手動新增
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Optional, Literal

from .storage import Storage


Trigger = Literal[
    "idle_3hr", "idle_30m", "after_meal", "saw_post",
    "woke_up", "bedtime", "after_work", "manual"
]


@dataclass
class Monologue:
    profile_name: str
    thought: str
    trigger_event: Optional[str] = None
    valence: Optional[float] = None     # -1 ~ 1
    arousal: Optional[float] = None     # 0-1
    ts: float = 0.0
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


def log_monologue(storage: Storage, m: Monologue) -> int:
    return storage.add_monologue(
        profile_name=m.profile_name,
        thought=m.thought,
        trigger_event=m.trigger_event,
        valence=m.valence,
        arousal=m.arousal,
        ts=m.ts,
    )


def get_recent_monologues(
    storage: Storage,
    profile_name: str,
    hours: float = 12,
    limit: int = 10,
) -> list[dict]:
    since_ts = time.time() - hours * 3600
    return storage.get_monologues(profile_name, since_ts=since_ts, limit=limit)
