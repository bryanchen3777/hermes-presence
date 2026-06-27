"""
inner_life/activity.py — 活動記錄的邏輯層

儲存 + 查詢活動。
活動分類：
- wake     起床
- sleep    睡覺
- meal     用餐（早/午/晚/點心）
- work     工作/任務
- leisure  休閒（看書、看電影、散步）
- social   社交（跟其他 agent 互動）
- rest     發呆、放空
- thought  思考、反思
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal

from .storage import Storage


ActivityType = Literal[
    "wake", "sleep", "meal", "work", "leisure", "social", "rest", "thought"
]


@dataclass
class Activity:
    profile_name: str
    activity_type: ActivityType
    title: str
    description: Optional[str] = None
    energy_delta: float = 0.0
    emotion_delta: float = 0.0
    related_profile: Optional[str] = None
    source: Literal["rule", "llm", "manual"] = "rule"
    ts: float = field(default_factory=time.time)
    id: Optional[int] = None  # 儲存後填入

    def to_dict(self) -> dict:
        return asdict(self)


def log_activity(storage: Storage, activity: Activity) -> int:
    """記錄一個活動"""
    return storage.add_activity(
        profile_name=activity.profile_name,
        activity_type=activity.activity_type,
        title=activity.title,
        description=activity.description,
        energy_delta=activity.energy_delta,
        emotion_delta=activity.emotion_delta,
        related_profile=activity.related_profile,
        source=activity.source,
        ts=activity.ts,
    )


def get_recent_activities(
    storage: Storage,
    profile_name: str,
    hours: float = 24,
    limit: int = 50,
) -> list[dict]:
    """取得最近 N 小時的活動"""
    since_ts = time.time() - hours * 3600
    return storage.get_activities(profile_name, since_ts=since_ts, limit=limit)


def get_today_activities(storage: Storage, profile_name: str) -> list[dict]:
    """取得今天 0:00 之後的活動"""
    import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Taipei")
    today_start = datetime.datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    since_ts = today_start.timestamp()
    return storage.get_activities(profile_name, since_ts=since_ts, limit=200)
