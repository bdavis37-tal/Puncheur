"""KOM attempt plan report generator.

Generates an HTML report for a KOM attempt plan, including target power,
pacing splits, W'bal projection, and warm-up protocol.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from puncheur.models.rider import Rider

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_kom_report(plan: dict, rider: Rider) -> str:
    """Generate an HTML KOM attempt plan report.

    Args:
        plan: KOM plan data from the strategy engine.
        rider: Rider profile.

    Returns:
        Complete HTML string for the report.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("kom_plan.html")

    context = {
        **plan,
        "rider_ftp": rider.ftp,
        "rider_weight": rider.weight_kg,
        "rider_wpkg": round(rider.w_per_kg, 2),
    }

    return template.render(**context)
