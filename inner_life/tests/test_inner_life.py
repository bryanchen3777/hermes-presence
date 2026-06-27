"""
test_inner_life.py — inner_life 全模組測試
"""
import sys, os
import unittest
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))


class TestStorage(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)  # 刪掉讓 Storage 重建
        self.path = path
        from inner_life.storage import Storage
        self.storage = Storage(self.path)

    def test_add_activity(self):
        aid = self.storage.add_activity(
            profile_name="yua",
            activity_type="work",
            title="整理花園",
            energy_delta=-0.1,
        )
        self.assertGreater(aid, 0)

    def test_get_activities(self):
        for i in range(3):
            self.storage.add_activity(
                profile_name="yua",
                activity_type="work",
                title=f"活動 {i}",
            )
            time.sleep(0.01)
        acts = self.storage.get_activities("yua")
        self.assertEqual(len(acts), 3)
        # 應該 DESC 排序
        self.assertIn("活動", acts[0]["title"])

    def test_get_activities_since(self):
        old_ts = time.time() - 7200
        self.storage.add_activity(
            profile_name="yua", activity_type="work", title="舊活動", ts=old_ts,
        )
        self.storage.add_activity(
            profile_name="yua", activity_type="work", title="新活動",
        )
        acts = self.storage.get_activities("yua", since_ts=time.time() - 3600)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["title"], "新活動")

    def test_add_body_state(self):
        bid = self.storage.add_body_state(
            profile_name="yua",
            energy=0.7, hunger=0.3, fatigue=0.5, comfort=0.8,
        )
        self.assertGreater(bid, 0)

    def test_get_latest_body_state(self):
        self.storage.add_body_state(
            profile_name="yua", energy=0.5, hunger=0.5, fatigue=0.5, comfort=0.8,
        )
        time.sleep(0.01)
        self.storage.add_body_state(
            profile_name="yua", energy=0.8, hunger=0.2, fatigue=0.3, comfort=0.9,
        )
        latest = self.storage.get_latest_body_state("yua")
        self.assertEqual(latest["energy"], 0.8)

    def test_add_monologue(self):
        mid = self.storage.add_monologue(
            profile_name="yua", thought="今天有點累",
            trigger_event="after_work", valence=-0.2, arousal=0.3,
        )
        self.assertGreater(mid, 0)


class TestBody(unittest.TestCase):
    def test_compute_body_state_no_history(self):
        from inner_life.body import compute_body_state
        state = compute_body_state("yua")
        self.assertEqual(state.profile_name, "yua")
        self.assertGreaterEqual(state.energy, 0)
        self.assertLessEqual(state.energy, 1)

    def test_compute_body_state_with_meal(self):
        from inner_life.body import compute_body_state
        state = compute_body_state("yua", last_meal_ts=time.time() - 3600)
        # 1 小時前吃過 → 不餓
        self.assertLess(state.hunger, 0.3)

    def test_compute_body_state_hungry(self):
        from inner_life.body import compute_body_state
        state = compute_body_state("yua", last_meal_ts=time.time() - 7 * 3600)
        # 7 小時前吃 → 很餓
        self.assertGreater(state.hunger, 0.9)

    def test_to_prompt_returns_natural_language(self):
        from inner_life.body import BodyState
        s = BodyState(
            profile_name="yua", energy=0.3, hunger=0.7, fatigue=0.6,
            ts=time.time(),
        )
        prompt = s.to_prompt()
        self.assertIn("能量", prompt)
        self.assertIn("累", prompt)  # 應該有描述


class TestActivity(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd); os.unlink(path)
        from inner_life.storage import Storage
        self.storage = Storage(path)

    def test_log_and_get(self):
        from inner_life.activity import Activity, log_activity, get_recent_activities
        a = Activity(
            profile_name="yua", activity_type="work",
            title="整理花園", energy_delta=-0.1,
        )
        log_activity(self.storage, a)
        acts = get_recent_activities(self.storage, "yua", hours=1)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["title"], "整理花園")


class TestGenerator(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd); os.unlink(path)
        from inner_life.storage import Storage
        self.storage = Storage(path)

    def test_generate_day(self):
        from inner_life.generator import generate_day, RuleBasedDetailGenerator
        gen = RuleBasedDetailGenerator(personality_keywords=["tea"])
        result = generate_day(
            self.storage, "yua",
            detail_generator=gen,
            day_start_ts=time.time() - 86400,  # 昨天
        )
        self.assertGreater(len(result.activities), 0)
        self.assertGreater(len(result.body_states), 0)

    def test_generate_day_personalized(self):
        from inner_life.generator import generate_day, RuleBasedDetailGenerator
        # 用 book 關鍵字
        gen = RuleBasedDetailGenerator(personality_keywords=["book"])
        result = generate_day(
            self.storage, "yua",
            detail_generator=gen,
            day_start_ts=time.time() - 86400,
        )
        # 找到 leisure 類型
        leisure = [a for a in result.activities if a.activity_type == "leisure"]
        if leisure:
            # 應該有「書」相關的細節
            titles = [a.title for a in leisure]
            self.assertTrue(any("書" in t for t in titles))

    def test_generate_day_variety(self):
        from inner_life.generator import generate_day, RuleBasedDetailGenerator
        gen = RuleBasedDetailGenerator()
        result = generate_day(
            self.storage, "yua",
            detail_generator=gen,
            day_start_ts=time.time() - 86400,
        )
        # 同一個 type 應該有多個不同的 title
        work_titles = [a.title for a in result.activities if a.activity_type == "work"]
        self.assertGreater(len(set(work_titles)), 1, "work 類型應該有變化")

    def test_generate_day_timezone(self):
        """時間軸應該是 Asia/Taipei (UTC+8)"""
        from inner_life.generator import generate_day, RuleBasedDetailGenerator
        from datetime import datetime
        from zoneinfo import ZoneInfo
        gen = RuleBasedDetailGenerator()
        # 從今天 0:00 Asia/Taipei 開始
        tz = ZoneInfo("Asia/Taipei")
        today_midnight = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        result = generate_day(
            self.storage, "yua",
            detail_generator=gen,
            day_start_ts=today_midnight.timestamp(),
        )
        # 第一個活動應該接近 00:00 但因為 schedule 從 6.5 開始，所以第一個應該是 06:30
        if result.activities:
            first = result.activities[0]
            dt = datetime.fromtimestamp(first.ts, tz=tz)
            self.assertEqual(dt.hour, 6)
            self.assertEqual(dt.minute, 30)


class TestPromptBlock(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd); os.unlink(path)
        from inner_life.storage import Storage
        self.storage = Storage(path)
        # 預先塞一些資料
        self.storage.add_activity(
            profile_name="yua", activity_type="work", title="整理花園",
            description="把陽台的植物重新種了",
        )
        self.storage.add_activity(
            profile_name="yua", activity_type="meal", title="午餐",
        )
        self.storage.add_body_state(
            profile_name="yua", energy=0.6, hunger=0.2, fatigue=0.4, comfort=0.8,
        )
        self.storage.add_monologue(
            profile_name="yua", thought="今天過得還挺悠閒",
            valence=0.3, arousal=0.2,
        )

    def test_render_block(self):
        from inner_life.prompt_blocks import render_inner_life_block
        block = render_inner_life_block(self.storage, "yua", hours=24)
        self.assertIn("內在世界", block)
        self.assertIn("整理花園", block)
        self.assertIn("午餐", block)

    def test_render_body_only(self):
        from inner_life.prompt_blocks import render_body_only
        s = render_body_only(self.storage, "yua")
        self.assertIn("能量", s)

    def test_empty_storage(self):
        from inner_life.prompt_blocks import render_inner_life_block
        # 不存在的 profile
        block = render_inner_life_block(self.storage, "nobody", hours=24)
        self.assertIn("內在世界", block)
        self.assertIn("還沒有", block)
