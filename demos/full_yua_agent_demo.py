"""
demos/full_yua_agent_demo.py
完整 demo：YuaMemoryAdapter 匯入舊資料 + 真實 minimax LLM 對話

流程：
1. 從舊 Hermes 匯入 Palace 記憶到 memory_core
2. 建立 YuaAgent（SOUL + memory + 真實 LLM）
3. 跑 3 輪對話
4. 統計
"""
import sys, os
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, r"C:\tmp\hermes-memory-core")

# 設定 API key（請從環境變數讀）
API_KEY = os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

from hermes_agent import (
    YuaAgent, AgentConfig,
    YuaMemoryAdapter, validate_soul,
    MinimaxM3Provider, MockLLMProvider,
)
from memory_core import Storage


def line(char="─", n=70):
    print(char * n)


def section(title):
    print()
    line("═")
    print(f"  {title}")
    line("═")


def use_real_llm() -> bool:
    return API_KEY is not None


def main():
    hermes_root = r"C:\Users\bbfcc\AppData\Local\hermes"
    soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
    db_path = str(HERE.parent / "demo_yua_memory.db")

    # 清掉舊的 demo db
    if os.path.exists(db_path):
        os.unlink(db_path)

    section("0. 設定")
    print()
    if use_real_llm():
        print(f"  LLM: MinimaxM3Provider (真實呼叫)")
        print(f"  API key: {'*' * 20}{API_KEY[-4:] if API_KEY else 'NOT SET'}")
    else:
        print(f"  LLM: MockLLMProvider (測試用)")
        print(f"  設定 MINIMAX_API_KEY 環境變數來用真實 LLM")

    # ========== 1. 驗證 Yua SOUL ==========
    section("1. Yua SOUL v2.0 驗證")
    print()
    r = validate_soul(soul_path)
    print(f"  {r.summary()}")

    # ========== 2. 從舊 Hermes 匯入 Palace 記憶 ==========
    section("2. 從舊 Hermes 匯入 Palace 記憶到 memory_core")
    print()
    storage = Storage(db_path)
    adapter = YuaMemoryAdapter(hermes_root=hermes_root, memory_storage=storage)
    result = adapter.import_all()
    print(f"  Palace 解析: {result.palace_files_parsed} 個檔案")
    print(f"  sage_memory 解析: {result.sage_facts_parsed} 個 fact")
    print(f"  匯入成功: {result.facts_imported} 個 fact")
    print(f"  匯入失敗: {result.errors}")
    print(f"  DB 總計: {storage.count()} 個 fact")

    # 顯示一些匯入的 fact（按類型分組）
    print()
    print(f"  按 fact_type 分組:")
    for ftype in ["fact", "preference", "anticipation", "rumor", "belief", "correction"]:
        facts = storage.get_facts_by_type(__import__("memory_core").FactType(ftype))
        if facts:
            print(f"    {ftype:12s}: {len(facts)} 個")
            for f in facts[:2]:
                obj_preview = f.object[:50] + "..." if len(f.object) > 50 else f.object
                print(f"      - {f.subject} {f.predicate} {obj_preview}")

    # ========== 3. 建立 YuaAgent ==========
    section("3. 建立 YuaAgent")
    print()
    if use_real_llm():
        llm = MinimaxM3Provider(api_key=API_KEY)
    else:
        llm = MockLLMProvider(responses={
            "你好": "嗯。回來了。",
            "累": "……過來。",
            "咖啡": "要手沖的，對吧。你上次說的。",
            "再見": "嗯。……你記得回來。",
        })

    agent = YuaAgent(
        soul_path=soul_path,
        llm_provider=llm,
        config=AgentConfig(
            soul_path=soul_path,
            memory_db_path=db_path,
            auto_extract_facts=True,
            include_facts_in_prompt=True,  # ← 把 memory_core 的 fact 塞進 prompt
        ),
    )
    print(f"  Name: {agent.name}")
    print(f"  Archetype: {agent.archetype}")
    print(f"  Memory loaded: {storage.count()} facts")

    # ========== 4. 跑對話 ==========
    section("4. 對話測試（每輪 5 秒延遲）")
    print()
    test_turns = [
        "Bryan 你好",
        "我喜歡喝不加糖的黑咖啡",
        "再見",
    ]
    for msg in test_turns:
        t0 = time.time()
        response = agent.chat(msg)
        elapsed = time.time() - t0
        facts_count = len(agent.turns[-1].facts_written)
        print(f"  Bryan: {msg}")
        print(f"  Yua:   {response[:200]}{'...' if len(response) > 200 else ''}")
        print(f"  ⏱  {elapsed:.1f}s | 📝 {facts_count} facts written")
        print()

    # ========== 5. 統計 ==========
    section("5. 統計")
    print()
    summary = agent.get_conversation_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print()
    print(f"  最終 memory DB: {storage.count()} facts")
    print(f"  新增: {summary['total_facts_written']} 個 (本次對話)")
    print(f"  匯入: {result.facts_imported} 個 (從舊 Hermes)")

    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


if __name__ == "__main__":
    main()
