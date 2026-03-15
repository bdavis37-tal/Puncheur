"""Tests for the KOM attempt planner."""

from puncheur.strategy.kom_planner import plan_kom_attempt


class TestKomPlanner:
    """Tests for KOM attempt plan generation."""

    def test_1min_plan(self, sample_rider):
        """1-minute plan should have anaerobic characteristics."""
        plan = plan_kom_attempt(sample_rider, "Test Hill", 60)

        assert plan["target_duration_s"] == 60
        assert plan["target_power"] > sample_rider.ftp  # Above FTP
        assert plan["effort_category"] == "anaerobic"
        assert len(plan["pacing_splits"]) > 0

    def test_2min_plan(self, sample_rider):
        """2-minute plan should target VO2max."""
        plan = plan_kom_attempt(sample_rider, "Test Hill", 120)

        assert plan["target_power"] > sample_rider.ftp
        assert plan["effort_category"] == "vo2max"

    def test_5min_plan(self, sample_rider):
        """5-minute plan should target sustained VO2max."""
        plan = plan_kom_attempt(sample_rider, "Long Climb", 300)

        assert plan["target_power"] > sample_rider.ftp
        assert plan["effort_category"] == "vo2max"

    def test_20min_plan(self, sample_rider):
        """20-minute plan should target threshold."""
        plan = plan_kom_attempt(sample_rider, "Epic Climb", 1200)

        # 20-min power should be close to FTP
        assert abs(plan["target_power"] - sample_rider.ftp) < sample_rider.ftp * 0.1
        assert plan["effort_category"] == "threshold"

    def test_warmup_duration_scales(self, sample_rider):
        """Warmup duration should scale with effort duration."""
        short = plan_kom_attempt(sample_rider, "Sprint", 60)
        long = plan_kom_attempt(sample_rider, "Climb", 1200)

        assert short["warmup_duration_min"] < long["warmup_duration_min"]

    def test_wbal_warning_for_unsustainable(self, sample_rider):
        """Should warn if target power is unsustainable for the duration."""
        # Very long duration at high power should trigger warning
        plan = plan_kom_attempt(sample_rider, "Monster", 600)

        # Check W'bal analysis is present
        assert "wbal_analysis" in plan
        assert "sustainable" in plan["wbal_analysis"]

    def test_pacing_splits_sum_to_100(self, sample_rider):
        """Pacing splits should cover the entire effort."""
        plan = plan_kom_attempt(sample_rider, "Hill", 120)
        splits = plan["pacing_splits"]
        assert len(splits) >= 2
        # First split should start at 0%
        assert "0-" in splits[0]["pct_of_effort"] or "0%" in splits[0]["pct_of_effort"]
        # Last split should end at 100%
        assert "100%" in splits[-1]["pct_of_effort"]
