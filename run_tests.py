"""
run_tests.py — 不依賴 pytest 的測試 runner
"""
import sys
import os
import unittest

# 確保可以 import temporal_awareness
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 收集所有測試 — 直接手動載入每個 test_*.py
import importlib

TESTS_DIR = os.path.join(HERE, "temporal_awareness", "tests")
loader = unittest.TestLoader()
suite = unittest.TestSuite()

for fname in sorted(os.listdir(TESTS_DIR)):
    if fname.startswith("test_") and fname.endswith(".py"):
        # 把 tests/ 加到 path 讓 import "test_clock" 等能運作
        sys.path.insert(0, TESTS_DIR)
        modname = fname[:-3]
        mod = importlib.import_module(modname)
        suite.addTests(loader.loadTestsFromModule(mod))
        sys.path.pop(0)

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
