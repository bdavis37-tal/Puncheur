"""Tests for the fatigue analysis module."""

from datetime import datetime, timedelta

import numpy as np

from puncheur.analytics.fatigue import (
    analyze_ride_fatigue,
    analyze_segment_fatigue,
    analyze_within_segment_fatigue,
)
from puncheur.models.ride import Ride, RidePoint
from puncheur.models.segment import Segment, SegmentMatch


class TestRideFatigue:
    """Tests for ride-level fatigue analysis."""

    def test_steady_ride_low_fatigue(self, steady_power_ride):
        """Steady power ride should show minimal fatigue."""
        report = analyze_ride_fatigue(steady_power_ride)
        assert report.score < 20
        assert abs(report.ride_power_fade_pct) < 5

    def test_fading_ride_high_fatigue(self):
        """Ride with declining power should show high fatigue."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        points = []
        for i in range(1800):
            # Power decreases from 300 to 150 over the ride
            power = 300 - (150 * i / 1800)
            points.append(
                RidePoint(
                    timestamp=start + timedelta(seconds=i),
                    power=power,
                    heart_rate=150,
                    cadence=90 - (20 * i / 1800),  # Cadence also drops
                )
            )
        ride = Ride(name="Fading Ride", points=points)
        report = analyze_ride_fatigue(ride)
        assert report.ride_power_fade_pct > 20
        assert report.score > 30

    def test_short_ride_returns_message(self):
        """Very short ride should return an informative message."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        points = [
            RidePoint(timestamp=start + timedelta(seconds=i), power=250)
            for i in range(10)
        ]
        ride = Ride(name="Short", points=points)
        report = analyze_ride_fatigue(ride)
        assert "too short" in report.assessment.lower()

    def test_fatigue_score_bounded(self, sample_ride):
        """Fatigue score should be between 0 and 100."""
        report = analyze_ride_fatigue(sample_ride)
        assert 0 <= report.score <= 100


class TestSegmentFatigue:
    """Tests for cross-segment fatigue analysis."""

    def test_declining_segment_power(self):
        """Decreasing power across segments should be detected."""
        now = datetime(2024, 1, 1)
        matches = [
            SegmentMatch(
                segment=Segment(name=f"Hill {i}", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
                start_time=now,
                end_time=now + timedelta(minutes=2),
                avg_power=power,
            )
            for i, power in enumerate([350, 320, 280], 1)
        ]
        results = analyze_segment_fatigue(matches)
        assert len(results) == 3
        assert results[0]["fade_from_first_pct"] == 0  # Baseline
        assert results[1]["fade_from_first_pct"] > 0  # Faded
        assert results[2]["fade_from_first_pct"] > results[1]["fade_from_first_pct"]

    def test_single_segment_no_analysis(self):
        """Single segment can't show cross-segment fade."""
        now = datetime(2024, 1, 1)
        matches = [
            SegmentMatch(
                segment=Segment(name="Hill 1", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
                start_time=now,
                end_time=now + timedelta(minutes=2),
                avg_power=300,
            )
        ]
        assert analyze_segment_fatigue(matches) == []


class TestWithinSegmentFatigue:
    """Tests for within-segment power fade."""

    def test_even_pacing(self):
        """Even power throughout should show minimal fade."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        points = [
            RidePoint(timestamp=start + timedelta(seconds=i), power=300.0)
            for i in range(120)
        ]
        ride = Ride(points=points)
        match = SegmentMatch(
            segment=Segment(name="Test", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
            start_time=start,
            end_time=start + timedelta(seconds=120),
            ride_data=ride,
        )
        result = analyze_within_segment_fatigue(match)
        assert result["fade_pct"] < 5

    def test_fading_effort(self):
        """Declining power should show positive fade."""
        start = datetime(2024, 1, 1, 8, 0, 0)
        points = [
            RidePoint(
                timestamp=start + timedelta(seconds=i),
                power=400.0 - (i * 2),  # 400 -> 160 over 120s
            )
            for i in range(120)
        ]
        ride = Ride(points=points)
        match = SegmentMatch(
            segment=Segment(name="Test", start_lat=0, start_lon=0, end_lat=0, end_lon=0),
            start_time=start,
            end_time=start + timedelta(seconds=120),
            ride_data=ride,
        )
        result = analyze_within_segment_fatigue(match)
        assert result["fade_pct"] > 20
