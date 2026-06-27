"""
test_history.py — 模組 D 整合測試
"""
import sys, os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from dataclasses import dataclass
from typing import Optional

from temporal_awareness import naturalize_memory_timestamps, group_facts_by_recency


@dataclass
class FakeFact:
    """模擬 yua-memory / sage-lite 的事實"""
    subject: str
    predicate: str
    object: str
    timestamp: float
    event_time: Optional[float] = None


class TestNaturalizeMemory(unittest.TestCase):
    def test_uses_event_time_over_timestamp(self):
        f = FakeFact("Bryan", "likes", "hiking", timestamp=100, event_time=50)
        result = naturalize_memory_timestamps([f], now=100, locale="zh_TW")
        # event_time=50, now=100 → 50 秒
        assert "剛剛" in result[0].label or result[0].snapshot.magnitude == "moments"

    def test_falls_back_to_timestamp(self):
        f = FakeFact("Bryan", "likes", "hiking", timestamp=100, event_time=None)
        result = naturalize_memory_timestamps([f], now=100, locale="zh_TW")
        assert result[0].snapshot.absence_seconds == 0

    def test_dict_also_works(self):
        # 7940 秒 ≈ 2 小時 12 分 → 屬於 "about_hour"
        facts = [{"timestamp": 0, "event_time": 0}]
        result = naturalize_memory_timestamps(facts, now=7940, locale="zh_TW")
        self.assertEqual(result[0].snapshot.magnitude, "about_hour")

    def test_label_zh(self):
        f = FakeFact("a", "b", "c", timestamp=0)
        result = naturalize_memory_timestamps([f], now=86400, locale="zh_TW")
        assert "天前" in result[0].label

    def test_label_en(self):
        f = FakeFact("a", "b", "c", timestamp=0)
        result = naturalize_memory_timestamps([f], now=86400, locale="en_US")
        assert "ago" in result[0].label

    def test_label_ja(self):
        f = FakeFact("a", "b", "c", timestamp=0)
        result = naturalize_memory_timestamps([f], now=86400, locale="ja_JP")
        assert "前" in result[0].label


class TestGroupByRecency(unittest.TestCase):
    def test_grouping(self):
        now = 100000
        facts = [
            FakeFact("a", "b", "c", timestamp=now - 3600),       # 1hr ago → today
            FakeFact("a", "b", "c", timestamp=now - 86400),      # 1 day ago → yesterday
            FakeFact("a", "b", "c", timestamp=now - 3 * 86400),  # 3 days → this_week
            FakeFact("a", "b", "c", timestamp=now - 10 * 86400), # 10 days → this_month
            FakeFact("a", "b", "c", timestamp=now - 60 * 86400), # 60 days → long_ago
        ]
        groups = group_facts_by_recency(facts, now=now, locale="zh_TW")
        assert len(groups["today"]) == 1
        assert len(groups["yesterday"]) == 1
        assert len(groups["this_week"]) == 1
        assert len(groups["this_month"]) == 1
        assert len(groups["long_ago"]) == 1
