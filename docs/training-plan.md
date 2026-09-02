# NashForge — training plan: evolutionary search and PPO, heads-up first

**Status:** Phases 0–2 complete. Written 15 August 2026, last updated the same day.

The goal is a comparison: how close do evolutionary search and policy gradient get to a
solver-derived strategy, given the same budget on the same engine? Heads-up first, six-max
after, so that both methods can be measured against the CFR agent.

---

## Why this is worth doing now

Every previous attempt in this repository measured agents against **other agents bred on a
broken metric** — self-referential, which is how a reported best of 5213 BB/100 survived 89
training runs. [`CODEBASE_AUDIT.md`](../CODEBASE_AUDIT.md) has the details.

What exists now that did not: a **CFR agent as an independent yardstick**. It was validated
against Kuhn poker's analytic value of −1/18 and against exact exploitability on Leduc, and it
shares no lineage with anything a GA or PPO run will produce. That turns this from another
round of tournaments into a comparison with a reference point.

Heads-up first is not just variance reduction. It is the only table size where the CFR agent
can serve as the benchmark at all — the solver work is heads-up throughout.

---

## The observation: audited, 15 August

Before planning training, the 17-feature observation was measured rather than assumed.
1,500 sampled decision states per table size, true equity by Monte Carlo at 400 samples,
reproduced by `scripts/audit_observation.py`.

### It carries six dimensions in seventeen slots

| | heads-up | 6-handed |
|---|---|---|
| components explaining 90% of variance | **6** | **6** |
| live slots | 16 of 17 | 17 of 17 |

`players_in_hand` has a standard deviation of **exactly 0.0000** heads-up — it is always 2.
Two pairs are perfect duplicates: `players_behind`/`opponent_all_in` at r = −1.000 (heads-up
only) and `stack_normalized`/`commitment` at r = −1.000 (both sizes). Six-handed,
`players_behind`/`players_in_hand` sit at r = +0.979.

### All card information is in one slot

Predicting a state's true equity:

| | heads-up | 6-handed |
|---|---|---|
| from all 17 features | 0.421 | 0.481 |
| from `hand_strength` alone | 0.238 | 0.219 |
| **from everything except `hand_strength`** | **0.013** | **0.024** |

Remove that one feature and the other sixteen know essentially nothing about the hand.
Postflop the concentration is starker: all features reach 0.475, `hand_strength` alone
reaches 0.423.

### And that slot is lossy in a way training cannot fix

Grouping postflop states by near-identical `hand_strength` — states the agent physically
cannot tell apart — and measuring the true equity within each group:

| `hand_strength` | n | equity range | std |
|---|---|---|---|
| 0.73 | 38 | **0.907** | 0.173 |
| 0.58 | 43 | 0.890 | 0.253 |
| 0.60 | 35 | 0.861 | 0.231 |

The worst group spans 0.907 of equity: two hands the agent receives as an identical input can
be a 5% underdog and a 95% favourite. This is the decisive statistic, not the R² figures
above — those are linear fits and understate what a network could extract, whereas identical
inputs are an information limit no model escapes.

The cause is known and not accidental. Postflop, `hand_strength` is
`made_hand_strength(hole, board)` — scoring only the hand made so far. It is the same signal
the CFR work measured as **provably blind to draws**: on a two-heart board, the nut flush draw
and the same overcards without it are the same number. The
[abstraction crossover](abstraction-crossover.html) found that blindness costs real chips above
roughly ten minutes of training. The network observation has been carrying it the whole time.

### The fix is cheap, and was measured

Four binary features — flush draw, open-ended straight draw, paired board, three-to-a-flush —
computed from suit counts and rank gaps, no simulation:

| | before | after |
|---|---|---|
| R² overall | 0.421 | **0.503** |
| **R² postflop** | 0.475 | **0.637** |

A 34% relative gain postflop. The within-group spread falls only 0.168 → 0.158, so draws
explain part of the blindness rather than all of it — kicker quality and board interaction
remain invisible. That is a reason to expect more from a richer card representation later, not
a reason to skip the cheap win now.

---

## What to do about the features

**Remove two slots. No information is lost.**

- `commitment` — r = −1.000 with `stack_normalized` in both table sizes; algebraically the
  same number, since stack + contributed = starting stack.
- `players_in_hand` — constant heads-up, and 97.9% explained by `players_behind` six-handed.

**Keep `players_behind` and `opponent_all_in` both**, despite being perfect duplicates
heads-up. They are independent six-handed, and one shared layout across table sizes is worth
more than one wasted slot — the cost is a few weights, and it keeps the two configurations
comparable.

**Add the four draw and texture features.** 17 → 19 slots that carry more than the original
seventeen did.

**Do not add Monte Carlo equity per decision.** It costs ~10.6 ms per call at 400 samples,
against ~8 µs for made-hand strength. The CFR work measured the same trade-off from the other
side: equity bucketing costs 44.05 ms per solver iteration against 8.11 ms, a factor of 5.4.
Per-decision equity in a training loop making millions of decisions is not affordable, which
is exactly why the draw features matter — they recover much of what equity knows for nothing.

**Optional, unmeasured:** an "equity if I improve" scalar, or a two-card lookahead. Worth
testing after the cheap features land, not before.

This invalidates every saved genome. All of them came from the invalidated pipeline, so
nothing of value is lost.

---

## Decisions taken, 15 August

| | Decision | Why |
|---|---|---|
| Feature change | **Approved** — 17 → 19 | Measured; invalidates saved genomes, all of which came from the invalidated pipeline |
| Layout | **One shared layout** for both table sizes | Two layouts re-open the exact crack the audit found bugs in — `FeatureCache` and `get_state_vector` had drifted apart. Costs two dead slots heads-up |
| Budget axis | **Hands played**, not wall-clock | GA is CPU-parallel and PPO is not; wall-clock would compare hardware as much as algorithms. Wall-clock is still recorded alongside |
| PPO device | **CPU**, pending a profile | The network is a small MLP over 19 inputs; the Python engine is almost certainly the bottleneck. GPU adds a second memory pool on a box that has died twice from memory pressure |
| PPO self-play | Snapshot every ~10 updates, pool of last 5–10 | Sample from the pool most of the time, with some probability of facing the current policy |

## Progress

Updated as work lands. "Blocked" means waiting on a decision, and the decision is named.

| | Item | State |
|---|---|---|
| 0a | Tests for `rl/` | **done** — 9 tests, `tests/test_rl.py` |
| 0b | Duplicate play | **done** — `cfr/play.py`, ~14% noise reduction |
| 0c | Benchmark harness | **done** — `evaluation/`, 9 tests |
| 1 | Rebuild the observation, 17 → 19 | **done** — effective dimensions 6 → 9 |
| 2 | Evolutionary search, heads-up | **done** — learned to exploit randomness, nothing transferred |
| 3 | PPO with self-play, heads-up | **done** — closes the gap to the CFR agent; flat after 2M hands |
| 4 | The comparison | **done** — one panel, one budget axis; PPO reaches break-even in ~1 h, evolution never does |
| 5 | Six-max | blocked on 4; also needs the `play_match` stack-drift fix below |

## Phases

### Phase 0 — make the measurement trustworthy

The audit's Step 1, never carried out for networks.

- **Tests for `rl/`.** 1,917 lines, currently **zero coverage**. Minimum: chip conservation
  through the environment, observation shape and bounds, that the policy never emits an
  illegal action, that one PPO update runs without producing NaN. Training against an untested
  environment is how the previous round produced numbers nobody could trust.
- **Duplicate play.** *Done, 15 August.* `alternate_seats` swapped the policies but drew fresh
  cards each time, so position cancelled and card luck did not. `_play_one` now records each
  chance outcome and the replay reuses it, so both policies hold the same cards against the
  same opposing cards. On by default; `duplicate=False` reproduces the old behaviour.

  **It buys about 14%, not the large factor the audit implied.** Per-hand outcomes swing by a
  full ±200 stack depending on whether an all-in happened, and that is driven by the action
  sampling, which sharing cards cannot cancel. It is free and strictly better, so it stays on
  — but hand count remains the real variance lever, and coupling the action stream is the next
  option if more is ever needed.

  Guarded by two tests: that the noise drops, averaged over seeds because a single run's
  standard error is itself noisy; and that the *expectation* does not move, since a duplicate
  run that drifts off a symmetric matchup's true zero would silently corrupt every comparison
  built on the harness.
- **One benchmark harness.** Any agent against a fixed panel: random, always-call, and the
  **CFR agent**. Error bars on every figure, seats duplicated, hand counts sized from the
  measured noise floor rather than convention.

### Phase 1 — rebuild the observation — DONE, 15 August

17 → 19: `commitment` and `players_in_hand` removed, four draw and texture features added,
`get_state_features` deleted. Re-running `scripts/audit_observation.py` confirms it did what
this document claimed:

| | before | after |
|---|---|---|
| effective dimensions | 6 of 17 | **9 of 19** |
| dead slots (std ≈ 0) | 1 | **0** |
| perfect duplicate pairs | 2 | 1 (kept for six-max) |
| R² against true equity | 0.421 | **0.499** |
| R² postflop | 0.475 | **0.633** |
| within-group equity std | 0.175 | **0.086** |

The last row is the one that matters, and measuring it required correcting the audit. It had
grouped states by `hand_strength` alone — which *was* the entire card signature and no longer
is. Grouped by all five card features, states the agent genuinely cannot distinguish now
differ in true equity by half as much. Grouping on strength alone would have understated the
gain while appearing to measure the same thing.

**The change needed nine coordinated edits, not the four predicted.** The Phase 0a tripwire
caught `PokerEnv.OBS_SIZE` and `PPOConfig.obs_size`; the failing suite caught three more that
nothing pointed at: `FeatureCache.__slots__`, whose declared attribute list rejected the two
new cache fields on assignment; `training/config.py`'s `input_size`, which was still building
networks with 17 inputs; and a hardcoded `GENOME_SIZE = 3430` in the tests. That constant is
now derived from the network config, since a written-down width is exactly what disagreed with
reality here.

### Phase 2 — evolutionary search, heads-up — DONE, 15 August

Fifty generations, population 30, **24,000 hands per genome** — a budget set from the measured
noise floor rather than convention. Re-scoring the same population under different hands moves
a genome by 136 BB/100 at 2,000 hands, 66 at 8,000 and 31 at 24,000.

**The endpoint result.** Final genome against an untrained one from the same initial
distribution, both against the same panel at 40,000 hands (±14 BB/100):

| opponent | untrained | after 50 generations | difference | |
|---|---|---|---|---|
| random | −13.4 ± 14 | **+192.7 ± 15** | **+206.1 ± 39** | improved |
| always-call | −8.1 ± 14 | +0.5 ± 4 | +8.6 ± 28 | no change |
| CFR | −403.9 ± 13 | −370.1 ± 14 | +33.8 ± 37 | no change |

**Evolutionary search learned to exploit randomness, not to play poker.** It punishes an
opponent that folds and raises at random by 206 BB/100, gains nothing against a station that
never folds, and is still beaten by the solver by 370 BB/100 after fifty generations. That is
a sharper finding than the audit's prediction that the method would simply plateau — it did
learn, and what it learned did not transfer.

Only the panel makes that visible. Self-play fitness sat near zero throughout, as the zero-sum
property requires, and says nothing about whether anything was learned.

### Phase 2's three false results, and what caught each

Every one of them looked like a finding, and each was caught by a check that already existed.
Recorded because the pattern is the argument for the framework, more than any single number in
it.

**The per-generation panel curve.** Taken over 3,000 hands, ±57 BB/100, and read during the run
as rising from +111 to +214. Across eleven readings it scattered with a standard deviation of
56 — indistinguishable from a constant. A measurement that coarse does not return "no result";
it returns a plausible shape. The endpoint test at 40,000 hands found the real effect the
curve could never have resolved.

**"The evolved agent beats a game-theoretic solver."** The CFR row first read +60.8, alongside
a 74.3% lookup miss rate. The miss-rate counter exists precisely so a benchmark that has
quietly become a second random opponent shows up as a number. In the previous regime this
would have been published.

**"Half the abstraction is unreachable."** The explanation offered for that miss rate — that
the solver covers 47% of its information sets at 4,000 iterations and 51% at 59,050, so a
network opponent lands off its trajectory and more training cannot help — was itself wrong,
and was committed. Nothing was missing: every lookup found its key. The solver stores one
probability per *legal action at a node*, so arrays are mostly length 2 or 5, and the harness
discarded anything that was not length 6. That was 77.5% of successful lookups. The tell was
available and misread — a 100% hit rate against a random opponent should have ruled out
"structurally unreachable" immediately.

### Phase 3 — PPO with genuine self-play, heads-up — DONE, 20 August

Snapshot pooling was the prerequisite and was built first: PPO trained against `RandomOpponent`
or against a Hall of Fame pool that was empty, and would have been tainted if it were not, since
every genome in it was bred on the withdrawn metric. Self-play here means the policy against its
own periodic snapshots.

Three seeds, 8M hands each, about 4.7 hours apiece, with rungs kept at 500k, 2M and 8M so
Phase 4 gets a budget axis rather than a single endpoint. The rungs are points on one run, not
three runs — the 2M policy is the 500k policy trained further, which is what makes them
comparable.

**The endpoint result.** Each rung against an untrained policy from the same initialisation,
both against the same panel, both at 40,000 hands, all three seeds
(`scripts/endpoint_test_ppo.py`, `results/ppo/phase3_endpoint.json`). Gains are the mean across
seeds; the spread is the range across them.

| trained to | vs random | vs always-call | vs CFR |
|---|---|---|---|
| 500,000 | +215.9 (spread 216.9) | +261.9 (spread 397.8) | **+324.3** (spread 79.2) |
| 2,000,000 | +233.3 (spread 73.3) | +276.9 (spread 369.7) | **+394.2** (spread 32.5) |
| 8,000,000 | +147.1 (spread 135.3) | +451.3 (spread 636.7) | **+373.1** (spread 48.4) |

All 27 rows — three seeds, three rungs, three opponents — separated from zero in the improving
direction. The CFR lookup miss rate was 0.0% across all nine matchups.

**What it learned transferred, and that is the contrast with Phase 2.** Against the solver the
untrained networks scored −399.1, −385.9 and −366.3 BB/100; after 8M hands the same three scored
−34.8, +35.4 and −32.7, a mean of −10.7. PPO closes essentially the whole gap to the CFR agent.
Evolutionary search, given the same panel and the same bar, moved −403.9 → −370.1 and was scored
*no change*. Both halves of the audit's prediction now have numbers: the evolutionary method
plateaus, and policy gradient produces a strong player.

**The ladder is flat after 2M.** +394.2 at 2M against +373.1 at 8M, on spreads of 33 and 48 — the
last six million hands of each run, three quarters of the wall-clock, bought nothing that can be
measured. Phase 4 should spend its budget accordingly rather than assuming more is more.

**Only the CFR column is quotable.** Its seed spreads are 33–79 BB/100; the two baselines run
73–637. Against always-call at 8M the seeds scored +426.1, +145.5 and +782.2 — the direction is
certain and the magnitude is not resolved at all. The opponent from outside the lineage is the
stable yardstick and the hand-written baselines are not, which is worth carrying into Phase 5,
where the CFR agent cannot serve.

**What this is not.** It is break-even against *this* CFR agent — six buckets, one raise per
street — not against a strong solver, and not an exploitability figure. Item 1 closed with no
usable bound, so no-limit still has none.

### Phase 4 — the comparison — DONE, 20 August

All three families against the same panel, at the same 40,000 hands, on one budget axis
(`scripts/phase4_comparison.py`, `results/comparison/phase4.json`).

**The budget axis needed no new training.** The families laddered along different axes — CFR
along seconds, evolution along generations, PPO along hands — but all three had recorded
wall-clock all along: the CFR budgets are seconds by construction, `phase2_history.json` keeps
`seconds` per generation, and each PPO history keeps `seconds` per interval. The axis was
arithmetic over files that already existed.

| family | wall-clock | vs random | vs always-call | vs CFR |
|---|---|---|---|---|
| CFR (the solver) | — | **+377.2** | **+722.9** | — |
| evolution, 50 generations | 3.16 h | +192.7 | +0.5 | −370.1 |
| PPO, 500k hands | 0.26 h | +204.1 | +278.6 | −59.5 |
| PPO, 2M hands | 1.02 h | +221.5 | +293.5 | **+10.4** |
| PPO, 8M hands | 4.81 h | +135.4 | +467.9 | −10.7 |

BB/100, big blind 2. The solver has no row against itself: a strategy against a copy of itself
is zero by symmetry, and printing that zero would put a structural identity in a column of
measurements.

**PPO reaches break-even against the solver in about one hour of training. Evolutionary search,
given more than three times that compute, is still 370 BB/100 behind** — and its gain over its
own untrained network was +33.8 ± 37, which is no change. Both families sit on one wall-clock
axis, so this is a like-for-like budget statement rather than a comparison of endpoints.

**The table is non-transitive, and that is the most interesting thing in it.** PPO at 2M draws
level with the CFR agent head to head, yet the solver takes far more off both baselines —
+377.2 against random to PPO's +221.5, and +722.9 against always-call to PPO's +293.5. Two
agents level against each other extract very different amounts from the same weak opponents,
so strength here is not a scalar and any single-number ranking of the three families would be
a fiction. It also runs against the intuition that the near-equilibrium strategy should be the
less exploitative one. The mechanism is not established; it is recorded as an open question
rather than explained away.

**Two hazards were found while building it, both of which produce a plausible-looking wrong
chart.** `results/cfr/strength_signals.json` is in chips/hand while the endpoint tests are in
BB/100 — a factor of fifty at big blind 2, which plotted unconverted shows the solver as fifty
times weaker than PPO rather than stronger. And evolution's CFR row exists twice: the +60.8
in `phase2_endpoint.log` was taken beside a 74.3% lookup miss rate, and only the −370.1 in
`phase2_cfr_row.log`, at 0.0%, is usable. The comparison script normalises units once at the
boundary and refuses to run if the withdrawn row ever loses the miss-rate marker that
identifies it.

### The intransitivity, measured and explained — 20 August

Phase 4's table did not rank, and three explanations were listed. Two were checked and failed:
the two families' rows are on one instrument, bit-for-bit
(`scripts/diagnostics/check_instrument.py`), and lifting the one-raise-per-street cap *widened*
the gap rather than closing it (`scripts/diagnostics/check_raise_cap.py`). The third was that
the intransitivity is genuine, and it now has a measurement
(`scripts/diagnostics/check_intransitivity.py`).

**The edge nobody had measured.** Phase 4's tournament graph had a hole in it: both learned
families were scored against the solver and the two baselines, never against each other.

| edge | BB/100 to the first named |
|---|---|
| CFR vs PPO | +10.4 — level |
| CFR vs evolution | +370.1 |
| **PPO vs evolution** | **+23.9** — per seed −12.7, +68.2, +16.3, spread 80.8 |

If strength were a scalar, PPO being level with the solver and the solver beating the evolved
genome by 370 would require PPO to beat it by about 360. It beats it by 23.9, which against a
spread of 80.8 is not separated from zero — one seed lost. **PPO is level with the solver and
also level with the genome the solver crushes**, and both cannot be true of a single ordering.
The edge was no part of the observation that raised the question, which is what makes it
evidence rather than a restatement of it.

**And the mechanism.** Counting what each agent actually does against a station that never
folds, over about 250,000 decisions each:

| | fold | check/call | raise ½ | raise pot | raise 2× | all-in |
|---|---|---|---|---|---|---|
| CFR solver | 1.5% | 24.2% | 20.9% | 21.0% | 17.3% | **15.0%** |
| PPO, 2M hands | 3.5% | 34.1% | 35.3% | 13.2% | 13.8% | **0.1%** |

The two raise at similar *rates* — 74.3% against 62.4% — so frequency is not the explanation.
**PPO has effectively eliminated the all-in from its strategy** and concentrates on the smallest
raise. Both agents face the identical cap, so this is a property of the policy rather than of
the rules.

That accounts for the whole table. Against an opponent who never folds, the value is in large
bets. PPO trained by self-play against snapshots of itself, and those snapshots fold; it never
faced an opponent worth jamming into, so it never learned to. Against the solver that costs it
nothing and the two are level. Against anything weak it leaves most of the value uncollected.

This is the audit's prediction that policy gradient would produce "a strong but exploitable bot",
made specific and measured: **self-play optimises for a peer, and produces a policy that cannot
punish a weak opponent.** It is also why no single-number ranking of these three families should
be quoted, in this report or anywhere downstream of it.

### The instrument defect found on 20 August, and how

Phases 3 and 4 were measured, then re-measured, because the panel's results depended on the
order they were taken in. Recording it here with the other three, since it is the fourth time
this project has had to distrust a number and the first one that no result would have revealed.

**What was wrong.** Three layers, all the same class:

1. `build_panel()` handed the random opponent and the solver **one** generator, so the solver's
   stream depended on how much the random matchup had drawn.
2. The policy samples its actions from **torch's global generator**, and nothing reseeded it
   between matchups. `torch.manual_seed` appeared once in the whole measurement path, inside
   `PPOTrainer.__init__`.
3. Callers build the panel **once** and reuse it, so each opponent's state carried across all
   twelve columns of the endpoint test.

Together: the same matchup read −28.9, −29.5 and −3.9 BB/100 depending only on what had been
measured before it. Every one of those is a valid sample. None was reproducible alone.

**How it was found, which is the part worth keeping.** Not by a result looking wrong — the
published numbers were fine. It came out of checking whether the Phase 4 non-transitivity was
an artefact: the instrument check passed, but a difference spotted while writing it led to
layer 1, and **the fix for layer 1 failed its own order-independence test**, which is what
exposed layers 2 and 3. A fix that had been committed without that test would have closed the
smallest of the three and reported the problem solved.

**The fix.** The panel hands out factories, and `panel_scores` builds a fresh opponent and
reseeds torch — from the evaluation seed and the opponent's *name*, so reordering cannot move a
number — for every matchup. `scripts/preflight_ppo.py` carried the same defect and got the same
fix. A matchup now returns the same figure measured alone, inside the full panel, with the panel
reversed, or on a reused panel object; all four differed before.

**What re-measuring changed: almost nothing, and that is the result.** Every Phase 3 figure moved
less than its own seed spread — at most 13.0 BB/100 against a spread of 216.9, and in the CFR
column no more than 3.6. The seed spreads themselves *tightened* (134/40/62 → 79/33/48), which is
what removing an uncontrolled source of variation should do. The conclusions stand and are now
reproducible.

`scripts/diagnostics/check_instrument.py` is kept as the check that would catch this class
returning.

### The training lever, and where it runs out — 2 September

`results/cfr/nolimit_strategy.pkl` shipped with 4,000 iterations, which at the crossover's
measured 32 iterations/second is about **two minutes of training**. Retraining the same
abstraction — same six buckets, same one-raise cap, same seed — at 150,000 and 250,000
iterations, and ranking the three head to head on `evaluation.benchmark` at 40,000 hands:

| step | head-to-head gain |
|---|---|
| 4,000 → 150,000 | **+185.0 ± 13 BB/100** |
| 150,000 → 250,000 | **+12.3 ± 7 BB/100** |

**The lever is spent.** A 37× increase in training bought 185 BB/100; a further 1.67× bought
12.3 — separated from zero and not worth the three hours. Information sets reached went 25,154 at
150,000 and 25,154 at 250,000: coverage saturated, and the extra iterations refined a fixed set
of nodes rather than finding new ones. Roughly half the abstraction's 49,200 information sets are
unreachable in practice under this betting tree.

So **the abstraction is now the binding constraint, not training** — which is the answer to a
question that had never been asked, and the cheap one to ask first.

It transferred externally too, at a discount. Against Slumbot the 4,000-iteration solver scored
−1750 ± 524 mbb/hand and the 150,000-iteration one −987 ± 374, an improvement of +764 ± 644.
Internally the same upgrade is +185 ± 13 BB/100; externally it is +76 ± 64. **Internal strength
overstated the external gain by about 2.4×**, which is worth carrying: beating your own previous
agent is evidence about a third party, not a measurement of one.

#### The baselines rank these three exactly backwards

| | vs random | vs always-call | true strength |
|---|---|---|---|
| 4,000 | **+377.2** | +722.9 | weakest |
| 150,000 | +280.1 | **+827.7** | middle |
| 250,000 | +264.8 | +633.5 | **strongest** |

Against a random opponent the ordering is monotonically **inverted** — 377 → 280 → 265 as the
solver genuinely improves. Against the calling station there is no ordering at all.

This is the third independent sighting of the effect and the cleanest. As CFR converges toward
equilibrium it becomes *less exploitative* of weak opponents while becoming *stronger* against a
peer: equilibrium play is unexploitable, not maximally exploitative. It is the same trade found
in PPO the same week — the policy level with the solver that took far less off both baselines,
moving all-in on 0.1% of its decisions against the solver's 15.0%. Two different algorithms,
the same mechanism.

**The panel's `vs random` column is therefore actively misleading as a strength signal for CFR
agents.** Anyone tuning on it would tune backwards. Rank on the head-to-head or not at all.

### Two betting implementations, and a 20% divergence between them — found 2 September

Poker's betting is written twice here. `engine.PokerGame` is the audited one and is where every
published figure is measured. `games/nolimit.py` rebuilds it, deliberately and for a stated
reason: the engine mutates state in place and consumes a dealt deck, so a CFR traverser cannot
branch over an action and back up.

So the solver is **trained** in the traversal game and **scored** in the engine, and until now
nothing had checked that the two agree about chips. `tests/test_betting_equivalence.py` drives
identical abstract action sequences through both and compares pot and stacks.

**They agree exactly on every line that does not contain a pot-fraction raise** — fold, check,
call and all-in cost the same to the chip. **Pot-fraction raises diverge by about 20%:**

| | pot the raise is sized against |
|---|---|
| `games/nolimit.py:200` | `sum(contributions) + to_call` — after the call |
| `training/fitness.py:121` | `game.state.pot.total` — before the call |

```
raise-pot preflop, blinds 1/2, small blind acting
  traversal: call 1 -> pot 4 -> raise 4, total in 6, pot 8
  engine:    pot 3 -> raise 3, plus the call, total in 5, pot 7
```

The traversal game follows the standard convention — a pot-sized raise means calling first, then
betting the pot including your call.

**What it affects, and what it does not.** The abstraction crossover is untouched: `crossover.py`
and `head_to_head.py` reference the engine zero times, so both strategies were trained *and*
measured in the traversal game, under identical rules. Kuhn and Leduc are different games
entirely. PPO and evolutionary search train *through* `training/fitness.py`, so they learned the
engine's convention and are consistent with how they are measured. The Slumbot bridge sizes
raises after the call, matching the game its solver was trained in.

What is affected is narrow: **a CFR strategy trained in the traversal game and then measured in
the engine** — the CFR agent's rows as the panel opponent, Phase 4's `vs CFR` column, and the
viewer. Those numbers are real measurements; what is true is that the agent makes raises about
20% smaller than the ones it was fitted for, so it is a slightly *softer* benchmark than the
strategy it came from. Everything scored against it was scored under the same conditions, so the
comparisons between families hold.

**Why it is recorded rather than fixed.** Fixing `training/fitness.py` naively makes things
worse. `rl/poker_env.py:353` uses the same function for PPO's *training*, and evolution's too, so
changing the convention moves the mismatch off CFR — which retrains in three hours — and onto two
families that need seventeen. The only consistent fix retrains everything, and that is a
deliberate overnight job rather than a hotfix. **It should be fixed**; it is listed in
[`NEXT.md`](../NEXT.md) rather than left as folklore.

The test passes while the defect exists and fails once it is corrected, which is deliberate: it
characterises the divergence so it cannot be rediscovered by accident, and tells whoever unifies
the convention to delete it.

### Phase 5 — six-max

After heads-up is complete. Note that the CFR agent cannot serve as a benchmark there, so the
panel loses its yardstick and the comparison becomes relative again. Worth planning separately
rather than assuming the heads-up design transfers.

---

## What to expect, stated in advance

The audit predicts both outcomes, and recording them now is what makes them findings rather
than surprises later.

**Evolutionary search will plateau.** It receives one scalar per genome per generation and
performs no credit assignment, so it cannot learn "in this spot, this action". Better features
raise the plateau; they do not remove it.

**PPO will produce a strong but exploitable bot.** Self-play policy gradient does not converge
to a Nash equilibrium in imperfect-information games. That is a property of the method, not a
bug to be found.

The value is not beating CFR. It is measuring *where* each method plateaus and *by how much*,
against a benchmark that does not share their lineage.

---

## Hazards

**`reset_hand()` does not restore stacks.** Once a player busts, every subsequent hand is
instantly over with no player to act, and a loop that only calls `reset_hand()` spins forever
producing nothing — silently, with no error raised. This hung the feature audit's sampler
before it was found.

*Checked, 15 August: the existing training paths are safe.* `training/fitness.py` never calls
`reset_hand` — its game pool calls `game.__init__` with fresh stacks per hand, which is the
correct cash-game semantics. `training/self_play.play_match` reuses a table but guards it,
resetting every stack once fewer than two players have chips. New code that reuses a table
still needs the guard; the existing code has it.

**Six-max stack drift in `play_match`, for Phase 5.** That guard fires only when fewer than
*two* players remain solvent. Six-handed, a player who busts stays at zero while the other five
play on, so a long match drifts from a cash game toward a tournament with progressively unequal
stacks. Per-hand chip deltas stay correct — `hand_start_stacks` measures from the top of each
hand — but the *game being played* changes as it goes, and short stacks play differently.
Heads-up is unaffected: one bust leaves one solvent player, the guard fires, both stacks reset.
Worth resolving before six-max evaluation, not before heads-up.

**The machine is memory-limited, not CPU-limited.** 16 cores against 7.7 GiB, and WSL has been
terminated twice under memory pressure this week. Torch has CUDA available, so PPO can train
on the GPU; the evolutionary runs are CPU-parallel and are the ones to watch.

**Wall-clock budgets measure the machine.** Any budget-ladder experiment needs the quiet-machine
gate, and load should be sampled inside each training window rather than once per measurement —
see the crossover run's instrumentation.
