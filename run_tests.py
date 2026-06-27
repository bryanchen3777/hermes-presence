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

TEST_DIRS = [
    os.path.join(HERE, "temporal_awareness", "tests"),
    os.path.join(HERE, "hermes_agent", "tests"),
    os.path.join(HERE, "inner_life", "tests"),
]

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for test_dir in TEST_DIRS:
    if not os.path.isdir(test_dir):
        continue
    for fname in sorted(os.listdir(test_dir)):
        if fname.startswith("test_") and fname.endswith(".py"):
            sys.path.insert(0, test_dir)
            modname = fname[:-3]
            mod = importlib.import_module(modname)
            suite.addTests(loader.loadTestsFromModule(mod))
            sys.path.pop(0)

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
