"""
types.py — 統一型別定義

所有跨模組共享的型別放這裡，避免循環 import。
"""
from __future__ import annotations

from typing import Literal, Protocol, Optional, runtime_checkable


# 6 時區（與 chrono-social-engine 對齊）
Period = Literal[
    "deep_night",   # 00:00-03:59
    "dawn",         # 04:00-06:59
    "morning",      # 07:00-11:59
    "afternoon",    # 12:00-17:59
    "evening",      # 18:00-21:59
    "night",        # 22:00-23:59
]

# 缺席的「規模」分級
AbsenceMagnitude = Literal[
    "just_now",     # < 1 分鐘
    "moments",      # < 5 分鐘
    "minutes",      # 5-60 分鐘
    "about_hour",   # 1-3 小時
    "hours",        # 3-12 小時
    "half_day",     # 12-18 小時
    "overnight",    # 18-32 小時
    "days",         # 2-6 天
    "weeks",        # 1-4 週
    "long_time",    # > 1 個月
]

# 身體感的「描述」分級
BodyFeeling = Literal[
    "exhausted",
    "sleepy",
    "winding_down",
    "alert",
    "just_woke",
    "relaxed_evening",
    "neutral",
]

# 支援的語系
Locale = Literal["zh_TW", "en_US", "ja_JP"]


@runtime_checkable
class FactLike(Protocol):
    """
    任何「帶 timestamp 的物件」都算 ——
    sage-lite Fact、yua-memory row、dict、dataclass 都可。
    """
    timestamp: float
    event_time: Optional[float]
