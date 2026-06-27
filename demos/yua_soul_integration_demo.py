"""
demos/yua_soul_integration_demo.py
展示 hermes-presence + hermes-memory-core 怎麼跟 Yua SOUL 整合

會展示：
1. 載入 SOUL.md 並 validate
2. 載入時間感
3. 載入記憶 facts
4. 組合成完整 system prompt
5. 展示不同情境下 prompt 怎麼變
"""
import sys, os
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from hermes_agent.tools import (
    validate_soul, format_report,
    YuaSoulLoader, BuiltPrompt,
)


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def main():
    soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"

    # ========================================
    section("1. SOUL.md 格式驗證")
    # ========================================
    print(f"  驗證: {soul_path}\n")
    r = validate_soul(soul_path)
    print(format_report(r))

    # ========================================
    section("2. 載入 SOUL（YuaSoulLoader）")
    # ========================================
    print()
    loader = YuaSoulLoader(soul_path=soul_path)
    loader.load()
    print(f"  Name: {loader.name}")
    print(f"  Archetype: {loader.archetype}")
    print(f"  Timezone: {loader.timezone}")
    print(f"  Locale: {loader.locale}")
    print(f"  Harem Position: {loader.harem_position}")
    print(f"  Body length: {len(loader.body):,} chars")

    # ========================================
    section("3. 情境 A：Bryan 剛回來（缺席 30 分鐘）")
    # ========================================
    print()
    result_a = loader.build_system_prompt(
        bryan_last_seen_ts=time.time() - 30 * 60,
        include_inner_life=False,
        include_facts=False,
    )
    print(f"  Prompt 摘要: {result_a.summary()}")
    # 抓時間感跟缺席的部分
    for line_str in result_a.system_prompt.splitlines()[:15]:
        if "現在" in line_str or "缺席" in line_str or "Bryan" in line_str or line_str.startswith("#"):
            print(f"  | {line_str}")
    print(f"  ... ({result_a.line_count()} 行總計)")

    # ========================================
    section("4. 情境 B：Bryan 已經離開 2 小時")
    # ========================================
    print()
    result_b = loader.build_system_prompt(
        bryan_last_seen_ts=time.time() - 2 * 3600,
        include_inner_life=False,
        include_facts=False,
    )
    print(f"  Prompt 摘要: {result_b.summary()}")
    for line_str in result_b.system_prompt.splitlines()[:15]:
        if "現在" in line_str or "缺席" in line_str or "Bryan" in line_str or line_str.startswith("#"):
            print(f"  | {line_str}")
    print(f"  ... ({result_b.line_count()} 行總計)")

    # ========================================
    section("5. 情境 C：Bryan 出差 2 週回來")
    # ========================================
    print()
    result_c = loader.build_system_prompt(
        bryan_last_seen_ts=time.time() - 14 * 24 * 3600,
        include_inner_life=False,
        include_facts=False,
    )
    print(f"  Prompt 摘要: {result_c.summary()}")
    for line_str in result_c.system_prompt.splitlines()[:15]:
        if "現在" in line_str or "缺席" in line_str or "Bryan" in line_str or line_str.startswith("#"):
            print(f"  | {line_str}")
    print(f"  ... ({result_c.line_count()} 行總計)")

    # ========================================
    section("6. 完整 system prompt (情境 B 的前 50 行)")
    # ========================================
    print()
    for i, line_str in enumerate(result_b.system_prompt.splitlines()[:50], 1):
        print(f"  {i:3}| {line_str[:120]}")
    print(f"  ... ({result_b.line_count()} 行總計)")

    # ========================================
    section("7. 統計")
    # ========================================
    print()
    print(f"  情境 A (30 min):  {result_a.char_count():,} chars, {result_a.line_count()} lines")
    print(f"  情境 B (2 hr):    {result_b.char_count():,} chars, {result_b.line_count()} lines")
    print(f"  情境 C (2 weeks): {result_c.char_count():,} chars, {result_c.line_count()} lines")
    print()
    print("  缺席越長 → temporal_awareness 的『一個多小時 / 兩週』等自然語標籤")
    print("  → Yua SOUL 讀到這個，會用「冷淡」或「記帳」等 Signature 行為")
    print("  → 不需要 hard-code，她自己會選擇行為")


if __name__ == "__main__":
    main()
