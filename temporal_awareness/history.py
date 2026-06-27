"""
history.py — 模組 D：歷史時間標籤

把記憶庫（yua-memory / sage-lite / dict）裡的 timestamp 翻成自然語標籤。

設計：duck typing ——
任何有 .timestamp 屬性的物件都接受。
不改原物件，產生新列表。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Optional

from .absence import get_absence_snapshot, AbsenceSnapshot
from .types import Locale


@dataclass(frozen=True)
class NaturalizedFact:
    """包裝過的事實 + 自然語時間標籤"""
    original: object
    snapshot: AbsenceSnapshot
    label: str              # 「昨天深夜」「上週三」「剛剛」


def naturalize_memory_timestamps(
    facts: Iterable,
    locale: Locale = "zh_TW",
    now: Optional[float] = None,
) -> list[NaturalizedFact]:
    """
    把一串事實 (有 .timestamp 屬性) 翻成自然語標籤。

    優先用 event_time > timestamp（事件發生時間 vs 記錄時間）。
    """
    now = now if now is not None else time.time()
    out: list[NaturalizedFact] = []
    for f in facts:
        ts = _get_field(f, "event_time")
        if ts is None:
            ts = _get_field(f, "timestamp")
        if ts is None:
            ts = now
        snap = get_absence_snapshot(ts, locale=locale, now=now)
        out.append(NaturalizedFact(
            original=f,
            snapshot=snap,
            label=snap.natural_relative,
        ))
    return out


def _get_field(obj, name: str):
    """
    從物件或 dict 取得欄位。
    - 物件：getattr(obj, name, None)
    - dict：obj.get(name)
    - 其它：None
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def group_facts_by_recency(
    facts: Iterable,
    locale: Locale = "zh_TW",
    now: Optional[float] = None,
) -> dict[str, list[NaturalizedFact]]:
    """
    把事實按時間分組：
    - "today"        當天
    - "yesterday"    昨天
    - "this_week"    本週
    - "this_month"   本月
    - "long_ago"     很久以前
    """
    now = now if now is not None else time.time()
    naturalized = naturalize_memory_timestamps(facts, locale=locale, now=now)

    groups: dict[str, list[NaturalizedFact]] = {
        "today": [], "yesterday": [], "this_week": [],
        "this_month": [], "long_ago": [],
    }

    for nf in naturalized:
        h = nf.snapshot.hours
        d = nf.snapshot.days
        if h < 24:
            groups["today"].append(nf)
        elif d < 2:
            groups["yesterday"].append(nf)
        elif d < 7:
            groups["this_week"].append(nf)
        elif d < 30:
            groups["this_month"].append(nf)
        else:
            groups["long_ago"].append(nf)

    return groups
