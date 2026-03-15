"""Tests for the power duration curve calculator."""

from puncheur.analytics.power_curve import (
    composite_power_curve,
    duration_buckets,
    power_at_duration,
    power_duration_curve,
)


class TestPowerDurationCurve:
    """Tests for MMP calculation."""

    def test_steady_power_curve(self, steady_power_ride):
        """Steady 250W ride should have ~250W at all durations."""
        curve = power_duration_curve(steady_power_ride, max_duration=60)
        assert len(curve) > 0

        # At any duration, max avg should be ~250W (steady ride)
        for duration, power in curve:
            assert abs(power - 250.0) < 1.0, f"Expected ~250W at {duration}s, got {power}W"

    def test_curve_is_monotonically_decreasing(self, sample_ride):
        """Power duration curve should generally decrease with duration."""
        curve = power_duration_curve(sample_ride, max_duration=300)
        # Short durations should have higher power than long durations
        if len(curve) >= 2:
            assert curve[0][1] >= curve[-1][1]

    def test_empty_ride(self):
        """Empty ride should return empty curve."""
        from puncheur.models.ride import Ride

        ride = Ride()
        curve = power_duration_curve(ride)
        assert curve == []

    def test_power_at_duration_lookup(self, sample_ride):
        """Look up power for a specific duration."""
        curve = power_duration_curve(sample_ride, max_duration=60)
        p = power_at_duration(curve, 30)
        assert p > 0

    def test_power_at_missing_duration(self, sample_ride):
        """Missing duration should return 0."""
        curve = power_duration_curve(sample_ride, max_duration=10)
        assert power_at_duration(curve, 9999) == 0.0

    def test_duration_buckets(self, sample_ride):
        """Duration buckets should return standard benchmarks."""
        curve = power_duration_curve(sample_ride, max_duration=3600)
        buckets = duration_buckets(curve)
        assert "5s" in buckets
        assert "1min" in buckets
        assert "5min" in buckets
        assert "20min" in buckets

    def test_composite_curve(self, sample_ride, steady_power_ride):
        """Composite curve should take best from each ride."""
        composite = composite_power_curve([sample_ride, steady_power_ride], max_duration=60)
        single = power_duration_curve(sample_ride, max_duration=60)

        # Composite should be >= any single ride
        for dur, power in composite:
            single_power = power_at_duration(single, dur)
            assert power >= single_power - 0.1  # Allow tiny floating point diff
