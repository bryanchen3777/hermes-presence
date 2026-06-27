"""
absence.py — 模組 C：缺席感知

「Bryan 離開了多久」 ——
不做情感判斷（那是 chrono-social-engine 的事），
只做「自然語生成」+「絕對時間」+「magnitude 分級」。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .naturalize import naturalize_duration
from .types import AbsenceMagnitude, Locale


@dataclass(frozen=True)
class AbsenceSnapshot:
    """「上次互動到現在」快照"""
    last_seen_ts: float
    absence_seconds: float
    magnitude: AbsenceMagnitude

    natural_short: str        # 「剛剛」「2 個多小時」
    natural_long: str         # 「2 小時 13 分鐘」
    natural_relative: str     # 「大約 2 小時 13 分鐘前」「剛剛」

    @property
    def hours(self) -> float:
        return self.absence_seconds / 3600

    @property
    def days(self) -> float:
        return self.absence_seconds / 86400

    def to_dict(self) -> dict:
        return {
            "last_seen_ts": self.last_seen_ts,
            "absence_seconds": self.absence_seconds,
            "magnitude": self.magnitude,
            "natural_short": self.natural_short,
            "natural_long": self.natural_long,
            "natural_relative": self.natural_relative,
            "hours": self.hours,
            "days": self.days,
        }


def _classify_magnitude(seconds: float) -> AbsenceMagnitude:
    """缺席的「規模」分級"""
    if seconds < 60:
        return "just_now"
    if seconds < 300:
        return "moments"
    if seconds < 3600:
        return "minutes"
    if seconds < 10800:        # 3 小時
        return "about_hour"
    if seconds < 43200:        # 12 小時
        return "hours"
    if seconds < 64800:        # 18 小時
        return "half_day"
    if seconds < 115200:       # 32 小時
        return "overnight"
    if seconds < 604800:       # 7 天
        return "days"
    if seconds < 2592000:      # 30 天
        return "weeks"
    return "long_time"


def get_absence_snapshot(
    last_seen_ts: float,
    locale: Locale = "zh_TW",
    now: Optional[float] = None,
) -> AbsenceSnapshot:
    """
    計算「上次互動到現在」的時間感。

    Args:
        last_seen_ts: 上次互動的 Unix timestamp
        locale: "zh_TW" / "en_US" / "ja_JP"
        now: 當前 timestamp（測試用）

    Returns:
        AbsenceSnapshot
    """
    now = now if now is not None else time.time()
    delta = max(0.0, now - last_seen_ts)
    magnitude = _classify_magnitude(delta)
    nat = naturalize_duration(delta, locale=locale)

    return AbsenceSnapshot(
        last_seen_ts=last_seen_ts,
        absence_seconds=delta,
        magnitude=magnitude,
        natural_short=nat["short"],
        natural_long=nat["long"],
        natural_relative=nat["relative"],
    )
