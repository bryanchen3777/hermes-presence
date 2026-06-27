"""
now.py — 模組 A：現在時刻感知

不存任何資料（純函式）。
從 chrono-social-engine 的「時區 + sleep pressure + behavior bias」概念取經。
輸出：NowSnapshot 物件 + 對應的 LLM prompt block。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .clock import (
    classify_period, sleep_pressure_at, circadian_energy_at,
    appetite_at, body_feeling_for,
)
from .locales import get_locale
from .types import Period, Locale, BodyFeeling


@dataclass(frozen=True)
class NowSnapshot:
    """現在這個時刻的完整快照"""

    # 絕對時間
    timestamp: float
    iso_8601: str
    timezone: str
    weekday: int            # 0=Mon, 6=Sun
    weekday_name: str

    # 時段
    period: Period
    period_label: str       # 「晚上」「傍晚」之類（依 locale）

    # 身體節律（純從時間推算，0-1）
    circadian_energy: float # 清醒度
    sleep_pressure: float   # 睡意
    appetite: float         # 食慾

    # 給 LLM 用的「身體感」
    body_feeling: BodyFeeling
    body_feeling_label: str # 自然語版本

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "iso_8601": self.iso_8601,
            "timezone": self.timezone,
            "weekday": self.weekday,
            "weekday_name": self.weekday_name,
            "period": self.period,
            "period_label": self.period_label,
            "circadian_energy": self.circadian_energy,
            "sleep_pressure": self.sleep_pressure,
            "appetite": self.appetite,
            "body_feeling": self.body_feeling,
            "body_feeling_label": self.body_feeling_label,
        }


def get_now_snapshot(
    timezone: str = "Asia/Taipei",
    locale: Locale = "zh_TW",
    now: Optional[float] = None,
) -> NowSnapshot:
    """
    取得「現在」的完整時間快照。

    Args:
        timezone: IANA timezone name (e.g. "Asia/Taipei", "America/New_York")
        locale: "zh_TW" / "en_US" / "ja_JP"
        now: Unix timestamp (測試用)

    Returns:
        NowSnapshot：包含絕對時間、時段、身體節律、自然語描述

    Raises:
        ValueError: timezone 不合法
    """
    now = now if now is not None else time.time()

    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"Invalid timezone: {timezone!r}") from e

    dt = datetime.fromtimestamp(now, tz=tz)
    loc = get_locale(locale)

    period = classify_period(dt.hour, dt.minute)
    weekday_name = loc.weekdays[dt.weekday()]
    period_label = loc.periods[period]

    sp = sleep_pressure_at(dt.hour, dt.minute)
    energy = circadian_energy_at(dt.hour, dt.minute)
    app = appetite_at(dt.hour, dt.minute)

    feeling = body_feeling_for(period, energy)
    feeling_label = loc.body_feelings[feeling]

    return NowSnapshot(
        timestamp=now,
        iso_8601=dt.isoformat(timespec="minutes"),
        timezone=timezone,
        weekday=dt.weekday(),
        weekday_name=weekday_name,
        period=period,
        period_label=period_label,
        circadian_energy=energy,
        sleep_pressure=sp,
        appetite=app,
        body_feeling=feeling,  # type: ignore[arg-type]
        body_feeling_label=feeling_label,
    )
