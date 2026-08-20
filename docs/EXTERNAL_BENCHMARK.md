# Goal: do not lose to Slumbot

**The target.** A measured head-to-head result against Slumbot at **0 mbb/hand or better**,
over enough hands for the confidence interval to mean something.

## Why this is the right goal for this project

Every strength number here is self-produced. Kuhn's −1/18 and exact Leduc exploitability
prove the solver converges to the right thing, and the abstraction crossover (item 2 in
[`BACKLOG.md`](../BACKLOG.md)) measures two of this project's own strategies against each
other. Nothing measures this project against anyone else's work.

That gap is not cosmetic. **Item 1 closed with no usable bound**: after four defects fixed and
three valuation models, LBR still could not beat a 59,050-iteration strategy, so no-limit has
no exploitability figure at all right now. Slumbot answers the same question — how good is
this really — by a route that does not depend on this repo's own machinery being correct.

It is also the right opponent rather than merely an available one. Slumbot plays a fixed CFR
strategy at heads-up no-limit: same game, same technique, no adaptation between sessions, free
public HTTP API with no auth. Results are reported in mbb/hand and published work cites them,
so the number lands in an existing comparison.

## Is the goal reachable

Honestly: it is hard, and it is not absurd.

Against it — Slumbot is a strong near-equilibrium blueprint built with serious compute, and it
won the ACPC. GTO Wizard, a heavily-resourced commercial solver, beats it by 194 ± 41 mbb/hand
over 150,000 hands. That is the scale of effort that clears it comfortably.

For it — Slumbot is itself abstraction-based and does no real-time solving, so it is not an
equilibrium. The LBR literature (Lisý & Bowling, 2017) established that abstraction-based
no-limit bots of this generation retain substantial exploitable weaknesses. Break-even is a
target with a real path to it, unlike beating an actual equilibrium.

Reaching it plausibly needs: a finer bet abstraction, far more iterations, randomized action
translation, and eventually real-time subgame re-solving, which is the technique that separates
blueprint-only agents from the ones that beat strong opponents. Treat re-solving as the thing
the milestones below are walking toward.

## Milestones

Staged, so progress is visible long before the goal is met.

| | Milestone | Meaning |
|---|---|---|
| M0 | One legal hand played end to end against the live API | Protocol works |
| M1 | 10,000 hands, any result, with a CI | **First externally-produced number in this repo** |
| M2 | Within 200 mbb/hand | Competitive with the blueprint generation |
| M3 | Within 50 mbb/hand | Abstraction and translation are close to sound |
| M4 | **0 mbb/hand or better** | Goal |

M1 is the one that changes the project. Everything after it is improvement against a scale
that already exists.

## The hard part: action translation

Slumbot bets any legal amount. This project plays a six-action bet abstraction
(`abstraction/`). Bridging them is most of the engineering:

- **Inbound** — a Slumbot bet landing between two abstraction sizes has to be mapped onto one
  before a strategy can be looked up. Nearest-size mapping is itself exploitable. Randomized
  translation between the two neighbouring sizes is the standard fix.
- **Outbound** — the chosen abstract action has to become a concrete chip amount.

Build this as its own module with its own tests, separate from the agent. A translation bug is
indistinguishable from a weak strategy by looking at the result.

## Measurement discipline

Non-negotiable here, given item 1's history.

- **10,000 hands minimum.** mbb/hand over a short sample is noise.
- **Duplicate seating** — every hand played twice with seats swapped and identical cards.
  Cheap against a fixed opponent and removes a large share of the variance. AIVAT is better
  and more work.
- **Always a confidence interval.** Never a bare point estimate.
- **Results as JSON in `results/cfr/`**, one file, matching every other measurement here:
  mbb/hand, hand count, CI, agent version, translation-layer version.

**The specific trap, already seen in this repo.** Item 1's cap-2 row read +2.783 and "PROVES
EXPLOITABLE" one afternoon and −2.900 that evening against an identical untouched strategy,
because only the exploiter's internal valuation had changed. Action translation is the same
class of hazard: a modelling choice, invisible in the result, that moves the number. Freeze
and version the translation layer before quoting anything, and run a throwaway pilot of a few
hundred hands whose result is deliberately not read.

## Steps

1. Build the Slumbot API client; play one hand end to end (M0).
2. Build the translation layer with its own test suite.
3. Verify chip accounting against the engine, which the audit found sound — a mismatch means
   translation is wrong, not the engine.
4. Pilot a few hundred hands to shake out protocol bugs. Do not read the result.
5. Run 10,000+ hands with duplicate seating; write the JSON (M1).
6. Iterate on abstraction granularity, iteration count and translation, re-measuring at each
   change, toward M2–M4.

## Reporting

Report a loss as a loss. A CFR agent over a coarse abstraction losing to Slumbot by a
measured, bounded margin is a legitimate result and the first honest external one this project
has. The reason this file exists at all is that `CODEBASE_AUDIT.md` established what a
flattering self-computed number is worth.

## References

- Slumbot API reference implementation: https://github.com/Gongsta/Poker-AI/blob/main/slumbot/slumbot_api.py
- Lisý & Bowling (2017), *Equilibrium Approximation Quality of Current No-Limit Poker Bots*:
  https://poker.cs.ualberta.ca/publications/aaai17ws-lisy-lbr.pdf
