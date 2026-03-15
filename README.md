# 🚴 Puncheur

### 🔥 Own the group ride.

> Tuesday at 5:30. The group rolls out. Four climbs between you and bragging rights. You've been training — but do you *know* you're ready? Do you know which climb to attack and which one to sit in? Do you know if you went harder last week or softer?
>
> **Puncheur knows.**

---

## ⚡ What is this?

Puncheur is a **ride analysis and race strategy weapon** for competitive road cyclists. It runs locally, opens in your browser, and does three things no other tool does:

🎯 **Tells you what happened** — Drop your .fit file, get instant segment-by-segment analysis with power, pacing, energy tracking, and fatigue scoring. Not 47 metrics. *The ones that matter.*

🧠 **Tells you what to do next** — Before your next ride, get a playbook: target power for every segment, match budget allocation, and tactical advice based on *your actual history* on that route.

📈 **Tells you if you're getting faster** — Week-over-week segment trends with statistical projections. *"+2.1W/week on Rea Road. Target 325W this Tuesday."*

> 🔒 No cloud. No subscription. No social features. Just you, your power meter, and a plan.

---

## 🚀 See it in 30 seconds

```bash
pip install -e .
puncheur --demo
```

💥 Boom. A 265W FTP rider, 8 weeks of training history on a Tuesday group ride in south Charlotte, full ride analysis with segment breakdowns. Everything Puncheur does — in your browser, right now.

## 🏁 The real quick start

```bash
pip install -e .
puncheur
```

Opens at `localhost:5050`. 30-second setup wizard. Upload a .fit file. **You're analyzing.**

---

## 💀 Why this exists

**Strava** tells you where you rank. It doesn't tell you where you're *headed*. It doesn't tell you whether you paced the approach to that climb correctly, or how much anaerobic energy you had left when you got there.

**Garmin Connect** gives you recovery advisors and VO2max estimates based on wrist heart rate. Cool. It doesn't know your Tuesday route has four climbs and *the third one is the selection*.

**TrainingPeaks** costs $20/month and is designed for coaches managing athletes. You just want to know if you should attack Hill 2 or save it for Hill 3.

🔥 **Puncheur is built for the rider who trains for a specific ride.** The Tuesday crit. The Saturday group ride. The local KOM that's been taunting you for months. It knows your route, knows your history on every segment, and gives you a plan.

---

## 🏆 What you get

### 💪 Post-ride analysis

Drop a .fit file. Puncheur matches your GPS to tagged segments and shows you:

- ⚡ **Power by segment** with FTP% context and zone coloring — instantly know Z5 or Z6
- 🔄 **Ride-over-ride comparison** — last week's power and time on every segment, green/red deltas
- 🥇 **PR detection** — beat your best-ever segment power? We celebrate it
- 🔋 **Energy reserve tracking** — W'bal through the ride, see exactly where you dug deep
- 🎯 **Pre-segment pacing** — did you arrive at that climb fresh or already in the red?
- 😤 **Fatigue scoring** — power fade, cadence drift, cardiac decoupling → one number
- 📊 **FTP reference line** on the power chart — see threshold crossings at a glance

### 🗺️ Pre-ride playbook

Tap a route before you ride and get:

- 🏅 **Race readiness score** (0-100) — fitness + freshness + trends + consistency
- 🎯 **Adaptive power targets** — from YOUR actual segment history, not generic FTP multipliers
- 🔋 **W' match budget** — total energy cost vs. your anaerobic capacity
- 📈 **Segment trends** — *"+2.1W/week on Rea Road (R²=0.85). You're on fire here lately."*
- ♟️ **Tactical recommendations** — *"Mark the leaders, respond but don't initiate. Save matches."*
- 📝 **Coach's notes** — *"Trending up on Rea Road and Providence Wall. Push these segments today."*

### 👑 KOM attempt planner

Pick a segment. Pick a duration. Get a plan:

- 🔥 **Target power** from a fitted CP/W' physiological model (not a lookup table)
- ⏱️ **Pacing splits** — front-load for short efforts, negative split for long ones
- 🔋 **Energy budget** — will your anaerobic tank survive this effort?
- 🌡️ **Warm-up protocol** — duration-specific, zone targets for each step

---

## 🧬 The science under the hood

> Built on published sports science, not vibes.

| What you see | What's happening | Source |
|---|---|---|
| ⚡ Energy Reserve | W'bal differential model tracking anaerobic depletion and recovery | Skiba et al., 2012 |
| 💪 Weighted Power | Fourth root of mean of fourth power of 30s rolling average | Coggan, 2003 |
| 📊 Fitness / Fatigue / Form | 42-day and 7-day exponential moving averages of daily training load | Banister, 1991 |
| 🎯 Target Power | Hyperbolic CP/W' model: `P = CP + W'/t`, fitted from your data | Morton, 1996 |
| 📈 Segment Trends | OLS linear regression on weekly segment power | Standard |
| 😤 Fatigue Score | Weighted combination of power fade, cadence drift, cardiac decoupling | Custom |
| 🏅 Race Readiness | Composite of CTL, TSB, segment trends, and route consistency | Custom |

🚀 **The CP/W' model is the secret weapon.** Instead of generic FTP multipliers ("1-minute power = FTP x 1.3"), we fit the actual power-duration curve to *your physiology*. Target power at any duration — 35 seconds or 20 minutes — from your own data.

---

## ⚙️ How it works

```
You ride Tuesday ──> Upload .fit ──> Segment analysis + comparison to last week
                                              │
                                    Ride history accumulates
                                              │
                    Next Tuesday <── Playbook with adaptive targets from YOUR data
```

The playbook runs a **three-tier intelligence cascade** 🧠:

1. 🔥 **3+ weeks of segment data?** → Targets from linear regression on your actual power with trend projection
2. 📊 **No segment history but has ride data?** → Targets from fitted CP/W' physiological model
3. 🆕 **Brand new user?** → Generic FTP-based estimates as scaffolding until you ride the route

**Every ride makes the next playbook smarter.** 🚀

---

## 🏗️ Architecture

```
puncheur/
├── web/            🌐 Flask UI — the primary interface
│   ├── templates/  Jinja2 with inline SVG charts (no JS charting libs)
│   └── static/     Dark theme CSS — premium, data-dense, mobile-ready
├── analytics/
│   ├── cp_model    🧬 CP/W' model fitting (Morton 1996 hyperbolic)
│   ├── matchbook   🔋 W'bal tracking (Skiba 2012 differential)
│   ├── trends      📈 Segment regression, race readiness scoring
│   ├── fatigue     😤 Multi-level fatigue detection
│   ├── fitness     💪 CTL/ATL/TSB performance management
│   ├── pacing      🎯 Pre-segment approach analysis
│   └── power_curve ⚡ Mean maximal power (cumulative sum method)
├── strategy/
│   ├── playbook    🗺️ Adaptive pre-ride strategy generation
│   ├── kom_planner 👑 CP-model-based KOM attempt planning
│   └── warmup      🌡️ Duration-specific warm-up protocols
├── models/         📦 Ride, RidePoint, Rider, Segment, RideProfile
├── parsers/        📂 FIT file + GPX parsing
├── demo.py         🎮 Full demo data generator (265W FTP, Charlotte route)
└── cli.py          ⌨️ Typer CLI (power-user escape hatch)
```

Python 3.11+. Flask for the web UI. NumPy for analytics. **Zero JavaScript charting libraries** — all charts are inline SVG generated server-side. Data stays local in `~/.puncheur/`.

---

## 🧭 Design philosophy

🎯 **Action over information.** Every number on screen answers a question or drives a decision. If a metric doesn't lead to "ride harder here" or "sit in there," it doesn't belong.

🧠 **Your data gets smarter.** First ride → analysis. Third ride → trends. Sixth ride → projections. The tool rewards consistency with better intelligence.

✨ **Consumer-grade UX, coach-grade analytics.** Human language first ("Energy Reserve" not "W'bal"). Dark theme, mobile-ready, drag-and-drop. Your mom could figure it out. But the CP/W' model under the hood is *publication-grade*.

🔒 **Local-first, private by design.** No accounts. No cloud sync. No "share to feed." Your power data is yours. Runs on localhost, stores in `~/.puncheur/`, never phones home.

---

## 📋 Requirements

- 🐍 Python 3.11+
- 📡 A cycling computer that exports .fit files (Garmin, Wahoo, Hammerhead, etc.)
- ⚡ A power meter (Puncheur is power-first — HR-only analysis is limited)

---

## 🤝 Contributing

We're particularly interested in:

- 🎲 **Stochastic pacing models** — Modeling group ride dynamics where power is not self-selected
- 🤖 **ML-based segment matching** — Fuzzy GPS matching that handles GPS drift and route variations
- 🎮 **Zwift/indoor integration** — Virtual ride analysis with segment mapping
- 🧬 **Multi-ride CP fitting** — Building the CP model from composite best efforts across rides

Open an issue or PR. Code should have tests. Analytics code should cite the source paper.

---

## 📄 License

MIT
