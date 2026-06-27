"""
test_naturalize.py — naturalize.py 純函式測試
"""
import sys, os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from temporal_awareness.naturalize import (
    naturalize_duration, naturalize_time_of_day, naturalize_day_phase,
)


class TestNaturalizeDuration(unittest.TestCase):
    def test_just_now(self):
        r = naturalize_duration(0)
        assert r["short"] == "剛剛"
        assert r["relative"] == "剛剛"

    def test_minutes_zh(self):
        r = naturalize_duration(30 * 60, locale="zh_TW")
        assert r["relative"] == "30分鐘前"
        assert r["short"] == "30 分鐘"

    def test_minutes_en(self):
        r = naturalize_duration(30 * 60, locale="en_US")
        assert "minutes ago" in r["relative"]

    def test_minutes_ja(self):
        r = naturalize_duration(30 * 60, locale="ja_JP")
        assert r["relative"] == "30分前"

    def test_about_hour_zh(self):
        r = naturalize_duration(90 * 60, locale="zh_TW")
        # 1.5 小時，有 30 分鐘零頭
        assert r["short"] == "一個多小時"

    def test_exact_hour_zh(self):
        r = naturalize_duration(3 * 3600, locale="zh_TW")
        assert r["short"] == "3 小時"
        assert r["relative"] == "3小時前"

    def test_days(self):
        r = naturalize_duration(2 * 86400, locale="zh_TW")
        assert "天" in r["short"]
        assert "前" in r["relative"]

    def test_weeks(self):
        r = naturalize_duration(2 * 604800, locale="zh_TW")
        assert "週" in r["short"]

    def test_months(self):
        r = naturalize_duration(2 * 2592000, locale="zh_TW")
        assert "個月" in r["short"]


class TestNaturalizeTimeOfDay:
    def test_evening_zh(self):
        s = naturalize_time_of_day(21, 47, locale="zh_TW")
        assert "晚上" in s
        assert "21" in s
        assert "47" in s

    def test_afternoon_en(self):
        s = naturalize_time_of_day(14, 30, locale="en_US")
        assert "2:30 PM" == s

    def test_morning_ja(self):
        s = naturalize_time_of_day(10, 15, locale="ja_JP")
        assert "10時15分" in s


class TestNaturalizeDayPhase:
    def test_evening_zh(self):
        assert "晚上" in naturalize_day_phase(20, 0, locale="zh_TW")

    def test_morning_en(self):
        assert "morning" in naturalize_day_phase(8, 0, locale="en_US")

    def test_deep_night_ja(self):
        assert "深夜" in naturalize_day_phase(2, 0, locale="ja_JP")
