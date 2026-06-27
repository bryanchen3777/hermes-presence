"""
clock.py — 純函式時鐘節律

不依賴任何外部資源、DB、檔案。
所有輸入都是 hour/minute，輸出都是 0-1 範圍的數值或 enum。

設計原則：
- 用分段線性 + 簡單平滑
- 每段都有一個 peak / valley
- 邊界值都明確處理（沒有跨午夜 bug）
"""
from __future__ import annotations

import math
from typing import Literal


def classify_period(hour: int, minute: int) -> Literal[
    "deep_night", "dawn", "morning", "afternoon", "evening", "night"
]:
    """
    6 時區分類（與 chrono-social-engine 對齊）：
    - deep_night  00:00-03:59
    - dawn        04:00-06:59
    - morning     07:00-11:59
    - afternoon   12:00-17:59
    - evening     18:00-21:59
    - night       22:00-23:59
    """
    h = hour + minute / 60
    if 0 <= h < 4:
        return "deep_night"
    if 4 <= h < 7:
        return "dawn"
    if 7 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "afternoon"
    if 18 <= h < 22:
        return "evening"
    return "night"


def sleep_pressure_at(hour: int, minute: int) -> float:
    """
    睡意曲線（0-1）：
    - 02:00  = 1.00 (最高峰)
    - 14:00  = 0.05 (最低)
    - 22:00  = 0.70 (晚上開始累)

    用分段線性插值 + cosine 平滑，無外部依賴。
    """
    h = hour + minute / 60

    # 基準點： (hour, sleep_pressure)
    anchors = [
        (0.0,  0.95),   # 00:00 已經很睏
        (2.0,  1.00),   # 02:00 最高峰
        (5.0,  0.85),   # 05:00 還是想睡
        (7.0,  0.45),   # 07:00 起床
        (10.0, 0.10),   # 10:00 清醒
        (14.0, 0.05),   # 14:00 最低
        (16.0, 0.12),   # 16:00 下午小累
        (19.0, 0.35),   # 19:00 吃完晚飯有點累
        (22.0, 0.70),   # 22:00 準備睡
        (24.0, 0.95),   # 24:00 = 00:00
    ]

    # 在 anchor 間線性插值
    for i in range(len(anchors) - 1):
        h1, v1 = anchors[i]
        h2, v2 = anchors[i + 1]
        if h1 <= h <= h2:
            t = (h - h1) / (h2 - h1)
            # 用 smoothstep 做輕微平滑
            t_smooth = t * t * (3 - 2 * t)
            return round(v1 + (v2 - v1) * t_smooth, 2)

    return 0.5  # fallback


def circadian_energy_at(hour: int, minute: int) -> float:
    """
    清醒度（0-1）：
    0 = 完全沒電, 1 = 神采奕奕
    公式：energy = 1 - sleep_pressure * 0.7
    """
    sp = sleep_pressure_at(hour, minute)
    return round(max(0.0, min(1.0, 1.0 - sp * 0.7)), 2)


def appetite_at(hour: int, minute: int) -> float:
    """
    食慾（0-1）：
    - 早餐 7-9 高
    - 午餐 12-13 高
    - 晚餐 18-20 高
    0 = 不餓, 1 = 很餓
    """
    h = hour + minute / 60
    # 三個峰值 (hour, peak)
    peaks = [
        (8.0, 0.85),    # 早餐
        (12.5, 0.90),  # 午餐
        (19.0, 0.95),  # 晚餐
    ]

    # 取三個峰中最高
    vals = []
    for peak_h, peak_v in peaks:
        # 用高斯距離，每離 peak 1 小時衰減 ~50%
        dist = abs(h - peak_h)
        v = peak_v * math.exp(-(dist ** 2) / (2 * 2.5 ** 2))
        vals.append(v)

    return round(min(1.0, max(vals)), 2)


def body_feeling_for(period: str, energy: float) -> str:
    """
    根據時段 + 清醒度，選擇身體感描述。
    """
    if energy < 0.20:
        return "exhausted"
    if energy < 0.40:
        return "sleepy"
    if energy < 0.55 and period in ("evening", "night", "deep_night"):
        return "winding_down"
    if energy > 0.80 and period in ("morning", "afternoon"):
        return "alert"
    if period in ("morning", "dawn") and energy < 0.70:
        return "just_woke"
    if period in ("evening", "night") and energy > 0.50:
        return "relaxed_evening"
    return "neutral"
