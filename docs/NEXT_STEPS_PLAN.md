# PokerBot — What To Do Next

**Written**: March 8, 2026  
**Updated**: March 9, 2026  
**Status**: Phase 1 ✅ complete. Phase 2 ✅ complete. **Phase 3 (PPO) is the active work item.**

B6 result: the aggression fix is architecturally correct but did not improve evolved agents (compensated weights). Both B6 agents lost to their B5 counterparts in their native formats. Evolution ceiling is fully confirmed. Proceeding to PPO.

---

## The Decision: Stop More Evolution, Start Architecture Work

The two previous recommendations were not in conflict — they described the same path at
different time horizons. Here is the single unified sequence:

```
PHASE 1 (now)          Architecture Fix 1 — implement opponent aggression feature
PHASE 2 (after fix)    Run one targeted B6 experiment to measure the fix's impact
PHASE 3 (after B6)     Transition to RL (PPO) self-play
PHASE 4 (optional)     CFR for heads-up theoretically optimal play
```

**Do NOT run another full hyperparameter sweep batch.** B5 confirmed σ=0.04 at 100% MT win rate.
More sigma tuning will not meaningfully improve performance. The ceiling is the feature set,
not the training process.

---

## Phase 1 — Architecture Fix 1: Opponent Aggression Feature ✅ COMPLETE

**Completed**: March 9, 2026

The fix was implemented in `engine/features.py`:
- `build_feature_vector_jit()` now takes `opponent_aggression: float` as a new parameter
- `get_state_vector()` computes `opponent_aggression = 1.0 if to_call > bb else 0.0` (facing_raise signal)
- Both JIT and NumPy fallback paths updated
- Stale Numba disk cache cleared after signature change
- Verified: `features[15]` returns `0.0` pre-raise, `1.0` after opponent raises

The signal mirrors `FeatureCache.get_features()[15]` exactly, making inference and training paths consistent for the first time.

**Note**: The fix is in the codebase permanently. Do not revert.

---

## Phase 2 — B6 Experiment (Measure the Fix) ✅ COMPLETE

**Completed**: March 9, 2026  
**Result: The fix did not improve evolved agents.**

### What ran

| Config | Result |
|---|---|
| `p12_m8_h500_s0.04_aggfix_seeded_hof4_g50` | MT: 43.8% (−4.4pp vs B5 champ's 48.2%). Lost H2H. |
| `p12_m7_h375_s0.06_hu100_aggfix_seeded_hof4_g50` | HU: 72.2% (−11pp vs B5 champ's 83.3%). Lost H2H. |

### Why it didn't help

The B5 champion weights were trained for 50 generations with `features[15] = 0.5`. The weights
for input slot 15 effectively learned to ignore it (near-zero weight) or compensate via other
features. Seeding B6 from these weights means starting with compensated weights that expect a
constant signal. Evolution adapts in 50 generations but does not fully reconverge.

### What it means

- The aggression fix benefits **fresh** training runs only (i.e. PPO training from scratch)
- It will not help an evolutionary run seeded from pre-fix champion weights without many more generations (>200), which is not cost-effective
- The fix stays in the codebase permanently for PPO
- **Evolution ceiling is confirmed.** No more evolution batches needed.

### Decision (per plan): Proceed to Phase 3 — PPO

---

## Phase 3 — RL (PPO) Self-Play ← CURRENT PRIORITY

**Status**: Not started. All infrastructure to be built from scratch.

After Phase 2 confirmed the aggression fix does not help evolution, the path to a stronger
agent is a new training paradigm. PPO reuses the existing engine almost unchanged and
provides a per-action gradient signal that evolution cannot.

### Nothing RL-related exists yet

Searches confirm zero existing RL code: no gym wrapper, no PyTorch network, no PPO trainer.
Everything in this phase is new code.

### What to build

**Step 1 — Gym environment wrapper** (`training/poker_env.py`)

```python
class PokerEnv:
    def reset() -> np.ndarray:       # returns 17-float observation vector
    def step(action: int) -> tuple:  # returns (obs, reward, done, info)
```

- Observation: same 17-feature vector from `engine/features.py`
- Reward: chip delta at end of hand, normalised to BB/100
- Action: integer 0–5 (same 6-action abstract space)
- Opponent: pool sampler rotating through HoF champions + random agent

The engine already supports `apply_action()` and `is_hand_over()` for single-step calls.
The wrapper is thin — roughly 100 lines of new code.

**Step 2 — PyTorch policy network** (`training/policy_network_torch.py`)

Same architecture as the existing NumPy network: `17 → 64 → 32 → 6`.
Additions needed for PPO:
- `log_softmax` output
- `entropy()` method
- Value head (separate `32 → 1` branch off the last hidden layer for actor-critic)

**Step 3 — PPO trainer** (`training/rl_trainer.py`)

Standard PPO:
- Collect 2048-step rollouts from `PokerEnv`
- Compute advantages with GAE (λ=0.95, γ=1.0 — no time discounting in poker)
- Clip ratio update (ε=0.2)
- Entropy bonus (β=0.01) to prevent premature strategy collapse
- Opponent pool: start with random agent, add HoF champions progressively

**Step 4 — Evaluate against evolution champions**

Use existing `scripts/evaluation/match_agents.py`.
Add a PyTorch network loader alongside the existing NumPy weight loader.

### Target and starting point

Start with **heads-up only** (2-player). HU has cleaner reward signal — one opponent,
no multi-way pot attribution issues. Target: beat B5 HU champion (88.0% win rate)
within 100k training hands. If PPO HU beats 88%, the architecture transition is
validated and multi-table RL follows.

---

## Phase 4 — CFR (Optional, Heads-Up Only)

CFR produces provably near-optimal strategies for 2-player zero-sum games. For heads-up poker
it can converge to a Nash equilibrium that RL cannot guarantee.

**Prerequisites not currently implemented**:
- `engine/state.py` needs `game.public_view(player_id)` hiding opponent hole cards.
  Currently the state exposes all cards — CFR requires imperfect-information game trees.
- Card abstraction layer: equity buckets for hole cards + board texture to keep the tree tractable

**Components to build**:
1. `engine/state.py` — add `public_view(player_id)` method
2. Info-set key: `(hole_bucket, board_bucket, bet_sequence_hash)`
3. `training/cfr_trainer.py` — Vanilla CFR or Chance-Sampling CFR

**Note**: CFR is bounded to 2-player. For multi-table play, RL remains the only option.
Pursue CFR only if theoretically optimal 1v1 play is a specific goal.

---

## Project Cleanup & Reorganisation

### Checkpoints — archive dead-end runs

These directories contain weights that will never be used again as seeds (σ≥0.09, σ=0.1,
p=40 non-seeded, all `_hu30_` configs, p=20 era). They clutter `checkpoints/`.

**Move to `checkpoints/archived_configs/`**:

```
All deep_p12_m*_h*_s0.09_*          (σ=0.09 permanently retired)
All deep_p12_m*_h*_s0.1_*           (σ=0.1 dead zone)
All deep_p12_m*_h*_s0.08_*          (σ=0.08 era — not a seed source)
All deep_p12_m*_hu30_*              (hybrid training — confirmed failure)
All deep_p20_*                      (p=20 era — consistently underperformed)
All deep_p40_*                      (p=40 era — superseded by p=12)
evolution_run/                      (stale root-level run directory)
runs/                               (stale root-level run directory)
```

**Keep active** (potential B6 seed sources):
```
deep_p12_m8_h500_s0.04_seeded_hof3_g50        ← B5 MT champion source
deep_p12_m7_h375_s0.06_hu100_seeded_hof3_g50  ← B5 HU champion source
deep_p12_m8_h500_s0.05_seeded_hof3_g50        ← B4 MT champion source (still strong)
deep_p12_m8_h500_s0.045_seeded_hof3_g50       ← B5 midpoint (comparison only)
deep_p12_m7_h375_s0.05_hu100_seeded_hof3_g50  ← B5 HU σ=0.05 (77.3%)
deep_p12_m7_h250_s0.06_hu100_seeded_hof3_g50  ← B5 HU h=250 (84.7%)
```

### Root-level scripts — move legacy batch runners

Currently four separate `run_batch*.py` files that are nearly identical.
Move old runners to `scripts/legacy/` to keep the root clean:

```
scripts/legacy/run_batch3_tournament.py    (moved from root)
scripts/legacy/run_batch4_tournament.py    (moved from root)
scripts/legacy/run_archive_tournament.py   (moved from root)
scripts/legacy/run_specific_configs.py     (moved from root)
scripts/legacy/train_configs.sh            (moved from root)
```

Keep at root (active):
```
run_batch5_configs.py      ← canonical training runner template
run_batch5_tournament.py   ← canonical tournament runner template
```

### Docs — consolidate documentation

Currently 13+ `.md` files live at root. Create a `docs/` folder:

```
docs/
  history/
    BATCH4_PREP_CHANGES.md
    GLOBAL_SYNTHESIS_REPORT.md
    TRAINING_FINDINGS_REPORT.md
  ARCHITECTURE.md              ← merge OPTIMIZATION_DOCS.md + README arch section
  HYPERPARAMETERS.md           ← merge all 4 HYPERPARAMETER_*.md files
  TRAINING_GUIDE.md            ← merge SWEEP_WORKFLOW_GUIDE.md + OPTIMIZATION_GUIDE.md
  HOF_GUIDE.md                 ← merge HOF_IMPACT_ANALYSIS.md + hall_of_fame/README.md
  ANALYSIS_GUIDE.md            ← rename ANALYSIS_CAPABILITIES.md
```

Keep at root only:
```
README.md                 ← main entry point (links to docs/)
TOTAL_RESULTS.md          ← living results log
NEXT_STEPS_PLAN.md        ← this file
```

### tests/ — not empty

`tests/` is completely empty. Add at minimum:

```
tests/test_engine.py      ← verify PokerGame runs a full hand without crashing
tests/test_features.py    ← verify all 17 features are in [0.0, 1.0] range
tests/test_actions.py     ← verify each of the 6 abstract actions resolves correctly
```

### hall_of_fame/milestones/ — populate or remove

The directory exists but is empty. Either:
- Add milestone `.npy` snapshots (e.g., first agent to hit 80% HU, first 90%+ MT)
- Or remove the directory if there is no intent to use it

---

## Summary Checklist

### Phase 1 — Feature Fix ✅ DONE
- [x] Fix `features[15]` in `engine/features.py` — real aggression metric (facing_raise)
- [x] Verify `engine/game.py` exposes action history for aggression computation
- [ ] Add `tests/test_features.py` — smoke test feature ranges after fix *(still outstanding)*

### Phase 2 — B6 Experiment ✅ DONE
- [x] Create `run_b6_aggfix_experiment.py` — 2 configs only
- [x] Run B6 (50 gens each, seeded from B5 champions)
- [x] Head-to-head tournament: aggfix agents vs B5 HoF champions
- [x] Decision: aggfix did NOT improve performance → proceed to PPO

### Phase 3 — PPO Transition ← DO THIS NOW
- [ ] Create `training/poker_env.py` — gym-style wrapper
- [ ] Create `training/policy_network_torch.py` — PyTorch port with value head
- [ ] Create `training/rl_trainer.py` — PPO loop with HoF opponent pool
- [ ] Evaluate PPO vs B5 HU champion — target: beat 83.3%–88.0%

### Phase 4 — CFR (optional, heads-up only)
- [ ] Add `game.public_view(player_id)` to `engine/state.py`
- [ ] Build info-set key + card abstraction
- [ ] Create `training/cfr_trainer.py`

### Cleanup (anytime)
- [ ] Archive σ≥0.08, p=20, p=40, hu30 checkpoint dirs to `archived_configs/`
- [ ] Move legacy batch runners to `scripts/legacy/`
- [ ] Create `docs/` folder and consolidate 13 root-level .md files
- [ ] Populate or remove `hall_of_fame/milestones/`
- [ ] Add `tests/test_engine.py` and `tests/test_actions.py`

---

## What NOT To Do

| Temptation | Why to avoid |
|---|---|
| Run B6 σ=0.03 full sweep | σ=0.04 is already at 100% MT. Lower σ with seeding adds marginal gain vs investing in features. |
| Run another 13-config hyperparameter batch | The bottleneck is features, not σ. More evolution batches will not break the ceiling. |
| Expand feature vector 17→22 immediately | Breaks all existing champion weights. Only worth doing when committing to full retraining from scratch. |
| Start RL before fixing aggression | ✅ Already done. `features[15]` is now a real signal. |
| Run evolution after PPO works | Once PPO beats 83.3% HU, evolution is retired. Do not mix paradigms. |

---

*Last updated: March 9, 2026*  
*Phase 1 (aggfix) and Phase 2 (B6 experiment) complete. Phase 3 (PPO) is active.*
