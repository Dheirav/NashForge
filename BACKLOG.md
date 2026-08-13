# Backlog

Open work, in the order it unblocks other work. Items carry a file reference where one
exists. Anything already settled lives in [`CODEBASE_AUDIT.md`](CODEBASE_AUDIT.md) rather
than here; this file is only what is still to do.

**Last reviewed:** 13 August 2026.

---

## 1. Blocking — the exploitability bound is too weak to answer the question it was built for

The crossover experiment ran to completion on 13 August and could not reach a conclusion:
across 40/160/640/2560-second budgets and three seeds, only the **40s** rung produced an LBR
bound that cleared zero for both bucketing signals. Above it the bound went slack, and at
2560s both signals measured *negative* — meaning the greedy exploiter lost money, not that
the strategies approached equilibrium.

**Measured, 13 August.** The obvious hypothesis — that the three LBR defects fixed the same
day were the whole cause — was tested directly and is false. Equity bucketing, seed 0,
retrained to the 59,050 iterations of the 2560s rung, measured with both exploiters over
1,000 hands at 20 rollout samples:

| exploiter | LBR | 95% CI | verdict |
|---|---|---|---|
| pre-fix (control) | −4.328 ± 1.205 | [−6.69, −1.97] | slack |
| post-fix | −0.172 ± 0.938 | [−2.01, +1.67] | slack |

The control reproduced the overnight run's −4.328 exactly, so the setup is faithful and the
comparison is sound. The defects accounted for **+4.156 chips/hand** of the slack and
tightened the error bar by 22%, which is a second sign the range is doing real work — but
the interval still straddles zero. Roughly **+2 more chips/hand** are needed to clear it, and
that part is structural rather than a bug.

**Rollout samples are not the lever, measured 13 August.** Same strategy, same exploiter,
1,000 hands per row:

| rollout samples | LBR | 95% CI | seconds |
|---|---|---|---|
| 20 | −0.172 ± 0.938 | [−2.01, +1.67] | 63 |
| 60 | −0.769 ± 0.970 | [−2.67, +1.13] | 77 |
| 120 | +0.518 ± 1.000 | [−1.44, +2.48] | 93 |
| 240 | +0.380 ± 1.087 | [−1.75, +2.51] | 125 |

The means wander non-monotonically across a spread of ~1.3 against standard errors of ~1.0:
a twelvefold cut in decision noise moved nothing detectable. Do not read the 120 row as a
winner — it is the luckiest of four noisy estimates, and extrapolating a required hand count
from it is the winner's curse. (The sweep intended paired hands but did not achieve them: one
rng drives both the rollouts and the dealing, so the streams diverge as soon as the sample
count differs. Fix that before trying to resolve small effects.)

### The actual diagnosis

**LBR is confined to the same abstraction as the strategy it measures.** It chooses among the
same six actions `game.legal_actions` offers the solver, and reads the opponent through the
same bucketing. CFR has converged inside that abstraction, so a greedy player restricted to
it is playing precisely the game its opponent is already near-optimal at. Measuring ≈0 is the
expected outcome of that design, not a shortfall to be tuned away — and no amount of rollout
precision or extra hands changes it.

In the literature LBR gets its teeth by playing *outside* the bot's abstraction: finer bet
sizes and off-tree actions the solver never planned against. That is the fix, and it reorders
what is left:

1. **Give LBR an action set the solver does not have.** This is the fix; the rest is
   refinement around it. Two parts, and the second is where the difficulty lives:
   - Let LBR propose bet sizes outside `RAISE_FRACTION`. `NoLimitHoldem._apply` understands
     only the six abstract actions, so an arbitrary raise amount needs a path through it.
   - **Action translation.** Once LBR bets off-tree the strategy has no entry for that
     history, so predicting the opponent's reply means mapping the off-tree action back onto
     the abstraction. This is the standard translation problem; a naive mapping makes the
     exploiter look strong for the wrong reason, which is worse than a weak bound.
2. **More hands** — but only once the mean is reliably positive. Tightening an interval around
   zero buys nothing.
3. **The second barrel**, last: the rollout assumes no betting after the modelled action,
   which is the standard LBR simplification and the remaining structural slack.

There is a consequence for item 3 below worth stating plainly: an exploiter confined to the
abstraction cannot distinguish *two* abstractions either, because it evaluates each on its
own terms. That may be the real reason the overnight run separated the signals at no depth,
and it means re-running the crossover before fixing this would fail the same way again.

Until then, `crossover.py` correctly reports "bound is slack" rather than naming a winner.
Do not weaken that check to obtain a result.

## 2. Answer the crossover question directly, by playing the two agents against each other

Not blocked by item 1, and worth doing first because it is assembly rather than algorithm
work.

`crossover.py` asks *"given N seconds of training, which bucketing should I use."* That
question does not require exploitability. Train one agent per signal to the same wall-clock
budget and play them head to head; whoever wins chips answers it.

The machinery exists and is currently unused. `games/nolimit.py:278` has
`information_set_with`, written precisely so two agents trained on *different* abstractions
can meet — each is asked the question its own bucketing poses, rather than one being handed
the other's key and losing for a mismatched lookup rather than for bad play. `cfr/play.py`
supplies the hand loop, seat alternation, standard errors and `separated_from_zero`.

Be honest about what it does and does not establish: beating the other abstraction does not
show either is near equilibrium, so this does not replace item 1. It answers the practical
question, not the theoretical one. Size the hand count from the measured noise floor rather
than convention — `play_hands` reports the standard error needed to do that.

## 3. Re-run the crossover experiment

The numbers in `results/cfr/crossover.json` were produced by an LBR carrying three defects,
all fixed on 13 August (see the changelog below). They should not be quoted. The run costs
roughly seven hours on a quiet machine and checkpoints per measurement, so it resumes from
an interruption rather than restarting.

Sequence it *after* item 1 — re-running against the same weak bound would reproduce the same
non-conclusion at the same cost.

## 4. Recover or replace the paper

`CODEBASE_AUDIT.md:264` defers every remaining open question to the threats-to-validity
section of `IEEE_CFR_Poker_Engine_Paper_v3.pdf`. **That file is not in the repository, not in
git history, and not anywhere under the home directory.** Whatever was recorded there is the
real backlog for the CFR work and is currently lost. Either recover the PDF or reconstruct
its threats-to-validity section here.

---

## Open decisions

### `scripts/testing/` — three scripts exercising the old feature layer

`test_ai_features.py`, `test_ai_hands.py` and `test_cli.py` (482 lines) predate the audit and
target the observation vector that E5 below describes as needing rebuilding. They were left
in place when the rest of the evolutionary pipeline was removed on 13 August, because they
were outside the agreed scope, not because they were judged worth keeping. Decide.

### `examples/` — one script and a README for the removed workflow

`train_vs_champions.py` imports only from `training/`, which is retained, so it still runs.
What it demonstrates — training against Hall of Fame champions — no longer has champions to
train against: `hall_of_fame/` holds nothing but `FAULTY_PIPELINE_NOTICE.md`. Its README was
patched on 13 August to remove links to four documents that no longer exist, but patching is
not a decision. Same question as `scripts/testing/`: keep, or remove with the rest.

### Experiment logs are not versioned

`.gitignore` excludes `logs/`, so `logs/crossover.log` — which timestamps every poll, records
when the machine went quiet and carries the per-measurement load average — is untracked. For
a wall-clock experiment that log *is* part of the evidence. Either carve out an exception or
copy the relevant log into `results/cfr/` alongside the JSON.

### `results/cfr/nolimit_strategy.pkl` cannot be loaded by current code

The pickle carries a `CardAbstraction` written before commit `6054b81` added `_centroid_list`,
the plain-list mirror of the centroids that `bucket()` now reads for its binary search.
Unpickling therefore yields an abstraction whose `_centroid_list` is `None`, and every
postflop lookup raises `TypeError: 'NoneType' object is not subscriptable`.

Nothing in the repository trips on this today — `measure_exploitability.py` retrains rather
than loading the file — so it fails only for someone trying to reuse the saved strategy,
which is the file's entire purpose. The clustering itself is intact, so the repair is a
rebuild rather than a refit:

```python
abstraction._centroid_list = {street: c.tolist()
                              for street, c in abstraction._centroids.items()}
```

Either re-save the artifact from a current run, or give `CardAbstraction` a
`__setstate__` that reconstructs the derived field. The second is worth preferring: this
class is pickled precisely so results outlive the code that produced them, and a derived
field that silently arrives as `None` will do this again.

### Loose artifacts at the repository root

`trained_demo_agent.npy` is an untracked genome from the superseded pipeline. `.agent.md` is
an untracked agent definition for generating academic reports, unrelated to the poker work.
Neither is referenced by anything. Delete or place deliberately.

---

## Deferred by choice

Both are the remaining halves of audit findings, and both carry a reasoned argument for
waiting. Recorded here so the reasoning is not rediscovered from scratch.

### E5 — the observation still has a duplicate pair

`engine/features.py`. `stack_normalized` and `commitment` correlate at r = −1.00; they are
algebraically the same number. Removing one takes the observation from 17 dimensions to 16,
which invalidates every saved genome and touches `NetworkConfig.input_size` and
`PPOConfig.obs_size`.

**Trigger:** a decision to resume work on `training/` or `rl/`. Not worth doing before that,
and not worth skipping after.

### S6 — `self_play.play_match` keeps its own hand loop

`training/self_play.py`. It drives arbitrary agent objects rather than policy networks and
accumulates per-hand VPIP/PFR statistics, so it cannot simply delegate to the batched path.
Unifying it means expressing that path through a per-seat `decide()` callback, giving up the
cross-game batching that makes training fast.

**Trigger:** same as E5.

---

## Changelog

### 13 August 2026 — three defects in Local Best Response, one in its caller

Found by reading `cfr/lbr.py` against `abstraction/buckets.py`; all four fixed, with
regression tests. `tests/` went from 148 to 150.

- **The range was carried across streets without re-bucketing.** `CardAbstraction` fits a
  separate k-means per street, so bucket 3 on the flop and bucket 3 on the turn are unrelated
  categories. The belief vector was indexed by bucket and never reset, so a read accumulated
  on one street was applied to different hands on the next. Preflop was worse still: it
  indexed a Chen-score table through a postflop bucket count. **Fixed** by tracking a weighted
  set of candidate *hands* and re-bucketing them against whatever board is actually out
  (`cfr/lbr.py`, class `Range`).
- **`_win_probability` always bucketed against the completed river board**, whatever street
  the belief was formed on — self-consistent only on the river. Removed with the same change.
- **LBR read `state.hole[1 - me]`**, the cards of the player it was exploiting, and excluded
  them from its own sampling pool. Its rollouts therefore never considered the opponent
  holding the hand they actually held. **Fixed**, and pinned by
  `test_the_exploiter_never_reads_the_cards_it_is_exploiting`.
- **`crossover.py` declared a winner from slack bounds.** It marked the lower LBR "ahead"
  unconditionally, so at 2560s — where both values are negative — it reported equity as ahead
  when the only fact available was that the exploiter lost more money against it. It now
  requires both bounds to clear zero before naming a winner.

Also: `ms_per_iteration` divided one rung's seconds by every iteration ever run (`elapsed` is
incremental, `solver.iterations` cumulative), understating cost by about 30% on every rung
after the first — reported ~30 ms where the true figure was ~43 ms. And the pooled error bar
averaged the per-seed standard errors, which estimates the noise of a single seed rather than
the uncertainty of their mean; it now takes the larger of the within-seed and between-seed
estimates.

### 13 August 2026 — the evolutionary pipeline was removed from master

13,816 lines across 39 files: `scripts/analysis`, `scripts/evaluation`, `scripts/training`,
`scripts/utilities`, fifteen root-level scripts, and `SWEEP_WORKFLOW_GUIDE.md`. Recoverable
by name:

```bash
git show pre-cfr-pipeline:scripts/training/hyperparam_sweep.py
git checkout pre-cfr-pipeline -- scripts/analysis
```

`scripts/run_ppo_training.py` was kept: it drives `rl/`, which the audit retains.
