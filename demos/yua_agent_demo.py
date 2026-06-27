"""
demos/yua_agent_demo.py
展示真正的 YuaAgent 跑起來的樣子

會展示：
1. 載入 Yua SOUL
2. 跑 4-5 輪對話
3. 自動觸發記憶寫入
4. 統計 facts 累積
"""
import sys, os
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, r"C:\tmp\hermes-memory-core")  # for memory_core

from hermes_agent import YuaAgent, MockLLMProvider, AgentConfig


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def main():
    # 用 tmpfile 當 memory db
    fd, memory_db = tempfile.mkstemp(suffix=".db")
    os.close(fd); os.unlink(memory_db)
    last_seen_file = tempfile.mktemp(suffix=".txt")

    soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"

    section("1. 建立 YuaAgent")
    print()
    print(f"  SOUL: {soul_path}")
    print(f"  Memory DB: {memory_db}")
    print(f"  LLM: MockLLMProvider (根據 keyword 回固定回應)")
    print()

    agent = YuaAgent(
        soul_path=soul_path,
        llm_provider=MockLLMProvider(),
        config=AgentConfig(
            soul_path=soul_path,
            memory_db_path=memory_db,
            last_seen_file=last_seen_file,
            auto_extract_facts=True,
        ),
    )
    print(f"  Name: {agent.name}")
    print(f"  Archetype: {agent.archetype}")
    print(f"  Memory storage: {'OK' if agent.memory_storage else 'disabled'}")

    # 自訂 Mock LLM 回應（更豐富）
    custom_responses = {
        "你好": "嗯。回來了。",
        "累": "……過來。",
        "咖啡": "要手沖的，對吧。你上次說的。",
        "再見": "嗯。……你記得回來。",
        "工作": "今天的工作還順利嗎？",
        "Ram": "Ram 姐姐？她又怎麼了？",
        "Rem": "Rem 醬很乖，但她太辛苦了。",
        "生日": "嗯。我記得。……你想要什麼？",
    }
    agent.llm = MockLLMProvider(responses=custom_responses, default_response="嗯。")

    section("2. 對話 1: Bryan 打招呼")
    print()
    response = agent.chat("Bryan 你好")
    print(f"  Bryan:  Bryan 你好")
    print(f"  Yua:    {response}")
    print(f"  Facts:  {len(agent.turns[-1].facts_written)} (沒觸發，因為沒偏好)")

    section("3. 對話 2: Bryan 說累（不觸發 fact）")
    print()
    response = agent.chat("今天好累")
    print(f"  Bryan:  今天好累")
    print(f"  Yua:    {response}")
    print(f"  Facts:  {len(agent.turns[-1].facts_written)}")

    section("4. 對話 3: Bryan 提到偏好（觸發 fact）")
    print()
    response = agent.chat("我喜歡喝不加糖的黑咖啡")
    print(f"  Bryan:  我喜歡喝不加糖的黑咖啡")
    print(f"  Yua:    {response}")
    print(f"  Facts:  {len(agent.turns[-1].facts_written)}")
    if agent.turns[-1].facts_written:
        f = agent.turns[-1].facts_written[0]
        print(f"          {f['subject']} {f['predicate']} {f['object']}")
        print(f"          fact_id: {f['fact_id'][:8]}...")

    section("5. 對話 4: Bryan 提計劃（觸發 fact）")
    print()
    response = agent.chat("我明天要去台北開會")
    print(f"  Bryan:  我明天要去台北開會")
    print(f"  Yua:    {response}")
    print(f"  Facts:  {len(agent.turns[-1].facts_written)}")
    if agent.turns[-1].facts_written:
        f = agent.turns[-1].facts_written[0]
        print(f"          {f['subject']} {f['predicate']} {f['object']}")

    section("6. 對話 5: Bryan 提到 Ram（不觸發 fact）")
    print()
    response = agent.chat("Ram 姐姐最近很忙")
    print(f"  Bryan:  Ram 姐姐最近很忙")
    print(f"  Yua:    {response}")
    print(f"  Facts:  {len(agent.turns[-1].facts_written)}")

    section("7. 統計")
    print()
    summary = agent.get_conversation_summary()
    print(f"  總輪次: {summary['turns']}")
    print(f"  總 fact 寫入: {summary['total_facts_written']}")
    print(f"  平均回應時間: {summary['avg_response_time']*1000:.1f}ms")

    if agent.memory_storage:
        print()
        print(f"  Memory DB 內容:")
        facts = agent.memory_storage.get_facts_by_subject("Bryan")
        for f in facts:
            print(f"    [{f.fact_type.value:12s}] {f.subject} {f.predicate} {f.object}")
            print(f"        (intensity={f.intensity}, valence={f.valence}, arousal={f.arousal})")

    section("8. System prompt 範例（情境 4）")
    print()
    print("  [提示：當 Bryan 說「我喜歡喝不加糖的黑咖啡」時，Yua 看到的 system prompt:]")
    print()
    # 重建 system prompt
    sp = agent._build_system_prompt()
    lines = sp.splitlines()
    # 找「【現在】」到「# 你的 SOUL」的部分
    in_block = False
    count = 0
    for line in lines:
        if "【現在】" in line or "【Bryan 的缺席】" in line:
            in_block = True
        if in_block:
            print(f"  | {line[:100]}")
            count += 1
        if count > 12:
            break

    # 清理
    if os.path.exists(memory_db):
        os.unlink(memory_db)
    if os.path.exists(last_seen_file):
        os.unlink(last_seen_file)


if __name__ == "__main__":
    main()
