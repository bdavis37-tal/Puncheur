"""Pre-ride playbook report generator.

Generates an HTML report with tactical recommendations, segment targets,
and match budget visualization for an upcoming ride.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from puncheur.models.ride_profile import RideProfile
from puncheur.models.rider import Rider

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_playbook_report(
    playbook_data: dict,
    rider: Rider,
    profile: RideProfile,
) -> str:
    """Generate an HTML playbook report.

    Args:
        playbook_data: Playbook data from the strategy engine.
        rider: Rider profile.
        profile: Ride profile with segments.

    Returns:
        Complete HTML string for the report.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("playbook.html")

    # Generate W' budget bar SVG
    budget = playbook_data.get("match_budget", {})
    budget_pct = budget.get("budget_pct", 0)
    budget_svg = _generate_budget_bar(budget_pct)

    context = {
        **playbook_data,
        "budget_svg": budget_svg,
        "rider_ftp": rider.ftp,
        "rider_weight": rider.weight_kg,
        "rider_wpkg": round(rider.w_per_kg, 2),
    }

    return template.render(**context)


def _generate_budget_bar(pct: float, width: int = 400, height: int = 30) -> str:
    """Generate an SVG bar showing W' budget usage."""
    fill_width = min(pct / 100 * width, width)

    if pct < 70:
        color = "#4ecdc4"
    elif pct < 90:
        color = "#f9c74f"
    else:
        color = "#ff6b35"

    return f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{width}px;height:{height}px">
  <rect x="0" y="0" width="{width}" height="{height}" fill="#2a2a3e" rx="4"/>
  <rect x="0" y="0" width="{fill_width:.1f}" height="{height}" fill="{color}" rx="4"/>
  <text x="{width/2}" y="{height/2 + 5}" text-anchor="middle" fill="white" font-size="14" font-family="monospace">{pct:.0f}% W' budget</text>
</svg>"""
