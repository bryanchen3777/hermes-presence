"""
inner_life/body.py — 身體狀態管理

純規則：根據「現在時間 + 上次用餐 + 上次睡覺」推算身體狀態。
不存任何狀態（無副作用），純函式 + 寫入 storage。

維度：
- energy:   0-1，整體能量
- hunger:   0-1，飢餓
- fatigue:  0-1，疲勞
- comfort:  0-1，環境舒適度
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from .storage import Storage


@dataclass
class BodyState:
    profile_name: str
    energy: float
    hunger: float
    fatigue: float
    comfort: float = 0.8
    last_meal_ts: Optional[float] = None
    last_sleep_ts: Optional[float] = None
    last_awake_hours: float = 0.0
    ts: float = 0.0
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt(self, locale: str = "zh_TW") -> str:
        """給 LLM 看的自然語"""
        energy_w = _bucket_word(self.energy, [
            ("沒電了", 0.15), ("很累", 0.35), ("有點累", 0.55),
            ("普通", 0.75), ("精神不錯", 0.90), ("神采奕奕", 1.01)
        ])
        hunger_w = _bucket_word(self.hunger, [
            ("很飽", 0.15), ("不餓", 0.35), ("微餓", 0.55),
            ("餓了", 0.75), ("很餓", 0.90), ("快昏了", 1.01)
        ])
        fatigue_w = _bucket_word(self.fatigue, [
            ("精神飽滿", 0.15), ("還行", 0.35), ("有點累", 0.55),
            ("想休息", 0.75), ("需要躺下", 0.90), ("快不行", 1.01)
        ])
        return f"能量 {energy_w}、{hunger_w}、{fatigue_w}"


def _bucket_word(value: float, buckets: list) -> str:
    for word, threshold in buckets:
        if value < threshold:
            return word
    return buckets[-1][0]


def compute_body_state(
    profile_name: str,
    last_meal_ts: Optional[float] = None,
    last_sleep_ts: Optional[float] = None,
    now: Optional[float] = None,
) -> BodyState:
    """
    純函式：根據時間計算身體狀態。
    """
    now = now if now is not None else time.time()
    dt = datetime.fromtimestamp(now, tz=ZoneInfo("UTC"))

    # 能量：依時段（與 temporal_awareness 一致的概念）
    hour = dt.hour
    if 6 <= hour < 9:
        energy = 0.55
    elif 9 <= hour < 12:
        energy = 0.85
    elif 12 <= hour < 14:
        energy = 0.75
    elif 14 <= hour < 18:
        energy = 0.80
    elif 18 <= hour < 22:
        energy = 0.65
    else:
        energy = 0.30

    # 飢餓：距離上次用餐時間越長越餓
    if last_meal_ts is None:
        hunger = 0.50  # 不知道上次吃飯
    else:
        hours_since_meal = (now - last_meal_ts) / 3600
        hunger = min(1.0, hours_since_meal / 6.0)  # 6 小時沒吃 → 1.0

    # 疲勞：依時段 + 距離上次睡覺
    if 14 <= hour < 17:
        fatigue = 0.50  # 下午小累
    elif 17 <= hour < 22:
        fatigue = 0.60
    elif 22 <= hour or hour < 6:
        fatigue = 0.80  # 晚上/深夜
    else:
        fatigue = 0.30

    # 舒適度（簡化：依溫度季節預設 0.8）
    comfort = 0.8

    # 上次清醒時長
    last_awake_hours = 0.0
    if last_sleep_ts is not None:
        last_awake_hours = (now - last_sleep_ts) / 3600
        last_awake_hours = max(0.0, min(48.0, last_awake_hours))

    return BodyState(
        profile_name=profile_name,
        energy=round(energy, 2),
        hunger=round(hunger, 2),
        fatigue=round(fatigue, 2),
        comfort=comfort,
        last_meal_ts=last_meal_ts,
        last_sleep_ts=last_sleep_ts,
        last_awake_hours=round(last_awake_hours, 2),
        ts=now,
    )


def save_body_state(storage: Storage, state: BodyState) -> int:
    """寫入 storage"""
    return storage.add_body_state(
        profile_name=state.profile_name,
        energy=state.energy,
        hunger=state.hunger,
        fatigue=state.fatigue,
        comfort=state.comfort,
        last_meal_ts=state.last_meal_ts,
        last_sleep_ts=state.last_sleep_ts,
        last_awake_hours=state.last_awake_hours,
        ts=state.ts,
    )


def get_latest_body_state(storage: Storage, profile_name: str) -> Optional[BodyState]:
    raw = storage.get_latest_body_state(profile_name)
    if raw is None:
        return None
    return BodyState(
        profile_name=raw["profile_name"],
        energy=raw["energy"],
        hunger=raw["hunger"],
        fatigue=raw["fatigue"],
        comfort=raw["comfort"],
        last_meal_ts=raw["last_meal_ts"],
        last_sleep_ts=raw["last_sleep_ts"],
        last_awake_hours=raw["last_awake_hours"],
        ts=raw["ts"],
        id=raw["id"],
    )
