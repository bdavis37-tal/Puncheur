"""Demo mode — pre-loaded data for showcasing Puncheur.

Creates a realistic rider profile, Charlotte-area route with tagged segments,
synthetic ride history, and a sample ride with realistic power/HR/cadence data.
Everything a sales demo needs to look convincing without a real FIT file.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from puncheur.config import get_data_dir, get_rides_dir, get_routes_dir, save_json
from puncheur.models.ride import Ride, RidePoint
from puncheur.models.rider import Rider
from puncheur.models.ride_profile import RideProfile
from puncheur.models.segment import Segment


def setup_demo() -> None:
    """Set up complete demo data: rider, route, fitness history, and sample ride.

    Creates a believable 265 FTP rider who's been training consistently
    for 8 weeks on a Tuesday group ride in south Charlotte.
    """
    _create_demo_rider()
    _create_demo_route()
    _create_demo_fitness_history()
    _create_demo_ride_history()
    _create_demo_ride()


def _create_demo_rider() -> None:
    """Create Brendan — a 265 FTP competitive group rider."""
    from puncheur.config import coggan_power_zones

    rider = Rider(
        name="Brendan",
        ftp=265,
        weight_kg=79.0,
        power_zones=coggan_power_zones(265),
        max_heart_rate=183,
        w_prime=19500,
    )
    rider.save()


def _create_demo_route() -> None:
    """Create the Tuesday Group Ride route with 4 tagged segments.

    Based on south Charlotte rolling terrain — Rea Road, Sardis Road,
    Providence Road, and Colony Road areas. Short punchy climbs typical
    of the Charlotte group ride scene.
    """
    # Write GPX file
    gpx_content = _generate_charlotte_gpx()
    routes_dir = get_routes_dir()
    gpx_path = routes_dir / "tuesday_group_ride.gpx"
    gpx_path.write_text(gpx_content, encoding="utf-8")

    profile = RideProfile(
        name="Tuesday Group Ride",
        gpx_file=str(gpx_path),
        segments=[
            Segment(
                name="Rea Road Kicker",
                start_lat=35.1082,
                start_lon=-80.8152,
                end_lat=35.1058,
                end_lon=-80.8128,
                segment_type="climb",
                estimated_duration_seconds=75,
                avg_gradient_pct=5.8,
                notes="First punch — group starts to split here. Attack usually goes from the base.",
            ),
            Segment(
                name="Sardis Lane Drag",
                start_lat=35.1145,
                start_lon=-80.7928,
                end_lat=35.1178,
                end_lon=-80.7892,
                segment_type="climb",
                estimated_duration_seconds=110,
                avg_gradient_pct=4.5,
                notes="Long false flat that hurts. Attacks come in the final third.",
            ),
            Segment(
                name="Providence Road Wall",
                start_lat=35.1312,
                start_lon=-80.7985,
                end_lat=35.1338,
                end_lon=-80.7968,
                segment_type="climb",
                estimated_duration_seconds=55,
                avg_gradient_pct=7.2,
                notes="Short and steep. The selection. If you're going to attack, this is it.",
            ),
            Segment(
                name="Colony Road Sprint",
                start_lat=35.1245,
                start_lon=-80.8215,
                end_lat=35.1232,
                end_lon=-80.8178,
                segment_type="sprint",
                estimated_duration_seconds=35,
                avg_gradient_pct=1.2,
                notes="Flat finish sprint for whoever's left. Leadout starts at the speed limit sign.",
            ),
        ],
    )
    profile.save()

    # Also create a second route for variety
    _create_saturday_route()


def _create_saturday_route() -> None:
    """Create a Saturday long ride route."""
    profile = RideProfile(
        name="Saturday Coffee Ride",
        gpx_file="",
        segments=[
            Segment(
                name="Marvin Road Roller",
                start_lat=35.0812,
                start_lon=-80.7542,
                end_lat=35.0845,
                end_lon=-80.7510,
                segment_type="climb",
                estimated_duration_seconds=95,
                avg_gradient_pct=4.0,
                notes="Steady grind on the way to Waxhaw. Keep it Z3.",
            ),
            Segment(
                name="Waxhaw Bypass Climb",
                start_lat=34.9378,
                start_lon=-80.7412,
                end_lat=34.9410,
                end_lon=-80.7385,
                segment_type="climb",
                estimated_duration_seconds=130,
                avg_gradient_pct=5.5,
                notes="Rolling terrain — don't surge on the false flats.",
            ),
        ],
    )
    profile.save()


def _create_demo_fitness_history() -> None:
    """Create 8 weeks of daily TSS data for a realistic fitness profile.

    Simulates a rider doing:
    - Tuesday group ride (TSS ~85)
    - Thursday intervals (TSS ~70)
    - Saturday long ride (TSS ~120)
    - Occasional Monday recovery (TSS ~30)
    - Rest days with TSS 0
    """
    fitness_path = get_data_dir() / "fitness_log.json"
    log: dict[str, float] = {}

    today = date.today()
    start = today - timedelta(days=56)  # 8 weeks back

    rng = random.Random(42)  # Reproducible

    current = start
    while current <= today:
        dow = current.weekday()  # 0=Mon, 1=Tue, 2=Wed...
        tss = 0.0

        if dow == 1:  # Tuesday — group ride
            tss = rng.gauss(85, 10)
        elif dow == 3:  # Thursday — intervals
            tss = rng.gauss(70, 12)
        elif dow == 5:  # Saturday — long ride
            tss = rng.gauss(120, 15)
        elif dow == 0 and rng.random() > 0.4:  # Monday — sometimes recovery
            tss = rng.gauss(30, 8)
        elif dow == 6 and rng.random() > 0.6:  # Sunday — sometimes easy
            tss = rng.gauss(40, 10)

        if tss > 0:
            log[current.isoformat()] = round(max(15, tss), 1)

        current += timedelta(days=1)

    fitness_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")


def _create_demo_ride_history() -> None:
    """Create ride-over-ride history for the Tuesday route.

    Shows 6 weeks of gradual improvement — power slowly increasing,
    times slowly decreasing. Realistic progression.
    """
    rides_dir = get_rides_dir()
    slug = "tuesday_group_ride"
    history_file = rides_dir / f"{slug}_history.json"

    history = []
    today = date.today()
    rng = random.Random(42)

    for week in range(7, -1, -1):
        ride_date = today - timedelta(days=week * 7 + today.weekday() - 1)  # Most recent Tuesday
        if ride_date > today:
            continue

        # Gradual improvement: avg power increases ~1W/week
        base_power = 195 + (8 - week) * 1.2
        avg_power = round(base_power + rng.gauss(0, 3), 1)
        np_power = round(avg_power * rng.uniform(1.05, 1.12), 1)
        tss = round(rng.gauss(85, 8), 1)

        history.append({
            "date": ride_date.isoformat(),
            "avg_power": avg_power,
            "np": np_power,
            "tss": tss,
            "segments": [
                {
                    "name": "Rea Road Kicker",
                    "avg_power": round(310 + (8 - week) * 2 + rng.gauss(0, 8)),
                    "duration": round(75 - (8 - week) * 0.5 + rng.gauss(0, 2), 1),
                },
                {
                    "name": "Sardis Lane Drag",
                    "avg_power": round(295 + (8 - week) * 1.5 + rng.gauss(0, 6)),
                    "duration": round(110 - (8 - week) * 0.8 + rng.gauss(0, 3), 1),
                },
                {
                    "name": "Providence Road Wall",
                    "avg_power": round(340 + (8 - week) * 2.5 + rng.gauss(0, 10)),
                    "duration": round(55 - (8 - week) * 0.3 + rng.gauss(0, 1.5), 1),
                },
                {
                    "name": "Colony Road Sprint",
                    "avg_power": round(520 + (8 - week) * 3 + rng.gauss(0, 20)),
                    "duration": round(35 - (8 - week) * 0.2 + rng.gauss(0, 1), 1),
                },
            ],
        })

    history_file.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def _create_demo_ride() -> None:
    """Create a synthetic but realistic 75-minute group ride.

    Power profile of a competitive group ride with 4 tagged efforts:
    - 20 min warm-up in the pack (Z2, ~175W)
    - Rea Road Kicker (75s at ~315W, HR spikes to 172)
    - Recovery section (8 min, ~155W)
    - Sardis Lane Drag (110s at ~298W, HR 168)
    - Recovery section (10 min, ~160W)
    - Providence Road Wall (55s at ~355W, HR 178, cadence drops)
    - Recovery coast (5 min, ~140W)
    - Colony Road Sprint (35s at ~540W, max HR 183)
    - Cool down (10 min, ~130W)

    Includes GPS coordinates matching the tagged segments, realistic
    HR lag, cadence variability, and power noise.
    """
    rng = np.random.RandomState(42)
    start_time = datetime(2026, 3, 10, 17, 30, 0)  # Recent Tuesday 5:30 PM
    points: list[RidePoint] = []

    def _section(
        start_offset_s: int,
        duration_s: int,
        base_power: float,
        base_hr: float,
        base_cadence: float,
        lat_start: float,
        lon_start: float,
        lat_end: float,
        lon_end: float,
        alt_start: float = 210.0,
        alt_end: float = 210.0,
        power_noise: float = 12.0,
        power_fade: float = 0.0,
        cadence_fade: float = 0.0,
        hr_ramp: float = 0.0,
    ) -> list[RidePoint]:
        """Generate a section of ride data with realistic variability."""
        pts = []
        for i in range(duration_s):
            t = start_time + timedelta(seconds=start_offset_s + i)
            frac = i / max(duration_s - 1, 1)

            # Power with noise, optional fade, and occasional surges
            p = base_power - (power_fade * frac)
            p += rng.normal(0, power_noise)
            # Occasional 2-3 second surges in group riding
            if rng.random() < 0.03 and base_power > 200:
                p += rng.uniform(30, 80)
            p = max(0, p)

            # HR with lag (responds slowly to power changes)
            hr = base_hr + (hr_ramp * frac) + rng.normal(0, 1.5)
            hr = max(90, min(195, hr))

            # Cadence with slight drift
            cad = base_cadence - (cadence_fade * frac) + rng.normal(0, 2)
            cad = max(0, min(120, cad))

            # GPS interpolation
            lat = lat_start + (lat_end - lat_start) * frac
            lon = lon_start + (lon_end - lon_start) * frac
            alt = alt_start + (alt_end - alt_start) * frac

            # Speed (roughly correlated to power and gradient)
            gradient = (alt_end - alt_start) / max(duration_s * 8, 1)  # rough
            speed = max(2.0, 9.0 - gradient * 50 + rng.normal(0, 0.3))

            pts.append(RidePoint(
                timestamp=t,
                power=round(p, 1),
                heart_rate=round(hr, 0),
                cadence=round(cad, 0),
                speed=round(speed, 2),
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                altitude=round(alt, 1),
            ))
        return pts

    offset = 0

    # ── Warm-up in the pack: 20 min at Z2 ─────────────────────────────
    points.extend(_section(
        offset, 1200, 175, 128, 90,
        35.1015, -80.8285, 35.1082, -80.8155,
        205, 210, power_noise=15,
    ))
    offset += 1200

    # ── Segment 1: Rea Road Kicker (75s, ~315W) ───────────────────────
    points.extend(_section(
        offset, 75, 318, 158, 82,
        35.1082, -80.8152, 35.1058, -80.8128,
        210, 232, power_noise=18, power_fade=15, cadence_fade=5, hr_ramp=14,
    ))
    offset += 75

    # ── Recovery 1: 8 min in the group ─────────────────────────────────
    points.extend(_section(
        offset, 480, 155, 145, 88,
        35.1058, -80.8128, 35.1145, -80.7930,
        232, 215, power_noise=20,
    ))
    offset += 480

    # ── Segment 2: Sardis Lane Drag (110s, ~298W) ─────────────────────
    points.extend(_section(
        offset, 110, 298, 155, 84,
        35.1145, -80.7928, 35.1178, -80.7892,
        215, 238, power_noise=15, power_fade=12, cadence_fade=3, hr_ramp=13,
    ))
    offset += 110

    # ── Recovery 2: 10 min ─────────────────────────────────────────────
    points.extend(_section(
        offset, 600, 160, 140, 89,
        35.1178, -80.7892, 35.1312, -80.7988,
        238, 218, power_noise=18,
    ))
    offset += 600

    # ── Segment 3: Providence Road Wall (55s, ~355W) ──────────────────
    #    This is the selection. Power fades, cadence drops, HR maxes out.
    points.extend(_section(
        offset, 55, 358, 165, 76,
        35.1312, -80.7985, 35.1338, -80.7968,
        218, 248, power_noise=20, power_fade=25, cadence_fade=8, hr_ramp=13,
    ))
    offset += 55

    # ── Recovery 3: 5 min coast ────────────────────────────────────────
    points.extend(_section(
        offset, 300, 140, 152, 85,
        35.1338, -80.7968, 35.1245, -80.8218,
        248, 215, power_noise=15,
    ))
    offset += 300

    # ── Segment 4: Colony Road Sprint (35s, ~540W) ────────────────────
    points.extend(_section(
        offset, 35, 545, 172, 98,
        35.1245, -80.8215, 35.1232, -80.8178,
        215, 218, power_noise=30, power_fade=40, hr_ramp=11,
    ))
    offset += 35

    # ── Cool down: 10 min ──────────────────────────────────────────────
    points.extend(_section(
        offset, 600, 128, 118, 82,
        35.1232, -80.8178, 35.1015, -80.8285,
        218, 205, power_noise=10,
    ))
    offset += 600

    ride = Ride(
        name="Tuesday Group Ride — Mar 10",
        points=points,
        source_file="demo_ride.fit",
    )

    # Save the ride as a pickle for the demo
    ride_path = get_data_dir() / "demo_ride.json"
    ride_data = {
        "name": ride.name,
        "source_file": ride.source_file,
        "points": [
            {
                "timestamp": p.timestamp.isoformat(),
                "power": p.power,
                "heart_rate": p.heart_rate,
                "cadence": p.cadence,
                "speed": p.speed,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "altitude": p.altitude,
            }
            for p in ride.points
        ],
    }
    save_json(ride_path, ride_data)


def load_demo_ride() -> Ride:
    """Load the pre-generated demo ride."""
    from puncheur.config import load_json

    ride_path = get_data_dir() / "demo_ride.json"
    data = load_json(ride_path)

    points = [
        RidePoint(
            timestamp=datetime.fromisoformat(p["timestamp"]),
            power=p.get("power"),
            heart_rate=p.get("heart_rate"),
            cadence=p.get("cadence"),
            speed=p.get("speed"),
            latitude=p.get("latitude"),
            longitude=p.get("longitude"),
            altitude=p.get("altitude"),
        )
        for p in data["points"]
    ]

    return Ride(
        name=data.get("name", "Demo Ride"),
        points=points,
        source_file=data.get("source_file", ""),
    )


def is_demo_available() -> bool:
    """Check if demo data has been set up."""
    return (get_data_dir() / "demo_ride.json").exists()


def _generate_charlotte_gpx() -> str:
    """Generate a GPX file for the Charlotte group ride loop."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Puncheur Demo" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Tuesday Group Ride — South Charlotte</name>
    <desc>Rolling loop through Ballantyne, Sardis, Providence. 4 segments.</desc>
  </metadata>
  <trk>
    <name>Tuesday Group Ride</name>
    <trkseg>
      <trkpt lat="35.1015" lon="-80.8285"><ele>205</ele></trkpt>
      <trkpt lat="35.1035" lon="-80.8245"><ele>207</ele></trkpt>
      <trkpt lat="35.1055" lon="-80.8200"><ele>208</ele></trkpt>
      <trkpt lat="35.1075" lon="-80.8165"><ele>209</ele></trkpt>
      <trkpt lat="35.1082" lon="-80.8152"><ele>210</ele></trkpt>
      <trkpt lat="35.1070" lon="-80.8140"><ele>218</ele></trkpt>
      <trkpt lat="35.1062" lon="-80.8132"><ele>228</ele></trkpt>
      <trkpt lat="35.1058" lon="-80.8128"><ele>232</ele></trkpt>
      <trkpt lat="35.1065" lon="-80.8090"><ele>228</ele></trkpt>
      <trkpt lat="35.1085" lon="-80.8040"><ele>222</ele></trkpt>
      <trkpt lat="35.1110" lon="-80.7985"><ele>218</ele></trkpt>
      <trkpt lat="35.1130" lon="-80.7955"><ele>216</ele></trkpt>
      <trkpt lat="35.1145" lon="-80.7928"><ele>215</ele></trkpt>
      <trkpt lat="35.1155" lon="-80.7918"><ele>220</ele></trkpt>
      <trkpt lat="35.1165" lon="-80.7905"><ele>228</ele></trkpt>
      <trkpt lat="35.1178" lon="-80.7892"><ele>238</ele></trkpt>
      <trkpt lat="35.1195" lon="-80.7895"><ele>235</ele></trkpt>
      <trkpt lat="35.1225" lon="-80.7910"><ele>228</ele></trkpt>
      <trkpt lat="35.1260" lon="-80.7935"><ele>222</ele></trkpt>
      <trkpt lat="35.1290" lon="-80.7965"><ele>220</ele></trkpt>
      <trkpt lat="35.1312" lon="-80.7985"><ele>218</ele></trkpt>
      <trkpt lat="35.1320" lon="-80.7978"><ele>228</ele></trkpt>
      <trkpt lat="35.1330" lon="-80.7972"><ele>240</ele></trkpt>
      <trkpt lat="35.1338" lon="-80.7968"><ele>248</ele></trkpt>
      <trkpt lat="35.1335" lon="-80.7990"><ele>242</ele></trkpt>
      <trkpt lat="35.1320" lon="-80.8040"><ele>235</ele></trkpt>
      <trkpt lat="35.1295" lon="-80.8100"><ele>228</ele></trkpt>
      <trkpt lat="35.1270" lon="-80.8160"><ele>220</ele></trkpt>
      <trkpt lat="35.1245" lon="-80.8215"><ele>215</ele></trkpt>
      <trkpt lat="35.1238" lon="-80.8198"><ele>216</ele></trkpt>
      <trkpt lat="35.1232" lon="-80.8178"><ele>218</ele></trkpt>
      <trkpt lat="35.1210" lon="-80.8200"><ele>215</ele></trkpt>
      <trkpt lat="35.1160" lon="-80.8240"><ele>210</ele></trkpt>
      <trkpt lat="35.1100" lon="-80.8265"><ele>207</ele></trkpt>
      <trkpt lat="35.1015" lon="-80.8285"><ele>205</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
