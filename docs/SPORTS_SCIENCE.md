# Sports Science Models

This document explains the physiological models used in Puncheur.

## Normalized Power (NP)

**What it is**: A weighted average power that accounts for the physiological cost of variability. A ride with lots of surges and recoveries is harder than a steady ride at the same average power.

**How it's calculated**:
1. Compute a 30-second rolling average of power
2. Raise each value to the 4th power
3. Take the mean
4. Take the 4th root

```
NP = (mean(rolling_30s_avg ^ 4)) ^ 0.25
```

**Why it matters**: NP better represents the true metabolic cost of a ride. Two rides with the same average power but different variability will have different NP values — the more variable ride will have higher NP.

## Intensity Factor (IF)

**What it is**: The ratio of Normalized Power to FTP.

```
IF = NP / FTP
```

- IF < 0.75: Recovery/endurance ride
- IF 0.75-0.85: Tempo ride
- IF 0.85-0.95: Threshold training
- IF 0.95-1.05: Threshold effort (race-pace)
- IF > 1.05: Above-threshold effort (short or unsustainable)

## Training Stress Score (TSS)

**What it is**: A single number representing the overall training load of a ride, normalized to your FTP.

```
TSS = (duration_seconds × NP × IF) / (FTP × 3600) × 100
```

A 1-hour ride at exactly FTP = 100 TSS. This is the reference point.

## CTL / ATL / TSB (Performance Management Chart)

### CTL — Chronic Training Load ("Fitness")
42-day exponentially weighted moving average of daily TSS. Represents your accumulated training adaptation. Higher CTL = more fit (to a point).

### ATL — Acute Training Load ("Fatigue")
7-day exponentially weighted moving average of daily TSS. Represents recent training stress. High ATL means you're carrying fatigue.

### TSB — Training Stress Balance ("Form")
```
TSB = CTL - ATL
```

- TSB > 15: Very fresh — possible detraining if prolonged
- TSB 5-15: Fresh and ready to perform — race day form
- TSB 0-5: Functional — can perform but not peaked
- TSB -10 to 0: Slightly fatigued — normal training
- TSB < -30: Deep fatigue — overreaching

**The sweet spot for race day**: TSB between +5 and +20, with high CTL.

## W' and W'bal (W-Prime Balance)

### W' (W-Prime)
Your finite anaerobic work capacity above FTP, measured in joules. Think of it as a rechargeable battery for efforts above threshold.

Typical values for trained cyclists: 15,000–25,000 joules.

### W'bal (W-Prime Balance)
The Skiba (2012) differential model tracks W' depletion and recovery:

**Depletion** (when power > FTP):
```
W'bal decreases by (power - FTP) joules per second
```

**Recovery** (when power ≤ FTP):
```
tau = 546 × e^(-0.01 × (FTP - power)) + 316
W'bal = W' - (W' - W'bal_prev) × e^(-1/tau)
```

The recovery is exponential — you recover faster when riding easier (lower power below FTP means shorter time constant).

### Match Burning
A "match" is a discrete effort above 120% FTP lasting at least 30 seconds. Puncheur counts matches and tracks remaining W'bal to answer: "How many matches do I have left?"

## Power Duration Curve

The Mean Maximal Power (MMP) curve shows your best average power for every duration from 1 second to 60 minutes. It represents your full physiological profile:

- **1-10s**: Neuromuscular (sprint) power
- **30-60s**: Anaerobic capacity
- **2-5min**: VO2max power
- **10-20min**: Threshold / MAP
- **30-60min**: Sub-threshold endurance

The shape of this curve reveals strengths and limiters. A cyclist with high 1-minute power but relatively low 20-minute power is a "puncher" (hence the tool's name) — strong on short climbs but vulnerable on longer efforts.

## Power Zones (Coggan)

Standard 7-zone model based on FTP:

| Zone | Name | % FTP |
|------|------|-------|
| Z1 | Recovery | 0-55% |
| Z2 | Endurance | 55-75% |
| Z3 | Tempo | 75-90% |
| Z4 | Threshold | 90-105% |
| Z5 | VO2max | 105-120% |
| Z6 | Anaerobic | 120-150% |
| Z7 | Neuromuscular | >150% |

## Cardiac Decoupling

The ratio of power to heart rate should remain relatively stable during a well-paced aerobic effort. When this ratio drifts — same heart rate but less power, or same power but higher heart rate — it signals cardiovascular fatigue.

```
Decoupling = ((Power:HR first half) - (Power:HR second half)) / (Power:HR first half) × 100
```

Greater than 5% decoupling indicates insufficient aerobic fitness for the effort.

## References

- Coggan, A.R. & Allen, H. (2010). Training and Racing with a Power Meter.
- Skiba, P.F. et al. (2012). Modeling the expenditure and reconstitution of work capacity above critical power.
- Skiba, P.F. et al. (2014). An improved method for quantifying W'balance.
