# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 2 September 2026 · `main` at `23d9a47` · 233 tests + 44 Slumbot tests

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

## Closed, 20 August: the Phase 4 intransitivity

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

## Now: the solver was under-trained, and it was worth half the gap

`results/cfr/nolimit_strategy.pkl` shipped with **4,000 iterations** — about two minutes of
training at the crossover's measured 32 iterations/second. Retraining the same abstraction for
**150,000** iterations (2h56m) and re-measuring:

| | vs Slumbot | vs the 4k solver | vs random | vs always-call |
|---|---|---|---|---|
| 4,000 iterations | −1750 ± 524 | — | +377.2 | +722.9 |
| **150,000 iterations** | **−987 ± 374** | **+185.0 ± 13** | +280.1 | +827.7 |

**Training was the binding constraint, not the abstraction.** It halved the Slumbot gap and wins
the head-to-head by fourteen standard errors.

**Three things this turned up, all worth keeping:**

**Internal strength overstates external gain by ~2.4x.** +185 ± 13 BB/100 internally became
+76 ± 64 against Slumbot. Beating your own previous agent is evidence about a third party, not a
measurement of one.

**The baselines still cannot rank.** The 150k solver is decisively stronger yet scores *worse*
against random (+280.1 against +377.2). Ranking these two by their random score would have picked
the weaker agent — the Phase 4 intransitivity, appearing again in an independent place.

**`train_nolimit.py`'s own evaluation disagrees with `evaluation.benchmark`.** On always-call it
reported the 150k solver worse (+348.1 against +581.5) where the audited instrument says better
(+827.7 against +722.9). Opposite conclusions, same two strategies. The benchmark path is the one
every Phase 4 number came through and it reproduces exactly; treat the trainer's built-in
evaluation as unfit for comparisons until someone works out why.

### The next lever is more iterations, not less abstraction

At 150,000 iterations the solver had reached **25,154 of 49,200** information sets — barely half
the abstraction it already has. More training is cheaper than widening buckets, lifting the raise
cap, or moving to 200bb, and it has not stopped paying yet.

Two things to fix before any longer run:

- **`train_nolimit.py` prints nothing during training and saves only at the end.** A 500,000
  iteration attempt ran six hours, reached ~4.9 GB, and was killed with nothing written. It needs
  a progress line and periodic checkpointing.
- **Memory, not time, is the ceiling.** The abstraction's table is 4.7 MB; the solver's
  bookkeeping reached 4.9 GB. 150,000 iterations peaked around 1.6 GB, so roughly 250,000 is what
  this machine can hold.

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
