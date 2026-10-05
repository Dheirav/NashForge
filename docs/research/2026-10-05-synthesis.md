# What the six research notes say, and the order to act on them

5 October 2026, written during the season 8 final night. Six notes were written in parallel, each from our own
measurements plus the literature. The sources sit beside this file:

- `2026-10-05-search-and-exploitation.md` covers search at play time.
- `2026-10-05-robust-exploitation.md` covers exploiting the field without losing head to head.
- `2026-10-05-action-abstraction.md` covers bet sizes and translation.
- `2026-10-05-convergence-and-compute.md` covers training bigger trees.
- `2026-10-05-opponent-modelling.md` covers profiles and reads.
- `2026-10-05-measurement.md` covers choosing between versions.

None of them changes the set for tonight's final.

## The one idea that runs through all six

Most of our tests tie because they cannot see what we changed. A copy duel scores an exploiter against the same
family of scripts it was trained on, so it is an in-distribution test. A head to head cannot see exploitability.
Our LBR cannot see the third-raise hole, because it only tries raises the tree already has. A 20-match burst is
decided by two or three all-ins. So the first job after the season is better instruments, and only then more
strategy work. Otherwise we keep building things whose effect we cannot read.

## What each note found

**Search** (why river solving hurt v5x). Every published search bot solves for the balanced answer. The two papers
that mix search with exploitation (SES 2022, OX-Search 2024) still assume the opponent plays perfectly inside the
subgame. Our solve also took the opponent's range from v5x's own table, so it assumed an exploiter-shaped
opponent. That fits the measurements: the blueprint-range arm was the worst (55.8), and the true range helped
only against the bully shape (+3.6 ± 2.2). It also corrects our frontier audit. Modicum's +22 mbb against
Slumbot came from its whole search stack, not from a turn solver on its own.

**Robust exploitation.** v5x and v5xRR3 spend 40 percent of their training against scripts, which is past the
cheap part of the exploitation curve. That is why balanced-next takes 57.7 head to head. Whether to play the
exploiter against a known opponent depends on how often its copy is right, and that has never been measured.

**Action abstraction.** The third-raise hole is real in principle, and the papers show off-tree bets beating
coarse bots by large margins. But its size here is unmeasured, and our LBR is blind to it. Pseudo-harmonic
translation cannot help, because at the third raise there is only one abstract size to translate between.

**Convergence.** No paper gives an iterations-per-node rule. Theory says regret falls as one over the square root
of a node's visits, so "equal iterations per point" is right to first order. Our sampled-CFR recipe is already
Pluribus's. The rare-node tail has never been measured, because the solver keeps no per-node visit count. A bigger
70bb tree needs about 180M iterations, roughly 7 hours cold or about 2.5 hours warm.

**Opponent modelling.** Several reads put their threshold right at the line they test, so they fire on noise.
The bounds collapse to zero width at 0 and 1, exactly where "never" reads live. Bets within a match are
correlated, so the real sample is closer to matches than to bets. The double counting made the bounds 2 to 2.3
times too narrow.

**Measurement.** A burst is decided by a few all-ins: today three hands lost about 22,800 chips against a total
deficit of about 10,900. Our logs show both hands on every called all-in, so the luck in those pots can be removed
exactly. Peeking after every burst raises a 5 percent false-positive rate to about 14 percent over five looks.

## The order, after the season

| # | What | Why first | Cost |
|---|---|---|---|
| 1 | All-in equity adjustment on the match logs (the cheap half of AIVAT) | every burst gets a usable error bar; the agent guesses ±68 falls to 20 to 35 chips a hand, unmeasured | half a day |
| 2 | A written stopping rule for bursts (SPRT or a confidence sequence) | stops the peeking error | 1 day |
| 3 | Copy validation: fit on matches before a date, predict the ones after | tells us how far to trust every copy duel, and when to play the exploiter | 1 to 2 days |
| 4 | Third-raise probes in LBR, then paired LBR at 70 and 100bb on the live set and the (4,3,2,1) rung | measures the hole before paying 5 hours to close it | half a day plus the runs |
| 5 | Profiles as posteriors pulled toward the population average, counted per match; a false-fire budget; merge `profile-base` and the clean file | the reads stop firing on noise | 1 to 1.5 days |
| 6 | A per-node visit counter and a stopping rule for training | ends guessing budgets; up to 3x time saved on converged rungs | half a day |
| 7 | A price-aware fallback for small third raises, no training | the cheap fix for the hole, if 4 shows one | half a day |
| 8 | The exploiter share sweep at 0.10 and 0.20, starting with decomposing the head to head | finds the knee of the curve | an overnight retrain a point |
| 9 | River solving against the fitted opponent model, not the balanced answer | the only search design that keeps the exploit | 1.5 to 2.5 days |
| 10 | Bigger trees (a sized third raise), turn solving, data-biased response | only once 1 to 6 can read their effect | days each |

Items 1 to 3 come first because without them nothing below them can be read. Items 4 and 5 are cheap and target
the two holes this weekend actually found. Item 10 is where the papers say the long-run strength is, but it is the
part we can least afford to build blind.

## Caveats carried from the notes

Some numbers are estimates: the "worth about 45 bets" for Dronev4, "about 40 BB/100" for a small four-bet bluffer,
and the AIVAT error shrinkage. Some references were written from memory rather than fetched; the measurement note
names which. Two process slips were reported by the agents themselves. One agent used system `python3` to trim its
own report, and another used it to read a JSON file. Neither touched the venv or any other file.
