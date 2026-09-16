# The two-week push: concrete, low-gate ways to get stronger

Written 15 September 2026, evening, from two audits beside this file:
`2026-09-15-frontier-audit.md` (where the design stands against Libratus, Pluribus, Modicum,
DecisionHoldem, GTO Wizard AI and the 2026 papers, with the improvements the literature backs)
and `2026-09-15-solver-engineering-audit.md` (every cost on this machine, measured). This is the
plan that comes out of the two, sorted by what needs no gate at all, what needs only a
same-tree head-to-head, and what needs Slumbot.

## Where we stand, in one paragraph

Every bot that has beaten Slumbot since 2018 had real-time search, a blueprint one to two
orders of magnitude denser than ours, or both. Ours has six postflop buckets against 200 to
30,000, three million iterations against 200 million, and no search at play time. Modicum's
blueprint alone, at forty times our compute and five thousand times our buckets, still lost to
Slumbot by 11 mbb/hand, and its turn-to-end solver was worth 22. So the honest fortnight goal
is the Slumbot loss from about −1,000 to a few hundred and a turn solver that works; beating
Slumbot is the month. The arena rating is a separate problem, decided by exploiting a weak
field, and the ledger is its only instrument.

## Tier 0: correctness-preserving, no gate, bit-identical strategy at a fixed seed

These change how fast and how big, not what the solver computes. Guard each with a native
golden test: 2,000 cap-2 iterations at a fixed seed, `average_strategy()` byte-identical.

| item | measured today | gain | hours |
|---|---|---|---|
| `street_actions` builds a string 4,052 times per iteration | 1.43 ms/it | 1.3 to 2x on traversal | 2 |
| post-recursion refetch and no `reserve()` | | 2 to 4 percent plus rehash spikes | 0.5 |
| bucket memo of 500,000 entries with a zero cross-iteration hit rate | 24 MB | a few percent | 0.5 |
| export builds a `std::map`, then a dict, then 2.3M numpy arrays | +1.1 GB transient, 6.6 s | the memory-kill state on every write | 1.5 |
| packed `uint64` info-set keys | 20-char strings | 10 to 15 percent, 30 percent of the table | 3 |
| flat strategy table: sorted keys, offsets, one float32 array | 160 MB pickle, 5.5 s load, 1,465 MB resident | 52 to 61 MB, 70 ms load, 24x smaller | 6 to 8 |
| memoise the river solver's hand set and per-board buckets | 0.29 s of a 1.5 s river decision | 0.3 s per repeat river | 1 |

The flat table alone turns the ladder from 2.4 GB and 18 seconds into about 200 MB and under a
second, which also removes the memory juggling of this evening and makes the container upload
possible.

## Tier 1: convergence-preserving, path-changing; Kuhn and Leduc as the anchor, one same-tree head-to-head as the check

| item | evidence | gain | hours |
|---|---|---|---|
| common random numbers: one deal per iteration, prefixes revealed | Lanctot 2009; Pluribus samples one board per thread; Li, Chen, Huang 2026 measure 19 to 34 percent lower exploitability | 1.43 to about 0.28 ms/it, 5x, and lower variance | 4 to 6 |
| exact all-in terminals: preflop by a suit-aware table, turn by 44 runouts | a Rao-Blackwellised terminal, the cheapest slice of VR-MCCFR (Schmid et al. 2019) | removes the ±100bb single-runout noise at exactly the shove nodes | 4 |
| skip the average for the first part of the run | Pluribus (800 minutes), Modicum (first half of subgame iterations) | small under linear, larger at rarely reached nodes | 0.5 |
| regret-based pruning | Brown and Sandholm 2015, Pluribus | speed, about 2x | 4 |
| eight threads on one solve: pre-sized open-addressed table with CAS insert, per-thread RNG and game, relaxed atomic accumulation | Pluribus and Libratus; slumbot2019's threaded CFR | 6 to 7x wall clock: 20M iterations overnight where 3M takes two hours | 8 to 16, after the packed keys |
| current-strategy fallback where the average is empty | Pluribus plays the final iteration in search | removes the exact 50/50 at never-averaged nodes | 1, plus a gate |

Together tier 0 and tier 1 are roughly 30x per night: a rung that takes two hours for 3M
iterations takes a night for 60M, and that is the budget at which the 20-bucket draw and the
lossless preflop's thin nodes stop being about density.

## Tier 2: changes the strategy; same-tree head-to-head at 40,000 hands x 3 seeds

- Purification postflop: built, `--purify postflop`; Tartanian7 +17 to +25 mbb/h.
- Exact bucketing: river by enumerating the 990 opponent hands at the cost of 200 samples;
  flop through a table. Retrains and gates.
- Fifty to 200 imperfect-recall buckets, once tier 1 makes the iterations affordable. The
  20-bucket draw was at 3M; the papers' bucket counts were trained at tens of millions.
- The river solver kept unsafe (at 200 buckets unsafe is 130 mbb/g against 424 for max-margin;
  only the estimate variants do better and need per-hand values we cannot supply), with
  Modicum's tweaks, ported to C++, then the turn solved to the end with its 44 rivers.

## Tier 3: needs Slumbot

- The always-fold calibration, 1,000 hands: the raw must read −750, and what the baseline-
  differenced column does then says whether it can be trusted. A chance-only AIVAT from the
  blueprint's values is two days and would cut the ±396 interval by most of its width.
- Translation distance histogram from the Slumbot logs, then opponent-only sizes or cap-3.
- The best contender at the end of the fortnight.

## The order

Days 1 to 3: tier 0 and the golden test, then common random numbers, exact terminals, skip-
early-averaging and pruning with Kuhn and Leduc; then the threads. Retrain the 200bb cap-2
contender to 20M iterations overnight. Day 4: the always-fold calibration, then Slumbot on the
new contender with the miss histogram. Days 5 to 9: the river solver in C++, gated on the same
tree and under its own arena label, then the turn. Days 10 to 11: exact bucketing and the
current-strategy fallback, the ladder retrained at the new throughput, purification and the
bucket count gated. Days 12 to 14: the best contender against Slumbot, the translation
histogram, and the arena on the exploitation rules the ledger can see.

None of it before Friday's fixture: a native rebuild kills a running training and the bot needs
the machine stable through the season. Thursday daytime is the earliest start.
