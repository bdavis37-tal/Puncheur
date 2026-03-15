# Puncheur

**Your Ride. Your Hills. Your Playbook.**

Built for cyclists who train for a specific group ride, not for dashboard tourists. Puncheur is an opinionated post-ride analysis and pre-ride strategy tool for competitive road cyclists who care about two things: "How did I perform on the segments that matter?" and "What's my plan for next time?"

## The Problem

Garmin gives you 47 metrics. Strava gives you segments. TrainingPeaks charges $20/month. None of them answer the question that matters: **"Am I ready for Tuesday?"**

You don't need another dashboard. You need a tool that knows your route, knows your climbs, and tells you exactly how many matches you can burn before the final selection.

## What Puncheur Does

### Post-Ride Debrief

Analyze your ride against your tagged route. For each climb: power, W'bal at entry, pacing analysis, and fatigue scoring. Did you arrive at Hill 3 with empty legs because you went too hard on Hill 1? Puncheur tells you.

```
puncheur debrief ride.fit --route tuesday_ride
```

### Pre-Ride Playbook

Before you clip in, know the plan. Puncheur generates segment-by-segment power targets, match budget allocation, and tactical recommendations based on your fitness, your power profile, and the route's demands.

```
puncheur playbook tuesday_ride
```

### KOM Attempt Planner

Target a segment, get a plan: target power, pacing splits, W'bal projection, and a proper warm-up protocol matched to the effort duration.

```
puncheur kom plan --segment "Hill 3" --duration 60
puncheur kom warmup --duration 60
```

## Quick Start

```bash
# Install
pip install -e .

# Set up your profile
puncheur init

# Add a route from GPX
puncheur route add tuesday_ride route.gpx

# Tag the segments that matter
puncheur route tag tuesday_ride

# Analyze a ride
puncheur debrief ride.fit --route tuesday_ride

# Get your playbook for next time
puncheur playbook tuesday_ride
```

## Sports Science

Puncheur is built on established cycling performance models:

- **Normalized Power (NP)**: Fourth-root-of-mean-of-fourth-power of 30-second rolling average — weights hard efforts more heavily than simple average power.
- **W'bal (W-prime balance)**: Skiba 2012 differential model tracking anaerobic capacity depletion and exponential recovery.
- **CTL/ATL/TSB**: Standard Performance Management Chart — chronic training load (fitness), acute training load (fatigue), and training stress balance (form).
- **Power Duration Curve**: Mean maximal power from 1 second to 60 minutes — your physiological fingerprint.

See [docs/SPORTS_SCIENCE.md](docs/SPORTS_SCIENCE.md) for the full deep dive.

## Architecture

```
puncheur/
├── models/       # Ride, Segment, Rider, RideProfile
├── parsers/      # FIT + GPX file parsing
├── analytics/    # Power curve, W'bal, fatigue, pacing, fitness
├── strategy/     # Playbook, KOM planner, warm-up protocols
└── reporting/    # HTML reports with inline SVG charts
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details.

## Philosophy

Fewer numbers, more insight. Every metric in Puncheur exists because it answers a question a competitive road cyclist actually asks:

- "How many matches do I have left?"
- "Did I pace the approach to that climb correctly?"
- "Should I attack Hill 2 or save it for Hill 3?"
- "Am I fit enough to contest the sprint after three climbs?"

If a number doesn't lead to an action, it doesn't belong here.

## CLI Commands

| Command | Description |
|---------|-------------|
| `puncheur init` | Set up rider profile |
| `puncheur profile update --ftp 285` | Update profile |
| `puncheur route add name file.gpx` | Add a route |
| `puncheur route tag name` | Tag segments on a route |
| `puncheur route list` | List saved routes |
| `puncheur debrief ride.fit` | Post-ride analysis |
| `puncheur playbook route_name` | Pre-ride strategy |
| `puncheur kom plan --segment X --duration 60` | KOM attempt plan |
| `puncheur kom warmup --duration 60` | Warm-up protocol |
| `puncheur fitness` | CTL/ATL/TSB overview |
| `puncheur history route_name` | Ride-over-ride trends |

All commands support `--json` for machine-readable output and `--output file.html` for styled HTML reports.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

MIT
