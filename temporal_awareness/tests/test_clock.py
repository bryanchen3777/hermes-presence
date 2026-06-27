"""
test_clock.py — clock.py 純函式測試
"""
import sys, os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from temporal_awareness.clock import (
    classify_period, sleep_pressure_at, circadian_energy_at,
    appetite_at, body_feeling_for,
)


class TestClassifyPeriod(unittest.TestCase):
    def test_deep_night_00(self):
        assert classify_period(0, 0) == "deep_night"
        assert classify_period(1, 30) == "deep_night"
        assert classify_period(3, 59) == "deep_night"

    def test_dawn(self):
        assert classify_period(4, 0) == "dawn"
        assert classify_period(5, 0) == "dawn"
        assert classify_period(6, 59) == "dawn"

    def test_morning(self):
        assert classify_period(7, 0) == "morning"
        assert classify_period(11, 59) == "morning"

    def test_afternoon(self):
        assert classify_period(12, 0) == "afternoon"
        assert classify_period(17, 59) == "afternoon"

    def test_evening(self):
        assert classify_period(18, 0) == "evening"
        assert classify_period(21, 59) == "evening"

    def test_night(self):
        assert classify_period(22, 0) == "night"
        assert classify_period(23, 59) == "night"


class TestSleepPressure:
    def test_peak_at_2am(self):
        assert sleep_pressure_at(2, 0) == 1.00

    def test_lowest_at_2pm(self):
        assert sleep_pressure_at(14, 0) == 0.05

    def test_in_range(self):
        for h in range(24):
            for m in (0, 30):
                v = sleep_pressure_at(h, m)
                assert 0.0 <= v <= 1.0, f"out of range at {h}:{m} = {v}"

    def test_evening_rising(self):
        # 22:00 > 19:00 > 14:00
        assert sleep_pressure_at(22, 0) > sleep_pressure_at(19, 0)
        assert sleep_pressure_at(19, 0) > sleep_pressure_at(14, 0)


class TestEnergy:
    def test_inverse_of_pressure(self):
        # 能量 = 1 - 壓力 * 0.7
        e_2am = circadian_energy_at(2, 0)
        e_2pm = circadian_energy_at(14, 0)
        assert e_2am < e_2pm
        assert e_2pm > 0.90  # 14:00 應該很清醒

    def test_in_range(self):
        for h in range(24):
            v = circadian_energy_at(h, 0)
            assert 0.0 <= v <= 1.0


class TestAppetite:
    def test_three_peaks(self):
        # 三個高峰：8, 12.5, 19
        assert appetite_at(8, 0) > 0.70
        assert appetite_at(12, 30) > 0.70
        assert appetite_at(19, 0) > 0.70

    def test_low_at_3am(self):
        assert appetite_at(3, 0) < 0.20

    def test_in_range(self):
        for h in range(24):
            v = appetite_at(h, 0)
            assert 0.0 <= v <= 1.0


class TestBodyFeeling:
    def test_exhausted_when_very_low_energy(self):
        assert body_feeling_for("deep_night", 0.15) == "exhausted"

    def test_sleepy_when_low(self):
        assert body_feeling_for("evening", 0.35) == "sleepy"

    def test_alert_morning(self):
        assert body_feeling_for("morning", 0.90) == "alert"

    def test_relaxed_evening(self):
        assert body_feeling_for("evening", 0.65) == "relaxed_evening"

    def test_neutral(self):
        # 中等能量 + 任何時段 → 中性
        result = body_feeling_for("afternoon", 0.65)
        assert result in ("alert", "neutral")
