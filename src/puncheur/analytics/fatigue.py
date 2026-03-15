"""Fatigue analysis — power fade, cadence drift, and cardiac decoupling.

Detects fatigue patterns at the ride level, across segments, and within
individual efforts. A dropping cadence on climbs often signals fatigue
before power drops — this module catches that.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from puncheur.models.ride import Ride
from puncheur.models.segment import SegmentMatch


@dataclass
class FatigueReport:
    """Fatigue analysis results.

    Attributes:
        score: Overall fatigue score 0-100 (higher = more fatigued).
        ride_power_fade_pct: Power drop from first third to last third of ride.
        cadence_drift_pct: Cadence change over the ride.
        cardiac_decoupling_pct: Power:HR ratio drift (if HR data available).
        segment_fade: Power fade across sequential segments.
        within_segment_fade: Power fade within individual segments.
        assessment: Human-readable fatigue assessment.
    """

    score: float = 0.0
    ride_power_fade_pct: float = 0.0
    cadence_drift_pct: float = 0.0
    cardiac_decoupling_pct: float = 0.0
    segment_fade: list[dict] = None  # type: ignore[assignment]
    within_segment_fade: list[dict] = None  # type: ignore[assignment]
    assessment: str = ""

    def __post_init__(self) -> None:
        if self.segment_fade is None:
            self.segment_fade = []
        if self.within_segment_fade is None:
            self.within_segment_fade = []


def analyze_ride_fatigue(ride: Ride) -> FatigueReport:
    """Analyze fatigue across an entire ride.

    Compares power and cadence in the first third vs. last third
    of the ride to detect overall fade.

    Args:
        ride: The ride to analyze.

    Returns:
        A FatigueReport with ride-level fatigue metrics.
    """
    power = ride.power_stream
    n = len(power)
    if n < 30:
        return FatigueReport(assessment="Ride too short for fatigue analysis.")

    third = n // 3

    # Power fade: first third vs last third
    first_third_power = np.mean(power[:third])
    last_third_power = np.mean(power[2 * third :])
    power_fade = 0.0
    if first_third_power > 0:
        power_fade = ((first_third_power - last_third_power) / first_third_power) * 100

    # Cadence drift
    cadence = ride.cadence_stream
    cadence_drift = 0.0
    if np.any(cadence > 0):
        first_cad = np.mean(cadence[:third][cadence[:third] > 0]) if np.any(cadence[:third] > 0) else 0
        last_cad = np.mean(cadence[2 * third :][cadence[2 * third :] > 0]) if np.any(cadence[2 * third :] > 0) else 0
        if first_cad > 0:
            cadence_drift = ((first_cad - last_cad) / first_cad) * 100

    # Cardiac decoupling
    decoupling = 0.0
    if ride.has_heart_rate:
        hr = ride.heart_rate_stream
        first_hr = np.mean(hr[:third][hr[:third] > 0]) if np.any(hr[:third] > 0) else 0
        last_hr = np.mean(hr[2 * third :][hr[2 * third :] > 0]) if np.any(hr[2 * third :] > 0) else 0
        if first_hr > 0 and last_hr > 0 and first_third_power > 0 and last_third_power > 0:
            first_ratio = first_third_power / first_hr
            last_ratio = last_third_power / last_hr
            decoupling = ((first_ratio - last_ratio) / first_ratio) * 100

    # Score: weighted combination
    score = min(100.0, abs(power_fade) * 2 + abs(cadence_drift) * 1.5 + abs(decoupling) * 1.5)

    # Assessment
    if score < 20:
        assessment = "Minimal fatigue — you paced well or had plenty in reserve."
    elif score < 40:
        assessment = "Moderate fatigue — some power fade in the final third, typical for a solid effort."
    elif score < 60:
        assessment = "Significant fatigue — notable power and cadence drop. Consider pacing adjustments."
    elif score < 80:
        assessment = "Heavy fatigue — you were digging deep by the end. Recovery efforts or pacing issue."
    else:
        assessment = "Severe fatigue — dramatic power collapse. Either heroic effort or went out too hard."

    return FatigueReport(
        score=score,
        ride_power_fade_pct=power_fade,
        cadence_drift_pct=cadence_drift,
        cardiac_decoupling_pct=decoupling,
        assessment=assessment,
    )


def analyze_segment_fatigue(matches: list[SegmentMatch]) -> list[dict]:
    """Analyze power fade across sequential segments.

    Compares power on Hill 1 vs Hill 2 vs Hill 3 within the same ride.

    Args:
        matches: List of segment matches from the same ride.

    Returns:
        List of dicts with segment name, power, and fade percentage.
    """
    if len(matches) < 2:
        return []

    results = []
    baseline_power = matches[0].avg_power

    for i, match in enumerate(matches):
        fade_pct = 0.0
        if baseline_power > 0:
            fade_pct = ((baseline_power - match.avg_power) / baseline_power) * 100

        results.append({
            "segment": match.segment.name,
            "avg_power": match.avg_power,
            "fade_from_first_pct": fade_pct,
            "index": i,
        })

    return results


def analyze_within_segment_fatigue(match: SegmentMatch) -> dict:
    """Analyze power fade within a single segment.

    Compares power in the first half vs. second half of a climb.

    Args:
        match: A segment match with ride data.

    Returns:
        Dict with first-half power, second-half power, and fade percentage.
    """
    if match.ride_data is None or len(match.ride_data.points) < 10:
        return {"fade_pct": 0.0, "assessment": "Segment too short for analysis."}

    power = match.ride_data.power_stream
    mid = len(power) // 2

    first_half = float(np.mean(power[:mid]))
    second_half = float(np.mean(power[mid:]))

    fade_pct = 0.0
    if first_half > 0:
        fade_pct = ((first_half - second_half) / first_half) * 100

    if fade_pct < 5:
        assessment = "Even pacing — well executed."
    elif fade_pct < 15:
        assessment = "Slight fade — typical for hard efforts."
    elif fade_pct < 25:
        assessment = "Significant fade — started too hard or fatigue accumulation."
    else:
        assessment = "Major power collapse — went out way too hard."

    return {
        "first_half_power": first_half,
        "second_half_power": second_half,
        "fade_pct": fade_pct,
        "assessment": assessment,
    }
