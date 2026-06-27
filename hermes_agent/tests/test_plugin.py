"""
test_plugin.py — hermes_agent/plugin.py 整合測試

不真的啟動 Hermes，模擬 ctx 物件
"""
import sys, os
import unittest
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))


class FakeCtx:
    def __init__(self):
        self.hooks = []
        self.tools = {}

    def register_hook(self, name, fn):
        self.hooks.append((name, fn))

    def register_tool(self, name, description, func):
        self.tools[name] = {"description": description, "func": func}


class TestPlugin(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        tmp.write("0.0")
        tmp.close()
        os.environ["HERMES_LAST_SEEN_FILE"] = tmp.name
        os.environ["HERMES_TIMEZONE"] = "Asia/Taipei"
        os.environ["HERMES_LOCALE"] = "zh_TW"

        if "hermes_agent.plugin" in sys.modules:
            del sys.modules["hermes_agent.plugin"]
        if "hermes_agent" in sys.modules:
            del sys.modules["hermes_agent"]
        from hermes_agent import plugin
        self.plugin = plugin

    def test_pre_llm_returns_context(self):
        result = self.plugin._pre_llm_call()
        self.assertIn("context", result)
        self.assertIn("現在", result["context"])

    def test_pre_llm_no_last_seen(self):
        result = self.plugin._pre_llm_call()
        self.assertNotIn("缺席", result["context"])

    def test_post_llm_writes_file(self):
        self.plugin._post_llm_call()
        after = float(open(os.environ["HERMES_LAST_SEEN_FILE"]).read().strip())
        self.assertGreater(after, 0)

    def test_get_current_time(self):
        result = self.plugin.get_current_time()
        self.assertIn("iso_8601", result)
        self.assertIn("body_feeling", result)
        self.assertIn("period_label", result)

    def test_get_bryan_absence_first_meeting(self):
        result = self.plugin.get_bryan_absence()
        self.assertEqual(result["status"], "first_meeting")

    def test_get_bryan_absence_after_delay(self):
        past = time.time() - 7200
        with open(os.environ["HERMES_LAST_SEEN_FILE"], "w") as f:
            f.write(str(past))
        result = self.plugin.get_bryan_absence()
        self.assertNotIn("status", result)
        self.assertIn("hours", result)
        self.assertGreater(result["hours"], 1.5)
        self.assertLess(result["hours"], 2.5)

    def test_register_with_fake_ctx(self):
        ctx = FakeCtx()
        self.plugin.register(ctx)
        self.assertEqual(len(ctx.hooks), 2)
        self.assertIn("pre_llm_call", [h[0] for h in ctx.hooks])
        self.assertIn("post_llm_call", [h[0] for h in ctx.hooks])
        self.assertIn("get_current_time", ctx.tools)
        self.assertIn("get_bryan_absence", ctx.tools)
