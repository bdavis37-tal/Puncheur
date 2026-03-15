"""Tests for the pre-ride playbook generator."""

from puncheur.strategy.playbook import generate_playbook


class TestPlaybook:
    """Tests for playbook generation."""

    def test_generates_playbook(self, sample_rider, sample_ride_profile):
        """Should generate a complete playbook with all sections."""
        playbook = generate_playbook(sample_rider, sample_ride_profile)

        assert "rider" in playbook
        assert "route" in playbook
        assert "fitness" in playbook
        assert "match_budget" in playbook
        assert "segments" in playbook
        assert "pre_ride_notes" in playbook

    def test_segment_targets(self, sample_rider, sample_ride_profile):
        """Each segment should have power targets."""
        playbook = generate_playbook(sample_rider, sample_ride_profile)

        assert len(playbook["segments"]) == 3
        for seg in playbook["segments"]:
            assert "target_power" in seg
            assert seg["target_power"] > 0
            assert "tactic" in seg
            assert "w_cost" in seg

    def test_match_budget(self, sample_rider, sample_ride_profile):
        """Match budget should reflect W' capacity."""
        playbook = generate_playbook(sample_rider, sample_ride_profile)

        budget = playbook["match_budget"]
        assert budget["w_prime"] == sample_rider.w_prime
        assert budget["total_estimated_cost"] > 0
        assert budget["status"] in ("comfortable", "tight", "critical")

    def test_pre_ride_notes(self, sample_rider, sample_ride_profile):
        """Should generate at least one pre-ride note."""
        playbook = generate_playbook(sample_rider, sample_ride_profile)
        assert len(playbook["pre_ride_notes"]) > 0
