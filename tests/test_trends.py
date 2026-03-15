"""Tests for segment trend analysis and race readiness."""

import json

import pytest

from puncheur.analytics.trends import (
    SegmentTrend,
    analyze_segment_trends,
    analyze_route_trend,
    _compute_race_readiness,
)


@pytest.fixture
def trend_env(tmp_path, monkeypatch):
    """Set up isolated environment with ride history."""
    monkeypatch.setattr("puncheur.config.DEFAULT_DATA_DIR", tmp_path / ".puncheur")
    rides_dir = tmp_path / ".puncheur" / "rides"
    rides_dir.mkdir(parents=True)

    # 8 weeks of history with linear improvement
    history = []
    for week in range(8):
        history.append({
            "date": f"2026-01-{20 + week}",
            "avg_power": 195 + week * 1.5,
            "np": 210 + week * 1.5,
            "tss": 85,
            "segments": [
                {"name": "Rea Road Kicker", "avg_power": 310 + week * 2, "duration": 75 - week * 0.3},
                {"name": "Colony Road Sprint", "avg_power": 520 + week * 3, "duration": 35},
            ],
        })

    history_file = rides_dir / "test_route_history.json"
    history_file.write_text(json.dumps(history), encoding="utf-8")
    return tmp_path


class TestSegmentTrend:
    """Tests for segment trend dataclass."""

    def test_improving_detection(self):
        trend = SegmentTrend(
            segment_name="Test",
            weeks_of_data=6,
            power_trend_per_week=2.0,
            time_trend_per_week=-0.3,
            current_avg_power=320,
            projected_power=322,
            best_power=325,
            best_date="2026-01-25",
            consistency_pct=75.0,
            r_squared=0.8,
        )
        assert trend.is_improving

    def test_not_improving_low_confidence(self):
        trend = SegmentTrend(
            segment_name="Test",
            weeks_of_data=6,
            power_trend_per_week=2.0,
            time_trend_per_week=-0.3,
            current_avg_power=320,
            projected_power=322,
            best_power=325,
            best_date="2026-01-25",
            consistency_pct=75.0,
            r_squared=0.1,  # Low confidence
        )
        assert not trend.is_improving

    def test_trend_description_strong(self):
        trend = SegmentTrend(
            segment_name="Test", weeks_of_data=5, power_trend_per_week=4.0,
            time_trend_per_week=-0.5, current_avg_power=320, projected_power=324,
            best_power=325, best_date="2026-01-25", consistency_pct=75.0, r_squared=0.8,
        )
        assert "strong" in trend.trend_description.lower()


class TestAnalyzeSegmentTrends:
    """Tests for the full trend analysis pipeline."""

    def test_computes_trends_from_history(self, trend_env):
        trends = analyze_segment_trends("test_route")
        assert len(trends) == 2
        names = {t.segment_name for t in trends}
        assert "Rea Road Kicker" in names
        assert "Colony Road Sprint" in names

    def test_power_trend_is_positive(self, trend_env):
        trends = analyze_segment_trends("test_route")
        rea = next(t for t in trends if t.segment_name == "Rea Road Kicker")
        assert rea.power_trend_per_week > 0  # We seeded increasing data

    def test_projected_power_higher_than_current(self, trend_env):
        trends = analyze_segment_trends("test_route")
        rea = next(t for t in trends if t.segment_name == "Rea Road Kicker")
        assert rea.projected_power > rea.current_avg_power

    def test_no_history_returns_empty(self, trend_env):
        trends = analyze_segment_trends("nonexistent_route")
        assert trends == []


class TestRaceReadiness:
    """Tests for race readiness scoring."""

    def test_high_readiness(self):
        trends = [
            SegmentTrend("A", 8, 2.0, -0.3, 320, 322, 325, "2026-01-25", 100.0, 0.8),
            SegmentTrend("B", 8, 1.5, -0.2, 540, 541, 545, "2026-01-25", 100.0, 0.7),
        ]
        score, label = _compute_race_readiness(trends, fitness_ctl=55, fitness_tsb=8)
        assert score >= 65
        assert "ready" in label.lower() or "peak" in label.lower()

    def test_low_readiness(self):
        trends = [
            SegmentTrend("A", 2, -1.0, 0.5, 300, 299, 310, "2026-01-15", 25.0, 0.2),
        ]
        score, label = _compute_race_readiness(trends, fitness_ctl=15, fitness_tsb=-20)
        assert score < 40

    def test_route_trend_includes_readiness(self, trend_env):
        rt = analyze_route_trend("test_route", fitness_ctl=50, fitness_tsb=5)
        assert rt.race_readiness > 0
        assert len(rt.race_readiness_label) > 0
        assert len(rt.segment_trends) == 2
