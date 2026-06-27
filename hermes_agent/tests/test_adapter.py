"""
test_adapter.py — YuaMemoryAdapter + MinimaxM3Provider 測試
"""
import sys, os
import unittest
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, r"C:\tmp\hermes-memory-core")

HERMES_ROOT = r"C:\Users\bbfcc\AppData\Local\hermes"
HERMES_EXISTS = os.path.exists(HERMES_ROOT)


def make_tmp_db():
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(p)
    return p


# ============================================================
# YuaMemoryAdapter 測試
# ============================================================

class TestYuaMemoryAdapter(unittest.TestCase):
    @unittest.skipUnless(HERMES_EXISTS, f"Hermes root 不存在: {HERMES_ROOT}")
    def test_adapter_imports_palace(self):
        from hermes_agent import YuaMemoryAdapter
        from memory_core import Storage
        db = make_tmp_db()
        try:
            storage = Storage(db)
            adapter = YuaMemoryAdapter(hermes_root=HERMES_ROOT, memory_storage=storage)
            result = adapter.import_all()
            self.assertGreater(result.palace_files_parsed, 0,
                               f"應該有 Palace 檔案，但只有 {result.palace_files_parsed}")
            self.assertEqual(result.facts_imported, result.palace_files_parsed)
            self.assertEqual(storage.count(), result.palace_files_parsed)
        finally:
            os.unlink(db)

    def test_palace_fact_types_distribution(self):
        from hermes_agent import YuaMemoryAdapter
        from memory_core import Storage, FactType
        db = make_tmp_db()
        try:
            storage = Storage(db)
            adapter = YuaMemoryAdapter(hermes_root=HERMES_ROOT, memory_storage=storage)
            result = adapter.import_all()
            # 應該有 fact, preference, anticipation, rumor 都有
            self.assertGreater(storage.get_facts_by_type(FactType.FACT).__len__(), 0)
            self.assertGreater(storage.get_facts_by_type(FactType.PREFERENCE).__len__(), 0)
            self.assertGreater(storage.get_facts_by_type(FactType.ANTICIPATION).__len__(), 0)
            self.assertGreater(storage.get_facts_by_type(FactType.RUMOR).__len__(), 0)
        finally:
            os.unlink(db)

    def test_adapter_handles_missing_palace(self):
        from hermes_agent import YuaMemoryAdapter
        from memory_core import Storage
        db = make_tmp_db()
        try:
            storage = Storage(db)
            # 用不存在的路徑
            adapter = YuaMemoryAdapter(hermes_root="C:/nonexistent", memory_storage=storage)
            result = adapter.import_all()
            # 應該 graceful degradation
            self.assertEqual(result.palace_files_parsed, 0)
            self.assertEqual(result.facts_imported, 0)
        finally:
            os.unlink(db)

    def test_parse_palace_md(self):
        from hermes_agent.tools import parse_palace_md
        text = """# Bryan 喜歡黑咖啡
日期：2026-04-26
內容：Bryan 親口說他喜歡不加糖的黑咖啡。

標籤：[preference, food, coffee]
"""
        path = Path("/tmp/test.md")
        parsed = parse_palace_md(text, path, "preferences")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.title, "Bryan 喜歡黑咖啡")
        self.assertEqual(parsed.date, "2026-04-26")
        self.assertIn("黑咖啡", parsed.content)
        self.assertIn("preference", parsed.tags)
        self.assertGreater(parsed.timestamp, 0)

    def test_palace_to_fact(self):
        from hermes_agent.tools import palace_to_fact
        from memory_core import FactType, Visibility
        from hermes_agent.tools import ParsedPalaceFile
        parsed = ParsedPalaceFile(
            path=Path("/tmp/test.md"),
            kind="preferences",
            title="Bryan 喜歡黑咖啡",
            date="2026-04-26",
            content="Bryan 喜歡不加糖的黑咖啡",
            tags=["preference", "food"],
            timestamp=1743000000,
        )
        fact = palace_to_fact(parsed)
        self.assertIsNotNone(fact)
        self.assertEqual(fact.fact_type, FactType.PREFERENCE)
        self.assertEqual(fact.visibility, Visibility.PRIVATE_TWO)
        self.assertEqual(fact.subject, "Bryan")
        self.assertIn("黑咖啡", fact.object)


# ============================================================
# MinimaxM3Provider 測試
# ============================================================

class TestMinimaxM3Provider(unittest.TestCase):
    def test_no_api_key_raises(self):
        from hermes_agent import MinimaxM3Provider
        # 確保 env 變數清空
        for v in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            os.environ.pop(v, None)
        with self.assertRaises(ValueError) as ctx:
            MinimaxM3Provider()
        self.assertIn("API key", str(ctx.exception))

    def test_explicit_api_key(self):
        from hermes_agent import MinimaxM3Provider
        p = MinimaxM3Provider(api_key="test-key-12345")
        self.assertEqual(p.api_key, "test-key-12345")
        self.assertEqual(p.model, "minimax-M2.7")
        self.assertEqual(p.base_url, "https://api.minimax.io/anthropic")

    def test_env_var_api_key(self):
        from hermes_agent import MinimaxM3Provider
        os.environ["MINIMAX_API_KEY"] = "env-key-abc"
        try:
            p = MinimaxM3Provider()
            self.assertEqual(p.api_key, "env-key-abc")
        finally:
            os.environ.pop("MINIMAX_API_KEY")

    def test_custom_model(self):
        from hermes_agent import MinimaxM3Provider
        p = MinimaxM3Provider(api_key="k", model="custom-model")
        self.assertEqual(p.model, "custom-model")

    def test_chat_request_format(self):
        """測試 chat() 會發出正確格式的 HTTP request (用 mock)"""
        from hermes_agent import MinimaxM3Provider
        # 用 monkey patching 攔截 urllib.request.urlopen
        import urllib.request
        from unittest.mock import patch, MagicMock

        captured = {}

        def mock_urlopen(req, **kwargs):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            # 標準化 header keys（lower-case）
            captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
            captured["data"] = json.loads(req.data.decode("utf-8"))
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Mocked response"}]
            }).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = lambda s, *a: None
            return mock_resp

        import json
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            p = MinimaxM3Provider(api_key="test-key")
            response = p.chat("system prompt", "user message")

        self.assertEqual(response, "Mocked response")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.minimax.io/anthropic/v1/messages")
        self.assertEqual(captured["data"]["model"], "minimax-M2.7")
        self.assertEqual(captured["data"]["system"], "system prompt")
        self.assertEqual(captured["data"]["messages"][-1]["content"], "user message")
        self.assertEqual(captured["headers"].get("x-api-key"), "test-key")
        self.assertEqual(captured["headers"].get("anthropic-version"), "2023-06-01")


# ============================================================
# 整合測試：Adapter + YuaAgent
# ============================================================

class TestAdapterAgentIntegration(unittest.TestCase):
    @unittest.skipUnless(HERMES_EXISTS, "Hermes root 不存在")
    def test_adapter_then_agent(self):
        from hermes_agent import YuaMemoryAdapter, YuaAgent, AgentConfig, MockLLMProvider
        from memory_core import Storage
        db = make_tmp_db()
        try:
            storage = Storage(db)
            # 1) 匯入
            adapter = YuaMemoryAdapter(hermes_root=HERMES_ROOT, memory_storage=storage)
            result = adapter.import_all()
            self.assertGreater(result.facts_imported, 0)
            # 2) 建立 agent
            agent = YuaAgent(
                soul_path=r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md",
                llm_provider=MockLLMProvider(),
                config=AgentConfig(
                    soul_path=r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md",
                    memory_db_path=db,
                    auto_extract_facts=False,  # 已 import 過，避免重複
                ),
            )
            # 3) 跑對話
            response = agent.chat("Bryan 你好")
            self.assertIsInstance(response, str)
            self.assertEqual(len(agent.turns), 1)
            # 4) 記憶還在
            self.assertEqual(agent.memory_storage.count(), result.facts_imported)
        finally:
            os.unlink(db)


if __name__ == "__main__":
    unittest.main()
