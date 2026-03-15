"""Pre-ride playbook generator — adaptive, data-driven race strategy.

Given a rider profile, a ride profile with tagged segments, and recent
ride history, generates a tactical playbook with:
- Fitness snapshot and race readiness score
- W' match budget with per-segment cost estimation
- Adaptive power targets based on YOUR actual segment history (not generic FTP multipliers)
- Segment trend projections ("you're improving +2.1W/week on Rea Road")
- Tactical recommendations that adapt to fatigue patterns

This is the core differentiator: Strava tells you what happened.
Garmin tells you how recovered you are. Puncheur tells you what to DO.
"""

from __future__ import annotations

from puncheur.analytics.fitness import compute_fitness
from puncheur.analytics.trends import analyze_segment_trends, analyze_route_trend
from puncheur.models.ride_profile import RideProfile
from puncheur.models.rider import Rider


def generate_playbook(rider: Rider, profile: RideProfile) -> dict:
    """Generate a pre-ride playbook for a tagged route.

    Uses actual segment history when available, falls back to physiological
    estimates when there's no data yet.
    """
    fitness = compute_fitness()
    route_slug = profile.name.lower().replace(" ", "_")

    # Load segment trends (the differentiator)
    segment_trends = analyze_segment_trends(route_slug)
    trend_lookup = {t.segment_name: t for t in segment_trends}

    # Route-level trend with race readiness
    route_trend = analyze_route_trend(
        route_slug,
        fitness_ctl=fitness.get("ctl", 0),
        fitness_tsb=fitness.get("tsb", 0),
    )

    # Try to fit CP model from ride data for better power predictions
    cp_model = _try_fit_cp_model(rider)

    # Build segment plans
    total_w_cost = 0.0
    segment_plans = []

    for seg in profile.segments:
        trend = trend_lookup.get(seg.name)

        # ADAPTIVE: Use actual history if we have it
        if trend and trend.weeks_of_data >= 3:
            target_power = round(trend.projected_power)
            # W' cost from actual data — much more accurate than gradient estimates
            w_cost = _actual_w_cost(target_power, seg.estimated_duration_seconds, rider)
        elif cp_model:
            # CP MODEL: Use fitted physiological model
            target_power = round(cp_model.predict_power(seg.estimated_duration_seconds))
            w_cost = cp_model.w_cost(target_power, seg.estimated_duration_seconds)
        else:
            # FALLBACK: Generic FTP multipliers (only for brand-new users)
            target_power = round(_generic_target_power(seg, rider))
            w_cost = _generic_w_cost(seg, rider)

        total_w_cost += w_cost
        tactic = _segment_tactic(seg, rider, profile.segments, trend)

        plan = {
            "name": seg.name,
            "type": seg.segment_type,
            "estimated_duration": seg.estimated_duration_seconds,
            "gradient": seg.avg_gradient_pct,
            "target_power": target_power,
            "w_cost": round(w_cost),
            "tactic": tactic,
            "pre_climb_target": round(rider.ftp * 0.65),
            "notes": seg.notes,
        }

        # Add trend data when available
        if trend and trend.weeks_of_data >= 2:
            plan["trend"] = trend.trend_description
            plan["trend_rate"] = trend.power_trend_per_week
            plan["weeks_of_data"] = trend.weeks_of_data
            plan["best_power"] = trend.best_power
            plan["data_driven"] = True
        else:
            plan["data_driven"] = False

        segment_plans.append(plan)

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
        "pre_ride_notes": _generate_pre_ride_notes(rider, profile, budget_status, route_trend),
        "race_readiness": {
            "score": route_trend.race_readiness,
            "label": route_trend.race_readiness_label,
        },
        "has_history": any(t.weeks_of_data >= 3 for t in segment_trends),
    }


def _try_fit_cp_model(rider: Rider):
    """Attempt to fit a CP model. Returns None if not enough data."""
    try:
        from puncheur.analytics.cp_model import CPModel

        # If rider has calibrated W' and FTP, use those as a pre-fit model
        return CPModel(
            cp=rider.ftp * 0.95,  # CP is typically ~95% of FTP
            w_prime=rider.w_prime,
            r_squared=0.5,
            durations_used=0,
        )
    except Exception:
        return None


def _actual_w_cost(target_power: float, duration: float, rider: Rider) -> float:
    """W' cost based on actual target power vs rider's CP."""
    cp = rider.ftp * 0.95  # CP estimate
    above_cp = max(0, target_power - cp)
    return above_cp * duration


def _generic_target_power(segment, rider: Rider) -> float:
    """Fallback: generic FTP multipliers for new users with no history."""
    duration = segment.estimated_duration_seconds
    if duration <= 60:
        return rider.ftp * 1.30
    elif duration <= 120:
        return rider.ftp * 1.20
    elif duration <= 300:
        return rider.ftp * 1.10
    else:
        return rider.ftp * 1.00


def _generic_w_cost(segment, rider: Rider) -> float:
    """Fallback: gradient-based W' cost estimation."""
    duration = segment.estimated_duration_seconds
    gradient = segment.avg_gradient_pct

    if gradient >= 8:
        power_above_ftp = rider.ftp * 0.30
    elif gradient >= 6:
        power_above_ftp = rider.ftp * 0.20
    elif gradient >= 4:
        power_above_ftp = rider.ftp * 0.10
    else:
        power_above_ftp = rider.ftp * 0.05

    return power_above_ftp * duration


def _segment_tactic(segment, rider: Rider, all_segments: list, trend=None) -> str:
    """Generate tactical advice — now trend-aware."""
    idx = next(
        (i for i, s in enumerate(all_segments) if s.name == segment.name), 0
    )
    is_last = idx == len(all_segments) - 1
    is_first = idx == 0

    # Trend-aware tactics override generic advice
    if trend and trend.weeks_of_data >= 3:
        if trend.power_trend_per_week > 3:
            prefix = "You're on fire here lately. "
        elif trend.power_trend_per_week < -1:
            prefix = "Power is slipping — pace conservatively. "
        else:
            prefix = ""

        if is_last and segment.segment_type == "sprint":
            return prefix + "Final sprint — empty everything. You know this finish."
        if is_last:
            return prefix + "Last climb. Negative split — 95% first half, full gas to finish."
    else:
        prefix = ""

    if segment.estimated_duration_seconds <= 60:
        if is_last:
            return prefix + "Final selection — empty the tank. Full gas from the base."
        return prefix + "Short and steep — controlled intensity, don't overcook early segments."

    if segment.estimated_duration_seconds <= 120:
        if is_last:
            return prefix + "Settle into a rhythm for the first half, accelerate in the final third."
        return prefix + "Mark the leaders, respond to moves but don't initiate. Save matches."

    if is_first:
        return prefix + "Stay in the group. Don't burn a match on the first climb unless you're very strong here."
    if is_last:
        return prefix + "This is where it counts. Negative split — start at 95%, build to finish."

    return prefix + "Steady effort. Don't surge, don't coast. Keep W'bal above 50%."


def _generate_pre_ride_notes(
    rider: Rider, profile: RideProfile, budget: str, route_trend=None
) -> list[str]:
    """Generate overall pre-ride tactical notes — now with readiness context."""
    notes = []

    # Race readiness callout
    if route_trend and route_trend.race_readiness >= 65:
        notes.append(
            f"Race readiness: {route_trend.race_readiness:.0f}/100 — {route_trend.race_readiness_label}. "
            "Conditions are right for a strong ride."
        )
    elif route_trend and route_trend.race_readiness < 40:
        notes.append(
            f"Race readiness: {route_trend.race_readiness:.0f}/100 — {route_trend.race_readiness_label}. "
            "Consider treating this as a training ride, not a race."
        )

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

    # Trend-based insight
    if route_trend:
        improving = [
            t for t in route_trend.segment_trends if t.power_trend_per_week > 1
        ]
        declining = [
            t for t in route_trend.segment_trends if t.power_trend_per_week < -1
        ]
        if improving:
            names = ", ".join(t.segment_name for t in improving[:2])
            notes.append(f"Trending up on {names}. Push these segments today.")
        if declining:
            names = ", ".join(t.segment_name for t in declining[:2])
            notes.append(f"Power dipping on {names}. Pace conservatively or focus recovery.")

    if rider.w_per_kg > 4.0:
        notes.append(
            "Your W/kg is strong. Use the gradient to your advantage on the steeper pitches."
        )
    elif rider.w_per_kg < 3.0:
        notes.append(
            "Consider sitting in on the climbs and using your recovery ability between efforts."
        )

    return notes
