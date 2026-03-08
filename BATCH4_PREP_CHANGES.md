# Batch 4 Preparation — Changes Log

**Date:** February 28, 2026  
**Scope:** Post-Batch 3 cleanup, HoF refresh, and mixed-format training implementation

---

## 1. Checkpoint Archiving

**Script:** `scripts/batch4_prep.py`  
**Destination:** `checkpoints/archived_configs/batch3_poor_performers/`

### What was archived

| Category | Configs | Reason |
|---|---|---|
| All m=9 | `deep_p{12,20,40}_m9_*` | Worst matchup count across every format (33.7% combined, 45.2% HU, 32.2% MT) |
| h=750 + p≥40 + g200 | `deep_p40_m{7,8}_h750_*_g200` | Dead zone: up to −30pt vs g50 equivalent. HoF overfitting at high capacity |
| Bottom B3 combined | `deep_p40_m8_h500_s0.1_hof3_g200` | 25.2% combined (#57), confirmed underperformer |
| m=6 era | `deep_p{12,20,40}_m6_*` | Superseded by m=7/m=8 in all batches; no recovery path |

### What was NOT archived (restored from accidental archive)

- `deep_p40_m8_h750_s0.07_hof3_g200` — was mis-classified as dead zone. σ=0.07 is the exception: it was #4 combined (45.8%) even with h=750+g200+p=40. Restored to active checkpoints.

### Active configs remaining

40 directories — all m=7 or m=8, σ ∈ {0.07, 0.08, 0.09, 0.1}, g50/g200.

---

## 2. Hall of Fame Update

**Location:** `hall_of_fame/champions/`  
**Previous count:** 4 agents  
**Current count:** 6 agents

### Agents archived out of HoF

| File | Reason |
|---|---|
| `p12_m6_h750_s0.1_g200_champion.npy` | B1/B2 era m=6 — superseded in every metric |
| `p12_m6_h750_s0.1_g50_champion.npy` | Same config, early convergence variant — no longer competitive |

Moved to `hall_of_fame/archived/`.

### Agents added to HoF (B3 champions)

| File | Source Config | Tournament Result | Why Added |
|---|---|---|---|
| `p12_m8_h500_s0.09_g200_b3_champion.npy` | p12, m=8, h=500, σ=0.09, g200 | **#1 HeadsUp (81.3%)**, #2 Combined | Injects 1v1 specialist pressure — previously absent from HoF |
| `p12_m8_h750_s0.1_g200_b3_champion.npy` | p12, m=8, h=750, σ=0.1, g200 | **#1 MultiTable (57.7%)**, #1 Combined | Dominant 6-player specialist, highest combined win rate |
| `p12_m7_h500_s0.08_g200_b3_champion.npy` | p12, m=7, h=500, σ=0.08, g200 | #3 Combined (46.1%), #7 HeadsUp | Format-generalist; m=7 strategy diversity not previously in HoF |
| `p40_m8_h750_s0.07_g200_b3_champion.npy` | p40, m=8, h=750, σ=0.07, g200 | #4 Combined (45.8%) | Only σ=0.07 data point — injects low-sigma weight-space region |

### Agents retained from previous HoF

| File | Reason kept |
|---|---|
| `p12_m8_h500_s0.08_g200_champion.npy` | Prior era reference; σ=0.08 at m=8 canonical config |
| `p40_m8_h375_s0.1_champion.npy` | Large-pop, fast-training baseline; different population dynamics |

### Effect on B4 Training

Training agents in B4 must now beat **both** a HU specialist (81.3%) and a MT specialist (57.7%) simultaneously in their HoF matchups.  
The old HoF had no HU-oriented agent — there was zero evolutionary pressure to develop 1v1 skills. This directly caused the format inversion seen in B3.

---

## 3. Mixed-Format Training — Code Changes

### 3a. `training/config.py` — `FitnessConfig`

**Added fields:**

```python
heads_up_fraction: float = 0.0      # 0 = all MT, 0.333 = 1-in-3 HU, 1.0 = all HU
hu_hands_per_matchup: int = 500     # Hands for HU matchups (can differ from MT hands)
```

**Added derived properties:**

```python
@property
def num_hu_matchups(self) -> int:
    return round(self.matchups_per_agent * self.heads_up_fraction)

@property
def num_mt_matchups(self) -> int:
    return self.matchups_per_agent - self.num_hu_matchups
```

**Default is `heads_up_fraction=0.0`** — all existing configs and training scripts continue to work without modification (fully backward compatible).

---

### 3b. `training/config.py` — New factory `TrainingConfig.for_balanced_formats()`

```python
TrainingConfig.for_balanced_formats()
```

| Parameter | Value | Rationale |
|---|---|---|
| population_size | 12 | Best across B3 with HoF |
| mutation_sigma | 0.08 | Empirical optimum, σ=0.5/√p formula |
| matchups_per_agent | 9 | 3 HU + 6 MT (not the all-MT m=9 dead zone) |
| heads_up_fraction | 0.333 | 1-in-3 matchups HeadsUp |
| hands_per_matchup | 500 | MT hands: avoids opponent memorization at h=750 |
| hu_hands_per_matchup | 500 | HU hands: same budget |
| num_generations | 200 | Standard depth |

Note: `matchups_per_agent=9` here is not the same as the retired m=9 configs. Those were all-MT at m=9. This is 9 total matchups split 3 HU + 6 MT, which gives the MT portion an effective m=6 signal and the HU portion an m=3 signal.

---

### 3c. `training/fitness.py` — `create_opponent_groups`

**Before:** Returned `(groups, hof_tracking)` — a 2-tuple. All matchups used `num_players - 1 = 5` opponents.

**After:** Returns `(groups, hof_tracking, player_counts)` — a 3-tuple.  
- `player_counts[i]` is the table size for matchup `i`: `2` for HeadsUp, `num_players` (6) for MultiTable
- HU matchups sample only **1 opponent** (not 5); opponent sampling ratios (70/20/10) preserved
- Matchup order is **shuffled every generation** — agent cannot predict which matchup will be HU vs MT

---

### 3d. `training/fitness.py` — `evaluate_matchup`

**Added parameter:** `num_players_override: Optional[int] = None`

When set, this overrides `fitness_config.num_players` for the duration of that single matchup call. Used by the worker to spin up a 2-player game for HU matchups.

---

### 3e. `training/fitness.py` — `_worker_evaluate_genome`

**Before:** Unpacked 7-element args tuple. All matchups used `fitness_config.num_players` and `fitness_config.hands_per_matchup`.

**After:** Accepts optional 8th element `player_counts`. For each matchup:
- Reads `player_counts[matchup_idx]` to get table size
- Uses `hu_hands_per_matchup` if `n_players == 2`, else `hands_per_matchup`
- Calls `evaluate_matchup(..., num_players_override=n_players)`
- Fitness is still a single **BB/100 pooled across all hands** (HU + MT combined)

---

### 3f. `training/evolution.py` — `evaluate_population_fixed_hands`

Updated the `create_opponent_groups` unpacking call to handle the new 3-tuple return value:

```python
# Before
opponent_groups, _ = self.evaluator.create_opponent_groups(...)

# After
opponent_groups, _, player_counts = self.evaluator.create_opponent_groups(...)
```

---

## 4. Net Effect Summary

| Before | After |
|---|---|
| HoF had no HU specialist → zero 1v1 training pressure | HoF includes #1 HU agent (81.3%) → all B4 runs face 1v1 pressure |
| All matchups 6-player → format specialization unimpeded | 1-in-3 matchups HeadsUp → BB/100 penalises HU weakness directly |
| h=750+p40+g200 still active → dead zone re-run risk | Archived |
| m=6 era checkpoints cluttering workspace | Archived |
| `for_balanced_formats()` config did not exist | Added as recommended B4 starting point |
| `FitnessConfig` had no format-mixing controls | `heads_up_fraction` and `hu_hands_per_matchup` added |

---

## 5. How to Use Mixed-Format Training in B4

**Option A — Recommended balanced config:**
```python
from training.config import TrainingConfig
cfg = TrainingConfig.for_balanced_formats()
```

**Option B — Custom ratio:**
```python
from training.config import TrainingConfig, FitnessConfig
cfg = TrainingConfig()
cfg.fitness.heads_up_fraction = 0.5      # 50/50 HU vs MT
cfg.fitness.matchups_per_agent = 8       # 4 HU + 4 MT
cfg.fitness.hu_hands_per_matchup = 375   # shorter HU matchups (less opponent memorization)
cfg.fitness.hands_per_matchup = 500      # standard MT matchup depth
```

**Option C — Pure MT (unchanged behaviour):**
```python
cfg.fitness.heads_up_fraction = 0.0     # default; all matchups are 6-player
```

---

## 6. Files Changed

| File | Change type |
|---|---|
| `training/config.py` | Added `heads_up_fraction`, `hu_hands_per_matchup`, `num_hu_matchups`, `num_mt_matchups`, `for_balanced_formats()` |
| `training/fitness.py` | Extended `create_opponent_groups` return (3-tuple), added `num_players_override` to `evaluate_matchup`, reworked `_worker_evaluate_genome`, updated `evaluate_single` |
| `training/evolution.py` | Updated `evaluate_population_fixed_hands` unpacking |
| `scripts/batch4_prep.py` | New script — checkpoint archiving + HoF update (one-time run) |
| `hall_of_fame/champions/` | 2 old files archived, 4 new B3 champions added |
| `checkpoints/archived_configs/batch3_poor_performers/` | All m=9, m=6, and h=750+p40+g200 configs moved here |
