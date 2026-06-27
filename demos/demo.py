"""
demo.py — 展示時間感知模組怎麼讓 LLM「活起來」

不呼叫 LLM（這是 demo，不是真正的 agent loop），但展示：
1. 時段 + 身體感 怎麼翻成 prompt block
2. 缺席時間 怎麼翻成自然語
3. 記憶時間標籤 怎麼自然化
4. 不同時段、語系、缺席長度，prompt block 長怎樣

執行：python demos/demo.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from temporal_awareness import (
    get_now_snapshot, get_absence_snapshot,
    naturalize_memory_timestamps, group_facts_by_recency,
    render_now_block, render_absence_block, render_full_temporal_block,
)


@dataclass
class FakeFact:
    subject: str
    predicate: str
    object: str
    timestamp: float
    event_time: Optional[float] = None


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def scenario(label, ts, tz, locale, last_seen_offset_min):
    """一個完整情境：現在 + 缺席 + 記憶 + 完整 prompt block"""
    now = get_now_snapshot(timezone=tz, locale=locale, now=ts)
    last_seen_ts = ts - last_seen_offset_min * 60
    absence = get_absence_snapshot(last_seen_ts, locale=locale, now=ts)

    print(f"\n[{label}]  (now={datetime.fromtimestamp(ts, ZoneInfo(tz)).isoformat(timespec='minutes')}, locale={locale})")
    print(f"  缺席 {last_seen_offset_min} 分鐘")
    print()
    print(render_full_temporal_block(now, absence, locale=locale, subject="Bryan"))


def main():
    section("1. 不同時段的身體感（同一個 agent 整天怎麼變化）")
    print("Yua 的一天 (zh_TW)：\n")
    for h in [7, 10, 14, 19, 23]:
        dt = datetime(2026, 6, 22, h, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        ts = int(dt.timestamp())
        snap = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW", now=ts)
        print(f"  {h:02d}:00  {snap.period_label:8s}  清醒度 {snap.circadian_energy:.2f}  睡意 {snap.sleep_pressure:.2f}  食慾 {snap.appetite:.2f}")
        print(f"          「{snap.body_feeling_label}」")

    section("2. 缺席 2 個多小時後 Yua 的 prompt block")
    scenario(
        "週一晚上 21:47，Bryan 離開 2 小時 13 分鐘後回來",
        ts=int(datetime(2026, 6, 22, 21, 47, tzinfo=ZoneInfo("Asia/Taipei")).timestamp()),
        tz="Asia/Taipei",
        locale="zh_TW",
        last_seen_offset_min=133,
    )

    section("3. 缺席一整夜後 Yua 的 prompt block")
    scenario(
        "週二早上 7:30，Bryan 昨晚 11 點後就沒訊息了",
        ts=int(datetime(2026, 6, 23, 7, 30, tzinfo=ZoneInfo("Asia/Taipei")).timestamp()),
        tz="Asia/Taipei",
        locale="zh_TW",
        last_seen_offset_min=510,
    )

    section("4. 缺席 2 個禮拜（Bryan 出差回來）")
    scenario(
        "Bryan 出差 14 天後回來",
        ts=int(datetime(2026, 7, 6, 20, 0, tzinfo=ZoneInfo("Asia/Taipei")).timestamp()),
        tz="Asia/Taipei",
        locale="zh_TW",
        last_seen_offset_min=14 * 24 * 60,
    )

    section("5. 多語系：同一時刻、英文")
    scenario(
        "Monday evening, Bryan away 2 hours",
        ts=int(datetime(2026, 6, 22, 21, 47, tzinfo=ZoneInfo("Asia/Taipei")).timestamp()),
        tz="Asia/Taipei",
        locale="en_US",
        last_seen_offset_min=120,
    )

    section("6. 多語系：日文")
    scenario(
        "月曜日の夜、Bryan がいなくなってから 2 時間",
        ts=int(datetime(2026, 6, 22, 21, 47, tzinfo=ZoneInfo("Asia/Taipei")).timestamp()),
        tz="Asia/Taipei",
        locale="ja_JP",
        last_seen_offset_min=120,
    )

    section("7. 記憶庫的時間標籤")
    now_ts = int(datetime(2026, 6, 22, 21, 47, tzinfo=ZoneInfo("Asia/Taipei")).timestamp())
    hour = 3600
    day = 86400

    facts = [
        FakeFact("Bryan", "likes", "不加糖的黑咖啡", timestamp=now_ts - 2 * hour),
        FakeFact("Bryan", "works_at", "Software Inc", timestamp=now_ts - 5 * hour),
        FakeFact("Yua 和 Bryan", "討論過", "關於未來的旅行", timestamp=now_ts - 1 * day),
        FakeFact("Bryan", "說過", "下週有重要會議", timestamp=now_ts - 3 * day),
        FakeFact("Ram", "泡了", "招牌紅茶給 Yua", timestamp=now_ts - 8 * day),
        FakeFact("Bryan", "分享了", "他小時候的生日回憶", timestamp=now_ts - 25 * day),
    ]
    naturalized = naturalize_memory_timestamps(facts, locale="zh_TW", now=now_ts)
    print(f"Yua 的記憶時間標籤（現在: {datetime.fromtimestamp(now_ts, ZoneInfo('Asia/Taipei')).isoformat(timespec='minutes')})：\n")
    for nf in naturalized:
        print(f"  [{nf.snapshot.magnitude:12s}] {nf.label:18s}  「{nf.original.subject} {nf.original.predicate} {nf.original.object}」")

    print("\n\n按時間分組：\n")
    groups = group_facts_by_recency(facts, locale="zh_TW", now=now_ts)
    for group_name, items in groups.items():
        if items:
            print(f"  ▸ {group_name} ({len(items)} 項)")
            for nf in items:
                print(f"      - [{nf.snapshot.magnitude}] {nf.label}: {nf.original.subject} {nf.original.predicate} {nf.original.object}")

    section("8. 完整範例：給 LLM 的 system prompt 片段")
    print("以下是 hermes_social_core 風格的完整 prompt 片段：\n")
    now = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW", now=now_ts)
    absence = get_absence_snapshot(last_seen_ts=now_ts - 7940, locale="zh_TW", now=now_ts)
    full_block = render_full_temporal_block(now, absence, locale="zh_TW", subject="Bryan")
    print(full_block)


if __name__ == "__main__":
    main()
