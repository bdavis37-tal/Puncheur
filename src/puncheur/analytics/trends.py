"""Segment trend analysis — ride-over-ride progression tracking.

Computes linear regression on weekly segment performance to answer:
"Am I getting faster?" and "What should I target next week?"

This is the data Strava doesn't show you. They have leaderboards (ranking)
but not trajectories (direction). We tell you where you're headed.

Also includes race readiness scoring — a composite metric that combines
fitness, form, segment trends, and consistency to answer the only question
that matters before Tuesday: "Am I ready?"
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from puncheur.config import get_rides_dir


@dataclass
class SegmentTrend:
    """Trend analysis for a single segment across multiple rides.

    Attributes:
        segment_name: Name of the segment.
        weeks_of_data: Number of weeks with data.
        power_trend_per_week: Linear regression slope (watts/week). Positive = improving.
        time_trend_per_week: Linear regression slope (seconds/week). Negative = faster.
        current_avg_power: Most recent average power.
        projected_power: Projected power for next week based on trend.
        best_power: All-time best average power on this segment.
        best_date: Date of the best effort.
        consistency_pct: Percentage of weeks with data.
        r_squared: Goodness of fit for power trend.
    """

    segment_name: str
    weeks_of_data: int
    power_trend_per_week: float
    time_trend_per_week: float
    current_avg_power: float
    projected_power: float
    best_power: float
    best_date: str
    consistency_pct: float
    r_squared: float

    @property
    def is_improving(self) -> bool:
        return self.power_trend_per_week > 0.5 and self.r_squared > 0.3

    @property
    def trend_description(self) -> str:
        rate = self.power_trend_per_week
        if self.weeks_of_data < 3:
            return "Need 3+ weeks of data"
        if rate > 3:
            return f"+{rate:.1f}W/week — strong gains"
        if rate > 1:
            return f"+{rate:.1f}W/week — steady improvement"
        if rate > 0:
            return f"+{rate:.1f}W/week — slight gains"
        if rate > -1:
            return "Holding steady"
        return f"{rate:.1f}W/week — check recovery"


@dataclass
class RouteTrend:
    """Trend analysis for an entire route."""

    route_name: str
    segment_trends: list[SegmentTrend]
    overall_np_trend: float
    race_readiness: float
    race_readiness_label: str
    projected_tss: float


def save_ride_result(
    route_name: str,
    ride_date: str,
    avg_power: float,
    normalized_power: float,
    tss: float,
    segment_results: list[dict] | None = None,
) -> None:
    """Save a ride result to the history file for a route."""
    rides_dir = get_rides_dir()
    slug = route_name.lower().replace(" ", "_")
    history_file = rides_dir / f"{slug}_history.json"

    history: list[dict] = []
    if history_file.exists():
        history = json.loads(history_file.read_text(encoding="utf-8"))

    entry = {
        "date": ride_date,
        "avg_power": avg_power,
        "np": normalized_power,
        "tss": tss,
        "segments": segment_results or [],
    }
    history.append(entry)

    history_file.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def load_route_history(route_name: str) -> list[dict]:
    """Load ride history for a route, sorted by date."""
    rides_dir = get_rides_dir()
    slug = route_name.lower().replace(" ", "_")
    history_file = rides_dir / f"{slug}_history.json"

    if not history_file.exists():
        return []

    history = json.loads(history_file.read_text(encoding="utf-8"))
    return sorted(history, key=lambda x: x.get("date", ""))


def compute_trends(history: list[dict]) -> dict:
    """Compute basic trend metrics from ride history (legacy API)."""
    if len(history) < 2:
        return {"trend": "insufficient_data", "rides": len(history)}

    recent = history[-3:]
    older = history[:-3] if len(history) > 3 else history[:1]

    recent_avg_power = sum(r.get("avg_power", 0) for r in recent) / len(recent)
    older_avg_power = sum(r.get("avg_power", 0) for r in older) / len(older)

    power_change_pct = 0.0
    if older_avg_power > 0:
        power_change_pct = ((recent_avg_power - older_avg_power) / older_avg_power) * 100

    if power_change_pct > 3:
        trend = "improving"
    elif power_change_pct < -3:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "rides": len(history),
        "recent_avg_power": recent_avg_power,
        "older_avg_power": older_avg_power,
        "power_change_pct": power_change_pct,
    }


def analyze_segment_trends(route_slug: str) -> list[SegmentTrend]:
    """Compute per-segment trends from ride history using linear regression."""
    history = load_route_history(route_slug)
    if not history:
        return []

    segment_data: dict[str, list[dict]] = {}
    for entry in history:
        for seg in entry.get("segments", []):
            name = seg["name"]
            if name not in segment_data:
                segment_data[name] = []
            segment_data[name].append({
                "date": entry["date"],
                "avg_power": seg["avg_power"],
                "duration": seg.get("duration", 0),
            })

    return [_compute_segment_trend(name, pts) for name, pts in segment_data.items()]


def analyze_route_trend(
    route_slug: str,
    fitness_ctl: float = 0,
    fitness_tsb: float = 0,
) -> RouteTrend:
    """Full route trend analysis including race readiness."""
    segment_trends = analyze_segment_trends(route_slug)
    history = load_route_history(route_slug)

    # Overall NP trend
    np_trend = 0.0
    if len(history) >= 3:
        weeks = np.arange(len(history), dtype=float)
        nps = np.array(
            [h.get("np", h.get("avg_power", 0)) for h in history], dtype=float
        )
        if np.std(nps) > 0:
            coeffs = np.polyfit(weeks, nps, 1)
            np_trend = float(coeffs[0])

    projected_tss = 0.0
    if history:
        recent_tss = [h.get("tss", 0) for h in history[-4:]]
        projected_tss = float(np.mean(recent_tss)) if recent_tss else 0.0

    readiness, label = _compute_race_readiness(
        segment_trends, fitness_ctl, fitness_tsb
    )

    return RouteTrend(
        route_name=route_slug,
        segment_trends=segment_trends,
        overall_np_trend=round(np_trend, 2),
        race_readiness=readiness,
        race_readiness_label=label,
        projected_tss=round(projected_tss, 1),
    )


def _compute_segment_trend(name: str, data_points: list[dict]) -> SegmentTrend:
    """Compute trend for a single segment using linear regression."""
    data_points.sort(key=lambda d: d["date"])
    n = len(data_points)

    powers = np.array([d["avg_power"] for d in data_points], dtype=float)
    durations = np.array([d.get("duration", 0) for d in data_points], dtype=float)
    weeks = np.arange(n, dtype=float)

    # Power trend
    power_slope = 0.0
    r_squared = 0.0
    if n >= 3 and np.std(powers) > 0:
        coeffs = np.polyfit(weeks, powers, 1)
        power_slope = float(coeffs[0])
        predicted = np.polyval(coeffs, weeks)
        ss_res = float(np.sum((powers - predicted) ** 2))
        ss_tot = float(np.sum((powers - np.mean(powers)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Time trend
    time_slope = 0.0
    if n >= 3:
        valid = durations > 0
        if np.sum(valid) >= 3 and np.std(durations[valid]) > 0:
            coeffs_t = np.polyfit(weeks[valid], durations[valid], 1)
            time_slope = float(coeffs_t[0])

    # Best effort
    best_idx = int(np.argmax(powers))

    return SegmentTrend(
        segment_name=name,
        weeks_of_data=n,
        power_trend_per_week=round(power_slope, 2),
        time_trend_per_week=round(time_slope, 2),
        current_avg_power=round(float(powers[-1]), 1),
        projected_power=round(float(powers[-1]) + power_slope, 1),
        best_power=round(float(powers[best_idx]), 1),
        best_date=data_points[best_idx]["date"],
        consistency_pct=round(min(100.0, (n / 8.0) * 100), 1),
        r_squared=round(r_squared, 3),
    )


def _compute_race_readiness(
    segment_trends: list[SegmentTrend],
    fitness_ctl: float,
    fitness_tsb: float,
) -> tuple[float, str]:
    """Compute 0-100 race readiness score.

    Components:
    - Fitness (CTL): 30% — are you trained?
    - Form (TSB): 30% — are you fresh?
    - Segment trends: 25% — are you improving?
    - Consistency: 15% — are you riding the route?
    """
    fitness_score = min(30.0, (fitness_ctl / 60.0) * 30.0)

    if fitness_tsb > 15:
        form_score = 25.0
    elif fitness_tsb > 5:
        form_score = 30.0
    elif fitness_tsb > -5:
        form_score = 22.0
    elif fitness_tsb > -15:
        form_score = 12.0
    else:
        form_score = 5.0

    trend_score = 0.0
    if segment_trends:
        improving = sum(1 for t in segment_trends if t.power_trend_per_week > 0.5)
        trend_score = (improving / len(segment_trends)) * 25.0

    consistency_score = 0.0
    if segment_trends:
        avg_c = np.mean([t.consistency_pct for t in segment_trends])
        consistency_score = (avg_c / 100.0) * 15.0

    total = round(min(100.0, fitness_score + form_score + trend_score + consistency_score), 1)

    if total >= 80:
        label = "Peak form — go win something"
    elif total >= 65:
        label = "Race ready — you're sharp"
    elif total >= 50:
        label = "Good to go — solid shape"
    elif total >= 35:
        label = "Moderate — manage expectations"
    else:
        label = "Building — focus on the process"

    return total, label
