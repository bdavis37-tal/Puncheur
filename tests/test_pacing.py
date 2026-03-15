"""Tests for the pre-segment pacing analysis."""

from datetime import datetime, timedelta

from puncheur.analytics.pacing import analyze_pre_segment_pacing
from puncheur.models.ride import Ride, RidePoint
from puncheur.models.rider import Rider
from puncheur.models.segment import Segment, SegmentMatch


class TestPacingAnalysis:
    """Tests for pre-segment pacing."""

    def test_easy_approach(self, sample_rider):
        """Easy approach should get a positive recommendation."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        pre_points = [
            RidePoint(timestamp=start + timedelta(seconds=i), power=160.0)
            for i in range(300)
        ]
        pre_ride = Ride(points=pre_points)

        match = SegmentMatch(
            segment=Segment(name="Hill 1", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
            start_time=start + timedelta(seconds=300),
            end_time=start + timedelta(seconds=400),
            pre_segment_data=pre_ride,
        )

        result = analyze_pre_segment_pacing(match, ride_avg_power=200, rider=sample_rider)
        assert result.pre_segment_avg_power > 0
        assert "z2" in result.zone or "z1" in result.zone

    def test_hard_approach(self, sample_rider):
        """Hard approach should warn about burned matches."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        pre_points = [
            RidePoint(timestamp=start + timedelta(seconds=i), power=300.0)
            for i in range(300)
        ]
        pre_ride = Ride(points=pre_points)

        match = SegmentMatch(
            segment=Segment(name="Hill 1", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
            start_time=start + timedelta(seconds=300),
            end_time=start + timedelta(seconds=400),
            pre_segment_data=pre_ride,
        )

        result = analyze_pre_segment_pacing(match, ride_avg_power=200, rider=sample_rider)
        # Should flag the high approach power
        assert result.power_delta > 0

    def test_no_pre_segment_data(self, sample_rider):
        """Missing pre-segment data should return safe defaults."""
        match = SegmentMatch(
            segment=Segment(name="Hill 1", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1),
        )
        result = analyze_pre_segment_pacing(match, ride_avg_power=200, rider=sample_rider)
        assert result.pre_segment_avg_power == 0.0
