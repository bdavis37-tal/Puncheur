"""Shared test fixtures for Puncheur.

Provides synthetic ride data, rider profiles, and ride profiles with
known values for deterministic testing. No real FIT files needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from puncheur.models.ride import Ride, RidePoint
from puncheur.models.ride_profile import RideProfile
from puncheur.models.rider import Rider
from puncheur.models.segment import Segment


@pytest.fixture
def sample_rider() -> Rider:
    """A sample rider with known FTP and W' values."""
    return Rider(
        name="Test Rider",
        ftp=280,
        weight_kg=79.0,
        max_heart_rate=185,
        w_prime=20000,
    )


@pytest.fixture
def sample_ride() -> Ride:
    """A synthetic 60-minute ride with known power/HR/cadence/GPS data.

    Power profile:
    - First 20 min: steady Z2 at 200W
    - 20-25 min: climb 1 at 320W (above FTP)
    - 25-35 min: recovery at 150W
    - 35-40 min: climb 2 at 310W
    - 40-50 min: recovery at 160W
    - 50-55 min: climb 3 at 350W
    - 55-60 min: cool down at 120W
    """
    points = []
    start_time = datetime(2024, 3, 15, 8, 0, 0)

    # Charlotte area coordinates for a loop
    base_lat = 35.1200
    base_lon = -80.8800

    def make_points(
        start_min: int,
        end_min: int,
        power: float,
        hr: float,
        cadence: float,
        lat_start: float,
        lon_start: float,
        lat_end: float,
        lon_end: float,
        alt_start: float = 200.0,
        alt_end: float = 200.0,
    ) -> list[RidePoint]:
        """Generate ride points for a time window."""
        n = (end_min - start_min) * 60
        pts = []
        for i in range(n):
            t = start_time + timedelta(minutes=start_min, seconds=i)
            frac = i / max(n - 1, 1)
            # Add some noise to power/hr/cadence
            rng = np.random.RandomState(i + start_min * 1000)
            pts.append(
                RidePoint(
                    timestamp=t,
                    power=power + rng.normal(0, 10),
                    heart_rate=hr + rng.normal(0, 3),
                    cadence=cadence + rng.normal(0, 2),
                    speed=8.0,
                    latitude=lat_start + (lat_end - lat_start) * frac,
                    longitude=lon_start + (lon_end - lon_start) * frac,
                    altitude=alt_start + (alt_end - alt_start) * frac,
                )
            )
        return pts

    # Z2 warmup: 0-20 min
    points.extend(
        make_points(0, 20, 200, 135, 90, 35.1200, -80.8800, 35.1234, -80.8765)
    )
    # Climb 1: 20-25 min (matches segment 1 coordinates)
    points.extend(
        make_points(20, 25, 320, 170, 80, 35.1234, -80.8765, 35.1256, -80.8743, 200, 240)
    )
    # Recovery: 25-35 min
    points.extend(
        make_points(25, 35, 150, 125, 85, 35.1256, -80.8743, 35.1300, -80.8600)
    )
    # Climb 2: 35-40 min (matches segment 2 coordinates)
    points.extend(
        make_points(35, 40, 310, 168, 78, 35.1300, -80.8600, 35.1330, -80.8580, 200, 250)
    )
    # Recovery: 40-50 min
    points.extend(
        make_points(40, 50, 160, 128, 88, 35.1330, -80.8580, 35.1400, -80.8500)
    )
    # Climb 3: 50-55 min (matches segment 3 coordinates)
    points.extend(
        make_points(50, 55, 350, 178, 75, 35.1400, -80.8500, 35.1415, -80.8485, 200, 260)
    )
    # Cool down: 55-60 min
    points.extend(
        make_points(55, 60, 120, 110, 80, 35.1415, -80.8485, 35.1200, -80.8800)
    )

    return Ride(name="Test Ride", points=points, source_file="test_ride.fit")


@pytest.fixture
def sample_ride_profile() -> RideProfile:
    """A ride profile with three tagged climb segments."""
    return RideProfile(
        name="Tuesday Group Ride",
        gpx_file="tuesday_group_ride.gpx",
        segments=[
            Segment(
                name="Hill 1 — Rea Road Kicker",
                start_lat=35.1234,
                start_lon=-80.8765,
                end_lat=35.1256,
                end_lon=-80.8743,
                segment_type="climb",
                estimated_duration_seconds=90,
                avg_gradient_pct=6.5,
                notes="Attack usually starts at the base, 400m at 6-7%",
            ),
            Segment(
                name="Hill 2 — Sardis Lane",
                start_lat=35.1300,
                start_lon=-80.8600,
                end_lat=35.1330,
                end_lon=-80.8580,
                segment_type="climb",
                estimated_duration_seconds=120,
                avg_gradient_pct=5.0,
                notes="Longer drag, attacks come in the final third",
            ),
            Segment(
                name="Hill 3 — Providence Road Wall",
                start_lat=35.1400,
                start_lon=-80.8500,
                end_lat=35.1415,
                end_lon=-80.8485,
                segment_type="climb",
                estimated_duration_seconds=60,
                avg_gradient_pct=8.0,
                notes="Short and steep, final selection point",
            ),
        ],
    )


@pytest.fixture
def steady_power_ride() -> Ride:
    """A simple ride with perfectly steady power for predictable analytics."""
    start_time = datetime(2024, 3, 15, 8, 0, 0)
    points = []
    for i in range(1800):  # 30 minutes
        points.append(
            RidePoint(
                timestamp=start_time + timedelta(seconds=i),
                power=250.0,
                heart_rate=150.0,
                cadence=90.0,
                speed=8.0,
            )
        )
    return Ride(name="Steady Ride", points=points)


@pytest.fixture
def above_ftp_ride() -> Ride:
    """A ride with power above FTP for W'bal depletion testing."""
    start_time = datetime(2024, 3, 15, 8, 0, 0)
    points = []
    for i in range(300):  # 5 minutes at 350W
        points.append(
            RidePoint(
                timestamp=start_time + timedelta(seconds=i),
                power=350.0,
                heart_rate=175.0,
                cadence=85.0,
                speed=7.0,
            )
        )
    return Ride(name="Hard Effort", points=points)
