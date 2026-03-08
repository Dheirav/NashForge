# Champions — Reasoning & Selection Log

Four agents currently in the Hall of Fame. One is from Batch 3 (diversity), one
from Batch 4, and two from Batch 5. B5 champions seed B6 training as fixed opponents
and as warm-start weights for seeded fine-tune runs.

---

## Current Champions

### 1. `p40_m8_h750_s0.07_g200_b3_champion.npy`
| Field | Value |
|---|---|
| Population | 40 |
| Matchups / agent | 8 |
| Hands / matchup | 750 |
| Mutation σ | 0.07 |
| Generations | 200 |
| Batch | 3 |

**Why retained:** Only champion trained with a large population (p=40) and low σ=0.07
before B4 proved low-σ works. Its weight norm (34.02) is significantly different from
all p=12 champions, indicating a genuinely different policy basin learned under heavier
sampling pressure. Retained as a diversity HoF opponent — having one agent trained
under completely different population dynamics prevents B6 training from overfitting
to p=12/σ≤0.05 policy patterns.

**Use in B6:** HoF opponent only. Not a seed — B5 `p12` configs supersede in every metric.

---

### 2. `p12_m8_h500_s0.05_g50_b4_champion.npy`
| Field | Value |
|---|---|
| Population | 12 |
| Matchups / agent | 8 |
| Hands / matchup | 500 |
| Mutation σ | 0.05 |
| Generations | 50 |
| Batch | 4 |
| Tournament result | **#1 MultiTable B4 (98.5%)**, #1 Overall B4 (68.4%) |

**Why retained:** B4 MultiTable dominant champion. Despite being superseded by the B5
σ=0.04 champion in raw win rate, it still scored 99.3% MT win rate in B5 (second only
to B5 σ=0.04). Retained as a strong second HoF opponent for MT training — having both
σ=0.04 and σ=0.05 champions in the pool ensures B6 agents are tested against agents
with different fine-tuning depths.

**Use in B6:** HoF opponent for MT training. Optional secondary seed for `p12_m8` runs.

---

### 3. `p12_m8_h500_s0.04_g50_b5_champion.npy`
| Field | Value |
|---|---|
| Population | 12 |
| Matchups / agent | 8 |
| Hands / matchup | 500 |
| Mutation σ | 0.04 |
| Generations | 50 |
| Batch | 5 |
| Source checkpoint | `deep_p12_m8_h500_s0.04_seeded_hof3_g50/runs/run_20260308_090612` |
| Tournament result | **#1 MultiTable B5 (100.0%)**, #1 Overall B5 (76.2%) |

**Why selected:** Perfect 100% win rate in B5 MultiTable across 10 rounds — the highest
multi-table win rate ever recorded. σ=0.04 continues the trend of lower sigma outperforming:
B3 best was σ=0.09, B4 best was σ=0.05, B5 best is σ=0.04. Seeding from the B4 champion
was decisive: cold-start σ=0.04 scored only 28.5% overall vs 76.2% seeded — seeding is
non-negotiable at σ≤0.04.

**Critical insight:** σ=0.04 completely fails at HeadsUp (10% HU win rate). This is a pure
MultiTable specialist. Do not use as a HU seed.

**Use in B6:** Primary seed for all `p12_m8` fine-tune runs. Primary HoF opponent for
MultiTable training.

---

### 4. `p12_m7_h375_s0.06_hu100_g50_b5_champion.npy`
| Field | Value |
|---|---|
| Population | 12 |
| Matchups / agent | 7 |
| Hands / matchup | 375 |
| Mutation σ | 0.06 |
| Heads-up fraction | 1.0 (100% HU training) |
| Generations | 50 |
| Batch | 5 |
| Source checkpoint | `deep_p12_m7_h375_s0.06_hu100_seeded_hof3_g50/runs/run_20260308_113326` |
| Tournament result | **#1 HeadsUp B5 (88.0%)** |

**Why selected:** Best HeadsUp result across all batches. Up from B4's 82.7% HU win rate to
88.0% — the same σ=0.06/m=7/h=375 config, but B5 used `--heads-up-fraction 1.0` for
100% HU-only training. The improvement from 82.7% to 88.0% confirms that pure-HU
training pressure makes a measurable difference even within the same hyperparameter
config. Supersedes the B4 HU champion.

**Critical insight:** Scores only 31.7% in MultiTable — a deep HU specialist. The
`hu100` flag enforces full specialization, which is the correct strategy given B5
confirmed the format split cannot be bridged with a single set of weights.

**Use in B6:** Primary seed for all `p12_m7` HU fine-tune runs. Primary HoF opponent
for HeadsUp training.

---

## Known Architecture Ceiling (All Active Champions)

All agents use a `17→64→32→6` network (3,430 parameters). Key limitations:
- **`features[15]` = 0.5 hardcoded** — opponent aggression is a static constant, never updated during play
- **`features[14]` = `features[13]`** — hand potential is just a copy of hand strength (placeholder)
- **`features[12]` = `active/6.0`** — only 1 float distinguishes table size

These are not training issues — they are feature engineering ceilings that require
code changes to `engine/features.py`. All B6 champions will share this ceiling until
the architecture roadmap is executed.

---

## Archived Champions (`../archived/`)

Thirteen agents total:

### Archived after B5 (4 agents)
| File | Reason |
|---|---|
| `p12_m8_h500_s0.09_g200_b3_champion.npy` | σ=0.09 confirmed dead — 29.1% overall B5, declining every batch |
| `p12_m8_h500_s0.08_g200_champion.npy` | σ=0.08 / m=8 underperforms σ=0.05 in every format |
| `p12_m7_h500_s0.08_g200_b3_champion.npy` | σ=0.08 / m=7 consistently outcompeted; 30.1% overall B5 |
| `p12_m7_h375_s0.06_g50_b4_champion.npy` | Superseded by B5 HU champion with `hu100` training (+5.3% HU) |

### Archived after B4 (2 agents)
| File | Reason |
|---|---|
| `p12_m8_h750_s0.1_g200_b3_champion.npy` | σ=0.1 dead zone, h=750 too expensive per generation |
| `p40_m8_h375_s0.1_champion.npy` | σ=0.1 + p=40 both underperform |

### Archived earlier (7 m=6 era agents)
Pre-HoF training era, matchup count below 7. Kept for historical comparison only.
See `../archived/` for full list.

---

## Selection Criteria Summary

| Criterion | Champion |
|---|---|
| B3 diversity / large-population history | `p40_m8_h750_s0.07_g200_b3` |
| B4 MultiTable #1 — strong second MT opponent | `p12_m8_h500_s0.05_g50_b4` |
| **B5 MultiTable #1 — primary B6 MT seed** | `p12_m8_h500_s0.04_g50_b5` |
| **B5 HeadsUp #1 — primary B6 HU seed** | `p12_m7_h375_s0.06_hu100_g50_b5` |
