"""Tests for the GPS segment matcher."""

from puncheur.analytics.segment_matcher import match_segments


class TestSegmentMatcher:
    """Tests for GPS-based segment matching."""

    def test_matches_known_segments(self, sample_ride, sample_ride_profile):
        """Should match all three segments with known coordinates."""
        matches = match_segments(sample_ride, sample_ride_profile, tolerance_m=50)
        assert len(matches) == 3

    def test_match_order(self, sample_ride, sample_ride_profile):
        """Matches should be in route order."""
        matches = match_segments(sample_ride, sample_ride_profile, tolerance_m=50)
        if len(matches) >= 2:
            assert matches[0].start_time < matches[1].start_time

    def test_match_power_reasonable(self, sample_ride, sample_ride_profile):
        """Matched segments should have reasonable power values."""
        matches = match_segments(sample_ride, sample_ride_profile, tolerance_m=50)
        for match in matches:
            # Climb power should be above recovery power
            assert match.avg_power > 100

    def test_match_duration_positive(self, sample_ride, sample_ride_profile):
        """Matched segments should have positive duration."""
        matches = match_segments(sample_ride, sample_ride_profile, tolerance_m=50)
        for match in matches:
            assert match.duration_seconds > 0

    def test_no_gps_returns_empty(self, sample_ride_profile):
        """Ride without GPS should return empty matches."""
        from datetime import datetime, timedelta

        from puncheur.models.ride import Ride, RidePoint

        ride = Ride(
            points=[
                RidePoint(timestamp=datetime(2024, 1, 1) + timedelta(seconds=i), power=200)
                for i in range(100)
            ]
        )
        matches = match_segments(ride, sample_ride_profile)
        assert matches == []

    def test_tight_tolerance(self, sample_ride, sample_ride_profile):
        """Very tight tolerance might miss segments."""
        matches = match_segments(sample_ride, sample_ride_profile, tolerance_m=0.1)
        # With very tight tolerance, may not match all segments
        assert isinstance(matches, list)
