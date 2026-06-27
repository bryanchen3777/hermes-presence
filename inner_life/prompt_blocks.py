"""
inner_life/prompt_blocks.py — 給 LLM 用的 prompt block

私密原則：Bryan 沒問，agent 不會主動講
當 Bryan 問「你今天做什麼」時，這裡的 block 給 LLM 參考
"""
from __future__ import annotations
from typing import Optional

from .activity import get_today_activities, get_recent_activities
from .body import get_latest_body_state, BodyState
from .monologue import get_recent_monologues
from .storage import Storage


def render_inner_life_block(
    storage: Storage,
    profile_name: str,
    hours: float = 24,
    locale: str = "zh_TW",
) -> str:
    """
    完整的「內在世界」prompt block。

    包含：
    - 最近的活動（按時間排序）
    - 當下身體狀態
    - 最近的內心獨白

    注意：這個 block 是「參考資料」，不是「一定要講」。
    LLM 應該根據 SOUL.md 決定要不要說、說多少、用什麼語氣。
    """
    activities = get_recent_activities(storage, profile_name, hours=hours, limit=20)
    body = get_latest_body_state(storage, profile_name)
    monologues = get_recent_monologues(storage, profile_name, hours=hours, limit=5)

    lines = ["【你的內在世界（內部參考）】"]

    if body:
        lines.append(f"身體：{body.to_prompt(locale)}")

    if activities:
        lines.append("\n最近做過的事：")
        for a in reversed(activities):  # 由早到晚
            when = _format_time_short(a["ts"], locale=locale)
            title = a["title"]
            lines.append(f"  {when}  {title}")
            if a.get("description"):
                lines.append(f"          {a['description']}")
    else:
        lines.append("\n（還沒有活動記錄）")

    if monologues:
        lines.append("\n最近的想法：")
        for m in reversed(monologues):
            when = _format_time_short(m["ts"], locale=locale)
            thought = m["thought"]
            lines.append(f"  {when}  「{thought}」")

    return "\n".join(lines)


def render_body_only(storage: Storage, profile_name: str, locale: str = "zh_TW") -> str:
    """只渲染身體狀態（用於 LLM 短回應時）"""
    body = get_latest_body_state(storage, profile_name)
    if not body:
        return ""
    return f"身體：{body.to_prompt(locale)}"


def _format_time_short(ts: float, locale: str = "zh_TW") -> str:
    from datetime import datetime
    dt = datetime.fromtimestamp(ts)
    return f"{dt.hour:02d}:{dt.minute:02d}"
