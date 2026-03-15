"""Tests for the Puncheur web UI."""

import json
from pathlib import Path

import pytest

from puncheur.web.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with isolated data directory."""
    monkeypatch.setattr("puncheur.config.DEFAULT_DATA_DIR", tmp_path / ".puncheur")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def client_with_rider(client, tmp_path, monkeypatch):
    """Test client with a rider profile already set up."""
    data_dir = tmp_path / ".puncheur"
    data_dir.mkdir(parents=True, exist_ok=True)
    profile = {
        "name": "Test Rider",
        "ftp": 280,
        "weight_kg": 79.0,
        "power_zones": {
            "z1_recovery": [0, 154],
            "z2_endurance": [155, 210],
            "z3_tempo": [211, 252],
            "z4_threshold": [253, 294],
            "z5_vo2max": [295, 336],
            "z6_anaerobic": [337, 420],
            "z7_neuromuscular": [421, 9999],
        },
        "max_heart_rate": 185,
        "w_prime": 20000,
    }
    (data_dir / "rider_profile.json").write_text(json.dumps(profile))
    (data_dir / "routes").mkdir(exist_ok=True)
    (data_dir / "rides").mkdir(exist_ok=True)
    return client


class TestSetup:
    """Tests for the onboarding wizard."""

    def test_redirects_to_setup_when_no_profile(self, client):
        """Should redirect to setup when no rider profile exists."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/setup" in response.headers["Location"]

    def test_setup_page_loads(self, client):
        """Setup page should render without errors."""
        response = client.get("/setup")
        assert response.status_code == 200
        assert b"Puncheur" in response.data
        assert b"FTP" in response.data

    def test_setup_creates_profile(self, client, tmp_path, monkeypatch):
        """Submitting setup should create a rider profile."""
        response = client.post(
            "/setup",
            data={
                "name": "Brendan",
                "ftp": "280",
                "weight": "79",
                "experience": "intermediate",
                "age": "35",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        # Profile should exist now
        profile_path = tmp_path / ".puncheur" / "rider_profile.json"
        assert profile_path.exists()
        data = json.loads(profile_path.read_text())
        assert data["name"] == "Brendan"
        assert data["ftp"] == 280


class TestDashboard:
    """Tests for the dashboard."""

    def test_dashboard_loads(self, client_with_rider):
        """Dashboard should load when profile exists."""
        response = client_with_rider.get("/")
        assert response.status_code == 200
        assert b"Test Rider" in response.data
        assert b"Dashboard" in response.data

    def test_dashboard_shows_fitness(self, client_with_rider):
        """Dashboard should display fitness metrics."""
        response = client_with_rider.get("/")
        assert b"Fitness" in response.data
        assert b"Fatigue" in response.data
        assert b"Form" in response.data


class TestUpload:
    """Tests for the upload page."""

    def test_upload_page_loads(self, client_with_rider):
        """Upload page should render."""
        response = client_with_rider.get("/upload")
        assert response.status_code == 200
        assert b"Upload" in response.data or b"upload" in response.data
        assert b".fit" in response.data

    def test_upload_rejects_non_fit(self, client_with_rider):
        """Should reject non-.fit files."""
        from io import BytesIO

        data = {"file": (BytesIO(b"not a fit file"), "ride.txt")}
        response = client_with_rider.post(
            "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
        )
        assert b".fit" in response.data


class TestKOM:
    """Tests for the KOM planner."""

    def test_kom_page_loads(self, client_with_rider):
        """KOM planner page should render."""
        response = client_with_rider.get("/kom")
        assert response.status_code == 200
        assert b"KOM" in response.data

    def test_kom_generates_plan(self, client_with_rider):
        """Submitting KOM form should generate a plan."""
        response = client_with_rider.post(
            "/kom",
            data={"segment": "Test Hill", "duration": "60"},
        )
        assert response.status_code == 200
        assert b"Target Power" in response.data
        assert b"Pacing" in response.data


class TestSettings:
    """Tests for the settings page."""

    def test_settings_page_loads(self, client_with_rider):
        """Settings page should render with current values."""
        response = client_with_rider.get("/settings")
        assert response.status_code == 200
        assert b"280" in response.data  # FTP value
        assert b"Test Rider" in response.data

    def test_settings_update(self, client_with_rider):
        """Updating settings should save new values."""
        response = client_with_rider.post(
            "/settings",
            data={
                "name": "Updated Name",
                "ftp": "290",
                "weight": "78",
                "max_hr": "190",
                "w_prime": "22000",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Updated Name" in response.data


class TestWarmup:
    """Tests for the warm-up protocol page."""

    def test_warmup_page_loads(self, client_with_rider):
        """Warm-up page should render for 60s effort."""
        response = client_with_rider.get("/warmup/60")
        assert response.status_code == 200
        assert b"Warm-Up" in response.data
        assert b"Z1" in response.data or b"Z2" in response.data
