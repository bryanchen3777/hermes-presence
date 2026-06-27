"""
inner_life/demo.py — 展示 inner_life 模組

展示一個 agent 的一天怎麼被生成。
"""
import sys, os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from inner_life.storage import Storage
from inner_life.generator import (
    generate_day, RuleBasedDetailGenerator,
)
from inner_life.prompt_blocks import render_inner_life_block, render_body_only
from inner_life.body import compute_body_state


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def main():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd); os.unlink(db_path)

    storage = Storage(db_path)
    tz = ZoneInfo("Asia/Taipei")
    today_midnight = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = today_midnight.timestamp()

    section("1. 為 Yua 生成一天（預設 personality）")
    print("Yua (冷靜、輕諷、說話藏著鉤子) — 預設規則\n")
    result = generate_day(
        storage, "yua",
        detail_generator=RuleBasedDetailGenerator(),
        day_start_ts=today_ts,
    )
    print(f"生成 {len(result.activities)} 個活動，{len(result.body_states)} 個身體狀態記錄\n")
    for a in result.activities:
        dt = datetime.fromtimestamp(a.ts, tz=tz)
        print(f"  {dt.strftime('%H:%M')}  [{a.activity_type:8s}] {a.title}")

    print("\n")

    section("2. 為 Rem 生成一天（姊妹情深 personality）")
    print("Rem (低語、姊妹情深、無條件奉獻) — personality: [sister]\n")
    result_rem = generate_day(
        storage, "rem",
        detail_generator=RuleBasedDetailGenerator(personality_keywords=["sister"]),
        day_start_ts=today_ts,
    )
    for a in result_rem.activities:
        dt = datetime.fromtimestamp(a.ts, tz=tz)
        if a.title not in ["吃了簡單的餐點", "享用了一頓", "坐下來好好吃一頓",
                            "準備休息，整理一下思緒", "讓身心慢慢沉澱",
                            "準備進入睡眠狀態", "睡了", "闔上眼，安靜地入眠", "沉沉睡去",
                            "起床，伸個懶腰", "醒了，看了一下窗外的天色", "慢慢爬起來，整理一下儀容"]:
            print(f"  {dt.strftime('%H:%M')}  [{a.activity_type:8s}] {a.title}")

    print("\n")

    section("3. 為 Ram 生成一天（茶香型 personality）")
    print("Ram (傲慢、保護 Ram、說話不饒人) — personality: [tea, music]\n")
    result_ram = generate_day(
        storage, "ram",
        detail_generator=RuleBasedDetailGenerator(personality_keywords=["tea"]),
        day_start_ts=today_ts,
    )
    for a in result_ram.activities:
        dt = datetime.fromtimestamp(a.ts, tz=tz)
        if a.title not in ["吃了簡單的餐點", "享用了一頓", "坐下來好好吃一頓",
                            "準備休息，整理一下思緒", "讓身心慢慢沉澱",
                            "準備進入睡眠狀態", "睡了", "闔上眼，安靜地入眠", "沉沉睡去",
                            "起床，伸個懶腰", "醒了，看了一下窗外的天色", "慢慢爬起來，整理一下儀容"]:
            print(f"  {dt.strftime('%H:%M')}  [{a.activity_type:8s}] {a.title}")

    print("\n")

    section("4. 給 LLM 的 prompt block（Yua 視角）")
    print("(當 Bryan 問 Yua「你今天做什麼」時，給 LLM 的參考資料)\n")
    # 只看今天的活動
    from inner_life.activity import get_today_activities
    today_acts = get_today_activities(storage, "yua")
    lines = ["【你的內在世界（內部參考）】"]
    body = render_body_only(storage, "yua")
    if body:
        lines.append(body)
    if today_acts:
        lines.append("\n你今天做過的事：")
        for a in reversed(today_acts):  # 由早到晚
            when = datetime.fromtimestamp(a["ts"], tz=tz).strftime("%H:%M")
            lines.append(f"  {when}  {a['title']}")
    block = "\n".join(lines)
    print(block)

    print("\n\n")

    section("5. 三個 agent 各自的身體狀態（現在 22:00）")
    # 用一個固定的「現在」時間方便對照
    now = datetime(2026, 6, 22, 22, 0, tzinfo=tz).timestamp()
    last_meal_18 = today_ts + 18 * 3600  # 今天 18:00 吃過飯
    last_sleep_0 = today_ts              # 從 00:00 起算
    for profile in ["yua", "rem", "ram"]:
        state = compute_body_state(
            profile_name=profile,
            last_meal_ts=last_meal_18,
            last_sleep_ts=last_sleep_0,
            now=now,
        )
        print(f"  {profile:8s}  {state.to_prompt()}")

    print("\n")

    section("6. prompt block 中只取身體狀態（給 LLM 短回應用）")
    s = render_body_only(storage, "yua")
    print(f"Yua: {s}")

    # 清理
    os.unlink(db_path)


if __name__ == "__main__":
    main()
