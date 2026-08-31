# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 20 August 2026 · `main` at `3b21fb0` · 233 tests passing (9m32s)

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Learned to exploit randomness; nothing transferred against the solver |
| PPO | measured | Closes the gap to the CFR agent: −383.8 → −10.7 BB/100 after 8M hands. Flat after 2M |

All three are measured, and **Phase 4 — the comparison the project's title promises — is done**
(`results/comparison/phase4.json`). One panel, 40,000 hands, one wall-clock axis, in BB/100:

| family | wall-clock | vs random | vs always-call | vs CFR |
|---|---|---|---|---|
| CFR (the solver) | — | +377.2 | +722.9 | — |
| evolution, 50 generations | 3.16 h | +192.7 | +0.5 | −370.1 |
| PPO, 2M hands | 1.02 h | +221.5 | +293.5 | **+10.4** |
| PPO, 8M hands | 4.81 h | +135.4 | +467.9 | −10.7 |

**PPO reaches break-even against the solver in about an hour. Evolutionary search, given three
times that compute, is still 370 BB/100 behind.**

---

## Closed today: the Phase 4 intransitivity

It is **explained** — see
[`docs/training-plan.md`](docs/training-plan.md). All three candidate explanations were tested:
the instrument agrees bit-for-bit, lifting the raise cap widened the gap rather than closing it,
and the third turned out to be the answer.

The tournament graph's missing edge settles it. PPO against the evolved genome scores **+23.9
BB/100** (per seed −12.7, +68.2, +16.3, spread 80.8) where transitivity predicted about +360.
PPO is level with the solver *and* level with the genome the solver beats by 370, which no
single ordering allows.

The mechanism is in the action counts. Against a station that never folds the solver goes all-in
on **15.0%** of its decisions and PPO on **0.1%**; the two raise at similar rates, so the
difference is sizing rather than frequency. Self-play optimises against a peer, and its
snapshots fold — so the policy never learned to jam into an opponent who does not. Against the
solver that costs nothing; against anything weak it leaves the value uncollected.

**Do not quote a single-number ranking of the three families.** The data does not support one.

---

## Now: item 5 — do not lose to Slumbot

M0 is done: `slumbot/api.py` plays a hand end to end against the live API, with 21 offline tests
on the betting-string parsing. The next steps, from
[`docs/EXTERNAL_BENCHMARK.md`](docs/EXTERNAL_BENCHMARK.md):

**The stack depth is the first problem, and it is not small.** Slumbot plays 20,000 chips at
50/100 — **200 big blinds**, confirmed against the live server. This project's engine and solver
use 200 chips at 1/2, which is **100**. A strategy fitted for 100bb is off-tree at 200bb from
its first decision. Either something is built for the depth Slumbot plays, or the depth is
reported as a caveat on every number that follows. Decide which before writing the translation
layer, because it changes what the layer is for.

**Then the translation layer**, as its own module with its own tests. Slumbot bets any legal
amount; this project plays six abstract actions. Inbound, a bet landing between two abstraction
sizes has to be mapped onto one, and nearest-size mapping is itself exploitable — randomised
translation between the two neighbours is the standard fix. Outbound, an abstract action has to
become a chip amount. `bet_levels()` gives the raw levels; turning those into an amount owed
needs position and the posted blinds, which the API module deliberately does not do.

**Then M1**: 10,000 hands with a confidence interval, any result. Worth investigating first that
the API returns `baseline_winnings` per hand — its own variance-reduced estimate, which may do
some of the work the brief assigns to duplicate seating and AIVAT.

---

## After that

**Phase 5 — six-max.** After heads-up is complete. Note the CFR agent cannot serve as a
benchmark there, so the panel loses its only opponent from outside the lineage. Also needs the
`play_match` stack-drift fix described in [`docs/training-plan.md`](docs/training-plan.md).

---

## Closed — do not reopen without new information

- **Exploitability via LBR.** Four defects and three valuation models in, it still cannot beat a
  converged strategy. Stopped deliberately; the reasoning is in `BACKLOG.md` item 1.
- **Re-running the exploitability crossover.** Superseded by the head-to-head result, which
  answered the same question conclusively in four hours.

---

## Picking this up cold

```bash
venv/bin/python -m pytest -q            # expect 233 passed; collection alone takes ~5 min
venv/bin/python scripts/audit_observation.py   # the 19-feature observation, both table sizes
venv/bin/python scripts/make_figures.py        # rebuilds every figure from the repo alone
venv/bin/python -m gui.main                    # play the CFR agent, through the benchmark's own loop
```

Two conventions worth knowing before starting a long run:

**Checkpoint at 10% of the run**, via `evaluation.checkpoint_every`. Ten saves whatever the
unit.

**Never checkpoint into `/tmp`.** WSL wipes it on restart, and doing so cost 49 minutes of
training on 14 August. Use `~/pokerbot-scratch` or `results/`.

And the habit that matters more than either: **before trusting a number, check its error bar
against the spread of the thing it is measuring.** Three separate results in this project have
looked like findings and been noise, and each was caught by a check that already existed rather
than by a new one.

---

## A note on the history rewrite

On 20 August every commit reachable from `main` was re-hashed, to strip `Co-Authored-By`
trailers. File contents were unaffected — verified by comparing all 104 commit trees against
the pre-rewrite history, with no mismatches — but **every SHA quoted before that date is
dead**. Three references in tracked files were remapped; if an old SHA turns up in a note
elsewhere, resolve it by subject against the current `main` rather than trying to check it out.
