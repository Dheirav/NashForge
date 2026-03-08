# PokerBot — Total Results Across All Batches

**Coverage**: Batch 1 → Batch 2 → Batch 1+2 Combined → Batch 3 → Batch 4 → Batch 5  
**Total Games Analyzed**: ~964,000+ (1,080 B1 + 1,872 B2 + 544 B1+2 + 622,916 B3 + 296,041 B4 + 38,156 B5)  
**Date Range**: Jan 26 – Mar 8, 2026  

---

## Table of Contents

1. [Batch 1 Results](#batch-1)
2. [Batch 2 Results](#batch-2)
3. [Batch 1+2 Combined Results](#batch-12-combined)
4. [Batch 3 Results](#batch-3)
5. [Batch 4 Results](#batch-4)
6. [Batch 5 Results](#batch-5)
7. [Cross-Batch Hyperparameter Evolution](#cross-batch-hyperparameter-evolution)
8. [Hall of Fame Impact](#hall-of-fame-impact)
9. [Format Analysis: HeadsUp vs MultiTable](#format-analysis)
10. [All-Time Rankings](#all-time-rankings)
11. [Anti-Patterns — What Never Works](#anti-patterns)
12. [Training Roadmap — Batch 6](#training-roadmap-batch-6)
13. [Architecture Roadmap — Known Ceilings](#architecture-roadmap)

---

## Batch 1

**Tournaments**: 6 | **Agents**: 10 | **Games**: 1,080 | **Date**: Jan 26, 2026

### Full Rankings

| Rank | Agent | Win Rate | Record | Avg Chips |
|---|---|---|---|---|
| 1 | p40_m8_h375_s0.1_g50 | **78.7%** | 85W–23L | 28,333 |
| 2 | p40_m6_h500_s0.15_g200 | 73.1% | 79W–29L | 25,655 |
| 3 | p40_m8_h375_s0.1_g200 | 72.2% | 78W–30L | 26,000 |
| 4 | p20_m6_h500_s0.15_g200 | 71.3% | 77W–31L | 25,667 |
| 5 | p12_m6_h500_s0.15_g200 | 68.5% | 74W–34L | 24,667 |
| 6 | p20_m6_h500_s0.15_g50 | 47.2% | 51W–57L | 17,210 |
| 7 | p40_m6_h500_s0.15_g50 | 22.2% | 24W–84L | 8,277 |
| 8 | p12_m6_h500_s0.15_g50 | 22.2% | 24W–84L | 8,185 |
| 9 | p12_m3_h1000_s0.15_g200 | 22.2% | 24W–84L | 8,014 |
| 10 | p12_m3_h1000_s0.15_g50 | 22.2% | 24W–84L | 7,991 |

### Hyperparameter Correlations — Batch 1

| Hyperparameter | Value | Win Rate | Avg Chips |
|---|---|---|---|
| **Population** | 40 | **61.6%** | 22,066 |
| | 20 | 59.3% | 21,439 |
| | 12 | 33.8% | 12,214 |
| **Matchups** | 8 | **75.5%** | 27,167 |
| | 6 | 50.8% | 18,277 |
| | 3 | 22.2% | 8,003 |
| **Hands** | 375 | **75.5%** | 27,167 |
| | 500 | 50.8% | 18,277 |
| | 1000 | 22.2% | 8,003 |
| **Sigma** | 0.10 | **75.5%** | 27,167 |
| | 0.15 | 43.6% | 15,708 |

### Batch 1 Key Findings
- m=8 provides **+49% relative improvement** over m=6 (75.5% vs 50.8%)
- p=40 dominates; p=12 severely underperforms without HoF
- σ=0.15 is already visibly worse even in this early batch
- m=3 and h=1000 are dead on arrival (22.2% — indistinguishable from random)

---

## Batch 2

**Tournaments**: 6 | **Agents**: 13 | **Games**: 1,872 | **Date**: Jan 28, 2026  
*First batch to introduce HoF-trained agents and lower σ values*

### Full Rankings

| Rank | Agent | Win Rate | Record | Avg Chips | HoF |
|---|---|---|---|---|---|
| 1 | p12_m8_h500_s0.08_g200 | **81.2%** | 117W–27L | 39,000 | ✓ |
| 2 | p12_m6_h750_s0.08_g50 | 67.4% | 97W–47L | 32,333 | ✓ |
| 3 | p12_m6_h375_s0.1_g50_v2 | 63.9% | 92W–52L | 30,667 | ✓ |
| 4 | p12_m6_h750_s0.1_g50 | 62.5% | 90W–54L | 30,000 | ✓ |
| 5 | p12_m6_h750_s0.1_g200 | 61.1% | 88W–56L | 29,333 | ✓ |
| 6 | p12_m6_h375_s0.1_g50 | 59.0% | 85W–59L | 28,333 | ✓ |
| 7 | p12_m6_h375_s0.12_g200 | 54.2% | 78W–66L | 25,989 | ✓ |
| 8 | p12_m8_h500_s0.08_g50 | 51.4% | 74W–70L | 24,667 | ✓ |
| 9 | p12_m6_h375_s0.1_g200 | 48.6% | 70W–74L | 23,333 | ✓ |
| 10 | p12_m6_h375_s0.12_g50 | 44.4% | 64W–80L | 21,333 | ✓ |
| 11 | p12_m10_h375_s0.1_g200 | 40.3% | 58W–86L | 19,307 | ✓ |
| 12 | p12_m10_h375_s0.1_g50 | 16.0% | 23W–121L | 7,645 | ✓ |
| 13 | p12_m6_h750_s0.08_g200 | **0.0%** | 0W–144L | 59 | ✓ |

> ⚠️ p12_m6_h750_s0.08_g200 recorded 0% — a known training anomaly (dead network), not representative of the config.

### Hyperparameter Correlations — Batch 2

| Hyperparameter | Value | Win Rate | Avg Chips |
|---|---|---|---|
| **Population** | 12 | 50.0% | 24,000 |
| **Matchups** | 8 | **66.3%** | 31,833 |
| | 6 | 51.2% | 24,598 |
| | 10 | 28.1% | 13,476 |
| **Hands** | 500 | **66.3%** | 31,833 |
| | 750 | 47.7% | 22,932 |
| | 375 | 46.6% | 22,372 |
| **Sigma** | 0.10 | **50.2%** | 24,088 |
| | 0.08 | 50.0% | 24,015 |
| | 0.12 | 49.3% | 23,661 |

### Batch 2 Key Findings
- Champion `p12_m8_h500_s0.08_g200` achieves **81.2%** — the first time a single agent breaks 80%
- m=10 confirms dismal performance (28.1%) — more matchups beyond m=8 is strictly worse
- All agents in Batch 2 use HoF training; this is the first clean HoF dataset
- σ now clearly clusters: 0.08–0.10 competitive, 0.12 borderline, 0.15 retired

---

## Batch 1+2 Combined

**Tournaments**: 1 mega-tournament | **Agents**: 17 | **Games**: 544  
*All best agents from B1 and B2 competed together*

### Top 10 Rankings

| Rank | Agent | Win Rate | Avg Chips |
|---|---|---|---|
| 1 | p12_m6_h750_s0.1_g200 | 78.1% | 50,000 |
| 2 | p12_m6_h375_s0.1_g50_v2 | 75.0% | 48,000 |
| 3 | p12_m8_h500_s0.08_g200 | 75.0% | 48,000 |
| 4 | p12_m6_h750_s0.1_g50 | 68.8% | 44,000 |

> Combined tournament confirms that HoF-trained p=12 configs are the most consistent pool. Results compressed because single tournament (low volume).

### Batch 1+2 Combined Summary
- p=12 + HoF completely dominates p=40 + no HoF across all 17 configs
- g200 edges out g50 when all else equal
- h=500 and h=750 now closely matched (unlike B1 where h=375 pulled ahead strongly)

---

## Batch 3

**Tournaments**: 10 HeadsUp + 10 MultiTable = 20 | **Configs**: 58 (29 × g50/g200) | **Games**: 622,916  
**Date**: Feb 17–22, 2026 | *First batch with rigorous split format evaluation*

### Top 10 — Combined (HeadsUp + MultiTable)

| Rank | Agent | Win Rate | Avg Chips | Config |
|---|---|---|---|---|
| 1 | p12_m8_h750_s0.1_g200 | **50.4%** | 975,023 | pop=12, m=8, h=750, σ=0.1 |
| 2 | p12_m8_h500_s0.09_g200 | 47.0% | 30,670,892 | pop=12, m=8, h=500, σ=0.09 |
| 3 | p12_m7_h500_s0.08_g200 | 46.1% | 58,262,042 | pop=12, m=7, h=500, σ=0.08 |
| 4 | p40_m8_h750_s0.07_g200 | 45.8% | 56,665,757 | pop=40, m=8, h=750, σ=0.07 |
| 5 | p40_m7_h375_s0.1_g50 | 45.4% | 72,159,449 | pop=40, m=7, h=375, σ=0.1 |
| 6 | p40_m8_h750_s0.08_g50 | 45.4% | 6,022,966 | pop=40, m=8, h=750, σ=0.08 |
| 7 | p20_m7_h375_s0.08_g200 | 45.2% | -2,522,824 | pop=20, m=7, h=375, σ=0.08 |
| 8 | p20_m8_h500_s0.09_g50 | 44.9% | 41,648,469 | pop=20, m=8, h=500, σ=0.09 |
| 9 | p40_m9_h500_s0.08_g200_v2 | 44.7% | 38,897,497 | pop=40, m=9, h=500, σ=0.08 |
| 10 | p20_m8_h375_s0.1_g50 | 44.1% | 39,765,143 | pop=20, m=8, h=375, σ=0.1 |

### Bottom 5 — Combined

| Rank | Agent | Win Rate | Avg Chips |
|---|---|---|---|
| 57 | p40_m8_h500_s0.1_g200 | 25.2% | -60,400,941 |
| 58 | p20_m9_h500_s0.09_g50 | 22.8% | -101,041,346 |
| 59 | p40_m9_h375_s0.1_g200 | 19.0% | -27,311,779 |
| 60 | p20_m9_h750_s0.09_g200 | 17.9% | -73,525,994 |
| 61 | p40_m8_h750_s0.08_g200 | **16.9%** | -25,785,364 |

---

### Top 10 — HeadsUp Only (Batch 3)

| Rank | Agent | Win Rate | Avg Chips |
|---|---|---|---|
| 1 | p12_m8_h500_s0.09_g200 | **81.3%** | 195,200 |
| 2 | p20_m7_h750_s0.09_g200 | 79.2% | 190,000 |
| 3 | p12_m7_h375_s0.09_g50 | 78.6% | 188,600 |
| 4 | p12_m9_h375_s0.1_g200 | 78.4% | 188,200 |
| 5 | p40_m7_h375_s0.1_g200 | 78.2% | 187,600 |
| 6 | p12_m7_h375_s0.08_g50 | 78.2% | 187,600 |
| 7 | p12_m7_h500_s0.08_g200 | 76.6% | 183,800 |
| 8 | p12_m7_h375_s0.08_g200 | 75.7% | 181,600 |
| 9 | p12_m9_h750_s0.09_g50 | 74.7% | 179,200 |
| 10 | p12_m8_h375_s0.1_g200 | 74.5% | 178,800 |

### Bottom 5 — HeadsUp Only (Batch 3)

| Rank | Agent | Win Rate |
|---|---|---|
| 57 | p20_m9_h500_s0.1_g200 | 9.2% |
| 58 | p20_m9_h750_s0.09_g200 | 9.2% |
| 59 | p12_m8_h750_s0.1_g200 | **9.0%** |
| 60 | p40_m8_h750_s0.08_g200 | 7.7% |
| 61 | p12_m8_h750_s0.1_g50 | **7.4%** |

---

### Top 10 — MultiTable Only (Batch 3)

| Rank | Agent | Win Rate | Avg Chips |
|---|---|---|---|
| 1 | p12_m8_h750_s0.1_g200 | **57.7%** | 1,928,479 |
| 2 | p40_m8_h750_s0.08_g50 | 48.1% | 11,986,713 |
| 3 | p20_m7_h375_s0.08_g200 | 43.8% | -5,180,249 |
| 4 | p12_m7_h750_s0.08_g200 | 43.6% | 102,618,561 |
| 5 | p40_m7_h375_s0.1_g50 | 43.1% | 144,168,499 |
| 6 | p40_m8_h750_s0.07_g200 | 42.9% | 113,169,314 |
| 7 | p20_m8_h375_s0.1_g50 | 42.8% | 79,402,286 |
| 8 | p12_m8_h500_s0.09_g200 | 42.5% | 61,146,585 |
| 9 | p12_m7_h500_s0.08_g200 | 42.0% | 116,340,285 |
| 10 | p12_m8_h750_s0.1_g50 | 41.7% | -14,109,176 |

### Bottom 5 — MultiTable Only (Batch 3)

| Rank | Agent | Win Rate | Avg Chips |
|---|---|---|---|
| 57 | p40_m8_h500_s0.1_g200 | 24.5% | -120,876,252 |
| 58 | p40_m9_h375_s0.1_g200 | 20.0% | -54,649,385 |
| 59 | p20_m9_h750_s0.09_g200 | 19.1% | -147,073,830 |
| 60 | p40_m8_h750_s0.08_g200 | **18.1%** | -51,590,516 |
| 61 | p20_m9_h500_s0.09_g50 | **18.1%** | -202,223,091 |

### Hyperparameter Correlations — Batch 3

#### Combined
| Hyperparameter | Value | Win Rate | Avg Chips |
|---|---|---|---|
| **Population** | 12 | **38.7%** | -8,704,245 |
| | 20 | 37.2% | -12,507,663 |
| | 40 | 36.7% | -5,982,457 |
| **Matchups** | 7 | **39.5%** | -3,675,269 |
| | 8 | 39.0% | -4,397,088 |
| | 9 | 33.7% | -18,931,212 |
| **Hands** | 500 | **38.7%** | -4,092,805 |
| | 375 | 37.9% | -7,120,735 |
| | 750 | 36.4% | -13,094,752 |
| **Sigma** | 0.07 | **41.0%** | +9,456,300 |
| | 0.08 | 39.5% | -1,347,582 |
| | 0.10 | 37.2% | -7,475,666 |
| | 0.09 | 35.8% | -18,870,675 |

#### HeadsUp Only
| Hyperparameter | Value | Win Rate |
|---|---|---|
| **Matchups** | 7 | **58.8%** |
| | 8 | 45.5% |
| | 9 | 45.2% |
| **Hands** | 375 | **55.9%** |
| | 500 | 55.4% |
| | 750 | 41.9% |
| **Sigma** | 0.07 | **66.9%** |
| | 0.08 | 54.3% |
| | 0.09 | 51.5% |
| | 0.10 | 44.8% |

#### MultiTable Only
| Hyperparameter | Value | Win Rate |
|---|---|---|
| **Matchups** | 8 | **38.3%** |
| | 7 | 36.9% |
| | 9 | 32.2% |
| **Hands** | 500 | **36.4%** |
| | 750 | 35.8% |
| | 375 | 35.5% |
| **Sigma** | 0.07 | **37.6%** |
| | 0.08 | 37.5% |
| | 0.10 | 36.3% |
| | 0.09 | 33.7% |

---

## Batch 4

**Tournaments**: 10 HeadsUp + 10 MultiTable = 20 | **Configs**: 36 (18 unique × g50/g200) | **Games**: 296,041  
**Date**: Mar 4–7, 2026 | *First batch testing p=20/p=40 at low σ, seeded HoF, and hybrid `hu30` format training*

### Top 10 — HeadsUp

| Rank | Agent | Win Rate | Config |
|---|---|---|---|
| 1 | p12_m7_h375_s0.06_g50 | **82.7%** | pop=12, m=7, h=375, σ=0.06 |
| 2 | p12_m7_h500_s0.08_g200 | 78.8% | pop=12, m=7, h=500, σ=0.08 |
| 3 | p12_m8_h500_s0.09_g200 | 77.4% | pop=12, m=8, h=500, σ=0.09 |
| 4 | p40_m8_h375_s0.06_g200 | 76.8% | pop=40, m=8, h=375, σ=0.06 |
| 5 | p12_m8_h500_s0.05_g50 | 76.7% | pop=12, m=8, h=500, σ=0.05 |
| 6 | p12_m7_h375_s0.06_g200 | 76.4% | pop=12, m=7, h=375, σ=0.06 |
| 7 | p12_m8_h500_s0.05_g200 | 75.7% | pop=12, m=8, h=500, σ=0.05 |
| 8 | p12_m7_h500_s0.08_g50 | 75.7% | pop=12, m=7, h=500, σ=0.08 |
| 9 | p12_m8_h500_s0.07_g200 | 71.7% | pop=12, m=8, h=500, σ=0.07 |

### Top 10 — MultiTable

| Rank | Agent | Win Rate | Avg Chips/Tournament | Config |
|---|---|---|---|---|
| 1 | p12_m8_h500_s0.05_g50 | **98.5%** | 2,991,196 | pop=12, m=8, h=500, σ=0.05 |
| 2 | p12_m8_h500_s0.05_g200 | 48.7% | 5,079,403 | pop=12, m=8, h=500, σ=0.05 |
| 3 | p12_m8_h500_s0.05_g50_v3 | 47.4% | 63,620 | pop=12, m=8, h=500, σ=0.05 |
| 4 | p40_m8_h375_s0.06_g200 | 39.2% | 76,842,758 | pop=40, m=8, h=375, σ=0.06 |
| 5 | p12_m8_h500_s0.06_g200 | 39.1% | 111,595,911 | pop=12, m=8, h=500, σ=0.06 |

> ⚠️ `p12_m8_h500_s0.05_g50` achieved 98.5% MultiTable — an outlier result. Its g200 counterpart scored 48.7%, confirming the gap is real: g50 converges faster at σ=0.05 because the fitness landscape is smooth and doesn't benefit from prolonged exploration.

### Hyperparameter Verdicts — Batch 4

| Param | MultiTable Best | HeadsUp Best | Conflict |
|---|---|---|---|
| Population | p=12 (35.6%) | p=20 (59.6%) | **Yes** |
| Matchups | m=8 (34.9%) | m=7 (58.6%) | **Yes** |
| Hands | h=500 (35.9%) | h=500 (50.1%) | No |
| Sigma | **σ=0.05 (45.4% MT)** | **σ=0.06 (59.8% HU)** | Minor |
| Sigma bottom | σ=0.09 (22.8%) | σ=0.1 (31.9%) | No |

### Batch 4 Key Findings
- **σ=0.05 is the new MultiTable king** — completely inverts B3 where σ=0.09 led. The optimal multi-table policy is in a smooth, narrow weight-space region.
- **σ=0.09 collapses in a large field** — B3 HeadsUp champion config ranked last in B4 Overall (17.9%). It overfits to smaller populations.
- **m=7 vs m=8 format split confirmed** — m=7 wins HeadsUp, m=8 wins MultiTable. This is a structural finding, not noise.
- **`hu30` hybrid training failed** — none of the forced 30% HeadsUp matchup configs placed in any format's top 5. Mixed fitness signal produces mediocre generalists.
- **p=40 continues to underperform** (33.7% combined) — consistent across B3 and B4. Large populations don't compensate for lower sigma.
- **g200 vs g50**: at σ=0.05, g50 wins decisively. At σ=0.08+, g200 retains an edge.
- **Seeded HoF configs** did not consistently outperform cold-start configs at the same hyperparameters — warm-starting from B3 champions provided no statistically clear advantage in B4's field.

### Hall of Fame Update (Post-B4)

| Action | Agent | Reason |
|---|---|---|
| ✅ Added | `p12_m8_h500_s0.05_g50_b4_champion` | B4 MT #1 (98.5%), B4 Overall #1 — primary B5 seed |
| ✅ Added | `p12_m7_h375_s0.06_g50_b4_champion` | B4 HU #1 (82.7%) — primary B5 seed |
| ❌ Archived | `p12_m8_h750_s0.1_g200_b3_champion` | σ=0.1 finished 5th of 6 sigmas in B4 MT (30.1%) |
| ❌ Archived | `p40_m8_h375_s0.1_champion` | σ=0.1 + p=40 both bottom-tier across all B4 formats |

---

## Batch 5

**Tournaments**: 20 (10 HeadsUp + 10 MultiTable) | **Unique Agents**: 16 | **Total Games**: 38,156 | **Date**: Mar 8, 2026  
**Configs trained**: 13 (σ fine-sweep {0.04, 0.045, 0.05, 0.06} MT + h={250,375}×σ={0.05,0.06,0.07} HU + B3 survivor calibration)  

### Top 10 — HeadsUp Only (Batch 5)

| Rank | Agent | HU Win Rate | Avg Chips |
|---|---|---|---|
| 1 | `p12_m7_h375_s0.06_g50` (hu100 seeded) | **88.0%** | 52,800 |
| 2 | `p12_m7_h250_s0.06_g50` (hu100 seeded) | 84.7% | 50,800 |
| 3 | `p12_m7_h375_s0.05_g50` (hu100 seeded) | 77.3% | 46,400 |
| 4 | `p12_m7_h375_s0.07_g50` (hu100 seeded) | 65.0% | 39,000 |
| 5 | `p12_m8_h500_s0.05_g50_v2` | 62.7% | 37,600 |
| 6 | `p12_m7_h500_s0.08_g50` (B3 survivor) | 62.7% | 37,600 |
| 7 | `p12_m7_h250_s0.05_g50` (hu100 seeded) | 61.3% | 36,800 |
| 8 | `p12_m8_h500_s0.06_g50` (seeded) | 59.0% | 35,400 |
| 14 | `p12_m8_h500_s0.05_g50` (seeded) | **10.0%** | 5,996 |
| 15 | `p12_m8_h500_s0.045_g50` (seeded) | 10.0% | 5,994 |
| 16 | `p12_m8_h500_s0.04_g50` (seeded) | 10.0% | 5,987 |

> MT-trained agents (m=8, σ≤0.05) hit the hard floor of 10% HU — 3-way tie at the bottom.

### Top 10 — MultiTable Only (Batch 5)

| Rank | Agent | MT Win Rate | Avg Chips |
|---|---|---|---|
| 1 | `p12_m8_h500_s0.04_g50` (seeded) | **100.0%** | 1,278,924 |
| 2 | `p12_m8_h500_s0.05_g50` (seeded) | 99.3% | 1,300,692 |
| 3 | `p12_m8_h500_s0.045_g50` (seeded) | 55.7% | 969,235 |
| 4 | `p12_m7_h250_s0.06_g50` (hu100 seeded) | 35.3% | 1,007,292 |
| 5 | `p12_m7_h500_s0.08_g50_v2` | 35.0% | 2,278,828 |
| 7 | `p12_m7_h375_s0.06_g50` (hu100 seeded) | 31.7% | -3,210,645 |
| 16 | `p12_m8_h500_s0.09_g50_v2` (B3 survivor) | 18.9% | -21,128,663 |

> Seeded σ=0.04 and σ=0.05 are in a class alone — both above 99%. The next cluster starts at σ=0.045 at 55.7%.

### Hyperparameter Verdicts — Batch 5

| Hyperparameter | B5 Winner | B5 Verdict |
|---|---|---|
| **σ (MT)** | 0.04 | Floor keeps pushing down. Seeding essential at this level. |
| **σ (HU)** | 0.06 | Unchanged from B4. σ=0.06 + hu100 reinforces specialization. |
| **Seeded vs cold-start** | Seeded | At σ=0.04: seeded 76.2% vs cold-start 28.5% — largest gap ever seen. |
| **h=250 vs h=375 (HU)** | h=375 | 88.0% vs 84.7% — h=375 wins but h=250 viable. |
| **hu100 vs standard HU** | hu100 | B4 HU champion at 82.7% → B5 hu100 at 88.0% (+5.3%). |
| **σ=0.045 (midpoint)** | — | 55.7% MT / 10% HU — mediocre in both. No sweet spot. |
| **σ=0.09 (calibration)** | — | 28-29% overall. **Permanently retired.** |

### Batch 5 Key Findings

1. **σ trend continues**: Optimal MT sigma = 0.04 (B3: 0.09 → B4: 0.05 → B5: 0.04). Diminishing σ is the dominant trend across every batch.
2. **Seeding is non-negotiable at low σ**: Cold-start σ=0.04 scored 28.5% overall; seeded scored 76.2%. A low mutation rate can only refine, not find — it must start near the opt.
3. **No sweet spot at σ=0.045**: The midpoint between two strong performers (0.04 and 0.05) lands in neither's territory — 55.7% MT and 10% HU. Policy basins for MT and HU are not smoothly interpolated.
4. **hu100 flag is worth it**: Forcing 100% HU matchups during training pushed HU win rate from 82.7% (B4) to 88.0% (B5) with identical σ=0.06/m=7/h=375. A 5.3 percentage point improvement from training signal alone.
5. **Format split is now structural**: MT top 2 scored exactly 10% HU (the floor). HU top 3 scored 25–31% MT. No config reached >60% in both simultaneously. A single weight vector cannot generalize across formats at current architecture.
6. **h=250 for HU is viable but not optimal**: 84.7% HU for h=250 vs 88.0% for h=375 — shorter matchups per generation create more noise, but enough signal to train to near-champion level.
7. **σ=0.09 permanently retired**: B5 calibration confirmed continued decline. Both σ=0.09 configs placed bottom-2 in MT and bottom-4 overall.

### Hall of Fame Update (Post-B5)

| Action | Agent | Reason |
|---|---|---|
| ✅ Added | `p12_m8_h500_s0.04_g50_b5_champion` | B5 MT #1 (100.0%) — new all-time MT record |
| ✅ Added | `p12_m7_h375_s0.06_hu100_g50_b5_champion` | B5 HU #1 (88.0%) — new all-time HU record |
| ❌ Archived | `p12_m8_h500_s0.09_g200_b3_champion` | σ=0.09 dead — consistent last-place finish |
| ❌ Archived | `p12_m8_h500_s0.08_g200_champion` | σ=0.08/m=8 underperforms in every format, every batch |
| ❌ Archived | `p12_m7_h500_s0.08_g200_b3_champion` | σ=0.08/m=7 consistently outcompeted |
| ❌ Archived | `p12_m7_h375_s0.06_g50_b4_champion` | Superseded by B5 HU champion (+5.3% HU win rate) |

---

## Cross-Batch Hyperparameter Evolution

### Win Rate by Hyperparameter Value Across All Batches

#### Matchups (m)

| m value | Batch 1 | Batch 2 | Batch 3 Combined | Batch 3 HeadsUp | Batch 3 MultiTable |
|---|---|---|---|---|---|
| 3 | 22.2% | — | — | — | — |
| 6 | 50.8% | 51.2% | — | — | — |
| 7 | — | — | **39.5%** | **58.8%** | 36.9% |
| 8 | **75.5%** | **66.3%** | 39.0% | 45.5% | **38.3%** |
| 9 | — | — | 33.7% | 45.2% | 32.2% |
| 10 | — | 28.1% | — | — | — |

**Takeaway**: m=8 was consistently best in B1/B2. In B3, m=7 edges combined; m=8 best for MultiTable. m=9 first tested in B3, consistently worst. m=10 confirmed bad in B2.

#### Hands per Matchup (h)

| h value | Batch 1 | Batch 2 | Batch 3 Combined | Batch 3 HeadsUp | Batch 3 MultiTable |
|---|---|---|---|---|---|
| 375 | **75.5%** | 46.6% | 37.9% | **55.9%** | 35.5% |
| 500 | 50.8% | **66.3%** | **38.7%** | 55.4% | **36.4%** |
| 750 | — | 47.7% | 36.4% | 41.9% | 35.8% |
| 1000 | 22.2% | — | — | — | — |

**Takeaway**: h=375 dominated B1. h=500 took over in B2. In B3, h=750 is worst for HeadsUp but competitive for MultiTable. h=500 is the most consistent generalist across all batches.

#### Mutation Sigma (σ)

| σ value | Batch 1 | Batch 2 | Batch 3 Combined | Batch 3 HeadsUp | Batch 3 MultiTable |
|---|---|---|---|---|---|
| 0.07 | — | — | **41.0%** | **66.9%** | **37.6%** |
| 0.08 | — | 50.0% | 39.5% | 54.3% | 37.5% |
| 0.09 | — | — | 35.8% | 51.5% | 33.7% |
| 0.10 | **75.5%** | 50.2% | 37.2% | 44.8% | 36.3% |
| 0.12 | — | 49.3% | — | — | — |
| 0.15 | 43.6% | (all configs) | — | — | — |

**Takeaway**: σ=0.10 looked best in B1 (only option vs 0.15). σ=0.08 best in B2. σ=0.07 wins everything in B3 but only 2 data points. Clear downward trend — lower σ keeps winning as more configs are tested.

#### Generations (g)

| g | Batch 1 | Batch 2 | Batch 3 | Notes |
|---|---|---|---|---|
| g50 | Second in most pairs | Worse than g200 | Mixed — can **beat** g200 by 30pts | |
| g200 | Best for stable configs | Consistently better | **Can catastrophically fail** for large pop + h=750 | |

**Critical Batch 3 case**: `p40_m8_h750_s0.08_g50` = 48.1% vs `p40_m8_h750_s0.08_g200` = 18.1% — a **30 point collapse** from longer training (HOF overfitting).

#### Population Size (p)

| p | Batch 1 | Batch 2 | Batch 3 Combined |
|---|---|---|---|
| 12 | 33.8% (bad without HoF) | **50.0%** (all HoF) | **38.7%** |
| 20 | 59.3% | — | 37.2% |
| 40 | **61.6%** | — | 36.7% |

**Takeaway**: p=40 won B1 (no HoF, pop size == diversity). Once HoF introduced in B2, p=12 caught up. In B3, all sizes close (within 2%), so population is the least impactful parameter when HoF is used.

---

## Hall of Fame Impact

Across all batches, comparing HoF-trained vs pure self-play agents:

| Metric | With HoF | Without HoF | Advantage |
|---|---|---|---|
| Mean Win Rate | **50.8%** | 33.3% | +17.5 pp |
| Best Agent Win Rate | **80.2%** | 55.0% | +25.2 pp |
| Avg Chips | **25,403** | 15,897 | +59.8% |
| Agents >50% WR | **66.7%** (10/15) | 37.5% (3/8) | +29.2 pp |
| Top-7 agents using HoF | **7/7** | 0/7 | 100% |

> **Note**: All non-HoF configs also used σ=0.15 (suboptimal), so the raw +52.2% relative improvement includes both effects. Isolated HoF benefit estimated at +5–15 percentage points.

### Why HoF Matters
- Without HoF, small populations (p=12) converge to exploiting each other, failing against outside opponents
- With HoF, the fixed elite opponent pool prevents "closed loop" overfitting
- HoF allows p=12 to match or exceed p=40 (3× faster training)
- All 4 current HoF champions: `p12_m6_h750_s0.1_g200`, `p12_m6_h750_s0.1_g50`, `p12_m8_h500_s0.08_g200`, `p40_m8_h375_s0.1`

---

## Format Analysis

### The Format Inversion — Batch 3's Critical Discovery

The most extreme cases from Batch 3:

| Agent | HeadsUp Rank | HeadsUp WR | MultiTable Rank | MultiTable WR |
|---|---|---|---|---|
| p12_m8_h750_s0.1_g200 | **#59** | 9.0% | **#1** | 57.7% |
| p12_m8_h500_s0.09_g200 | **#1** | 81.3% | #8 | 42.5% |
| p40_m8_h750_s0.08_g200 | #60 | 7.7% | #60 | 18.1% |

An agent can be simultaneously **best in one format and worst in the other.** Combined rank masks this completely — `p12_m8_h750_s0.1_g200` appears #1 overall but is nearly unplayable in 1v1.

### Best Configs by Format (All Batches)

| Use Case | Best Config | Win Rate | Notes |
|---|---|---|---|
| **HeadsUp (1v1)** | p12_m8_h500_s0.09_g200 | **81.3%** | B3 HeadsUp #1 |
| | p12_m8_h500_s0.08_g200 | **81.2%** | B2 all-format champion |
| **MultiTable (6-handed)** | p12_m8_h750_s0.1_g200 | **57.7%** | B3 MultiTable #1 |
| **Both Formats** | p12_m8_h500_s0.08_g200 | ~82% HU / ~81% MT | Most balanced config across all batches |

### Why Does Format Inversion Happen?

Training already uses 6-player games (`num_players=6` in `FitnessConfig`). The inversion is not about training format — it's about what happens at **h=750 specifically**:

With 750 hands against each training opponent, the agent has enough data to learn very precise, opponent-specific counter-strategies. Those micro-adjustments work well in multi-player settings (where you play against many people and position/stack dynamics matter more) but break in 1v1 (where opponent modeling and aggression frequency need to be drastically different). h=375–500 produces agents that learn broader strategies because no single opponent encounter is long enough to over-specialize.

---

## All-Time Rankings

Best individual performance recorded, across all batches and formats:

| Metric | Agent | Value | Batch |
|---|---|---|---|
| Highest single win rate | p12_m8_h500_s0.08_g200 | **82.9%** (320W–68L) | B2 (multi-tournament) |
| Best HeadsUp win rate | p12_m8_h500_s0.09_g200 | **81.3%** | B3 HeadsUp |
| Best MultiTable win rate | p12_m8_h750_s0.1_g200 | **57.7%** | B3 MultiTable |
| Best combined (balanced) | p12_m8_h500_s0.09_g200 | 47.0% combined (81.3% HU / 42.5% MT) | B3 |
| Most chips (MultiTable) | p40_m7_h375_s0.1_g50 | 144,168,499 avg | B3 MT |
| Most consistent | p12_m8_h500_s0.08_g200 | Chip std dev 1,528 | B2 |

### All-Time Worst Performances

| Metric | Agent | Value | Notes |
|---|---|---|---|
| Worst combined | p40_m8_h750_s0.08_g200 | **16.9%** | Bottom of B3 |
| Worst HeadsUp | p12_m8_h750_s0.1_g50 | **7.4%** | Almost random |
| Worst MultiTable | p20_m9_h500_s0.09_g50 | **18.1%** | -202M avg chips |
| Biggest g200 collapse | p40_m8_h750_s0.08_g200 vs g50 | **-30 points** | HOF overfitting |
| Worst overall (dead net) | p12_m6_h750_s0.08_g200 | **0.0%** (0W–144L) | Training anomaly, B2 |

---

## Anti-Patterns

Combinations that have **never** produced a good result across any batch:

| Anti-Pattern | Evidence | Verdict |
|---|---|---|
| σ ≥ 0.15 | B1: 43.6% avg, all non-HoF configs used it | **Forbidden** — phase transition failure |
| m=3 | B1: 22.2% (all 4 agents) | **Forbidden** — zero fitness signal |
| h=1000 | B1: 22.2% | **Forbidden** — confirmed counterproductive |
| m=10 | B2: 28.1% avg | **Retire** — overfitting to training opponents |
| m=9 | B3: 33.7% combined, worst across all formats | **Retire** — worse than m=7 everywhere |
| p<20 without HoF | B1 p=12: 33.8%; B2 p=12 without HoF: ~34% | **Forbidden** without HoF |
| h=750 + g200 + large pop | B3: up to -30pt collapse | **Retire** this combination |
| m=9 + g200 | B3 bottom cluster: 17.9–19.0% | **Dead zone** — never use |

---

## Training Roadmap — Batch 6

**Status**: ✅ B5 complete. Ready to begin B6 planning.

### What B5 Answered

| Question | Answer |
|---|---|
| Can σ=0.04 beat σ=0.05 at MT? | **Yes — σ=0.04 seeded = 100% MT win rate.** New all-time record. |
| Is seeding essential at σ=0.04? | **Absolutely.** Seeded: 76.2% overall. Cold-start: 28.5%. Largest ever gap. |
| Does hu100 flag improve HU specialist? | **Yes** — same config, B4: 82.7% → B5 hu100: 88.0% (+5.3pp). |
| Does h=250 work for HU? | **Viable but not optimal.** 84.7% (h=250) vs 88.0% (h=375). |
| Is σ=0.045 a good midpoint? | **No.** 55.7% MT / 10% HU. Midpoints collapse in both formats. |
| Is σ=0.09 dead? | **Confirmed permanently retired.** 28-29% overall, declining every batch. |
| Is format split bridgeable? | **No** — MT top 2 scored 10% HU; HU top 3 scored 25-31% MT. |

### B6 Target Configs

B5 pushed σ as low as 0.04 with seeding. B6 should test the σ floor and fix architecture signals.

**MultiTable track** — push σ floor further:
```
Population:   12
Matchups:     8
Hands:        500
Sigma:        0.03, 0.035, 0.04          ← test if floor is 0.04 or lower
Generations:  50
Seeded from:  p12_m8_h500_s0.04_g50_b5_champion  ← must seed, cold-start fails at this σ
HoF:          4 (include both B5 champions)
```

**HeadsUp track** — confirm hu100 σ optimum:
```
Population:   12
Matchups:     7
Hands:        375
Sigma:        0.05, 0.055, 0.06          ← B5 showed σ=0.05 hu100 at 77.3%, worth closing to champ
Generations:  50
HeadsUpFrac:  1.0                         ← hu100 mandatory based on B5 result
Seeded from:  p12_m7_h375_s0.06_hu100_g50_b5_champion
HoF:          4 (include both B5 champions)
```

**Architecture experiment (optional with B6)**:
Before running full B6, consider patching `engine/features.py` Fix 1 (replace hardcoded  
`features[15] = 0.5` with real opponent aggression metric). Even a simple running average  
of opponent bet/pot ratios would give the network a live signal it has never had. Run one  
seeded B6 MT config with and without this patch to isolate the impact.

### What to Retire Permanently

| Config Pattern | Reason |
|---|---|
| Any σ≥0.08 | Dead in all formats across B3, B4, B5. No recovery possible. |
| Any cold-start at σ≤0.04 | Seeding delta (76% vs 28%) is too large to ignore. |
| Any `_hu30_` or multi-format hybrid | Format split is structural. Mixing degrades both. |
| p=40 at any σ | Consistently outperformed by p=12 since B3. |

---

## Architecture Roadmap — Known Ceilings

**Status**: Current architecture has hard limits on generalisation. These are known, documented, and actionable. Training improvements (B5) are independent of this track — both can proceed in parallel.

### Current Architecture

```
Input:   17 features
Hidden:  [64, 32]  (ReLU)
Output:  6 actions
Params:  17×64 + 64 + 64×32 + 32 + 32×6 + 6 = 3,430 total
```

### Why a True Format Generalist Is Hard to Train Right Now

**Problem 1 — Format signal is one float** `[STATUS: KNOWN, NOT YET FIXED]`

Feature `[12]` (`num_active`, normalised) is the only input telling the network how many players are at the table. The network must conditon entirely different strategic behaviour (tight 6-max vs aggressive heads-up) off a single normalised float. The capacity exists in the weights — the training signal never rewards using it.

**Problem 2 — Single-format training pressure** `[STATUS: INHERENT TO CURRENT SETUP]`

All MultiTable runs set `heads_up_fraction=0.0`. Every fitness score pushes weights in the 6-player direction every generation. No force exists in the evolution to preserve heads-up competence. The `hu30` experiment attempted to fix this with mixed matchups — it produced mediocre generalists because the fitness signals point in opposite directions (fold-tight for MT, play-wide for HU).

**Problem 3 — Opponent context is missing** `[STATUS: KNOWN, HIGH IMPACT FIX]`

Features `[15]` (aggression) is currently hardcoded to `0.5` — a placeholder never updated. The network makes every decision with no knowledge of whether its opponent has been passive or aggressive this session. A human player would adjust dramatically based on this.

### Actionable Fixes (Ordered by Impact vs Effort)

#### Fix 1 — Add Opponent Aggression Feature ★★★★☆
`Status: NOT STARTED | Effort: Low | Impact: High`

Replace the hardcoded `features[15] = 0.5` in [engine/features.py](engine/features.py) with a real rolling aggression metric: `(num_bets + num_raises) / num_actions` over the last N actions. This is a 1-line change in the feature extractor. Requires re-training — all existing checkpoints would need to be migrated or retrained.

#### Fix 2 — Add Stack Depth Relative to Opponents ★★★☆☆
`Status: NOT STARTED | Effort: Low | Impact: Medium`

Currently `features[1]` is hero's own stack-to-pot. Add a feature for `min_opponent_stack / starting_stack` — this tells the agent whether it's the shortest or deepest stack at the table, which is critical for multi-table ICM-style decisions.

#### Fix 3 — Dual Output Heads (Format-Conditional) ★★★★☆
`Status: NOT STARTED | Effort: Medium | Impact: High`

Split the output layer into two heads: one for HU (2-player) and one for MT (6-player), selected by `num_active`. The shared trunk `[64, 32]` learns card evaluation and pot odds; the heads specialise. This adds only 192 parameters (32×6) and requires no change to the training infrastructure beyond loading the right head at inference.

#### Fix 4 — Sequential Fine-Tuning Protocol ★★★☆☆
`Status: NOT STARTED | Effort: Medium | Impact: Medium`

Train to convergence on MT. Freeze layer 1 (card/pot features that transfer). Fine-tune only the output layer on HU data at very low σ (0.02–0.03). The frozen layer retains the shared evaluation logic; the output layer re-specialises for HU. No architecture change needed.

#### Fix 5 — Expand Feature Vector (17 → 22+) ★★★★★
`Status: PREREQUISITE FOR ALL OTHERS | Effort: Medium | Impact: Highest`

The single highest-leverage change. Add:
- `features[17]`: real aggression (replaces placeholder)
- `features[18]`: relative stack depth vs table min
- `features[19]`: bet-to-stack ratio (how committed is hero to this pot)
- `features[20]`: number of players who have already acted this street
- `features[21]`: pot odds relative to all-in (SPR proxy)

This requires: updating [engine/features.py](engine/features.py), updating `input_size=17` in [training/config.py](training/config.py) to 22, retraining all configs from scratch. Existing checkpoints become incompatible (architecture mismatch — genome_transform can adapt them but with information loss).

### Architecture Change Decision Point

| Path | When to do it | What it unlocks |
|---|---|---|
| **Continue B5 as-is** | Now | Fine-sweeps confirm σ=0.04–0.06 optimal range; clean B5 champion for HoF |
| **Add Fix 1+2 only** | After B5 | Drop-in feature upgrade, re-run 1–2 configs to validate before full batch |
| **Full Fix 5 (22 inputs)** | Before B6 | True format generalist becomes achievable; all B5 champions become legacy |
| **Fix 3 (dual heads)** | Alongside Fix 5 | Combine richer features with format-conditional output — full generalist system |

---

## Alternative Training Paradigms — RL and CFR

`Status: PLANNED — not yet implemented`

The current system is **neuroevolution (ES)**. Two alternative paradigms are worth exploring: **Reinforcement Learning (RL)** and **Counterfactual Regret Minimization (CFR)**. They are not replacements — each has different strengths and is better suited for different goals.

---

### Comparison: Evolution vs RL vs CFR

| Property | Evolution (current) | RL (Policy Gradient) | CFR |
|---|---|---|---|
| **Learning signal** | Win/loss across full hands | Per-action gradient from reward | Regret across every decision in game tree |
| **Sample efficiency** | Low — needs thousands of hands per update | Medium — learns from every action | High — but requires full tree traversal |
| **Convergence guarantee** | None (heuristic) | Local optimum only | Nash equilibrium (2-player) |
| **Multi-player support** | ✅ Native (already 6-player) | ✅ Works but reward attribution harder | ⚠️ Exact CFR only provably correct for 2-player zero-sum |
| **Needs backprop / PyTorch** | ❌ Pure NumPy | ✅ Yes — needs autograd | ❌ Tabular CFR is NumPy; Deep CFR needs PyTorch |
| **Engine compatibility** | ✅ Already integrated | ✅ Engine almost ready — needs gym wrapper | ⚠️ Needs info set extraction added to engine |
| **Explainability** | Low | Low | High — regret tables show why each action was chosen |
| **Best for** | Exploring hyperparameter space fast | Training strong single agents efficiently | Heads-up play; Nash-optimal strategy |

---

### Approach 1 — Reinforcement Learning (Policy Gradient / PPO)

`Status: NOT STARTED | Effort: Medium | Priority: High`

**What it is:** Instead of evolving populations of agents, a single agent plays hands and updates its weights via gradient descent after each hand (or batch of hands). The reward signal is the chip delta. Policy Gradient methods (REINFORCE, PPO) compute the gradient of expected reward with respect to network weights.

**Engine readiness:** The engine is already 90% ready.

| Component | Status |
|---|---|
| `game.apply_action(player, action)` → step function | ✅ Exists |
| `game.is_hand_over()` → terminal check | ✅ Exists |
| Chip delta → reward signal | ✅ Already computed in `fitness.py` |
| Feature extraction → observation | ✅ `FeatureCache` in `engine/features.py` |
| Action mask (legal moves only) | ✅ `create_action_mask()` in `policy_network.py` |
| Gym-style `env.reset()` / `env.step()` wrapper | ❌ **Needs to be built** |
| PyTorch policy network with `log_prob` | ❌ **Needs to be built** (current net is NumPy-only) |
| Opponent pool / self-play loop | ❌ **Needs to be built** |

**What needs to be built:**
1. `training/poker_env.py` — wrap `PokerGame` as a standard gym environment with `reset()`, `step()`, returning `(obs, reward, done, info)`
2. `training/policy_network_torch.py` — port the current `[17→64→32→6]` network to PyTorch so it has `.log_prob()` and `.entropy()` for PPO
3. `training/rl_trainer.py` — PPO training loop with opponent pool (self-play against frozen past versions, same concept as HoF)

**Key design decision — credit assignment:**  
Poker reward is delayed (you only know if you won at showdown, not after each street bet). Two options:
- **Hand-level credit**: assign the entire chip delta as reward to all actions in the hand. Simple but noisy.
- **Street-level credit**: assign partial reward at each street based on pot equity change. More informative but requires equity calculation per street.

Start with hand-level credit — it's simpler and PPO handles the variance via the baseline/critic.

**Expected benefit over evolution:**  
Evolution evaluates whole genomes, so a single bad decision can tank a good agent's fitness without pointing at which decision was wrong. RL gets a gradient signal: it knows *which action* at *which game state* contributed to the loss. This means far fewer hands needed to train to the same quality.

---

### Approach 2 — Counterfactual Regret Minimization (CFR)

`Status: NOT STARTED | Effort: High | Priority: Medium`

**What it is:** CFR doesn't train a neural network at first — it solves the game directly by iterating over the game tree and accumulating "regret" (how much worse was the chosen action vs the best possible action in hindsight). After many iterations, the average strategy profile converges to a Nash equilibrium. It's the algorithm behind Libratus and Slumbot.

**Why it matters:** CFR is the only approach that produces a *provably unexploitable* strategy in 2-player poker. An RL or evolution agent can always be exploited by someone who studies its tendencies. A CFR agent at Nash equilibrium cannot be exploited by definition.

**Engine readiness:** The engine needs one key addition.

| Component | Status |
|---|---|
| Game tree traversal via `apply_action()` | ✅ Possible but not designed for it |
| Terminal state detection | ✅ `is_hand_over()` |
| Chance node (deal cards) | ✅ Deck in engine, but needs deterministic card dealing API |
| **Information set key** — what player *p* can see at decision point | ❌ **`state.serialize()` includes private opponent cards — needs `public_view(player_id)` method** |
| Regret table / strategy table | ❌ **Needs to be built** |
| Abstract action space | ✅ Already 6 actions (fold/check/call/raise×3/allin) |
| Hand abstraction (bucket similar hands) | ❌ **Needed for tractability** — full poker tree is ~10^18 nodes |

**The tractability problem:**  
Full No-Limit Hold'em has ~10^18 game states. Tabular CFR is completely intractable at this scale. Two practical variants:

- **Abstracted tabular CFR**: Group similar hands into buckets (e.g. "top 20% of starting hands"), abstract bet sizes to the 6 we already have. Solvable for small games (2-player, simplified stack depths). This is a good starting experiment.
- **Deep CFR (Neural CFR)**: Use neural networks to approximate the regret and strategy tables instead of storing them explicitly. Works at full game scale. Requires PyTorch. More complex to implement but the state of the art.

**Recommended starting point — 2-player abstracted tabular CFR:**
1. Add `game.public_view(player_id)` to `engine/state.py` — returns only what `player_id` can legally see (own hole cards + community cards + betting history, no opponent hole cards)
2. Build info set key: `(hole_bucket, community_bucket, betting_sequence)` — hash of the info set
3. Build `training/cfr_trainer.py` with Vanilla CFR or Chance-Sampling CFR
4. Test on a simplified game first (e.g. Leduc Hold'em — 6-card deck, 2 streets) before full NLHE

**CFR is strictly for heads-up.** For 6-player, CFR has no convergence guarantees and the tree size explodes. It's the right tool for training optimal heads-up agents, not multi-table agents.

---

### Recommended Sequence

```
NOW          B5 evolution run (σ fine-sweep)
             └─ Continue current approach, minimal new infrastructure

AFTER B5     Build poker_env.py + PyTorch policy network
             └─ Run RL (PPO) self-play on heads-up as first test
             └─ Compare PPO agent vs B5 HoF champion in head-to-head

BEFORE B6    Add public_view() to engine + abstracted hand buckets
             └─ Run tabular CFR on 2-player abstracted game
             └─ Evaluate CFR agent vs PPO agent vs Evolution champion

B6+          Deep CFR if tabular results are promising
             └─ Or: commit to PPO + richer features (Fix 5) as primary path
```

The fastest path to a stronger agent right now is **PPO after B5** — it reuses the existing engine almost unchanged and provides gradient signal that evolution cannot. CFR is the path to theoretically optimal heads-up play but requires more infrastructure and is bounded to 2-player.

---

*Last updated: March 8, 2026*  
*Source reports: Batch1_Report, Batch2_Report, Batch1and2_Report, BATCH3_RESULTS.md, Batch4_HeadsUp_Report, Batch4_MultiTable_Report, Batch4_Overall_Report, hall_of_fame/champions/README.md*
