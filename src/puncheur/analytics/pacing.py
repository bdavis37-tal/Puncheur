"""Pre-segment pacing analysis.

For each tagged segment, analyzes the 5-10 minutes preceding it to answer:
"Did you arrive fresh or already in the red?" Quantifies the cost of
poor pre-climb pacing on segment performance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from puncheur.models.rider import Rider
from puncheur.models.segment import SegmentMatch


@dataclass
class PacingAnalysis:
    """Analysis of pacing in the approach to a segment.

    Attributes:
        segment_name: Name of the segment being approached.
        pre_segment_avg_power: Average power in the pre-segment window.
        ride_avg_power: Overall ride average power for comparison.
        time_above_threshold_s: Seconds spent above FTP in the pre-segment window.
        pre_segment_window_s: Duration of the analysis window.
        power_delta: Pre-segment power vs ride average (positive = hotter).
        zone: Power zone of the pre-segment effort.
        recommendation: Pacing recommendation for next time.
    """

    segment_name: str
    pre_segment_avg_power: float
    ride_avg_power: float
    time_above_threshold_s: float
    pre_segment_window_s: float
    power_delta: float
    zone: str
    recommendation: str


def analyze_pre_segment_pacing(
    match: SegmentMatch,
    ride_avg_power: float,
    rider: Rider,
) -> PacingAnalysis:
    """Analyze pacing in the approach to a segment.

    Looks at the pre-segment window to determine whether the rider
    arrived fresh or with a partially depleted W'bal.

    Args:
        match: A segment match with pre-segment data.
        ride_avg_power: Overall ride average power.
        rider: Rider profile for zone calculations.

    Returns:
        A PacingAnalysis with metrics and recommendations.
    """
    pre_data = match.pre_segment_data
    if pre_data is None or len(pre_data.points) == 0:
        return PacingAnalysis(
            segment_name=match.segment.name,
            pre_segment_avg_power=0.0,
            ride_avg_power=ride_avg_power,
            time_above_threshold_s=0.0,
            pre_segment_window_s=0.0,
            power_delta=0.0,
            zone="N/A",
            recommendation="No pre-segment data available.",
        )

    power = pre_data.power_stream
    pre_avg = float(np.mean(power)) if len(power) > 0 else 0.0
    window_duration = pre_data.duration_seconds

    # Time above FTP
    time_above = float(np.sum(power > rider.ftp))

    # Power delta vs ride average
    delta = pre_avg - ride_avg_power

    # Zone classification
    zone = rider.zone_for_power(pre_avg)

    # Generate recommendation
    recommendation = _generate_pacing_recommendation(
        pre_avg, ride_avg_power, time_above, rider, match.segment.name
    )

    return PacingAnalysis(
        segment_name=match.segment.name,
        pre_segment_avg_power=pre_avg,
        ride_avg_power=ride_avg_power,
        time_above_threshold_s=time_above,
        pre_segment_window_s=window_duration,
        power_delta=delta,
        zone=zone,
        recommendation=recommendation,
    )


def _generate_pacing_recommendation(
    pre_avg: float,
    ride_avg: float,
    time_above_ftp: float,
    rider: Rider,
    segment_name: str,
) -> str:
    """Generate a human-readable pacing recommendation."""
    delta = pre_avg - ride_avg
    zone = rider.zone_for_power(pre_avg)

    if time_above_ftp > 60:
        return (
            f"You spent {time_above_ftp:.0f}s above FTP before {segment_name}. "
            f"That's burning matches before the climb even starts. "
            f"Target Z2 power in the approach to arrive with full W'bal."
        )

    if delta > 20:
        return (
            f"You averaged {pre_avg:.0f}W in the approach — {delta:.0f}W above ride average. "
            f"Soft-pedal to Z2 in the final 5 minutes before {segment_name} "
            f"to maximize W'bal at the base."
        )

    if "z1" in zone or "z2" in zone:
        return f"Good pacing into {segment_name} — you arrived in {zone.split('_')[1]} zone with fresh legs."

    return (
        f"Approach power of {pre_avg:.0f}W ({zone.split('_')[1]} zone). "
        f"Consider dropping to Z2 earlier for more recovery."
    )
