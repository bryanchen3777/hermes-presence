"""
temporal_awareness — 時間感知 library

讓任何 agent 獲得「現在」、「缺席多久」、「記憶時間標籤」三種時間感。

設計原則：
- 純函式，0 DB，跨平台
- i18n：繁中、英文、日文
- 概念隔離：不綁定任何 agent framework

公開 API:
    NowSnapshot, get_now_snapshot
    AbsenceSnapshot, get_absence_snapshot
    NaturalizedFact, naturalize_memory_timestamps, group_facts_by_recency
    render_now_block, render_absence_block, render_full_temporal_block
    naturalize_duration, naturalize_time_of_day, naturalize_day_phase
"""
from .now import NowSnapshot, get_now_snapshot
from .absence import AbsenceSnapshot, get_absence_snapshot
from .history import (
    NaturalizedFact,
    naturalize_memory_timestamps,
    group_facts_by_recency,
)
from .prompt_blocks import (
    render_now_block,
    render_absence_block,
    render_full_temporal_block,
)
from .naturalize import (
    naturalize_duration,
    naturalize_time_of_day,
    naturalize_day_phase,
)

__version__ = "0.1.0"
__all__ = [
    # now
    "NowSnapshot",
    "get_now_snapshot",
    # absence
    "AbsenceSnapshot",
    "get_absence_snapshot",
    # history
    "NaturalizedFact",
    "naturalize_memory_timestamps",
    "group_facts_by_recency",
    # prompt blocks
    "render_now_block",
    "render_absence_block",
    "render_full_temporal_block",
    # naturalize
    "naturalize_duration",
    "naturalize_time_of_day",
    "naturalize_day_phase",
]
