"""
demos/yua_repl.py
互動式 Yua Agent REPL
- 用 Minimax-M2.7 雲端模型
- 載入 SOUL + 舊記憶
- 按 Ctrl+C 或打 "exit" 結束

環境變數 MINIMAX_API_KEY 必須設定（雲端需要）
"""
import sys, os, time, signal
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, r"C:\tmp\hermes-memory-core")

from hermes_agent import (
    YuaAgent, AgentConfig,
    YuaMemoryAdapter,
    MinimaxM3Provider,
    validate_soul,
)
from memory_core import Storage


def main():
    hermes_root = r"C:\Users\bbfcc\AppData\Local\hermes"
    soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
    db_path = str(HERE / "yua_repl.db")

    # 確認 API key
    api_key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  需要 MINIMAX_API_KEY 環境變數")
        print("   設定方式：")
        print("   set MINIMAX_API_KEY=sk-cp-...")
        return

    # 清掉舊的
    if os.path.exists(db_path):
        os.unlink(db_path)

    print("="*60)
    print("  Yua Agent REPL (Minimax-M2.7)")
    print("="*60)

    # SOUL 驗證
    print("\n[SOUL]")
    r = validate_soul(soul_path)
    print(f"  {r.summary()}")

    # 匯入舊記憶
    print("\n[Memory]")
    storage = Storage(db_path)
    adapter = YuaMemoryAdapter(hermes_root=hermes_root, memory_storage=storage)
    result = adapter.import_all()
    print(f"  舊記憶: {result.facts_imported} 個 fact (from {result.palace_files_parsed} Palace 檔案)")
    print(f"  DB 總計: {storage.count()} facts")

    # 建立 Agent
    print("\n[Agent]")
    llm = MinimaxM3Provider(api_key=api_key, timeout=120)
    print(f"  LLM: Minimax-M2.7 (雲端)")
    print(f"  Provider: {llm}")

    config = AgentConfig(
        soul_path=soul_path,
        memory_db_path=db_path,
        auto_extract_facts=True,
        include_facts_in_prompt=False,
    )
    agent = YuaAgent(
        soul_path=soul_path,
        llm_provider=llm,
        config=config,
    )
    print(f"  SOUL loaded: {agent.name}")
    print(f"  Memory: {agent.memory_storage.count()} facts")

    print()
    print("="*60)
    print("  開始聊天（打 exit 結束，Ctrl+C 中斷）")
    print("="*60)
    print()

    # REPL
    def sigint_handler(sig, frame):
        print("\n\n  👋 再見！")
        print(f"  累計: {len(agent.turns)} 回合, {agent.memory_storage.count()} facts in DB")
        if os.path.exists(db_path):
            os.unlink(db_path)
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        while True:
            try:
                user_input = input("Bryan: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Yua: 再見。")
                break

            t0 = time.time()
            try:
                response = agent.chat(user_input)
                elapsed = time.time() - t0
                facts = len(agent.turns[-1].facts_written) if agent.turns else 0
                print(f"Yua:   {response}")
                print(f"       ⏱ {elapsed:.1f}s  📝 {facts} fact(s) written")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n  累計: {len(agent.turns)} 回合, {agent.memory_storage.count()} facts")
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("  DB cleaned up. 👋")


if __name__ == "__main__":
    main()
