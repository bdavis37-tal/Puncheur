"""Pre-ride playbook generator.

Given a rider profile, a ride profile with tagged segments, and recent
ride history, generates a tactical playbook: fitness snapshot, match budget,
pacing targets for each segment, and tactical recommendations.
"""

from __future__ import annotations

from puncheur.analytics.fitness import compute_fitness
from puncheur.models.ride_profile import RideProfile
from puncheur.models.rider import Rider


def generate_playbook(rider: Rider, profile: RideProfile) -> dict:
    """Generate a pre-ride playbook for a tagged route.

    Args:
        rider: Rider profile with FTP, W', and power zones.
        profile: Ride profile with tagged segments.

    Returns:
        Dict containing the complete playbook data.
    """
    # Fitness snapshot
    fitness = compute_fitness()

    # Match budget: estimate W' cost for each segment
    total_w_cost = 0.0
    segment_plans = []

    for seg in profile.segments:
        w_cost = _estimate_segment_w_cost(seg, rider)
        total_w_cost += w_cost

        target_power = _segment_target_power(seg, rider)
        tactic = _segment_tactic(seg, rider, profile.segments)

        segment_plans.append({
            "name": seg.name,
            "type": seg.segment_type,
            "estimated_duration": seg.estimated_duration_seconds,
            "gradient": seg.avg_gradient_pct,
            "target_power": round(target_power),
            "w_cost": round(w_cost),
            "tactic": tactic,
            "pre_climb_target": round(rider.ftp * 0.65),  # Z2 approach power
            "notes": seg.notes,
        })

    # Overall match budget
    budget_pct = (total_w_cost / rider.w_prime * 100) if rider.w_prime > 0 else 0
    budget_status = "comfortable" if budget_pct < 70 else "tight" if budget_pct < 90 else "critical"

    return {
        "rider": rider.name,
        "route": profile.name,
        "fitness": {
            "ctl": round(fitness.get("ctl", 0), 1),
            "atl": round(fitness.get("atl", 0), 1),
            "tsb": round(fitness.get("tsb", 0), 1),
        },
        "match_budget": {
            "w_prime": rider.w_prime,
            "total_estimated_cost": round(total_w_cost),
            "budget_pct": round(budget_pct, 1),
            "status": budget_status,
        },
        "segments": segment_plans,
        "pre_ride_notes": _generate_pre_ride_notes(rider, profile, budget_status),
    }


def _estimate_segment_w_cost(segment, rider: Rider) -> float:
    """Estimate the W' cost of a segment based on its characteristics."""
    duration = segment.estimated_duration_seconds
    gradient = segment.avg_gradient_pct

    # Rough power estimate based on gradient
    # Steeper = more power above FTP needed
    if gradient >= 8:
        power_above_ftp = rider.ftp * 0.30  # 130% FTP typical for steep
    elif gradient >= 6:
        power_above_ftp = rider.ftp * 0.20  # 120% FTP
    elif gradient >= 4:
        power_above_ftp = rider.ftp * 0.10  # 110% FTP
    else:
        power_above_ftp = rider.ftp * 0.05  # Just above FTP

    return power_above_ftp * duration


def _segment_target_power(segment, rider: Rider) -> float:
    """Calculate target power for a segment based on duration and profile."""
    duration = segment.estimated_duration_seconds

    # Use standard power-duration relationship
    if duration <= 60:
        return rider.ftp * 1.30  # ~1 min power
    elif duration <= 120:
        return rider.ftp * 1.20  # ~2 min power
    elif duration <= 300:
        return rider.ftp * 1.10  # ~5 min power
    else:
        return rider.ftp * 1.00  # Threshold


def _segment_tactic(segment, rider: Rider, all_segments: list) -> str:
    """Generate tactical advice for a specific segment."""
    idx = next(
        (i for i, s in enumerate(all_segments) if s.name == segment.name),
        0,
    )
    is_last = idx == len(all_segments) - 1
    is_first = idx == 0

    if segment.estimated_duration_seconds <= 60:
        if is_last:
            return "Final selection — empty the tank. Full gas from the base."
        return "Short and steep — controlled intensity, don't overcook early segments."

    if segment.estimated_duration_seconds <= 120:
        if is_last:
            return "Settle into a rhythm for the first half, accelerate in the final third."
        return "Mark the leaders, respond to moves but don't initiate. Save matches."

    # Longer efforts
    if is_first:
        return "Stay in the group. Don't burn a match on the first climb unless you're very strong here."

    if is_last:
        return "This is where it counts. Negative split — start at 95%, build to finish."

    return "Steady effort. Don't surge, don't coast. Keep W'bal above 50%."


def _generate_pre_ride_notes(rider: Rider, profile: RideProfile, budget: str) -> list[str]:
    """Generate overall pre-ride tactical notes."""
    notes = []

    if budget == "critical":
        notes.append(
            "W' budget is tight for this route. You cannot go hard on every climb. "
            "Pick your battle — conserve early, attack late."
        )
    elif budget == "tight":
        notes.append(
            "Moderate W' demand. You can contest most climbs but need to pace at least one."
        )
    else:
        notes.append(
            "Comfortable W' budget. You can attack every climb if you pace the approaches."
        )

    notes.append(
        f"Pre-climb target: {round(rider.ftp * 0.65)}W (Z2) for 5 minutes before each segment."
    )

    if rider.w_per_kg > 4.0:
        notes.append(
            "Your W/kg is strong. Use the gradient to your advantage on the steeper pitches."
        )
    elif rider.w_per_kg < 3.0:
        notes.append(
            "Consider sitting in on the climbs and using your recovery ability between efforts."
        )

    return notes
