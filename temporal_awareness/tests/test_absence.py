"""
test_absence.py — 模組 C 整合測試
"""
import sys, os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from temporal_awareness import get_absence_snapshot


class TestAbsenceSnapshot(unittest.TestCase):
    def test_just_now(self):
        snap = get_absence_snapshot(last_seen_ts=100, now=130, locale="zh_TW")
        assert snap.magnitude == "just_now"
        assert snap.natural_short == "剛剛"

    def test_moments(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=120, locale="zh_TW")
        assert snap.magnitude == "moments"

    def test_minutes(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=15 * 60, locale="zh_TW")
        assert snap.magnitude == "minutes"
        assert "15分鐘前" == snap.natural_relative

    def test_about_hour(self):
        # 1.5 小時
        snap = get_absence_snapshot(last_seen_ts=0, now=1.5 * 3600, locale="zh_TW")
        assert snap.magnitude == "about_hour"
        assert snap.natural_short == "一個多小時"

    def test_hours(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=5 * 3600, locale="zh_TW")
        assert snap.magnitude == "hours"
        assert "5小時前" == snap.natural_relative

    def test_half_day(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=14 * 3600, locale="zh_TW")
        assert snap.magnitude == "half_day"

    def test_overnight(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=24 * 3600, locale="zh_TW")
        assert snap.magnitude == "overnight"

    def test_days(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=3 * 86400, locale="zh_TW")
        assert snap.magnitude == "days"

    def test_weeks(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=2 * 604800, locale="zh_TW")
        assert snap.magnitude == "weeks"

    def test_long_time(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=60 * 86400, locale="zh_TW")
        assert snap.magnitude == "long_time"

    def test_locale_en(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=2 * 3600, locale="en_US")
        assert "hours ago" in snap.natural_relative

    def test_locale_ja(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=2 * 3600, locale="ja_JP")
        assert "時間前" in snap.natural_relative

    def test_negative_delta_clamped(self):
        # 未來時間 → 應該 clamp 到 0
        snap = get_absence_snapshot(last_seen_ts=200, now=100, locale="zh_TW")
        assert snap.absence_seconds == 0
        assert snap.magnitude == "just_now"

    def test_hours_property(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=3600, locale="zh_TW")
        assert snap.hours == 1.0

    def test_days_property(self):
        snap = get_absence_snapshot(last_seen_ts=0, now=86400, locale="zh_TW")
        assert snap.days == 1.0
