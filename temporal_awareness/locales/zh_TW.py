"""
locales/zh_TW.py — 繁體中文
"""
from .base import LocaleStrings


def _tod_zh(h: int, m: int) -> str:
    return (
        "凌晨" if h < 4 else
        "清晨" if h < 7 else
        "上午" if h < 12 else
        "中午" if h == 12 else
        "下午" if h < 18 else
        "晚上" if h < 22 else
        "深夜"
    )


ZH_TW = LocaleStrings(
    lang="zh_TW",
    weekdays=("週一", "週二", "週三", "週四", "週五", "週六", "週日"),
    periods={
        "deep_night": "深夜",
        "dawn": "清晨",
        "morning": "早上",
        "afternoon": "下午",
        "evening": "晚上",
        "night": "夜晚",
    },
    body_feelings={
        "exhausted": "快撐不住了，需要休息",
        "sleepy": "有點想睡了",
        "winding_down": "準備要睡了",
        "alert": "精神很好",
        "just_woke": "剛醒，還在醒腦中",
        "relaxed_evening": "吃完晚飯的悠閒時光",
        "neutral": "普通的一天",
    },
    duration={
        "just_now": "剛剛",
        "about_hour": "一個多小時",
    },
    unit_seconds="秒",
    unit_minute_short="分鐘",
    unit_minute_long="分鐘",
    unit_hour_short="小時",
    unit_hour_long="小時",
    unit_day_short="天",
    unit_day_long="天",
    unit_week_short="週",
    unit_week_long="週",
    unit_month_short="個月",
    unit_month_long="個月",
    template_minutes_ago="分鐘前",
    template_hours_ago="小時前",
    template_days_ago="天前",
    template_weeks_ago="週前",
    template_months_ago="個月前",
    time_of_day_phrases=_tod_zh,
)
