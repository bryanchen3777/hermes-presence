"""
locales/ja_JP.py — 日本語
"""
from .base import LocaleStrings


def _tod_ja(h: int, m: int) -> str:
    return (
        "未明" if h < 4 else
        "明け方" if h < 7 else
        "午前" if h < 12 else
        "正午" if h == 12 else
        "午後" if h < 18 else
        "夜" if h < 22 else
        "深夜"
    )


JA_JP = LocaleStrings(
    lang="ja_JP",
    weekdays=("月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"),
    periods={
        "deep_night": "深夜",
        "dawn": "明け方",
        "morning": "朝",
        "afternoon": "午後",
        "evening": "夕方〜夜",
        "night": "夜",
    },
    body_feelings={
        "exhausted": "もう限界、休憩が必要",
        "sleepy": "少し眠い",
        "winding_down": "眠る準備中",
        "alert": "とても元気",
        "just_woke": "起きたばかり、まだぼんやり",
        "relaxed_evening": "夕食後、のんびり",
        "neutral": "普通の一日",
    },
    duration={
        "just_now": "たった今",
        "about_hour": "1時間ちょっと",
    },
    unit_seconds="秒",
    unit_minute_short="分",
    unit_minute_long="分",
    unit_hour_short="時間",
    unit_hour_long="時間",
    unit_day_short="日",
    unit_day_long="日",
    unit_week_short="週",
    unit_week_long="週間",
    unit_month_short="ヶ月",
    unit_month_long="ヶ月",
    template_minutes_ago="分前",
    template_hours_ago="時間前",
    template_days_ago="日前",
    template_weeks_ago="週間前",
    template_months_ago="ヶ月前",
    time_of_day_phrases=_tod_ja,
)
