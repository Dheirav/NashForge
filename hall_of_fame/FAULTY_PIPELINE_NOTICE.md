# Hall of Fame — genomes removed, archived as faulty

**Date removed:** 12 August 2026
**Archive:** `../PokerBot_hall_of_fame_FAULTY_PIPELINE_2026-08-12.tar.gz`
**Also contained in:** `../PokerBot_superseded_2026-08-12.tar.gz`

Every genome that lived in `champions/`, `milestones/`, `archived/` and
`ppo_hu/` was **selected against a fitness function that did not measure what it
claimed to measure.** They have been archived rather than deleted, and are
labelled faulty so they are never mistaken for a valid result.

## Why they are faulty

These agents were *bred* under the defects below, not merely evaluated under
them. Rescoring cannot repair them; only retraining can. See
`../CODEBASE_AUDIT.md` for the full findings and evidence.

| Defect | Effect on selection |
|---|---|
| Fitness read seat 0's chip delta while seating the hero at random | The hero's own result was counted in 11 of 48 six-handed hands (23%). The other 77% selected on an opponent's outcome. |
| Pots were never awarded on hands won by folding | The majority of hands — 377 of 400 in one heads-up sample — scored every player as having lost their contribution. |
| Chip deltas measured after blinds left the stacks | Winners were credited with their own blind back, a positional bias, since the button does not rotate between hands. |
| Undeclared randomisation of stacks, blinds and antes | Every evaluation silently varied stacks 500–1500 and blinds 10–20, recorded in no saved config, then normalised by the nominal blind. |
| Hand strength constant for all pocket pairs, and blind to the board | The only card feature read 0.5 for every pair and never changed after the flop. |

An untrained random network scored **+451 BB/100** on that fitness function.
The same measurement, corrected, gives approximately zero.

## What this means for use

**Do not present these as "the evolutionary method."** They represent neither
what evolutionary training achieves nor anything reproducible — the pipeline
that produced them no longer exists. Using them as the evolutionary arm of a
method comparison would misstate the result.

They remain well-defined *opponents*: each is a fixed policy, and BB/100 against
one is a real quantity. If a fixed reference opponent is useful, label it as
that and nothing more.

**For a legitimate evolutionary comparison, retrain on the fixed pipeline.** A
50-generation run at p12/m7/h375 takes on the order of ten to twenty minutes,
and yields an agent with a publishable config and seed.

## Why they were kept at all

They are the artifacts the broken pipeline produced, and cannot be
reconstructed once discarded. If the bug-ablation study described in
`CODEBASE_AUDIT.md` Part 3 is pursued — quantifying how far each defect moved
the reported results — these are its primary evidence.

## Restoring

```bash
tar xzf ../PokerBot_hall_of_fame_FAULTY_PIPELINE_2026-08-12.tar.gz -C ..
```
