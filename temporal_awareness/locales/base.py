"""
locales/base.py — LocaleStrings 資料結構
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict


@dataclass(frozen=True)
class LocaleStrings:
    lang: str

    # 星期
    weekdays: tuple

    # 6 時區
    periods: Dict[str, str]

    # 身體感
    body_feelings: Dict[str, str]

    # 特殊 duration 短語
    duration: Dict[str, str]

    # 單位
    unit_seconds: str
    unit_minute_short: str
    unit_minute_long: str
    unit_hour_short: str
    unit_hour_long: str
    unit_day_short: str
    unit_day_long: str
    unit_week_short: str
    unit_week_long: str
    unit_month_short: str
    unit_month_long: str

    # 模板
    template_minutes_ago: str
    template_hours_ago: str
    template_days_ago: str
    template_weeks_ago: str
    template_months_ago: str

    # 時段短語函式：hour, minute → "凌晨" / "下午" / "PM"
    time_of_day_phrases: Callable[[int, int], str]
