# Backlog

Open work, in the order it unblocks other work. Items carry a file reference where one
exists. Anything already settled lives in [`CODEBASE_AUDIT.md`](CODEBASE_AUDIT.md) rather
than here; this file is what is still to do, plus the reasoning behind what was closed.

**Last reviewed:** 15 August 2026.

## State of play

Nothing here is blocking. Items 1–4 are all closed, and the reasoning is kept rather than
deleted because three of them were closed by a negative result — the kind that is expensive to
find and cheap to forget.

| | | |
|---|---|---|
| 1 | Exploitability bound (LBR) | **Closed** — investigation stopped deliberately; no usable bound |
| 2 | Which bucketing to use | **Done** — the crossover, measured at 7.8σ |
| 3 | Re-run the crossover experiment | **Closed** — superseded by item 2, will not be done |
| 4 | Recover the paper | **Largely superseded** by `docs/abstraction-crossover.html` |

What remains is **two audit findings deferred by choice**, each with the condition that would
make them worth doing, and **one substantial piece of work** — the second barrel — that nothing
else depends on. The four maintainer decisions that stood open all week were made on 15 August;
they are recorded below with what was removed and why.

The project's result is the crossover (item 2). It requires none of the LBR machinery, and it
is written up in [`docs/abstraction-crossover.html`](docs/abstraction-crossover.html).

---

## 1. LBR does not produce a usable bound on a converged strategy — investigation closed

> **Conclusion, 14 August.** Four defects fixed and three successive valuation models later,
> LBR still cannot beat a 59,050-iteration strategy at either raise cap. The investigation is
> stopped deliberately rather than abandoned: at some point the honest reading is that a
> greedy one-step exploiter genuinely cannot beat this strategy, and LBR failing to clear zero
> is a legitimate — if weak — result rather than a defect still to be chased. **The project's
> result is the head-to-head crossover (item 2), which needs none of this.**
>
> Final measurements, both strategies from the action-abstraction study, 2,000 hands:
>
> | | original | first fix | conditioned |
> |---|---|---|---|
> | cap 1, on-tree | −0.402 | −3.679 | −3.459 |
> | cap 1, off-tree | −0.415 | −5.104 | **−0.977** |
> | cap 2, on-tree | **+2.783** | −1.185 | −2.900 |
> | cap 2, off-tree | +2.059 | −1.399 | −1.748 |
>
> **No exploitability figure produced before 14 August should be quoted.** The cap-2 row is
> the warning: it read +2.783 and "PROVES EXPLOITABLE" on the afternoon of the 14th, and
> −2.900 that evening, against an identical untouched strategy. Only the exploiter's internal
> valuation changed. Every LBR number in this repository's history is sensitive to a modelling
> choice that was wrong until now.
>
> **Off-tree betting does help, once the valuation is right** — worth +2.5 chips/hand at cap 1
> and +1.2 at cap 2 over the on-tree exploiter. It was worth nothing under the earlier
> valuations because LBR was using it badly. The machinery is correct and kept.
>
> **What remains, if this is ever resumed:** the second barrel. The rollout still assumes no
> betting after the modelled action, which is the last structural simplification and the
> largest remaining source of slack in the literature. It is also the most work. Nothing below
> is blocked on it.

### The three valuation models, and why the first two were wrong

Each was a genuine correctness improvement and each exposed the next layer. Recorded so the
sequence is not rediscovered.

1. **No call counted.** The showdown was valued against the opponent's contribution *before*
   they responded, so every extra chip bet was pure downside and fold equity the only upside.
   The cheapest legal bet won by construction: LBR bet the smallest size offered in 47% of
   decisions, and kept betting it as the floor was lowered and its results got worse.
2. **Call counted, range unconditioned.** Adding the called chips fixed the underbetting and
   broke the other way. Equity was still computed against the opponent's *whole* range, but
   folding removes the weak hands, so whoever calls is stronger than average — increasingly so
   as the bet grows. LBR turned aggressive on 52% of decisions against a converged strategy
   and lost 4.9 chips/hand.
3. **Call counted, range conditioned on calling.** Each raise is priced against the hands that
   would actually call it, by reweighting the range by `1 − P(fold)` per hand. Showdowns are
   sampled once per decision and reweighted per candidate bet, so conditioning each bet on its
   own calling range costs almost nothing rather than one full set of rollouts each.

### The original diagnosis, kept for the record

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

1. ~~**Give LBR an action set the solver does not have.**~~ **Built 14 August. It bought
   nothing.** LBR now chooses from eleven pot fractions (0.25 to 3.5) against the
   abstraction's three, with pseudo-harmonic translation (`abstraction/translation.py`) so an
   off-tree bet is perceived as a probabilistic mixture of its neighbours rather than snapped
   to the nearest. Measured on the same 59,050-iteration strategy, 1,000 hands:

   | exploiter | LBR | 95% CI | verdict |
   |---|---|---|---|
   | on-tree control | −0.402 ± 0.981 | [−2.32, +1.52] | slack |
   | off-tree | −0.415 ± 0.859 | [−2.10, +1.27] | slack |

   A difference of −0.013 against a combined error near 1.3. The diagnosis in this section
   was confident and appears to be wrong, or at least incomplete: escaping the action
   abstraction is not what was holding the bound down.

   **Why it bought nothing: LBR uses the off-tree sizes badly.** Both diagnostics were run on
   14 August (`~/pokerbot-scratch/action_abstraction_study.py`). Off-tree sizes are chosen
   constantly — 47.8% of decisions — so the null result is not vacuous. But 97% of those picks
   are the *smallest size offered*, and lowering the floor shows the choice is degenerate:

   | grid | LBR | share at floor |
   |---|---|---|
   | floor 0.25 | +6.237 ± 2.021 | 46.6% |
   | floor 0.10 | +5.499 ± 2.100 | 46.7% |
   | floor 0.02 | +3.304 ± 1.900 | 48.3% |

   LBR bets the minimum whatever the minimum is, and **its results get worse as the floor
   drops** while it keeps choosing it. That is a valuation error, not a poker insight. The
   one-step model reasons "same fold equity for fewer chips, therefore better", because any
   sub-minimum bet translates to the smallest abstract size deterministically. It misses that
   a 0.02-pot bet builds no pot to win when the opponent calls, and that the opponent's later
   play is keyed to a history claiming a raise that never really happened.

   **Fix the valuation before trusting any off-tree number.** Until an exploiter stops
   choosing bets that lose it money, nothing measured through it means anything.

### `raise_cap=1` was tested too, and the result is confounded

Trained to the same 59,050 iterations at each cap, 1,000 LBR hands:

| | LBR | information sets | iterations/info set |
|---|---|---|---|
| cap 1, on-tree | −0.402 ± 0.981 | 25,089 | 2.354 |
| cap 2, on-tree | **+2.783 ± 1.072** | 446,745 | **0.132** |

The bound clears zero at cap 2 — but holding *iterations* fixed while the game grew 17.8×
means the cap-2 strategy got 0.132 iterations per information set. Most have been visited
less than once. It is not a converged strategy that proved exploitable; it is an untrained
one, and untrained strategies were already known to be exploitable.

The corroboration is in this project's own data: the crossover run measured cap 1 at 4,075
iterations (≈0.177 iterations/info set) at **+3.366 ± 1.001** — indistinguishable from cap 2's
+2.783 at 0.132. Different raise caps, near-identical training density, near-identical
exploitability.

**So exploitability tracks training density, not raise cap**, and the conclusion printed by
the study script ("raise_cap=1 was the constraint") does not follow. The confound was designed
in: varying raise_cap while holding iterations constant necessarily varies convergence too.

The useful consequence: the bound going slack at cap 1 / 59,050 iterations is a fact about the
*strategy* — a converged strategy resists a greedy one-step exploiter even in a coarse
abstraction — rather than a defect in the measurement. It still proves nothing about nearness
to equilibrium, since LBR only ever bounds from below.

Answering the raise-cap question properly needs cap 2 trained to matched density, about 1.05M
iterations — roughly 18× the cost, and not worth spending before the valuation is fixed.

2. **More hands** — but only once the mean is reliably positive. Tightening an interval around
   zero buys nothing.
3. **The second barrel**, now the leading candidate rather than the last resort: the rollout
   assumes no betting after the modelled action. With the action-set hypothesis measured and
   dead, this is the largest remaining structural simplification.

There is a consequence for item 3 below worth stating plainly: an exploiter confined to the
abstraction cannot distinguish *two* abstractions either, because it evaluates each on its
own terms. That may be the real reason the overnight run separated the signals at no depth,
and it means re-running the crossover before fixing this would fail the same way again.

Until then, `crossover.py` correctly reports "bound is slack" rather than naming a winner.
Do not weaken that check to obtain a result.

## 2. ~~Answer the crossover question directly~~ — DONE, 14 August

**The crossover exists.** `scripts/cfr/head_to_head.py`, 3 seeds, 20,000 hands per matchup,
seats alternating. Positive favours equity; results in `results/cfr/head_to_head.json`.

| budget | equity iters | made_hand iters | chips/hand | verdict |
|---|---|---|---|---|
| 40s | 1,075 | 5,600 | −3.136 ± 0.729 | made_hand ahead |
| 160s | 3,808 | 19,758 | −1.531 ± 0.164 | made_hand ahead |
| 640s | 14,850 | 73,158 | +0.273 ± 0.203 | not separated |
| 2560s | 60,117 | 288,050 | **+0.916 ± 0.118** | **equity ahead** |

Made-hand bucketing wins at short budgets on sheer iteration count, the lead vanishes around
640s, and equity takes a separated lead by 2560s at about 7.8σ — winning on roughly a fifth
of the opponent's iterations (60,117 against 288,050). The crossing point lies between 640s
and 2560s; the budgets tested do not locate it more precisely than that.

All three seeds agree on direction at every rung. At 2560s they give +1.152, +0.786, +0.811
— individually separated as well as pooled. The 640s rung is where they disagree (+0.053,
+0.088, +0.678), which is why it pools to "not separated" rather than to a narrow result.

The wide error bar at 40s (±0.729, against per-seed errors near 0.35) is between-seed
disagreement, not measurement noise: the seeds give −3.026, −4.450, −1.932. Short budgets
produce genuinely different strategies from different seeds, which is worth remembering
before quoting any single-seed figure at that end of the scale.

**Contention did not distort it.** Recorded load was 4.0 and 4.5 for seed 0's first two rungs
and about 1.0 everywhere else. Seed 0's values at those rungs sit inside the spread of the
quiet seeds, and at 2560s the busiest seed gave the *largest* result, so there is no
detectable systematic effect. Not proof of none — see the instrumentation gap below.

**What this does not establish.** Beating the other abstraction says nothing about distance
from equilibrium. Both agents may be far from it, and the one that wins is merely less bad.
Item 1 remains the only route to that claim.

### ~~Follow-up: record load per training window~~ — DONE, 14 August

`train_to` now samples `/proc/loadavg` every 10 seconds *during* each agent's window and
returns the mean, so a rung records `equity_load_avg`, `made_hand_load_avg` and their
`load_imbalance` rather than one reading taken after both had finished. An imbalance above
1.0 prints a `[!]` marker at the time, since a rung whose two agents trained under different
load did not really give them equal budgets. `load_avg` is retained as the mean of the two so
the existing result file stays comparable.

### The original rationale, kept

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

## 3. ~~Re-run the crossover experiment~~ — CLOSED, will not be done

`results/cfr/crossover.json` measures the two bucketings by comparing their exploitability,
and its numbers came from an LBR carrying four defects. The plan was to fix the exploiter and
run it again. **That plan is dead, and the file should be treated as a record of how the
question was first attempted rather than as a result.**

Two independent reasons, either sufficient:

- **The exploiter never got strong enough.** Item 1 closed with LBR unable to clear zero on a
  converged strategy at either raise cap. A re-run would reproduce the same non-conclusion at
  the same seven-hour cost.
- **The question was answered another way.** Item 2 settled it by playing the agents against
  each other — conclusively, at 7.8σ, in about four hours. Exploitability was never required
  to answer "which bucketing should I use given N seconds".

Nothing is lost by closing it. If a working exploitability bound ever exists, the interesting
experiment is not this one re-run but a new one: whether the *head-to-head* winner is also the
less exploitable agent. Those can disagree, and the disagreement would be the finding.

## 4. Recover or replace the paper — largely superseded

`CODEBASE_AUDIT.md:264` defers every remaining open question to the threats-to-validity
section of `IEEE_CFR_Poker_Engine_Paper_v3.pdf`. **That file is not in the repository, not in
git history, and not anywhere under the home directory.**

`docs/abstraction-crossover.html` (15 August) now covers that ground: the withdrawn results,
the CFR validation, the crossover, the LBR investigation, and a threats-to-validity section
written from the measurements rather than recovered from the PDF. What it cannot recover is
anything the original recorded that nobody has since re-derived.

**Remaining action:** if the PDF turns up on another machine, reconcile the two rather than
assuming either is complete. Otherwise this is closed.

---

## Decisions, now made

All four were settled on 15 August. Kept rather than deleted: each names something that was
removed, and the reason is easier to find here than in a commit message.

### ~~`scripts/testing/`~~ — reviewed and removed, 15 August

482 lines of hand-run scripts written when `tests/` was an empty directory. They imported only
from `engine/` — the verified, retained part — so they were never pipeline leftovers, only
superseded ones. Reviewed against the suite before deleting rather than after: most of what
they touched is now covered, and what they checked *uniquely* they checked by printing it,
which is not a check.

Four things had no coverage at all and are now in `tests/test_engine_surface.py` with
assertions: raise-sizing hints and their agreement with the action mask, the action history the
engine records, hand-history logging, and whether `engine/cli.py` can play a hand — the only
path a person drives the engine by hand, and imported by nothing else.

The CLI test hung on first run, which is its own small finding: the CLI re-prompts on an
illegal action, and a fallback answer of `check` is illegal when facing a bet. It now falls
back to `fold` and carries a prompt budget, so a loop fails with a message instead of hanging
the suite.

### ~~`examples/`~~ — removed, 15 August

One script demonstrating training against Hall of Fame champions, and a 194-line README for a
workflow that no longer exists. `hall_of_fame/` holds nothing but `FAULTY_PIPELINE_NOTICE.md`,
so the example could not have run. Recoverable from `pre-cfr-pipeline` alongside the pipeline
it belonged to.

A worked example of the *current* stack — fit an abstraction, train a solver, measure head to
head — would be worth having. That is new work rather than a decision, and is not started.

### ~~Experiment logs are not versioned~~ — resolved by convention, 15 August

`logs/` stays gitignored for routine output. When an experiment's timing is part of its claim,
its run log is committed beside the JSON it produced: `results/cfr/crossover.log` and
`results/cfr/head_to_head.log` are there now. Both record per-rung load average, which is what
makes a wall-clock-budgeted result auditable rather than merely reported.

### ~~Loose artifacts at the repository root~~ — removed, 15 August

`trained_demo_agent.npy` was a genome from the invalidated pipeline. `.agent.md` was an
academic-report-generator agent definition, superseded by
[`docs/abstraction-crossover.html`](docs/abstraction-crossover.html), which was written from
the measurements. Neither was referenced by anything; both are in git history if wanted.

## Closed, and the lessons kept

Resolved, but recorded rather than deleted: each cost real time to discover and the
hazard behind it recurs.

### Long-running checkpoints must not live in /tmp

WSL restarted on 14 August and wiped the scratchpad, taking `deep_solver.pkl` — a
59,050-iteration solver that cost about 49 minutes to train — along with the rollout sweep
and off-tree measurement files. The checkpointing worked exactly as designed; it was
checkpointing to volatile storage. Anything that takes more than a few minutes to regenerate
belongs under `results/` or another path that survives a reboot, even when it is scratch work.

### ~~`results/cfr/nolimit_strategy.pkl` cannot be loaded by current code~~ — DONE, 14 August

`CardAbstraction.__setstate__` now rebuilds `_centroid_list` from `_centroids` when a pickle
predates it, so the artifact loads unaided. Rebuilt rather than refitted: refitting would
answer with a different clustering and look like it had worked. Two tests cover it — one
restoring a state dict with the field removed, one round-tripping an ordinary pickle, since a
`__setstate__` that fixes the old path and breaks the new one is the obvious way to get this
wrong.

The original report follows, since the same hazard applies to the next derived field added.

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
