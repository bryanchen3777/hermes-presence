"""
hermes_agent/plugin.py — Hermes Agent 0.17.0 整合範例

複製到：~/.hermes/plugins/temporal_presence/plugin.py
（或每個 profile 的 plugins/ 子目錄）

功能：
- pre-LLM hook：注入時間感 prompt block
- 工具：get_current_time, get_bryan_absence（讓 LLM 主動查詢）
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

# 從 hermes-presence 引入
from temporal_awareness import (
    get_now_snapshot,
    get_absence_snapshot,
    render_full_temporal_block,
    NowSnapshot,
    AbsenceSnapshot,
)


# ===== 設定 =====

DEFAULT_TIMEZONE = os.environ.get("HERMES_TIMEZONE", "Asia/Taipei")
DEFAULT_LOCALE = os.environ.get("HERMES_LOCALE", "zh_TW")
# Bryan 最後上線時間戳（由應用層傳入；0 = 第一次）
LAST_SEEN_FILE = os.environ.get(
    "HERMES_LAST_SEEN_FILE",
    os.path.expanduser("~/.hermes/last_seen.txt"),
)


# ===== 工具：讀寫 Bryan 最後上線時間 =====

def _read_last_seen() -> float:
    try:
        with open(LAST_SEEN_FILE, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0.0


def _write_last_seen(ts: float) -> None:
    os.makedirs(os.path.dirname(LAST_SEEN_FILE), exist_ok=True)
    with open(LAST_SEEN_FILE, "w", encoding="utf-8") as f:
        f.write(str(ts))


# ===== pre-LLM hook =====

def _pre_llm_call(**kwargs) -> Dict[str, str]:
    """
    每次 LLM 呼叫前，把時間感 block 注入 system prompt。

    Hermes plugin 介面：必須回傳 dict，key 為 "context" 或 "system"。
    """
    now: NowSnapshot = get_now_snapshot(
        timezone=DEFAULT_TIMEZONE,
        locale=DEFAULT_LOCALE,
    )

    last_seen = _read_last_seen()
    if last_seen > 0:
        absence: Optional[AbsenceSnapshot] = get_absence_snapshot(
            last_seen_ts=last_seen,
            locale=DEFAULT_LOCALE,
            now=now.timestamp,
        )
    else:
        absence = None

    block = render_full_temporal_block(
        now=now,
        absence=absence,
        locale=DEFAULT_LOCALE,
        subject="Bryan",
    )

    return {"context": block}


# ===== post-LLM hook：記錄 Bryan 最後上線時間 =====

def _post_llm_call(**kwargs) -> Dict[str, Any]:
    """
    每次 LLM 呼叫後，記錄現在時間為 Bryan 最後上線時間。
    """
    _write_last_seen(time.time())
    return {}


# ===== 工具：讓 LLM 主動查詢 =====

def get_current_time() -> Dict[str, Any]:
    """
    讓 LLM 在對話中查詢「現在幾點、感覺如何」。

    Hermes tool 介面：回傳 dict。
    """
    snap = get_now_snapshot(
        timezone=DEFAULT_TIMEZONE,
        locale=DEFAULT_LOCALE,
    )
    return {
        "iso_8601": snap.iso_8601,
        "weekday_name": snap.weekday_name,
        "period_label": snap.period_label,
        "body_feeling": snap.body_feeling_label,
        "circadian_energy": snap.circadian_energy,
        "sleep_pressure": snap.sleep_pressure,
        "appetite": snap.appetite,
    }


def get_bryan_absence() -> Dict[str, Any]:
    """
    讓 LLM 在對話中查詢「Bryan 離開了多久」。
    """
    last_seen = _read_last_seen()
    if last_seen == 0.0:
        return {
            "status": "first_meeting",
            "message": "這是第一次對話，沒有缺席紀錄。",
        }
    snap = get_now_snapshot(
        timezone=DEFAULT_TIMEZONE,
        locale=DEFAULT_LOCALE,
    )
    absence = get_absence_snapshot(
        last_seen_ts=last_seen,
        locale=DEFAULT_LOCALE,
        now=snap.timestamp,
    )
    return {
        "natural_short": absence.natural_short,
        "natural_long": absence.natural_long,
        "magnitude": absence.magnitude,
        "hours": round(absence.hours, 2),
    }


# ===== Hermes plugin 標準入口 =====

def register(ctx) -> None:
    """
    Hermes Agent plugin 標準入口。

    註冊：
    - pre_llm_call hook
    - post_llm_call hook（記錄 Bryan 最後上線時間）
    - 兩個工具供 LLM 主動查詢
    """
    # Hook
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_llm_call", _post_llm_call)

    # Tools（讓 LLM 在對話中能呼叫）
    try:
        ctx.register_tool(
            name="get_current_time",
            description="取得現在的時間、星期、時段、身體感",
            func=get_current_time,
        )
        ctx.register_tool(
            name="get_bryan_absence",
            description="取得 Bryan 離開了多久（自然語版）",
            func=get_bryan_absence,
        )
    except AttributeError:
        # 較舊的 Hermes 版本可能沒有 register_tool
        pass

    print("[hermes-presence] Temporal awareness plugin registered")
