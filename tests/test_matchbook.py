"""Tests for the W'bal (match book) model."""

import numpy as np
import pytest

from puncheur.analytics.matchbook import (
    compute_wbal,
    count_matches_burned,
    matches_remaining,
    wbal_at_timestamp,
)


class TestWbalComputation:
    """Tests for W'bal calculation using the Skiba 2012 model."""

    def test_wbal_starts_at_w_prime(self):
        """W'bal should start at W' capacity."""
        power = np.array([200.0] * 10)
        wbal = compute_wbal(power, ftp=280, w_prime=20000)
        assert wbal[0] == 20000.0

    def test_wbal_depletes_above_ftp(self):
        """Riding above FTP should deplete W'bal."""
        power = np.array([350.0] * 60)  # 60s at 350W, FTP=280
        wbal = compute_wbal(power, ftp=280, w_prime=20000)

        # Should deplete by (350-280) * 59 = 4130J over 59 seconds
        # (first second stays at w_prime)
        assert wbal[-1] < wbal[0]
        assert wbal[-1] < 20000.0

    def test_wbal_recovers_below_ftp(self):
        """Riding below FTP should recover W'bal."""
        # First deplete, then recover
        power = np.concatenate([
            np.full(60, 350.0),   # Deplete for 60s
            np.full(300, 150.0),  # Recover for 300s
        ])
        wbal = compute_wbal(power, ftp=280, w_prime=20000)

        wbal_after_depletion = wbal[59]
        wbal_after_recovery = wbal[-1]

        assert wbal_after_recovery > wbal_after_depletion

    def test_wbal_never_exceeds_w_prime(self):
        """W'bal should never go above W' capacity."""
        power = np.array([100.0] * 600)  # Very easy riding
        wbal = compute_wbal(power, ftp=280, w_prime=20000)
        assert np.all(wbal <= 20000.0)

    def test_wbal_never_negative(self):
        """W'bal should be clipped at 0."""
        power = np.array([500.0] * 300)  # Very hard for 5 minutes
        wbal = compute_wbal(power, ftp=200, w_prime=15000)
        assert np.all(wbal >= 0.0)

    def test_steady_below_ftp_stays_full(self):
        """Riding entirely below FTP should keep W'bal near W'."""
        power = np.array([200.0] * 600)
        wbal = compute_wbal(power, ftp=280, w_prime=20000)
        # Should stay at or very near 20000
        assert wbal[-1] > 19900.0

    def test_empty_power(self):
        """Empty power array should return empty W'bal."""
        wbal = compute_wbal(np.array([]), ftp=280, w_prime=20000)
        assert len(wbal) == 0

    def test_predictable_depletion(self):
        """Depletion rate should match (power - FTP) per second."""
        ftp = 280
        w_prime = 20000
        power = np.array([330.0] * 100)  # 50W above FTP
        wbal = compute_wbal(power, ftp=ftp, w_prime=w_prime)

        # After 1 second: W'bal = 20000 - 50 = 19950
        expected_after_1s = w_prime - (330 - ftp)
        assert abs(wbal[1] - expected_after_1s) < 1.0


class TestMatchesBurned:
    """Tests for match counting."""

    def test_no_matches_below_ftp(self):
        """No matches should be burned when all power is below threshold."""
        power = np.array([200.0] * 600)
        assert count_matches_burned(power, ftp=280) == 0

    def test_single_match(self):
        """One sustained effort above threshold should count as one match."""
        power = np.concatenate([
            np.full(100, 200.0),  # Easy
            np.full(60, 400.0),   # One hard effort (60s > 30s min)
            np.full(100, 200.0),  # Easy
        ])
        assert count_matches_burned(power, ftp=280) == 1

    def test_multiple_matches(self):
        """Multiple separated efforts should count as multiple matches."""
        power = np.concatenate([
            np.full(60, 400.0),   # Match 1
            np.full(60, 200.0),   # Recovery
            np.full(60, 400.0),   # Match 2
            np.full(60, 200.0),   # Recovery
            np.full(60, 400.0),   # Match 3
        ])
        assert count_matches_burned(power, ftp=280) == 3

    def test_short_effort_not_counted(self):
        """Effort shorter than min_duration should not count."""
        power = np.concatenate([
            np.full(100, 200.0),
            np.full(10, 400.0),   # Too short (10s < 30s)
            np.full(100, 200.0),
        ])
        assert count_matches_burned(power, ftp=280) == 0


class TestMatchesRemaining:
    """Tests for remaining match estimation."""

    def test_sufficient_wbal(self):
        """Should cover all segments when W'bal is sufficient."""
        assert matches_remaining(15000, [3000, 3000, 3000]) == 3

    def test_insufficient_wbal(self):
        """Should stop when W'bal can't cover next segment."""
        assert matches_remaining(5000, [3000, 3000, 3000]) == 1

    def test_exact_fit(self):
        """Exact W'bal for demands should cover all."""
        assert matches_remaining(9000, [3000, 3000, 3000]) == 3

    def test_empty_wbal(self):
        """Zero W'bal should cover nothing."""
        assert matches_remaining(0, [3000, 3000]) == 0


class TestWbalAtTimestamp:
    """Tests for W'bal lookup."""

    def test_valid_index(self):
        """Should return value at valid index."""
        wbal = np.array([20000.0, 19500.0, 19000.0])
        assert wbal_at_timestamp(wbal, 1) == 19500.0

    def test_out_of_range(self):
        """Should return 0 for out-of-range index."""
        wbal = np.array([20000.0])
        assert wbal_at_timestamp(wbal, 5) == 0.0
