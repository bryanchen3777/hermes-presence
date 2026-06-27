"""
inner_life/generator.py — 規則 + LLM 細節生成器

設計哲學（你決定的）：
- 純規則生成大方向（起床/吃飯/睡覺 — 固定 schedule）
- LLM 生成細節（「她今天下午做了什麼」— 因個性而異）
- 內在世界是私人的 — Bryan 問了才回

Schedule（規則產生的大方向）：
- 06:30-07:30  wake
- 08:00-09:00  meal (breakfast)
- 12:00-13:00  meal (lunch)
- 14:00-17:00  work or leisure
- 18:00-19:30  meal (dinner)
- 20:00-22:00  leisure
- 22:30-23:30  rest
- 23:30-06:30  sleep

LLM 細節（在 schedule 區間內，agent 具體做了什麼）：
  例如 14:00-17:00 work ——
  Rem 會做：「整理姊姐姐大人的髮帶」
  Ram 會做：「擦拭前輩的茶杯」
  Yua 會做：「重新整理書架上的文學小說」
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass
from typing import Optional, Protocol
from datetime import datetime
from zoneinfo import ZoneInfo

from .activity import Activity, ActivityType, log_activity
from .body import BodyState, compute_body_state, save_body_state
from .storage import Storage


# ===== Schedule（純規則） =====

# 固定 schedule：每個 (start_hour, end_hour, activity_type, title_template, energy_delta)
DAILY_SCHEDULE = [
    (6.5,  7.5,  "wake",    "起床",          0.30),
    (8.0,  9.0,  "meal",    "早餐",          0.20),
    (12.0, 13.0, "meal",    "午餐",          0.20),
    (14.0, 17.0, "work",    "下午工作",      -0.10),
    (18.0, 19.5, "meal",    "晚餐",          0.20),
    (20.0, 22.0, "leisure", "晚間休閒",       0.00),
    (22.5, 23.5, "rest",    "準備休息",      -0.10),
    (23.5, 30.5, "sleep",   "睡覺",          -0.50),  # 23:30 ~ 06:30 (next day)
]


# ===== LLM Detail Generator Protocol =====

class LLMDetailGenerator(Protocol):
    """
    介面：把 schedule 的「下午工作」翻成「具體做了什麼」。
    實作者：可以是 LLM、可以是規則表、可以是混合。
    """
    def generate(self, profile_name: str, schedule_slot: dict) -> str:
        """
        輸入：profile_name, schedule_slot（包含 type, time_range, title）
        輸出：自然語標題（"整理花園"、"擦拭茶杯"）
        """
        ...


class RuleBasedDetailGenerator:
    """
    純規則備援：根據 personality 關鍵字 + schedule slot 配對細節。
    LLM 不可用時用這個。
    每個 activity_type 都有 3-5 個變體，避免單調。
    """
    DEFAULT_TEMPLATES = {
        "wake": [
            "起床，伸個懶腰", "醒了，看了一下窗外的天色", "慢慢爬起來，整理一下儀容",
        ],
        "meal": [
            "吃了簡單的餐點", "享用了一頓", "坐下來好好吃一頓",
        ],
        "work": [
            "處理了一些日常事務", "認真地工作了一會兒", "把待辦的事項整理了一下",
        ],
        "leisure": [
            "看了點書、發了會呆", "享受一下自己的時間", "讓自己放鬆一下",
        ],
        "rest": [
            "準備休息，整理一下思緒", "讓身心慢慢沉澱", "準備進入睡眠狀態",
        ],
        "sleep": [
            "睡了", "闔上眼，安靜地入眠", "沉沉睡去",
        ],
    }

    PERSONALITY_DETAILS = {
        # 關鍵字 → 細節（每個 type 都有 3 個變體）
        "tea": {
            "wake":   ["起床，泡一杯熱茶暖胃", "用茶的香氣把自己喚醒", "茶香中醒來"],
            "meal":   ["配著茶一起用餐", "細細品茶配菜", "茶香佐餐"],
            "work":   ["泡了一壺熱茶，一邊工作一邊品嚐", "茶香繚繞，專注工作", "工作之餘不忘添茶"],
            "leisure":["泡了一壺好茶，翻開書慢慢讀", "在茶香中享受片刻寧靜", "茶、書、午後時光"],
            "rest":   ["品完最後一口茶，準備休息", "在茶香中沉澱思緒", "讓茶的餘韻帶自己入睡"],
            "sleep":  ["帶著茶香入眠", "在茶香中安睡", "茶香伴眠"],
        },
        "book": {
            "wake":   ["從書堆裡爬起來", "夢裡還在讀書，醒來繼續", "書本的味道把我叫醒"],
            "meal":   ["一邊吃飯一邊看書", "書本墊在餐盤下", "邊讀邊吃"],
            "work":   ["寫了一點東西", "整理了讀書筆記", "把想法寫下來"],
            "leisure":["翻了幾頁書，沉浸在故事裡", "讓自己沉浸在書的世界", "閱讀的時間最安靜"],
            "rest":   ["闔上書，準備休息", "書的餘韻帶我入睡", "讓書頁陪我入睡"],
            "sleep":  ["書還攤在胸口就睡著了", "書香入眠", "帶著書本的氣味睡去"],
        },
        "cook": {
            "wake":   ["想著今天要煮什麼，醒了", "被廚房飄來的味道叫醒"],
            "meal":   ["下廚做了一道家常菜", "煮了一鍋想吃的", "做了拿手菜"],
            "work":   ["整理了食譜筆記", "把冰箱清點了一遍"],
            "leisure":["研發新菜單", "翻食譜找靈感"],
            "rest":   ["飯後休息一下", "讓食物消化"],
            "sleep":  ["吃飽喝足後睡著了", "帶著飽足感入睡"],
        },
        "music": {
            "wake":   ["被音樂鬧鐘叫醒", "一邊哼歌一邊醒來"],
            "meal":   ["邊吃飯邊聽音樂", "配著喜歡的音樂用餐"],
            "work":   ["戴著耳機工作", "音樂讓工作更專注"],
            "leisure":["聽了一會兒喜歡的音樂", "放鬆地聽音樂", "沉浸在旋律裡"],
            "rest":   ["讓音樂撫平疲憊", "伴著音樂放空"],
            "sleep":  ["在音樂中入睡", "戴著耳機睡著了"],
        },
        "garden": {
            "wake":   ["想著陽台的花，醒了", "聞到花香"],
            "meal":   ["從花園摘了點香草配餐", "配著花園的香氣用餐"],
            "work":   ["整理了陽台的花", "修剪了幾株植物", "把植物重新種了"],
            "leisure":["在花園裡散步", "欣賞一下自己種的花"],
            "rest":   ["在花園裡發呆", "看著花，什麼都不想"],
            "sleep":  ["花香的陪伴下入睡"],
        },
        "clean": {
            "wake":   ["打掃完房間，精神很好", "整理好自己"],
            "meal":   ["把廚房整理乾淨再吃"],
            "work":   ["打掃了房間，讓一切歸位", "整理了桌面", "把雜物清掉"],
            "leisure":["整理了一下衣櫃", "把東西歸位"],
            "rest":   ["在乾淨的環境裡放鬆"],
            "sleep":  ["在整潔的房間入睡"],
        },
        "sister": {
            "wake":   ["想著姊姐姐大人，醒了", "擔心姊姐姐大人，爬起來看看"],
            "meal":   ["幫姊姐姐大人 / 雷姆妹妹準備了餐點", "一起吃飯"],
            "work":   ["幫姊姐姐大人 / 雷姆妹妹做了些事", "想著姊妹的事，一邊工作"],
            "leisure":["想著姊妹的時光", "和姊妹聊了一下"],
            "rest":   ["想著姊妹，慢慢入眠"],
            "sleep":  ["帶著對姊妹的思念入睡"],
        },
        "master": {
            "wake":   ["想著 Bryan 的事，醒了", "今天的自己，想讓 Bryan 看到"],
            "meal":   ["用餐時想著 Bryan", "想著 Bryan 喜歡的口味"],
            "work":   ["一邊工作一邊想 Bryan", "想把事情做好給 Bryan 看"],
            "leisure":["想著 Bryan 的笑容", "讓自己看起來更好了些"],
            "rest":   ["想著 Bryan，慢慢休息"],
            "sleep":  ["帶著對 Bryan 的想念入睡"],
        },
        "yandere": {
            "wake":   ["夢到 Bryan 的笑容，醒了", "Bryan 還在睡嗎？"],
            "meal":   ["為 Bryan 準備了喜歡的", "邊吃邊想 Bryan"],
            "work":   ["為了 Bryan 努力著", "一切都為了 Bryan"],
            "leisure":["想著 Bryan 的一切", "沉浸在 Bryan 的回憶裡"],
            "rest":   ["想著 Bryan 的溫柔，慢慢休息"],
            "sleep":  ["帶著 Bryan 的名字入眠", "Bryan……Bryan……"],
        },
    }

    def __init__(self, personality_keywords: Optional[list[str]] = None):
        self.personality_keywords = personality_keywords or []
        # 為了讓同一天有變化，記錄每個 type 用到第幾個
        self._counters: dict[str, dict[str, int]] = {}

    def generate(self, profile_name: str, schedule_slot: dict) -> str:
        slot_type = schedule_slot.get("activity_type", "")

        # 累積 counter
        if profile_name not in self._counters:
            self._counters[profile_name] = {}
        if slot_type not in self._counters[profile_name]:
            self._counters[profile_name][slot_type] = 0
        idx = self._counters[profile_name][slot_type]
        self._counters[profile_name][slot_type] = (idx + 1)

        # 先看 personality 關鍵字
        for kw in self.personality_keywords:
            if kw in self.PERSONALITY_DETAILS:
                variants = self.PERSONALITY_DETAILS[kw].get(slot_type, [])
                if variants:
                    return variants[idx % len(variants)]

        # fallback
        defaults = self.DEFAULT_TEMPLATES.get(slot_type, ["過了一段時間"])
        return defaults[idx % len(defaults)]


# ===== Generate Day 工具 =====

@dataclass
class DayGenerationResult:
    """一天的生成結果"""
    profile_name: str
    day_start_ts: float
    activities: list[Activity]
    body_states: list[BodyState]


def generate_day(
    storage: Storage,
    profile_name: str,
    detail_generator: Optional[LLMDetailGenerator] = None,
    day_start_ts: Optional[float] = None,
) -> DayGenerationResult:
    """
    為某個 agent 生成一天的內在世界。

    Args:
        storage: SQLite 持久化
        profile_name: agent id
        detail_generator: LLM/規則細節產生器（None = RuleBased 預設）
        day_start_ts: 從哪天 0:00 開始（None = 今天）

    Returns:
        DayGenerationResult
    """
    import datetime as _dt_mod
    if day_start_ts is None:
        tz = ZoneInfo("Asia/Taipei")
        today_midnight = _dt_mod.datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        day_start_ts = today_midnight.timestamp()

    detail_generator = detail_generator or RuleBasedDetailGenerator()
    activities: list[Activity] = []
    body_states: list[BodyState] = []

    last_meal_ts: Optional[float] = None
    last_sleep_ts: Optional[float] = None

    # 用 Asia/Taipei 處理時間軸
    tz_local = ZoneInfo("Asia/Taipei")
    base_date = _dt_mod.datetime.fromtimestamp(day_start_ts, tz=tz_local)
    # 模擬一天的時間軸（每 30 分鐘一個 tick）
    for hour_offset in [i * 0.5 for i in range(48)]:
        sim_ts = day_start_ts + hour_offset * 3600
        sim_dt = _dt_mod.datetime.fromtimestamp(sim_ts, tz=tz_local)
        sim_hour = sim_dt.hour + sim_dt.minute / 60.0

        # 1) 決定 schedule
        slot = _match_schedule(sim_hour)
        if slot is None:
            continue

        start_h, end_h, slot_type, default_title, energy_delta = slot

        # 2) 細節
        title = detail_generator.generate(profile_name, {
            "activity_type": slot_type,
            "time_range": (start_h, end_h),
            "title": default_title,
        })

        # 3) 寫入 activity
        act = Activity(
            profile_name=profile_name,
            activity_type=slot_type,
            title=title,
            description=None,
            energy_delta=energy_delta,
            source="rule" if isinstance(detail_generator, RuleBasedDetailGenerator) else "llm",
            ts=sim_ts,
        )
        log_activity(storage, act)
        activities.append(act)

        # 4) 更新 last_meal / last_sleep
        if slot_type == "meal":
            last_meal_ts = sim_ts
        elif slot_type == "sleep" and last_sleep_ts is None:
            last_sleep_ts = sim_ts

        # 5) 每 3 個小時記錄一次身體狀態（不要每 30 分鐘都記，太多）
        if int(hour_offset) % 3 == 0:
            body = compute_body_state(
                profile_name=profile_name,
                last_meal_ts=last_meal_ts,
                last_sleep_ts=last_sleep_ts,
                now=sim_ts,
            )
            save_body_state(storage, body)
            body_states.append(body)

    return DayGenerationResult(
        profile_name=profile_name,
        day_start_ts=day_start_ts,
        activities=activities,
        body_states=body_states,
    )


def _match_schedule(hour: float) -> Optional[tuple]:
    """根據小時數找對應 schedule slot"""
    for start_h, end_h, slot_type, default_title, energy_delta in DAILY_SCHEDULE:
        if start_h <= hour < end_h:
            return (start_h, end_h, slot_type, default_title, energy_delta)
    return None
