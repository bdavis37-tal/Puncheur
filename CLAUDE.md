# CLAUDE.md — Development Guide for Puncheur

## What is this project?

Puncheur is a post-ride analysis and pre-ride strategy tool for competitive road cyclists. It runs locally (Flask web UI on localhost:5050) and stores data in `~/.puncheur/`. The primary interface is the browser — CLI is a power-user escape hatch.

## Quick commands

```bash
# Install dependencies
pip install -e .

# Run tests (104 tests, ~10s)
python -m pytest tests/ -v

# Launch the app
puncheur

# Launch with demo data (265W FTP rider, Charlotte group ride)
puncheur --demo

# Run in CLI mode
puncheur --cli
```

## Project structure

```
src/puncheur/
├── web/              # Flask app — primary interface
│   ├── app.py        # All routes: /, /setup, /upload, /analyze, /playbook, /kom, /demo/ride
│   ├── templates/    # Jinja2 — base.html, dashboard, analyze, playbook, setup, etc.
│   └── static/       # style.css (single file, ~1100 lines, CSS custom properties)
├── analytics/        # The computational engine
│   ├── cp_model.py   # CP/W' model fitting (Morton 1996) — P = CP + W'/t
│   ├── matchbook.py  # W'bal tracking (Skiba 2012 differential model)
│   ├── trends.py     # Segment regression, race readiness scoring
│   ├── fatigue.py    # Multi-level fatigue: power fade, cadence drift, cardiac decoupling
│   ├── fitness.py    # CTL/ATL/TSB — 42-day and 7-day EWMA
│   ├── pacing.py     # Pre-segment approach analysis
│   ├── power_curve.py # Mean maximal power curve (cumulative sum method)
│   └── segment_matcher.py # GPS proximity matching (geopy geodesic)
├── strategy/         # The intelligence layer
│   ├── playbook.py   # Adaptive playbook — 3-tier target cascade (history → CP model → generic)
│   ├── kom_planner.py # KOM attempt planning with CP model
│   └── warmup.py     # Duration-specific warm-up protocols
├── models/           # Data classes
│   ├── ride.py       # Ride + RidePoint — core data model
│   ├── rider.py      # Rider profile with auto-calculated power zones
│   ├── segment.py    # Segment + SegmentMatch
│   └── ride_profile.py # Route template with tagged segments
├── parsers/          # File parsing
│   ├── fit_parser.py # FIT file parsing (fitparse library, semicircle conversion)
│   └── gpx_parser.py # GPX parsing (gpxpy)
├── reporting/
│   └── debrief.py    # Inline SVG chart generation (power + W'bal)
├── config.py         # Paths, Coggan power zones, JSON helpers
├── demo.py           # Demo data generator (synthetic ride, 8 weeks history)
└── cli.py            # Typer CLI entry point
```

## Key concepts

**W'bal (Energy Reserve):** The anaerobic work capacity model. Above FTP, W' depletes. Below FTP, it recovers exponentially (tau = 546*e^(-0.01*(FTP-power))+316). This is the core of match tracking.

**CP/W' Model:** The hyperbolic power-duration relationship: P = CP + W'/t. Fitted via linearized OLS on work-duration data. This replaces arbitrary FTP multipliers for target power predictions.

**Adaptive Playbook:** Three-tier intelligence — (1) actual segment history via linear regression, (2) CP/W' model predictions, (3) generic FTP multipliers as fallback. Every ride makes the next playbook smarter.

**Race Readiness:** Composite 0-100 score weighting fitness/CTL (30%), freshness/TSB (30%), segment trends (25%), and route consistency (15%).

## Data storage

All data lives in `~/.puncheur/`:
- `rider_profile.json` — Name, FTP, weight, power zones, W', max HR
- `routes/*.json` — Route profiles with tagged segments (GPS coords, gradient, notes)
- `rides/*_history.json` — Ride-over-ride history per route
- `fitness_log.json` — Daily TSS log for CTL/ATL/TSB
- `demo_ride.json` — Synthetic demo ride data

## Testing conventions

- Tests live in `tests/` — currently 104 tests, all passing
- Use `monkeypatch` to isolate `DEFAULT_DATA_DIR` to `tmp_path` (see conftest.py)
- Analytics tests use known synthetic data with predictable outputs
- Web tests use Flask's `test_client()`
- Test files mirror source: `test_cp_model.py`, `test_trends.py`, `test_matchbook.py`, etc.

## Design principles

- **Consumer-first UX** — Human language labels ("Energy Reserve" not "W'bal"), dark theme, mobile-ready
- **Action-oriented** — Every metric should lead to a decision. No dashboard tourism
- **Cite your sources** — Analytics code should reference the paper (Skiba 2012, Morton 1996, etc.)
- **Local and private** — No cloud, no accounts, no telemetry. Data stays in `~/.puncheur/`
- **No over-engineering** — Single CSS file, inline SVG charts, no JS build step

## Common development tasks

### Adding a new analytics module
1. Create `src/puncheur/analytics/your_module.py`
2. Write tests in `tests/test_your_module.py`
3. Wire into `web/app.py` route handlers if it surfaces in the UI
4. Update templates if needed

### Adding a new segment metric
1. Add the field to `SegmentMatch` in `models/segment.py`
2. Compute it in `segment_matcher.py`
3. Include it in the segment data dict in `app.py` (both `analyze` and `demo_ride` routes)
4. Display it in `analyze.html`

### Modifying the playbook
The playbook in `strategy/playbook.py` has three target-power tiers. If you change target calculations, ensure tests in `test_playbook.py` still pass. The playbook template is `templates/playbook.html`.

## Tech stack

- **Python 3.11+** with type hints
- **Flask 3.x** for web UI
- **Jinja2** for HTML templates
- **NumPy** for all analytics computation
- **fitparse** for FIT file parsing
- **gpxpy** for GPX parsing
- **geopy** for geodesic distance calculations
- **Typer + Rich** for CLI
- **pytest** for testing
- **Hatchling** for build system
