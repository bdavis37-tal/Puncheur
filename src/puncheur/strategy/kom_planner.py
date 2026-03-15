"""KOM attempt planner.

Plans a KOM attempt for a target segment: target power from the rider's
power duration curve, pacing strategy based on gradient profile, W'bal
budget modeling, and warm-up protocol selection.
"""

from __future__ import annotations

import math

from puncheur.models.rider import Rider


def plan_kom_attempt(
    rider: Rider,
    segment_name: str,
    duration_seconds: int,
) -> dict:
    """Plan a KOM attempt for a target segment.

    Args:
        rider: Rider profile with FTP, W', and power data.
        segment_name: Name of the target segment.
        duration_seconds: Target duration for the attempt in seconds.

    Returns:
        Dict containing the complete KOM attempt plan.
    """
    target_power = _target_power_for_duration(rider, duration_seconds)
    pacing = _pacing_strategy(duration_seconds)
    wbal_analysis = _wbal_sustainability(rider, target_power, duration_seconds)
    warmup_duration = _warmup_duration_for_effort(duration_seconds)

    plan = {
        "segment": segment_name,
        "target_duration_s": duration_seconds,
        "target_power": round(target_power),
        "target_power_per_kg": round(target_power / rider.weight_kg, 2) if rider.weight_kg > 0 else 0,
        "pacing_strategy": pacing["strategy"],
        "pacing_splits": pacing["splits"],
        "wbal_analysis": wbal_analysis,
        "warmup_duration_min": warmup_duration,
        "effort_category": _effort_category(duration_seconds),
    }

    # Add W'bal sustainability warning if needed
    if not wbal_analysis["sustainable"]:
        plan["wbal_warning"] = (
            f"Target power of {round(target_power)}W for {duration_seconds}s "
            f"will deplete W'bal by {round(wbal_analysis['depletion_pct'])}%. "
            f"Consider reducing target by {round(wbal_analysis['suggested_reduction'])}W "
            f"for a sustainable effort."
        )

    return plan


def _target_power_for_duration(rider: Rider, duration_seconds: int) -> float:
    """Estimate target power using the CP/W' model.

    Uses the hyperbolic power-duration relationship: P = CP + W'/t
    which is physiologically grounded (Morton 1996) rather than
    arbitrary FTP multipliers.

    Falls back to stepwise estimates for very short durations where
    the 2-parameter model breaks down (neuromuscular domain).
    """
    from puncheur.analytics.cp_model import CPModel

    # Build a CP model from the rider's known parameters
    cp = rider.ftp * 0.95  # CP is ~95% of FTP
    w_prime = rider.w_prime

    model = CPModel(cp=cp, w_prime=w_prime, r_squared=0.5, durations_used=0)
    return model.predict_power(duration_seconds)


def _pacing_strategy(duration_seconds: int) -> dict:
    """Generate pacing splits based on effort duration.

    Short efforts: Front-load power in the first 20%.
    Long efforts: Negative split — start conservative, build.
    """
    if duration_seconds <= 120:
        # Short and steep: front-load
        return {
            "strategy": (
                "Front-load power in the first 20%, then settle into a sustainable effort. "
                "Don't save anything for the way home."
            ),
            "splits": [
                {"pct_of_effort": "0-20%", "power_pct": 110, "note": "Hard start — establish your pace"},
                {"pct_of_effort": "20-80%", "power_pct": 98, "note": "Settle in — find the rhythm"},
                {"pct_of_effort": "80-100%", "power_pct": 105, "note": "Everything left — sprint to the line"},
            ],
        }
    elif duration_seconds <= 600:
        # Medium: even with kick
        return {
            "strategy": (
                "Even pacing with a finish kick. Start at target power, "
                "resist the urge to go harder early. Build in the final third."
            ),
            "splits": [
                {"pct_of_effort": "0-33%", "power_pct": 97, "note": "Controlled start — just under target"},
                {"pct_of_effort": "33-66%", "power_pct": 100, "note": "On target — steady and smooth"},
                {"pct_of_effort": "66-100%", "power_pct": 105, "note": "Build to finish — progressive increase"},
            ],
        }
    else:
        # Long: negative split
        return {
            "strategy": (
                "Negative split — start at 95% target, build progressively. "
                "The first half should feel too easy. The second half is where you race."
            ),
            "splits": [
                {"pct_of_effort": "0-25%", "power_pct": 93, "note": "Easy start — resist the adrenaline"},
                {"pct_of_effort": "25-50%", "power_pct": 97, "note": "Build gradually — approaching target"},
                {"pct_of_effort": "50-75%", "power_pct": 102, "note": "Above target — this is where you work"},
                {"pct_of_effort": "75-100%", "power_pct": 108, "note": "Empty the tank — all-in to the line"},
            ],
        }


def _wbal_sustainability(rider: Rider, target_power: float, duration_seconds: int) -> dict:
    """Model W'bal depletion for the planned effort."""
    power_above_ftp = max(0, target_power - rider.ftp)
    total_w_cost = power_above_ftp * duration_seconds
    depletion_pct = (total_w_cost / rider.w_prime * 100) if rider.w_prime > 0 else 0

    sustainable = depletion_pct <= 100

    suggested_reduction = 0.0
    if not sustainable and duration_seconds > 0:
        # How much to reduce to hit exactly 100% depletion
        max_above_ftp = rider.w_prime / duration_seconds
        suggested_reduction = power_above_ftp - max_above_ftp

    return {
        "power_above_ftp": round(power_above_ftp),
        "total_w_cost": round(total_w_cost),
        "depletion_pct": round(depletion_pct, 1),
        "sustainable": sustainable,
        "suggested_reduction": round(max(0, suggested_reduction)),
    }


def _warmup_duration_for_effort(duration_seconds: int) -> int:
    """Recommended warm-up duration based on effort length."""
    if duration_seconds <= 60:
        return 30
    elif duration_seconds <= 120:
        return 35
    elif duration_seconds <= 300:
        return 40
    else:
        return 50


def _effort_category(duration_seconds: int) -> str:
    """Categorize the effort by physiological system."""
    if duration_seconds <= 10:
        return "neuromuscular"
    elif duration_seconds <= 60:
        return "anaerobic"
    elif duration_seconds <= 300:
        return "vo2max"
    elif duration_seconds <= 1200:
        return "threshold"
    else:
        return "sub_threshold"
