"""
naturalize.py — 純函式：timestamp → 自然語
所有 locale 規則都在 locales/ 裡
"""
from __future__ import annotations

from typing import Dict

from .locales import get_locale
from .types import Locale


def naturalize_duration(
    seconds: float,
    locale: Locale = "zh_TW",
) -> Dict[str, str]:
    """
    把秒數翻成自然語。回傳三種版本：
    - short:   簡潔版（「剛剛」「30 分鐘」「2 天」）
    - long:    精確版（「30 分鐘」「2 小時 13 分鐘」「3 天 4 小時」）
    - relative: 帶「前」的版本（「30 分鐘前」「2 小時前」）
    """
    s = max(0.0, seconds)
    loc = get_locale(locale)

    if s < 60:
        return {
            "short": loc.duration["just_now"],
            "long": f"{int(s)} {loc.unit_seconds}",
            "relative": loc.duration["just_now"],
        }
    if s < 3600:
        m = int(s / 60)
        return {
            "short": f"{m} {loc.unit_minute_short}",
            "long": f"{m} {loc.unit_minute_long}",
            "relative": f"{m}{loc.template_minutes_ago}",
        }
    if s < 86400:
        h_full = s / 3600
        h_int = int(h_full)
        m_part = int((h_full - h_int) * 60)
        if m_part == 0:
            short_str = f"{h_int} {loc.unit_hour_short}"
            return {
                "short": short_str,
                "long": f"{h_int} {loc.unit_hour_long}",
                "relative": f"{h_int}{loc.template_hours_ago}",
            }
        # 有零頭
        return {
            "short": loc.duration["about_hour"],
            "long": f"{h_int} {loc.unit_hour_long} {m_part} {loc.unit_minute_long}",
            "relative": loc.duration["about_hour"],
        }
    if s < 604800:
        d = int(s / 86400)
        return {
            "short": f"{d} {loc.unit_day_short}",
            "long": f"{d} {loc.unit_day_long}",
            "relative": f"{d}{loc.template_days_ago}",
        }
    if s < 2592000:
        w = int(s / 604800)
        return {
            "short": f"{w} {loc.unit_week_short}",
            "long": f"{w} {loc.unit_week_long}",
            "relative": f"{w}{loc.template_weeks_ago}",
        }
    mo = int(s / 2592000)
    return {
        "short": f"{mo} {loc.unit_month_short}",
        "long": f"{mo} {loc.unit_month_long}",
        "relative": f"{mo}{loc.template_months_ago}",
    }


def naturalize_time_of_day(
    hour: int,
    minute: int,
    locale: Locale = "zh_TW",
) -> str:
    """
    21:47 → 「晚上 9 點 47 分」(zh_TW)
    21:47 → "9:47 PM"     (en_US)
    21:47 → "夜 21時47分"   (ja_JP)
    """
    loc = get_locale(locale)
    if loc.lang == "zh_TW":
        period_str = loc.time_of_day_phrases(hour, minute)
        return f"{period_str}{hour} 點 {minute:02d} 分"
    if loc.lang == "ja_JP":
        period_str = loc.time_of_day_phrases(hour, minute)
        return f"{period_str}{hour}時{minute}分"
    # en_US
    h12 = hour % 12 or 12
    ampm = "AM" if hour < 12 else "PM"
    return f"{h12}:{minute:02d} {ampm}"


def naturalize_day_phase(
    hour: int,
    minute: int,
    locale: Locale = "zh_TW",
) -> str:
    """
    21:47 → 「晚上」(zh_TW)
    14:00 → "afternoon" (en_US)
    """
    from .clock import classify_period
    period = classify_period(hour, minute)
    loc = get_locale(locale)
    return loc.periods[period]
