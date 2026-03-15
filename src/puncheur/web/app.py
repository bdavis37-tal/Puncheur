"""Flask application for Puncheur web UI.

Serves the dashboard, handles file uploads, and renders analysis views.
Designed to run locally — no authentication, no cloud, your data stays yours.
"""

from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from threading import Timer

import numpy as np
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from puncheur.config import get_data_dir, get_rider_profile_path, get_routes_dir

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = "puncheur-local-session-key"

# Store uploads temporarily
UPLOAD_FOLDER = tempfile.mkdtemp(prefix="puncheur_")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max


def _rider_exists() -> bool:
    """Check if a rider profile has been set up."""
    return get_rider_profile_path().exists()


def _load_rider():
    """Load the rider profile."""
    from puncheur.models.rider import Rider

    return Rider.load()


def _list_routes() -> list[dict]:
    """List all saved routes."""
    routes_dir = get_routes_dir()
    routes = []
    for f in sorted(routes_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        routes.append({
            "name": data.get("name", f.stem),
            "slug": f.stem,
            "segments": len(data.get("segments", [])),
            "gpx_file": data.get("gpx_file", ""),
        })
    return routes


# ── Routes ────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Dashboard — the home screen."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    rider = _load_rider()
    routes = _list_routes()

    # Load fitness data
    from puncheur.analytics.fitness import compute_fitness
    from puncheur.demo import is_demo_available

    fitness = compute_fitness()

    return render_template(
        "dashboard.html",
        rider=rider,
        routes=routes,
        fitness=fitness,
        demo_ride_available=is_demo_available(),
    )


@app.route("/setup", methods=["GET", "POST"])
def setup():
    """Guided onboarding wizard."""
    if request.method == "POST":
        from puncheur.config import coggan_power_zones
        from puncheur.models.rider import Rider

        name = request.form.get("name", "").strip()
        ftp = int(request.form.get("ftp", 200))
        weight = float(request.form.get("weight", 75.0))
        experience = request.form.get("experience", "intermediate")

        # Smart W' defaults based on experience level
        w_prime_defaults = {
            "beginner": 15000,
            "intermediate": 20000,
            "advanced": 22000,
            "elite": 25000,
        }
        w_prime = w_prime_defaults.get(experience, 20000)

        max_hr = int(request.form.get("max_hr", 0))
        if max_hr == 0:
            # Estimate max HR from age if provided, otherwise use 185
            age = int(request.form.get("age", 0))
            max_hr = (220 - age) if age > 0 else 185

        rider = Rider(
            name=name,
            ftp=ftp,
            weight_kg=weight,
            power_zones=coggan_power_zones(ftp),
            max_heart_rate=max_hr,
            w_prime=w_prime,
        )
        rider.save()
        return redirect(url_for("index"))

    return render_template("setup.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Drag-and-drop ride upload + analysis."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected")
            return redirect(url_for("upload"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected")
            return redirect(url_for("upload"))

        if not file.filename.lower().endswith(".fit"):
            flash("Please upload a .fit file from your cycling computer")
            return redirect(url_for("upload"))

        # Save uploaded file
        filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Get optional route
        route_name = request.form.get("route", "")

        return redirect(url_for("analyze", filepath=filepath, route=route_name))

    routes = _list_routes()
    return render_template("upload.html", routes=routes)


@app.route("/analyze")
def analyze():
    """Ride analysis view — the post-ride debrief."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    filepath = request.args.get("filepath", "")
    route_name = request.args.get("route", "")

    if not filepath or not Path(filepath).exists():
        flash("Ride file not found")
        return redirect(url_for("upload"))

    rider = _load_rider()

    # Parse the ride
    from puncheur.parsers.fit_parser import parse_fit

    try:
        ride = parse_fit(filepath)
    except Exception as e:
        flash(f"Could not read ride file: {e}")
        return redirect(url_for("upload"))

    if not ride.has_power:
        flash("This ride file doesn't contain power data. Are you using a power meter?")
        return redirect(url_for("upload"))

    # Run analytics
    from puncheur.analytics.matchbook import compute_wbal, count_matches_burned
    from puncheur.analytics.power_curve import duration_buckets, power_duration_curve
    from puncheur.analytics.fatigue import analyze_ride_fatigue
    from puncheur.reporting.debrief import _generate_power_svg, _generate_wbal_svg

    pdc = power_duration_curve(ride)
    benchmarks = duration_buckets(pdc)
    np_val = ride.normalized_power()
    tss = ride.tss(rider.ftp)
    if_val = ride.intensity_factor(rider.ftp)
    wbal = compute_wbal(ride.power_stream, rider.ftp, rider.w_prime)
    matches = count_matches_burned(ride.power_stream, rider.ftp)
    fatigue = analyze_ride_fatigue(ride)

    power_svg = _generate_power_svg(ride.power_stream, width=800, height=120)
    wbal_svg = _generate_wbal_svg(wbal, rider.w_prime, width=800, height=100)

    # Segment matching
    segment_matches = []
    if route_name:
        try:
            from puncheur.analytics.segment_matcher import match_segments
            from puncheur.models.ride_profile import RideProfile

            profile = RideProfile.load(route_name)
            segment_matches = match_segments(ride, profile)
        except Exception:
            pass

    # Build segment data for template
    segments_data = []
    for sm in segment_matches:
        seg_power_svg = ""
        if sm.ride_data:
            seg_power_svg = _generate_power_svg(sm.ride_data.power_stream, width=600, height=80)
        segments_data.append({
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
            "power_svg": seg_power_svg,
        })

    return render_template(
        "analyze.html",
        ride=ride,
        rider=rider,
        np=round(np_val),
        tss=round(tss),
        intensity_factor=round(if_val, 2),
        wbal_min=round(float(np.min(wbal))) if len(wbal) > 0 else 0,
        matches_burned=matches,
        benchmarks=benchmarks,
        fatigue=fatigue,
        power_svg=power_svg,
        wbal_svg=wbal_svg,
        segments=segments_data,
    )


@app.route("/playbook/<route_slug>")
def playbook(route_slug):
    """Pre-ride playbook view."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    rider = _load_rider()

    try:
        from puncheur.models.ride_profile import RideProfile
        from puncheur.strategy.playbook import generate_playbook

        profile = RideProfile.load(route_slug)
        playbook_data = generate_playbook(rider, profile)
    except FileNotFoundError:
        flash(f"Route '{route_slug}' not found")
        return redirect(url_for("index"))

    return render_template(
        "playbook.html",
        rider=rider,
        playbook=playbook_data,
        route=profile,
    )


@app.route("/kom", methods=["GET", "POST"])
def kom():
    """KOM attempt planner."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    rider = _load_rider()
    plan = None

    if request.method == "POST":
        from puncheur.strategy.kom_planner import plan_kom_attempt

        segment_name = request.form.get("segment", "Target Segment")
        duration = int(request.form.get("duration", 60))
        plan = plan_kom_attempt(rider, segment_name, duration)

    return render_template("kom.html", rider=rider, plan=plan)


@app.route("/warmup/<int:duration>")
def warmup(duration):
    """Warm-up protocol view."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    rider = _load_rider()

    from puncheur.strategy.warmup import get_warmup_protocol

    protocol = get_warmup_protocol(rider, duration)
    return render_template("warmup.html", rider=rider, protocol=protocol, duration=duration)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Profile settings."""
    if not _rider_exists():
        return redirect(url_for("setup"))

    rider = _load_rider()

    if request.method == "POST":
        from puncheur.config import coggan_power_zones

        rider.name = request.form.get("name", rider.name)
        rider.ftp = int(request.form.get("ftp", rider.ftp))
        rider.weight_kg = float(request.form.get("weight", rider.weight_kg))
        rider.max_heart_rate = int(request.form.get("max_hr", rider.max_heart_rate))
        rider.w_prime = int(request.form.get("w_prime", rider.w_prime))
        rider.power_zones = coggan_power_zones(rider.ftp)
        rider.save()
        flash("Profile updated")
        return redirect(url_for("settings"))

    return render_template("settings.html", rider=rider)


@app.route("/demo")
def demo_setup():
    """Set up demo mode with pre-loaded data and redirect to dashboard."""
    from puncheur.demo import setup_demo

    setup_demo()
    flash("Demo loaded — meet Brendan, 265W FTP, south Charlotte group rider.")
    return redirect(url_for("index"))


@app.route("/demo/ride")
def demo_ride():
    """Analyze the pre-loaded demo ride."""
    from puncheur.demo import is_demo_available, load_demo_ride

    if not is_demo_available():
        return redirect(url_for("demo_setup"))

    rider = _load_rider()
    ride = load_demo_ride()

    from puncheur.analytics.fatigue import analyze_ride_fatigue
    from puncheur.analytics.matchbook import compute_wbal, count_matches_burned
    from puncheur.analytics.pacing import analyze_pre_segment_pacing
    from puncheur.analytics.power_curve import duration_buckets, power_duration_curve
    from puncheur.analytics.segment_matcher import match_segments
    from puncheur.models.ride_profile import RideProfile
    from puncheur.reporting.debrief import _generate_power_svg, _generate_wbal_svg

    pdc = power_duration_curve(ride)
    benchmarks = duration_buckets(pdc)
    np_val = ride.normalized_power()
    tss = ride.tss(rider.ftp)
    if_val = ride.intensity_factor(rider.ftp)
    wbal = compute_wbal(ride.power_stream, rider.ftp, rider.w_prime)
    matches = count_matches_burned(ride.power_stream, rider.ftp)
    fatigue = analyze_ride_fatigue(ride)

    power_svg = _generate_power_svg(ride.power_stream, width=800, height=120)
    wbal_svg = _generate_wbal_svg(wbal, rider.w_prime, width=800, height=100)

    # Segment matching against the Tuesday route
    segment_matches = []
    pacing_insights = []
    try:
        profile = RideProfile.load("tuesday_group_ride")
        segment_matches = match_segments(ride, profile, tolerance_m=80)

        # Compute W'bal at each segment entry
        for sm in segment_matches:
            # Find the index in the ride closest to this segment's start
            for idx, pt in enumerate(ride.points):
                if pt.timestamp >= sm.start_time:
                    sm.wbal_at_entry = float(wbal[idx]) if idx < len(wbal) else 0.0
                    break

            # Pacing analysis
            pa = analyze_pre_segment_pacing(sm, ride.avg_power, rider)
            pacing_insights.append(pa)
    except Exception:
        pass

    # Build segment data for template
    segments_data = []
    for i, sm in enumerate(segment_matches):
        seg_power_svg = ""
        if sm.ride_data:
            seg_power_svg = _generate_power_svg(sm.ride_data.power_stream, width=600, height=80)

        pacing_note = ""
        if i < len(pacing_insights):
            pacing_note = pacing_insights[i].recommendation

        segments_data.append({
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
            "power_svg": seg_power_svg,
            "pacing_note": pacing_note,
            "notes": sm.segment.notes,
        })

    return render_template(
        "analyze.html",
        ride=ride,
        rider=rider,
        np=round(np_val),
        tss=round(tss),
        intensity_factor=round(if_val, 2),
        wbal_min=round(float(np.min(wbal))) if len(wbal) > 0 else 0,
        matches_burned=matches,
        benchmarks=benchmarks,
        fatigue=fatigue,
        power_svg=power_svg,
        wbal_svg=wbal_svg,
        segments=segments_data,
        is_demo=True,
    )


@app.route("/api/fitness")
def api_fitness():
    """JSON API for fitness data (for AJAX updates)."""
    from puncheur.analytics.fitness import compute_fitness

    return jsonify(compute_fitness())


def run_app(
    host: str = "127.0.0.1",
    port: int = 5050,
    open_browser: bool = True,
    demo: bool = False,
) -> None:
    """Launch the Puncheur web app.

    Args:
        host: Host to bind to.
        port: Port to run on.
        open_browser: Whether to automatically open the browser.
        demo: Whether to set up demo data and open demo ride automatically.
    """
    if demo:
        from puncheur.demo import setup_demo

        setup_demo()

        url = f"http://{host}:{port}/demo/ride"
    else:
        url = f"http://{host}:{port}"

    if open_browser:
        Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=False)
