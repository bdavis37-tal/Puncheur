# Architecture

## Overview

Puncheur is a monorepo Python package with a clean separation of concerns:

```
src/puncheur/
├── cli.py              # Typer CLI — user-facing commands
├── config.py           # Configuration, paths, data persistence
├── models/             # Domain models (dataclasses)
├── parsers/            # File I/O (FIT, GPX)
├── analytics/          # Computational engine
├── strategy/           # Decision engine (playbook, KOM planning)
└── reporting/          # Output generation (HTML, terminal)
```

## Data Flow

```
FIT File → Parser → Ride Model → Analytics → Strategy → Reports
GPX File → Parser → RideProfile Model ─────────┘
                     Rider Profile ─────────────┘
```

1. **Parsers** convert raw files into domain models
2. **Analytics** compute derived metrics from ride data
3. **Strategy** combines analytics with rider profile to generate recommendations
4. **Reporting** renders results as terminal output or HTML

## Data Models

### Ride
Time-ordered sequence of `RidePoint` samples (power, HR, cadence, speed, GPS, altitude). Provides stream accessors (`.power_stream`, `.heart_rate_stream`) as numpy arrays for efficient computation.

### Rider
Physiological profile: FTP, weight, power zones, W', max HR. Power zones auto-calculate from FTP using Coggan's standard percentages.

### RideProfile
A named route (GPX file) with tagged `Segment` objects marking climbs and key efforts.

### Segment / SegmentMatch
A segment defines start/end GPS coordinates. A `SegmentMatch` links a segment to actual ride data — the time window and computed metrics for when you rode that section.

## Analytics Engine

### Power Duration Curve (`power_curve.py`)
Rolling window MMP calculation using cumulative sums for O(n) per duration.

### Segment Matcher (`segment_matcher.py`)
Proximity-based GPS matching with configurable tolerance (default 30m). Uses geopy for geodesic distance calculations.

### W'bal (`matchbook.py`)
Skiba 2012 differential model. Iterative computation over the power stream with exponential recovery time constant.

### Fatigue (`fatigue.py`)
Multi-level fatigue detection: ride-level power fade, cross-segment fade, within-segment fade, cadence drift, cardiac decoupling.

### Fitness (`fitness.py`)
Standard PMC model: exponentially weighted moving averages for CTL (42-day), ATL (7-day), TSB = CTL - ATL.

## Data Persistence

File-based storage in `~/.puncheur/`:
- `rider_profile.json` — Rider profile
- `routes/*.json` — Ride profiles with segments
- `rides/*_history.json` — Ride history per route
- `fitness_log.json` — Daily TSS log for CTL/ATL/TSB

No database. JSON for everything. Simple, portable, inspectable.

## Reports

Single-file HTML with embedded CSS and inline SVG charts. No JavaScript. No external dependencies. Server-side rendered SVG for power charts, W'bal traces, and budget bars.

Design language: dark charcoal (#1a1a2e), electric orange (#ff6b35) accents, cool blue (#4ecdc4) for comparison data. Cycling computer meets Bloomberg terminal.
