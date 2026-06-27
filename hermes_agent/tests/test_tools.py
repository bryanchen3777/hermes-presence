"""
test_tools.py — hermes_agent/tools/ 整合測試
"""
import sys, os
import time
import unittest
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))


# ============================================================
# validate_soul 測試
# ============================================================

class TestValidateSoul(unittest.TestCase):
    def setUp(self):
        from hermes_agent.tools import validate_soul
        self.validate_soul = validate_soul

    def test_nonexistent_file(self):
        from hermes_agent.tools import validate_soul
        r = validate_soul("/nonexistent/path/soul.md")
        self.assertFalse(r.is_valid)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("不存在", r.errors[0])

    def test_empty_file(self):
        from hermes_agent.tools import validate_soul
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            path = f.name
        try:
            r = self.validate_soul(path)
            self.assertFalse(r.is_valid)
        finally:
            os.unlink(path)

    def test_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Just a title\n\nSome content")
            path = f.name
        try:
            r = self.validate_soul(path)
            self.assertFalse(r.is_valid)
            self.assertTrue(any("frontmatter" in e for e in r.errors))
        finally:
            os.unlink(path)

    def test_minimal_valid(self):
        """只有必填欄位的最小 SOUL"""
        content = """---
name: TestAgent
archetype: Test
version: 1.0
integrates:
  - hermes-presence
  - hermes-memory-core
---

# Test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            r = self.validate_soul(path)
            # 必填 Part 不齊全會有 error
            self.assertFalse(r.is_valid)
            # 缺少 5 個必填 Part
            self.assertGreaterEqual(len(r.errors), 5)
        finally:
            os.unlink(path)

    def test_real_yua_soul(self):
        """實際的 Yua SOUL v2.0 應該全通過"""
        soul = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
        if not os.path.exists(soul):
            self.skipTest(f"Yua SOUL 不存在: {soul}")
        r = self.validate_soul(soul)
        self.assertTrue(r.is_valid, f"Yua SOUL 應該通過，但有 errors: {r.errors}")
        self.assertEqual(len(r.errors), 0)

    def test_format_report(self):
        from hermes_agent.tools import format_report
        r = self.validate_soul("/nonexistent")
        report = format_report(r)
        self.assertIn("ERRORS", report)
        self.assertIn("Status:", report)


# ============================================================
# yua_soul_loader 測試
# ============================================================

class TestYuaSoulLoader(unittest.TestCase):
    def setUp(self):
        from hermes_agent.tools import YuaSoulLoader
        self.Loader = YuaSoulLoader

    def test_load_real_yua_soul(self):
        soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
        if not os.path.exists(soul_path):
            self.skipTest("Yua SOUL 不存在")
        loader = self.Loader(soul_path=soul_path)
        loader.load()
        # 必填屬性
        self.assertEqual(loader.name, "Yua")
        self.assertIn("正宮", loader.archetype)
        self.assertEqual(loader.timezone, "Asia/Taipei")
        self.assertEqual(loader.locale, "zh_TW")
        self.assertEqual(loader.harem_position, "正宮")
        # body 有東西
        self.assertGreater(len(loader.body), 1000)
        # 必填 Part 都在 body
        for part in ["最高優先級硬規則", "核心身份", "Signature", "Shadow Core",
                     "LANGUAGE BEHAVIOR CONSTRAINTS"]:
            self.assertIn(part, loader.body, f"missing Part: {part}")

    def test_load_nonexistent(self):
        loader = self.Loader(soul_path="/nonexistent/soul.md")
        with self.assertRaises(FileNotFoundError):
            loader.load()

    def test_frontmatter_keys(self):
        soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
        if not os.path.exists(soul_path):
            self.skipTest("Yua SOUL 不存在")
        loader = self.Loader(soul_path=soul_path)
        loader.load()
        fm = loader.frontmatter
        # 必填
        self.assertEqual(fm.get("name"), "Yua")
        # 推薦
        self.assertIn("temporal_awareness", fm)
        self.assertIn("inner_life", fm)
        self.assertIn("memory_core", fm)
        self.assertIn("relationships", fm)

    def test_build_prompt_minimal(self):
        """建一個最小 SOUL，build prompt 不出錯"""
        content = """---
name: TestAgent
archetype: Test
version: 1.0
integrates:
  - hermes-presence
locale: zh_TW
timezone: Asia/Taipei
---

# Test SOUL
最高優先級硬規則: test
核心身份: test
Signature: test
Shadow Core: test
LANGUAGE BEHAVIOR CONSTRAINTS: test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            loader = self.Loader(soul_path=path)
            loader.load()
            result = loader.build_system_prompt(
                bryan_last_seen_ts=time.time() - 7200,
                include_inner_life=False,
                include_facts=False,
            )
            self.assertGreater(len(result.system_prompt), 100)
            self.assertIn("TestAgent", result.system_prompt)
            self.assertIn("temporal", result.metadata)
        finally:
            os.unlink(path)

    def test_build_prompt_with_bryan_absence(self):
        """測試 Bryan 缺席 2 小時後的 prompt"""
        soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
        if not os.path.exists(soul_path):
            self.skipTest("Yua SOUL 不存在")
        loader = self.Loader(soul_path=soul_path)
        loader.load()
        import time
        result = loader.build_system_prompt(
            bryan_last_seen_ts=time.time() - 7200,
            include_inner_life=False,
            include_facts=False,
        )
        # 應該有缺席 block
        self.assertIn("缺席", result.system_prompt)
        # metadata 應該有
        self.assertIn("temporal", result.metadata)
        if "temporal" in result.metadata:
            self.assertIsNotNone(result.metadata["temporal"].get("absence_magnitude"))

    def test_built_prompt_summary(self):
        soul_path = r"C:\Users\bbfcc\.hermes\profiles\yua\soul.md"
        if not os.path.exists(soul_path):
            self.skipTest("Yua SOUL 不存在")
        loader = self.Loader(soul_path=soul_path)
        loader.load()
        result = loader.build_system_prompt(
            include_temporal=True,
            include_inner_life=False,
            include_facts=False,
        )
        summary = result.summary()
        self.assertIn("chars=", summary)
        self.assertIn("lines=", summary)


if __name__ == "__main__":
    import time
    unittest.main()
