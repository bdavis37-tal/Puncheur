"""Tests for the CP/W' model fitting."""

import pytest

from puncheur.analytics.cp_model import CPModel, fit_cp_model


class TestCPModel:
    """Tests for the fitted CP model."""

    def test_predict_power_decreases_with_duration(self):
        """Longer durations should have lower predicted power."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        p60 = model.predict_power(60)
        p300 = model.predict_power(300)
        p1200 = model.predict_power(1200)
        assert p60 > p300 > p1200

    def test_predict_power_approaches_cp_at_long_durations(self):
        """At very long durations, power should approach CP."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        p3600 = model.predict_power(3600)
        assert abs(p3600 - 250) < 10  # Within 10W of CP

    def test_predict_power_neuromuscular_cap(self):
        """Very short durations should be capped at neuromuscular ceiling."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        p1 = model.predict_power(1)
        assert p1 <= 250 * 2.5  # Capped at 2.5x CP

    def test_predict_duration_below_cp(self):
        """Below CP, duration should be infinite."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        assert model.predict_duration(200) == float("inf")

    def test_predict_duration_above_cp(self):
        """Above CP, duration should be finite and positive."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        t = model.predict_duration(350)
        assert t > 0
        assert t < 300  # Should be < 5 min at 350W with 20kJ W'

    def test_w_cost_below_cp(self):
        """Below CP, W' cost should be zero."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        assert model.w_cost(200, 60) == 0.0

    def test_w_cost_above_cp(self):
        """Above CP, W' cost should equal (power - CP) * duration."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        cost = model.w_cost(350, 60)
        assert cost == 100 * 60  # (350 - 250) * 60

    def test_depletion_pct(self):
        """Depletion percentage should be proportional to W' cost."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        pct = model.depletion_pct(350, 100)  # 100W above CP for 100s = 10000J = 50%
        assert abs(pct - 50.0) < 0.1

    def test_zero_duration(self):
        """Zero duration should return zero power."""
        model = CPModel(cp=250, w_prime=20000, r_squared=0.95, durations_used=10)
        assert model.predict_power(0) == 0.0


class TestCPFitting:
    """Tests for the model fitting algorithm."""

    def test_fit_from_known_model(self):
        """Fitting data generated from a known model should recover the parameters."""
        # Generate synthetic curve from known CP=260, W'=18000
        true_cp = 260
        true_w = 18000
        curve = [(d, true_cp + true_w / d) for d in range(120, 1201, 30)]

        model = fit_cp_model(curve)
        assert abs(model.cp - true_cp) < 5  # Within 5W
        assert abs(model.w_prime - true_w) < 1000  # Within 1kJ
        assert model.r_squared > 0.99

    def test_fit_with_noise(self):
        """Model should be reasonably robust to noisy data."""
        import numpy as np

        rng = np.random.RandomState(42)
        true_cp = 250
        true_w = 20000
        curve = []
        for d in range(120, 1201, 60):
            p = true_cp + true_w / d + rng.normal(0, 5)
            curve.append((d, p))

        model = fit_cp_model(curve)
        assert abs(model.cp - true_cp) < 15
        assert abs(model.w_prime - true_w) < 3000
        assert model.r_squared > 0.9

    def test_fit_sparse_data_fallback(self):
        """With insufficient data, should fall back to estimation."""
        curve = [(300, 280), (60, 350)]  # Only 2 points in range
        model = fit_cp_model(curve)
        assert model.cp > 0
        assert model.w_prime > 0
        assert model.durations_used == 0  # Sparse fallback

    def test_fit_empty_curve(self):
        """Empty curve should still return a valid model."""
        model = fit_cp_model([])
        assert model.cp > 0
        assert model.w_prime > 0
