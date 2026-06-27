"""
test_agent.py — YuaAgent 整合測試
"""
import sys, os
import time
import unittest
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))


# 加 hermes-memory-core 到 path
import sys
sys.path.insert(0, r"C:\tmp\hermes-memory-core")


SOUL_PATH = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
SOUL_EXISTS = os.path.exists(SOUL_PATH)


def make_tmp_db():
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(p)
    return p


class TestMockLLMProvider(unittest.TestCase):
    def test_default_response(self):
        from hermes_agent import MockLLMProvider
        m = MockLLMProvider()
        resp = m.chat("system", "完全不相關的訊息")
        self.assertEqual(resp, "在。")

    def test_keyword_matching(self):
        from hermes_agent import MockLLMProvider
        m = MockLLMProvider()
        # 每個 keyword 都要對
        for kw, expected in m.responses.items():
            resp = m.chat("system", f"我今天{kw}")
            self.assertEqual(resp, expected)


class TestExtractFactHeuristic(unittest.TestCase):
    def test_preference_trigger(self):
        from hermes_agent import extract_fact_heuristic
        r = extract_fact_heuristic("我喜歡喝咖啡", "嗯。")
        self.assertTrue(r.should_write)
        self.assertEqual(r.fact_dict["fact_type"], "preference")

    def test_dislike_trigger(self):
        from hermes_agent import extract_fact_heuristic
        r = extract_fact_heuristic("我討厭香菜", "嗯。")
        self.assertTrue(r.should_write)
        self.assertEqual(r.fact_dict["fact_type"], "preference")

    def test_plan_trigger(self):
        from hermes_agent import extract_fact_heuristic
        r = extract_fact_heuristic("我明天要去台北", "嗯。")
        self.assertTrue(r.should_write)
        self.assertEqual(r.fact_dict["fact_type"], "fact")

    def test_no_trigger(self):
        from hermes_agent import extract_fact_heuristic
        r = extract_fact_heuristic("嗯", "在。")
        self.assertFalse(r.should_write)


class TestYuaAgent(unittest.TestCase):
    def setUp(self):
        if not SOUL_EXISTS:
            self.skipTest(f"Yua SOUL 不存在: {SOUL_PATH}")
        from hermes_agent import YuaAgent, MockLLMProvider, AgentConfig
        self.YuaAgent = YuaAgent
        self.MockLLMProvider = MockLLMProvider
        self.AgentConfig = AgentConfig

    def test_load_yua_soul(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        self.assertEqual(agent.name, "Yua")
        self.assertIn("正宮", agent.archetype)

    def test_chat_returns_string(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        response = agent.chat("你好")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_chat_records_turn(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        agent.chat("第一句")
        agent.chat("第二句")
        self.assertEqual(len(agent.turns), 2)
        self.assertEqual(agent.turns[0].bryan_message, "第一句")
        self.assertEqual(agent.turns[1].bryan_message, "第二句")

    def test_conversation_history_grows(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        agent.chat("msg1")
        agent.chat("msg2")
        # 2 個 user + 2 個 assistant = 4 條 history
        self.assertEqual(len(agent.conversation_history), 4)

    def test_reset_conversation(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        agent.chat("test")
        self.assertGreater(len(agent.turns), 0)
        agent.reset_conversation()
        self.assertEqual(len(agent.turns), 0)
        self.assertEqual(len(agent.conversation_history), 0)

    def test_fact_auto_extraction(self):
        db_path = make_tmp_db()
        try:
            agent = self.YuaAgent(
                soul_path=SOUL_PATH,
                llm_provider=self.MockLLMProvider(),
                config=self.AgentConfig(
                    soul_path=SOUL_PATH,
                    memory_db_path=db_path,
                    auto_extract_facts=True,
                ),
            )
            self.assertIsNotNone(agent.memory_storage)

            agent.chat("我喜歡喝咖啡")
            # 至少 1 個 fact
            self.assertGreater(len(agent.turns[-1].facts_written), 0)

            # 從 db 驗證
            facts = agent.memory_storage.get_facts_by_subject("Bryan")
            self.assertGreater(len(facts), 0)
            self.assertEqual(facts[0].fact_type.value, "preference")
        finally:
            os.unlink(db_path)

    def test_no_fact_without_trigger(self):
        db_path = make_tmp_db()
        try:
            agent = self.YuaAgent(
                soul_path=SOUL_PATH,
                llm_provider=self.MockLLMProvider(),
                config=self.AgentConfig(
                    soul_path=SOUL_PATH,
                    memory_db_path=db_path,
                    auto_extract_facts=True,
                ),
            )
            agent.chat("嗯")  # 沒觸發 fact
            self.assertEqual(len(agent.turns[-1].facts_written), 0)
            # db 應該是空的
            if agent.memory_storage:
                self.assertEqual(agent.memory_storage.count(), 0)
        finally:
            os.unlink(db_path)

    def test_summary(self):
        agent = self.YuaAgent(
            soul_path=SOUL_PATH,
            llm_provider=self.MockLLMProvider(),
            config=self.AgentConfig(soul_path=SOUL_PATH),
        )
        agent.chat("msg1")
        agent.chat("msg2")
        summary = agent.get_conversation_summary()
        self.assertEqual(summary["name"], "Yua")
        self.assertEqual(summary["turns"], 2)
        self.assertIn("avg_response_time", summary)

    def test_last_seen_writes(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("0.0")
            last_seen_file = f.name
        try:
            agent = self.YuaAgent(
                soul_path=SOUL_PATH,
                llm_provider=self.MockLLMProvider(),
                config=self.AgentConfig(
                    soul_path=SOUL_PATH,
                    last_seen_file=last_seen_file,
                ),
            )
            before = time.time()
            agent.chat("test")
            after_ts = float(Path(last_seen_file).read_text().strip())
            self.assertGreaterEqual(after_ts, before - 1)
            self.assertLessEqual(after_ts, time.time() + 1)
        finally:
            os.unlink(last_seen_file)

    def test_mock_llm_keyword_yua_response(self):
        """Mock LLM 應該根據 keyword 給對應回應"""
        from hermes_agent import MockLLMProvider
        m = MockLLMProvider()
        # "累" 應該回 "過來"
        self.assertEqual(m.chat("s", "今天很累"), "……過來。")
        # "咖啡" 應該提到 "手沖"
        self.assertIn("手沖", m.chat("s", "想喝咖啡"))


if __name__ == "__main__":
    unittest.main()
