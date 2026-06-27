"""
demos/yua_real_llm_demo.py
用 LocalLLMProvider（真實 LLM）跑 Yua 對話

MINIMAX_API_KEY 不用設定，直接用本地 server：
  http://192.168.0.37:8080/v1/messages
"""
import sys, os, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, r"C:\tmp\hermes-memory-core")

from hermes_agent import (
    YuaAgent, AgentConfig,
    YuaMemoryAdapter,
    LocalLLMProvider, MockLLMProvider,
    validate_soul,
)
from memory_core import Storage


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def main():
    hermes_root = r"C:\Users\bbfcc\AppData\Local\hermes"
    soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
    db_path = str(HERE / "demo_yua_real.db")

    # 清掉舊的
    if os.path.exists(db_path):
        os.unlink(db_path)

    section("0. 設定")
    print()
    print(f"  LLM: LocalLLMProvider (http://192.168.0.37:8080/v1/messages)")
    print(f"  Model: M2.7 (由 server 決定)")
    print(f"  SOUL: {soul_path}")
    print(f"  Memory DB: {db_path}")

    # 驗證 SOUL
    section("1. Yua SOUL 驗證")
    print()
    r = validate_soul(soul_path)
    print(f"  {r.summary()}")

    # 匯入舊記憶
    section("2. 匯入舊 Hermes 記憶")
    print()
    storage = Storage(db_path)
    adapter = YuaMemoryAdapter(hermes_root=hermes_root, memory_storage=storage)
    result = adapter.import_all()
    print(f"  匯入: {result.facts_imported} 個 fact (from {result.palace_files_parsed} Palace 檔案)")
    print(f"  DB 總計: {storage.count()}")

    # 建立 YuaAgent（用真實 LLM）
    section("3. 建立 YuaAgent（真實 LLM）")
    print()
    llm = LocalLLMProvider(timeout=120)
    print(f"  Provider: {llm}")

    config = AgentConfig(
        soul_path=soul_path,
        memory_db_path=db_path,
        auto_extract_facts=True,
        include_facts_in_prompt=False,  # 避免模型嘗試生成 fact JSON，保持自然語言回覆
    )
    agent = YuaAgent(
        soul_path=soul_path,
        llm_provider=llm,
        config=config,
    )
    print(f"  Name: {agent.name}")
    print(f"  Memory: {agent.memory_storage.count()} facts")

    # 對話
    section("4. 對話（用真實 LLM）")
    print()

    test_messages = [
        "Bryan: 你好",
        "Bryan: 我喜歡喝不加糖的黑咖啡",
        "Bryan: 我明天要去台北出差",
        "Bryan: 今天好累",
        "Bryan: Ram 姐姐還好嗎",
        "Bryan: 再見",
    ]

    for msg in test_messages:
        user_msg = msg.replace("Bryan: ", "")
        t0 = time.time()
        try:
            response = agent.chat(user_msg)
            elapsed = time.time() - t0
            facts = len(agent.turns[-1].facts_written)
            print(f"  Bryan: {user_msg}")
            print(f"  Yua:   {response[:200]}{'...' if len(response) > 200 else ''}")
            print(f"  ⏱  {elapsed:.1f}s  |  📝 {facts} facts")
            print()
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  Bryan: {user_msg}")
            print(f"  ❌ Error after {elapsed:.1f}s: {e}")
            print()

    # 統計
    section("5. 統計")
    print()
    summary = agent.get_conversation_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"  最終 DB: {storage.count()} facts")

    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)
    print()
    print("  ✅ 完成（DB 已清理）")


if __name__ == "__main__":
    main()
