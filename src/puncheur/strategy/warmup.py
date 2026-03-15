"""Warm-up protocols by effort duration.

Generates structured warm-up plans based on established sports science.
Each protocol is tailored to the physiological demands of the target
effort — short anaerobic efforts need neuromuscular priming, longer
threshold efforts need progressive cardiovascular preparation.
"""

from __future__ import annotations

from puncheur.models.rider import Rider


def get_warmup_protocol(rider: Rider, effort_duration_seconds: int) -> dict:
    """Generate a warm-up protocol for a target effort duration.

    Args:
        rider: Rider profile for zone-based power targets.
        effort_duration_seconds: Duration of the target effort in seconds.

    Returns:
        Dict containing warm-up steps with zone, power, and duration.
    """
    if effort_duration_seconds <= 60:
        return _warmup_1min(rider)
    elif effort_duration_seconds <= 120:
        return _warmup_2min(rider)
    elif effort_duration_seconds <= 300:
        return _warmup_5min(rider)
    else:
        return _warmup_20min(rider)


def _zone_power(rider: Rider, zone: str) -> str:
    """Get power range string for a zone."""
    zones = rider.power_zones
    if zone in zones:
        return f"{zones[zone][0]}-{zones[zone][1]}W"
    return "—"


def _warmup_1min(rider: Rider) -> dict:
    """Warm-up protocol for 1-minute (neuromuscular/anaerobic) efforts.

    Total: ~30 minutes. Includes neuromuscular priming sprint.
    """
    return {
        "effort_type": "1-minute (anaerobic/neuromuscular)",
        "total_minutes": 30,
        "steps": [
            {
                "zone": "Z1-Z2",
                "duration_min": 15,
                "power": _zone_power(rider, "z2_endurance"),
                "description": "15 min easy spinning — gradually increase cadence",
            },
            {
                "zone": "Z3",
                "duration_min": 2,
                "power": _zone_power(rider, "z3_tempo"),
                "description": "2x 1 min at tempo with 1 min rest between",
            },
            {
                "zone": "Z5",
                "duration_min": 0.5,
                "power": _zone_power(rider, "z5_vo2max"),
                "description": "1x 30 sec at VO2max — blow out the cobwebs",
            },
            {
                "zone": "Z1",
                "duration_min": 2,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "2 min easy recovery",
            },
            {
                "zone": "Z1-Z2",
                "duration_min": 5,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "5 min easy spinning",
            },
            {
                "zone": "Z7",
                "duration_min": 0.17,
                "power": "MAX",
                "description": "1x 10 sec sprint — prime the neuromuscular system",
            },
            {
                "zone": "Z1",
                "duration_min": 4,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "3-5 min easy spinning before the effort",
            },
        ],
    }


def _warmup_2min(rider: Rider) -> dict:
    """Warm-up protocol for 2-minute (VO2max) efforts.

    Total: ~35 minutes. Progressive warm-up with threshold openers.
    """
    return {
        "effort_type": "2-minute (VO2max)",
        "total_minutes": 35,
        "steps": [
            {
                "zone": "Z1→Z2→Z3",
                "duration_min": 15,
                "power": _zone_power(rider, "z2_endurance"),
                "description": "15 min progressive warm-up: Z1 → Z2 → Z3",
            },
            {
                "zone": "Z4",
                "duration_min": 6,
                "power": _zone_power(rider, "z4_threshold"),
                "description": "3x 1 min at threshold with 1 min rest between",
            },
            {
                "zone": "Z5",
                "duration_min": 0.5,
                "power": _zone_power(rider, "z5_vo2max"),
                "description": "1x 30 sec at VO2max — open up the engine",
            },
            {
                "zone": "Z1",
                "duration_min": 3,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "3 min easy recovery",
            },
            {
                "zone": "Z1-Z2",
                "duration_min": 5,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "5 min easy spinning before the effort",
            },
        ],
    }


def _warmup_5min(rider: Rider) -> dict:
    """Warm-up protocol for 5-minute (sustained VO2max) efforts.

    Total: ~40 minutes.
    """
    return {
        "effort_type": "5-minute (sustained VO2max)",
        "total_minutes": 40,
        "steps": [
            {
                "zone": "Z1→Z2→Z3",
                "duration_min": 20,
                "power": _zone_power(rider, "z2_endurance"),
                "description": "20 min progressive warm-up: Z1 → Z2 → Z3",
            },
            {
                "zone": "Z4",
                "duration_min": 8,
                "power": _zone_power(rider, "z4_threshold"),
                "description": "2x 2 min at threshold with 2 min rest between",
            },
            {
                "zone": "Z5",
                "duration_min": 1,
                "power": _zone_power(rider, "z5_vo2max"),
                "description": "1x 1 min at VO2max — high-end activation",
            },
            {
                "zone": "Z1",
                "duration_min": 3,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "3 min easy recovery",
            },
            {
                "zone": "Z1-Z2",
                "duration_min": 5,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "5 min easy spinning before the effort",
            },
        ],
    }


def _warmup_20min(rider: Rider) -> dict:
    """Warm-up protocol for 20-minute (threshold/sub-threshold) efforts.

    Total: ~50 minutes. Extended progressive warm-up.
    """
    return {
        "effort_type": "20-minute (threshold)",
        "total_minutes": 50,
        "steps": [
            {
                "zone": "Z1→Z2→Z3",
                "duration_min": 20,
                "power": _zone_power(rider, "z2_endurance"),
                "description": "20 min progressive warm-up: Z1 → Z2 → Z3",
            },
            {
                "zone": "Z3",
                "duration_min": 14,
                "power": _zone_power(rider, "z3_tempo"),
                "description": "2x 5 min at tempo with 2 min rest between",
            },
            {
                "zone": "Z4",
                "duration_min": 2,
                "power": _zone_power(rider, "z4_threshold"),
                "description": "1x 2 min at threshold — feel the burn, then back off",
            },
            {
                "zone": "Z1",
                "duration_min": 5,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "5 min easy recovery",
            },
            {
                "zone": "Z1-Z2",
                "duration_min": 5,
                "power": _zone_power(rider, "z1_recovery"),
                "description": "5 min easy spinning before the effort",
            },
        ],
    }
