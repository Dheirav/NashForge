# PokerBot — What To Do Next

**Written**: March 8, 2026  
**Status at writing**: B5 complete. 4 active HoF champions. σ floor reached at 0.04 (100% MT win rate).

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

## Phase 1 — Architecture Fix 1: Opponent Aggression Feature

**Why first**: Single-line code change in the feature extractor. Highest impact-to-effort ratio
of any possible improvement. The network currently has zero opponent-read capability — `features[15]`
has been hardcoded to `0.5` since the very first training run.

### What to change

**File: `engine/features.py`** — two locations:
- Line 81: inside `build_feature_vector_jit()` (JIT/Numba path)
- Line 427: inside `extract_features()` (numpy fallback path)

Replace `features[15] = 0.5` with a real running aggression metric:

```python
# aggression = fraction of opponent actions that were bets or raises this hand
aggression = (num_bets + num_raises) / max(total_opponent_actions, 1)
features[15] = float(aggression)
```

This must be passed in as a parameter. The `PokerGame` action history in `engine/game.py`
already tracks all actions — the metric can be computed per opponent from `game.history`.

**Files to touch**:
1. `engine/features.py` — replace constant with the computed value at both locations
2. `engine/game.py` — verify action history is accessible; add helper to compute per-opponent aggression
3. `training/config.py` — no change (input_size stays 17, slot 15 already allocated)

### Backward compatibility

All existing `.npy` champion weights remain valid. The network weights for slot 15 already
exist — they were trained on a constant `0.5`. When you seed a B6 run from B5 weights,
the network will immediately receive live data for the input it previously saw as `0.5`,
and evolution will adapt those weights within a few generations. No architecture change,
no retraining from scratch.

### How to verify

Run `scripts/testing/test_ai_features.py` after the change.
Use `scripts/analysis/visualize_agent_behavior.py` to compare agent behaviour against
an aggressive opponent vs a passive opponent — the actions should now differ.

---

## Phase 2 — B6 Experiment (Measure the Fix)

Run **two configs only** — not a full sweep:

| Config | Purpose | Seed |
|---|---|---|
| `p12_m8_h500_s0.04_aggfix_seeded_hof4_g50` | MT with Fix 1 applied | B5 MT champion |
| `p12_m7_h375_s0.06_hu100_aggfix_seeded_hof4_g50` | HU with Fix 1 applied | B5 HU champion |

Name them with `_aggfix_` in the checkpoint directory to distinguish from B5 runs in
tournament reports.

After training, run both against the B5 HoF champions in a head-to-head tournament using
the existing `run_archive_tournament.py` pattern.

**Interpret the result**:
- If aggfix agents beat B5 champions → architecture change has measurable impact, proceed to full feature expansion (Fix 5)
- If aggfix agents tie or lose → the ceiling is not the aggression feature; proceed directly to RL (Phase 3)

**Script to create**: `run_b6_aggfix_experiment.py` — copy `run_batch5_configs.py`, remove all
configs except the two above, point seed weights at B5 champions.

---

## Phase 3 — RL (PPO) Self-Play

After Phase 2, transition to PPO. This replaces evolution as the **training algorithm** —
it does NOT replace the engine. The same `engine/game.py`, same feature vector, same 6-action
abstract action space.

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

### Phase 1 — Feature Fix (do this first)
- [ ] Fix `features[15]` in `engine/features.py` lines 81 and 427 — real aggression metric
- [ ] Verify `engine/game.py` exposes action history for aggression computation
- [ ] Add `tests/test_features.py` — smoke test feature ranges after fix

### Phase 2 — B6 Experiment
- [ ] Create `run_b6_aggfix_experiment.py` — 2 configs only
- [ ] Run B6 (50 gens each, seeded from B5 champions)
- [ ] Head-to-head tournament: aggfix agents vs B5 HoF champions
- [ ] Decision: did the fix improve performance?

### Phase 3 — PPO Transition
- [ ] Create `training/poker_env.py` — gym-style wrapper
- [ ] Create `training/policy_network_torch.py` — PyTorch port with value head
- [ ] Create `training/rl_trainer.py` — PPO loop with HoF opponent pool
- [ ] Evaluate PPO vs B5 HU champion — target: beat 88.0%

### Phase 4 — CFR (optional, heads-up only)
- [ ] Add `game.public_view(player_id)` to `engine/state.py`
- [ ] Build info-set key + card abstraction
- [ ] Create `training/cfr_trainer.py`

### Cleanup (can be done anytime)
- [ ] Archive σ≥0.08, p=20, p=40, hu30 checkpoint dirs to archived_configs/
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
| Start RL before fixing aggression | The gym wrapper uses the same 17 features. If `features[15]` is still fake, PPO hits the same ceiling as evolution. |
| Run evolution after PPO works | Once PPO beats 88% HU, evolution is retired. Do not mix paradigms. |
