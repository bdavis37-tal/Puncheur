"""Tests for the demo mode."""

import json
from pathlib import Path

import pytest

from puncheur.demo import is_demo_available, load_demo_ride, setup_demo


@pytest.fixture
def demo_env(tmp_path, monkeypatch):
    """Set up an isolated environment for demo tests."""
    monkeypatch.setattr("puncheur.config.DEFAULT_DATA_DIR", tmp_path / ".puncheur")
    return tmp_path


class TestDemoSetup:
    """Tests for demo data creation."""

    def test_setup_creates_rider(self, demo_env):
        """Demo should create a rider profile."""
        setup_demo()
        profile_path = demo_env / ".puncheur" / "rider_profile.json"
        assert profile_path.exists()
        data = json.loads(profile_path.read_text())
        assert data["name"] == "Brendan"
        assert data["ftp"] == 265

    def test_setup_creates_route(self, demo_env):
        """Demo should create the Tuesday Group Ride route."""
        setup_demo()
        routes_dir = demo_env / ".puncheur" / "routes"
        route_files = list(routes_dir.glob("*.json"))
        assert len(route_files) >= 1
        # Find the Tuesday route
        tuesday = None
        for f in route_files:
            data = json.loads(f.read_text())
            if "Tuesday" in data.get("name", ""):
                tuesday = data
                break
        assert tuesday is not None
        assert len(tuesday["segments"]) == 4

    def test_setup_creates_fitness_log(self, demo_env):
        """Demo should create fitness history."""
        setup_demo()
        fitness_path = demo_env / ".puncheur" / "fitness_log.json"
        assert fitness_path.exists()
        data = json.loads(fitness_path.read_text())
        assert len(data) > 10  # At least 10 training days in 8 weeks

    def test_setup_creates_ride_history(self, demo_env):
        """Demo should create ride-over-ride history."""
        setup_demo()
        rides_dir = demo_env / ".puncheur" / "rides"
        history_files = list(rides_dir.glob("*_history.json"))
        assert len(history_files) >= 1

    def test_setup_creates_demo_ride(self, demo_env):
        """Demo should create a sample ride."""
        setup_demo()
        assert is_demo_available()
        ride = load_demo_ride()
        assert ride.name == "Tuesday Group Ride — Mar 10"
        assert len(ride.points) > 100
        assert ride.has_power
        assert ride.has_gps
        assert ride.has_heart_rate

    def test_demo_ride_has_realistic_data(self, demo_env):
        """Demo ride should have realistic power and duration."""
        setup_demo()
        ride = load_demo_ride()
        # Should be roughly 55-60 min of data
        assert 3000 < ride.duration_seconds < 4000
        # Average power should be reasonable for a group ride
        assert 150 < ride.avg_power < 250
        # NP should be higher than avg (group ride dynamics)
        np_val = ride.normalized_power()
        assert np_val > ride.avg_power

    def test_demo_ride_segments_are_matchable(self, demo_env):
        """Demo ride GPS should match the tagged segments."""
        setup_demo()
        ride = load_demo_ride()

        from puncheur.analytics.segment_matcher import match_segments
        from puncheur.models.ride_profile import RideProfile

        profile = RideProfile.load("tuesday_group_ride")
        matches = match_segments(ride, profile, tolerance_m=80)
        # Should match at least 3 of the 4 segments
        assert len(matches) >= 3


class TestDemoWeb:
    """Tests for demo mode in the web UI."""

    @pytest.fixture
    def demo_client(self, demo_env, monkeypatch):
        """Create a test client with demo data."""
        from puncheur.web.app import app

        setup_demo()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_demo_ride_page_loads(self, demo_client):
        """Demo ride analysis should render."""
        response = demo_client.get("/demo/ride")
        assert response.status_code == 200
        assert b"Tuesday Group Ride" in response.data
        assert b"Avg Power" in response.data

    def test_demo_dashboard_shows_ride_link(self, demo_client):
        """Dashboard should show link to demo ride."""
        response = demo_client.get("/")
        assert response.status_code == 200
        assert b"Last Ride" in response.data or b"Tuesday" in response.data

    def test_demo_playbook_works(self, demo_client):
        """Playbook should work for the demo route."""
        response = demo_client.get("/playbook/tuesday_group_ride")
        assert response.status_code == 200
        assert b"Rea Road" in response.data
        assert b"Target Power" in response.data
