"""
locales/en_US.py — English (US)
"""
from .base import LocaleStrings


def _tod_en(h: int, m: int) -> str:
    h12 = h % 12 or 12
    ampm = "AM" if h < 12 else "PM"
    return f"{h12}:{m:02d} {ampm}"


EN_US = LocaleStrings(
    lang="en_US",
    weekdays=("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    periods={
        "deep_night": "deep night",
        "dawn": "early dawn",
        "morning": "morning",
        "afternoon": "afternoon",
        "evening": "evening",
        "night": "night",
    },
    body_feelings={
        "exhausted": "running on empty, need rest",
        "sleepy": "getting sleepy",
        "winding_down": "winding down for the night",
        "alert": "wide awake and focused",
        "just_woke": "just woke up, still groggy",
        "relaxed_evening": "relaxed post-dinner evening",
        "neutral": "a normal kind of day",
    },
    duration={
        "just_now": "just now",
        "about_hour": "a little over an hour",
    },
    unit_seconds="seconds",
    unit_minute_short="min",
    unit_minute_long="minutes",
    unit_hour_short="hr",
    unit_hour_long="hours",
    unit_day_short="day",
    unit_day_long="days",
    unit_week_short="wk",
    unit_week_long="weeks",
    unit_month_short="mo",
    unit_month_long="months",
    template_minutes_ago=" minutes ago",
    template_hours_ago=" hours ago",
    template_days_ago=" days ago",
    template_weeks_ago=" weeks ago",
    template_months_ago=" months ago",
    time_of_day_phrases=_tod_en,
)
