# Puncheur

**Your Ride. Your Hills. Your Playbook.**

Built for cyclists who train for a specific group ride, not for dashboard tourists. Puncheur is an opinionated post-ride analysis and pre-ride strategy tool for competitive road cyclists who care about two things: "How did I perform on the segments that matter?" and "What's my plan for next time?"

## The Problem

Garmin gives you 47 metrics. Strava gives you segments. TrainingPeaks charges $20/month. None of them answer the question that matters: **"Am I ready for Tuesday?"**

You don't need another dashboard. You need a tool that knows your route, knows your climbs, and tells you exactly how many matches you can burn before the final selection.

## What Puncheur Does

### Post-Ride Debrief

Drop your .fit file into the browser. Puncheur analyzes every climb: power, energy reserve at entry, pacing analysis, and fatigue scoring. Did you arrive at Hill 3 with empty legs because you went too hard on Hill 1? Puncheur tells you.

### Pre-Ride Playbook

Before you clip in, know the plan. Segment-by-segment power targets, match budget allocation, and tactical recommendations based on your fitness and the route's demands.

### KOM Attempt Planner

Target a segment, get a plan: target power, pacing splits, energy budget, and a warm-up protocol matched to the effort duration.

## Quick Start

```bash
# Install
pip install -e .

# Launch (opens in your browser)
puncheur
```

That's it. Puncheur opens a beautiful web UI at `http://localhost:5050`. A guided setup wizard walks you through creating your profile — no jargon, smart defaults, 30 seconds to value.

### What you'll see:

1. **Setup wizard** — Enter your name, weight, FTP, and experience level. We estimate the rest.
2. **Dashboard** — Your fitness snapshot, quick actions, and saved routes.
3. **Upload** — Drag and drop a .fit file for instant analysis.
4. **Playbook** — Tap a route for pre-ride strategy and segment targets.
5. **KOM Planner** — Pick an effort duration, get a complete attack plan with warm-up.

### Power users: CLI still works

```bash
# Traditional CLI mode
puncheur --cli init
puncheur --cli debrief ride.fit --route tuesday_ride
puncheur --cli playbook tuesday_ride
puncheur --cli kom plan --segment "Hill 3" --duration 60
```

## Sports Science

Puncheur is built on established cycling performance models:

- **Weighted Power**: Accounts for the extra cost of surges and hard efforts (Normalized Power algorithm).
- **Energy Reserve**: Tracks your anaerobic tank throughout the ride — how many matches you have left (W'bal / Skiba 2012).
- **Fitness / Fatigue / Form**: Your training load trend over weeks — are you fit, tired, or fresh? (CTL/ATL/TSB model).
- **Power Profile**: Your best efforts from 5 seconds to 60 minutes — your physiological fingerprint.

See [docs/SPORTS_SCIENCE.md](docs/SPORTS_SCIENCE.md) for the full deep dive.

## Architecture

```
puncheur/
├── web/          # Flask web UI (the primary interface)
├── models/       # Ride, Segment, Rider, RideProfile
├── parsers/      # FIT + GPX file parsing
├── analytics/    # Power curve, W'bal, fatigue, pacing, fitness
├── strategy/     # Playbook, KOM planner, warm-up protocols
├── reporting/    # HTML reports with inline SVG charts
└── cli.py        # Typer CLI (power-user escape hatch)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details.

## Design Philosophy

**Consumer-first.** If your mom can't figure out how to analyze a ride, we failed. The web UI is the default. CLI is for power users.

**Fewer numbers, more insight.** Every metric exists because it answers a question a competitive road cyclist actually asks:

- "How many matches do I have left?"
- "Did I pace the approach to that climb correctly?"
- "Should I attack Hill 2 or save it for Hill 3?"
- "Am I fit enough to contest the sprint after three climbs?"

**Human language over jargon.** We say "Energy Reserve" not "W'bal". "Weighted Power" not "NP". "Training Load" not "TSS". The science labels are still there for those who want them — but they're not the first thing you see.

If a number doesn't lead to an action, it doesn't belong here.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

MIT
