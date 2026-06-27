"""
test_now.py — 模組 A 整合測試
"""
import sys, os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from datetime import datetime
from zoneinfo import ZoneInfo

from temporal_awareness import get_now_snapshot


# 固定 timestamp 對照表：(unix_ts, tz, 預期 ISO 8601, 預期 period, 預期 weekday_name)
FIXTURES = [
    # 2026-06-22 21:47 Asia/Taipei → 週一晚上
    (1782136020, "Asia/Taipei", "2026-06-22T21:47+08:00", "evening", "週一"),
    # 2026-01-01 00:00 Asia/Taipei → 週四深夜
    (1767196800, "Asia/Taipei", "2026-01-01T00:00+08:00", "deep_night", "週四"),
    # 2026-12-25 14:30 Asia/Taipei → 週五下午
    (1798180200, "Asia/Taipei", "2026-12-25T14:30+08:00", "afternoon", "週五"),
]


class TestNowSnapshot(unittest.TestCase):
    def test_basic_zh_tw(self):
        ts, tz, expected_iso, expected_period, expected_weekday = FIXTURES[0]
        snap = get_now_snapshot(timezone=tz, locale="zh_TW", now=ts)
        assert snap.iso_8601 == expected_iso
        assert snap.period == expected_period
        assert snap.weekday_name == expected_weekday
        assert snap.timezone == tz

    def test_basic_en_us(self):
        ts, tz, _, expected_period, _ = FIXTURES[0]
        snap = get_now_snapshot(timezone=tz, locale="en_US", now=ts)
        # 2026-06-22 21:47 Asia/Taipei = 2026-06-22 13:47 UTC = 週一
        # en 模式 weekday_name 應該是 Monday
        assert snap.weekday_name == "Monday"
        assert snap.period == expected_period

    def test_basic_ja_jp(self):
        ts, tz, _, _, expected_weekday_zh = FIXTURES[0]
        snap = get_now_snapshot(timezone=tz, locale="ja_JP", now=ts)
        assert snap.weekday_name == "月曜日"
        # 體感描述要能翻譯
        assert snap.body_feeling_label != ""

    def test_body_feeling_label_localized(self):
        ts = FIXTURES[0][0]
        zh = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW", now=ts)
        en = get_now_snapshot(timezone="Asia/Taipei", locale="en_US", now=ts)
        ja = get_now_snapshot(timezone="Asia/Taipei", locale="ja_JP", now=ts)
        # 同一時刻三種語系都應該有標籤
        assert zh.body_feeling_label != en.body_feeling_label
        assert zh.body_feeling_label != ja.body_feeling_label

    def test_energy_in_range(self):
        snap = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW", now=FIXTURES[0][0])
        assert 0.0 <= snap.circadian_energy <= 1.0
        assert 0.0 <= snap.sleep_pressure <= 1.0
        assert 0.0 <= snap.appetite <= 1.0

    def test_invalid_timezone_raises(self):
        try:
            get_now_snapshot(timezone="Mars/Olympus_Mons", now=0)
            assert False, "should have raised"
        except ValueError:
            pass

    def test_to_dict_serializable(self):
        snap = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW", now=FIXTURES[0][0])
        d = snap.to_dict()
        # 應該可以 JSON serialize
        import json
        json.dumps(d)
