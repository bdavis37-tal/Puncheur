"""Post-ride debrief report generator.

Generates a comprehensive HTML report analyzing a completed ride against
tagged segments, including power metrics, W'bal tracking, fatigue analysis,
and pacing insights.
"""

from __future__ import annotations

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from puncheur.models.ride import Ride
from puncheur.models.rider import Rider
from puncheur.models.segment import SegmentMatch

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_template_env() -> Environment:
    """Create and return Jinja2 template environment."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _generate_power_svg(
    power: np.ndarray, width: int = 600, height: int = 100, ftp: float = 0
) -> str:
    """Generate an inline SVG power chart.

    Args:
        power: Array of power values.
        width: SVG width in pixels.
        height: SVG height in pixels.
        ftp: If > 0, draws a horizontal FTP reference line.

    Returns:
        SVG string for embedding in HTML.
    """
    if len(power) == 0:
        return ""

    # Downsample for performance
    if len(power) > width:
        step = len(power) // width
        power = power[::step]

    max_power = max(float(np.max(power)), 1.0)
    # Ensure FTP line is visible even if all power is above FTP
    if ftp > 0:
        max_power = max(max_power, ftp * 1.1)
    n = len(power)
    x_scale = width / max(n - 1, 1)
    y_scale = height / max_power

    # Build polyline points
    points = []
    for i, p in enumerate(power):
        x = i * x_scale
        y = height - (p * y_scale)
        points.append(f"{x:.1f},{y:.1f}")

    points_str = " ".join(points)

    # Filled area
    area_points = f"0,{height} {points_str} {width:.1f},{height}"

    # FTP reference line
    ftp_line = ""
    if ftp > 0:
        ftp_y = height - (ftp * y_scale)
        ftp_line = (
            f'  <line x1="0" y1="{ftp_y:.1f}" x2="{width}" y2="{ftp_y:.1f}" '
            f'stroke="#4ecdc4" stroke-width="1" stroke-dasharray="6,4" opacity="0.7"/>\n'
            f'  <text x="{width - 4}" y="{ftp_y - 4:.1f}" fill="#4ecdc4" '
            f'font-size="10" font-family="Inter,sans-serif" text-anchor="end" opacity="0.8">'
            f'FTP {int(ftp)}W</text>\n'
        )

    return f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:{height}px">
{ftp_line}  <polygon points="{area_points}" fill="rgba(255,107,53,0.3)" stroke="none"/>
  <polyline points="{points_str}" fill="none" stroke="#ff6b35" stroke-width="1.5"/>
</svg>"""


def _generate_wbal_svg(wbal: np.ndarray, w_prime: float, width: int = 600, height: int = 80) -> str:
    """Generate an inline SVG W'bal chart."""
    if len(wbal) == 0:
        return ""

    if len(wbal) > width:
        step = len(wbal) // width
        wbal = wbal[::step]

    n = len(wbal)
    x_scale = width / max(n - 1, 1)
    y_scale = height / max(w_prime, 1.0)

    points = []
    for i, w in enumerate(wbal):
        x = i * x_scale
        y = height - (w * y_scale)
        points.append(f"{x:.1f},{y:.1f}")

    points_str = " ".join(points)
    area_points = f"0,{height} {points_str} {width:.1f},{height}"

    return f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:{height}px">
  <polygon points="{area_points}" fill="rgba(78,205,196,0.3)" stroke="none"/>
  <polyline points="{points_str}" fill="none" stroke="#4ecdc4" stroke-width="1.5"/>
</svg>"""


def generate_debrief(
    ride: Ride,
    rider: Rider,
    power_curve: list[tuple[int, float]],
    wbal: np.ndarray,
    segment_matches: list[SegmentMatch],
) -> str:
    """Generate a complete post-ride debrief HTML report.

    Args:
        ride: The analyzed ride.
        rider: Rider profile.
        power_curve: Power duration curve data.
        wbal: W'bal array over the ride.
        segment_matches: Matched segment results.

    Returns:
        Complete HTML string for the report.
    """
    env = _get_template_env()
    template = env.get_template("debrief.html")

    np_val = ride.normalized_power()
    tss = ride.tss(rider.ftp)
    if_val = ride.intensity_factor(rider.ftp)

    # Key power benchmarks from curve
    benchmarks = {}
    for dur, label in [(5, "5s"), (60, "1min"), (300, "5min"), (1200, "20min")]:
        for d, p in power_curve:
            if d == dur:
                benchmarks[label] = round(p)
                break

    context = {
        "ride_name": ride.name or "Ride",
        "duration_min": round(ride.duration_seconds / 60),
        "avg_power": round(ride.avg_power),
        "normalized_power": round(np_val),
        "tss": round(tss),
        "intensity_factor": round(if_val, 2),
        "wbal_min": round(float(np.min(wbal))) if len(wbal) > 0 else 0,
        "power_svg": _generate_power_svg(ride.power_stream),
        "wbal_svg": _generate_wbal_svg(wbal, rider.w_prime),
        "benchmarks": benchmarks,
        "segments": [
            {
                "name": sm.segment.name,
                "avg_power": round(sm.avg_power),
                "max_power": round(sm.max_power),
                "np": round(sm.normalized_power),
                "duration": round(sm.duration_seconds),
                "avg_hr": round(sm.avg_heart_rate),
                "avg_cadence": round(sm.avg_cadence),
                "wbal_entry": round(sm.wbal_at_entry),
                "gradient": sm.segment.avg_gradient_pct,
                "elevation_gain": round(sm.elevation_gain, 1),
                "power_svg": _generate_power_svg(
                    sm.ride_data.power_stream if sm.ride_data else np.array([])
                ),
            }
            for sm in segment_matches
        ],
        "rider_ftp": rider.ftp,
        "rider_w_prime": rider.w_prime,
    }

    return template.render(**context)
