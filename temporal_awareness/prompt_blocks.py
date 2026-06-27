"""
prompt_blocks.py — 給 LLM 用的 prompt block

把 NowSnapshot / AbsenceSnapshot 翻成 LLM 看得懂的中文 block。
agent 接上 library 後，每次 pre-LLM hook 呼叫它，得到的字串塞進 system prompt。
"""
from __future__ import annotations
from typing import Optional

from .now import NowSnapshot
from .absence import AbsenceSnapshot
from .types import Locale


def render_now_block(
    snap: NowSnapshot,
    locale: Locale = "zh_TW",
) -> str:
    """
    給 LLM 看的「現在」。

    範例輸出 (zh_TW)：
        【現在】
        時間：2026-06-22（週一）21:47 Asia/Taipei
        時段：晚上
        身體：清醒度 0.61、睡意 0.70、食慾 0.18
        感覺：吃完晚飯的悠閒時光
    """
    if locale == "en_US":
        return f"""[Now]
Time: {snap.iso_8601} ({snap.weekday_name}) {snap.timezone}
Period: {snap.period_label}
Body: energy {snap.circadian_energy}, sleep pressure {snap.sleep_pressure}, appetite {snap.appetite}
Feeling: {snap.body_feeling_label}
"""
    if locale == "ja_JP":
        return f"""【今】
時刻: {snap.iso_8601}（{snap.weekday_name}）{snap.timezone}
時間帯: {snap.period_label}
体調: エネルギー {snap.circadian_energy}、眠気 {snap.sleep_pressure}、食欲 {snap.appetite}
感覚: {snap.body_feeling_label}
"""
    # zh_TW
    return f"""【現在】
時間：{snap.iso_8601}（{snap.weekday_name}）{snap.timezone}
時段：{snap.period_label}
身體：清醒度 {snap.circadian_energy}、睡意 {snap.sleep_pressure}、食慾 {snap.appetite}
感覺：{snap.body_feeling_label}
"""


def render_absence_block(
    snap: AbsenceSnapshot,
    locale: Locale = "zh_TW",
    subject: str = "Bryan",
) -> str:
    """
    給 LLM 看的「Bryan 離開了多久」。

    範例輸出 (zh_TW)：
        【Bryan 的缺席】
        精確：2 小時 13 分鐘
        自然語：一個多小時
        規模：hours
    """
    if locale == "en_US":
        return f"""[{subject}'s absence]
Exact: {snap.natural_long}
Natural: {snap.natural_short}
Magnitude: {snap.magnitude}
"""
    if locale == "ja_JP":
        return f"""【{subject}の不在】
正確: {snap.natural_long}
自然: {snap.natural_short}
規模: {snap.magnitude}
"""
    return f"""【{subject} 的缺席】
精確：{snap.natural_long}
自然語：{snap.natural_short}
規模：{snap.magnitude}
"""


def render_full_temporal_block(
    now: NowSnapshot,
    absence: Optional[AbsenceSnapshot] = None,
    subject: str = "Bryan",
    locale: Locale = "zh_TW",
) -> str:
    """完整版：現在 + 缺席 一起塞進 prompt"""
    parts = [render_now_block(now, locale=locale)]
    if absence is not None:
        parts.append(render_absence_block(absence, locale=locale, subject=subject))
    return "\n".join(parts)
