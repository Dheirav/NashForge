# NashForge against the frontier, and what to change without a gate

Written 15 September 2026 from the repo and the primary papers by a research agent. Nothing
was modified. Where a number is inference rather than a paper's, it says so.

## 1. Where the design stands

Every HUNL bot that has beaten Slumbot since 2018 did it with real-time search, a blueprint
one to two orders of magnitude denser than ours, or both.

| system | vs Slumbot (mbb/h) | what it is |
|---|---|---|
| Slumbot 2018/19 | baseline | static CFR blueprint, public chance sampling, ~250,000 core-hours, 2 TB (https://arxiv.org/pdf/1805.08195) |
| Baby Tartanian8 2016 | +36 ± 12 | MCCFR blueprint with pruning, purified postflop, ~2M core-hours |
| Modicum 2018 | blueprint alone −11 ± 8; with search +11 ± 9 | 169 preflop then 30,000 buckets, 700 core-hours, 16 GB, plays on 4 cores; from the turn solves to the end with CFR+ (150 to 1,000 turn iterations, 300 to 2,000 river), unsafe first then nested safe |
| DeepStack 2017 | replication −63 ± 40 (https://arxiv.org/pdf/2007.10442) | continual re-solving with value nets, ~1M core-hours |
| Libratus 2017 | beat humans +147 ± 77 | MCCFR blueprint on 196 nodes, nested safe subgame solving from the turn |
| Pluribus 2019 (6-max) | n/a | linear MCCFR, negative-regret pruning, 64 cores for 8 days, 4-byte int regrets |
| Supremus 2020 | +176 ± 44 | DeepStack-style value nets |
| ReBeL 2020 | +45 ± 5 | RL plus search |
| Player/Student of Games 2021/23 | +7 ± 3 | general search, large compute |
| AlphaHoldem 2022 | +111.6 | end-to-end RL, one PC, three days |
| DecisionHoldem 2022 | +730 | linear CFR blueprint, 200M iterations on 48 cores for 3 to 4 days, safe depth-limited solving (https://arxiv.org/pdf/2201.11580) |
| GTO Wizard AI (Ruse) 2023 to 2026 | +194 ± 41 over 150k hands, 7 s per move | value nets plus search; the March 2026 benchmark paper (https://arxiv.org/abs/2603.23660) puts every frontier LLM far below it |
| EVPA, ICLR 2025 | +10 to +100 at 0.02 to 2 s per solve | minimax pruning before CFR plus online subgame abstraction |

2026 work that bears on the list: correlated chance sampling for MCCFR (Li, Chen, Huang,
July 2026, https://arxiv.org/abs/2607.27035, 19 to 34 percent lower exploitability on Kuhn and
Leduc at no cost); real-time parallel CFR for subgames (https://arxiv.org/abs/2605.19928, 3.3x);
CFR as linear algebra on GPU (https://arxiv.org/abs/2605.14277); equilibrium refinements in the
re-solving gadget (https://arxiv.org/abs/2601.17131); full-recall outcome isomorphism
abstractions (https://arxiv.org/abs/2510.15094).

NashForge in that light: −997 ± 396 mbb/h with the one-raise solver where always-fold loses
750; the cap-2 contender is unmeasured beyond its 4.1 percent miss rate. Six postflop buckets
against 200 (Pluribus), 30,000 (Modicum), thousands (Slumbot). Three million iterations, about
16 core-hours per rung, against 200 million for DecisionHoldem. No search at play time yet.
Modicum's blueprint alone, at 40 times our compute and 5,000 times our buckets, was still −11
against Slumbot, and search was worth +22. So the honest expectation is that two weeks moves
the loss from −1,000 to a few hundred; a win over Slumbot needs the turn solver working and a
denser blueprint, which is the month. The arena rating is a different problem, decided by
exploitation of a weak field, which the ledger measures and Slumbot does not.

## 2. Improvements ranked

### A. No gate: computation only; equality or convergence tests suffice

A1. Flat node storage with integer keys. `information_set()` builds a string and the map hashes
it twice per traverser visit; the pickle is a dict of 4.2M small arrays, which is the 2.4 GB.
Replace with an enumerated betting-sequence index times buckets, an int32 slot table into a
dense node vector, int32 regrets and float32 strategy sums as Pluribus stored them. Effect: 56
bytes per node instead of about 200, play-time footprint a few hundred MB, and 1.5 to 3x per
iteration (inference). Files: `nolimit_game.hpp`, `mccfr.hpp`, `bindings.cpp`, plus a compact
loader for `chipzen/player.py`, `slumbot/player.py`, `evaluation/benchmark.py`. Test: same seed,
identical average strategy. 1.5 to 2 days. Do it while the bot is down.

A2. Common random numbers. `walk` calls `sample_chance` at every chance node, so each traverser
branch draws its own board and `values[i] - value` compares actions on different boards. Deal
the nine cards once per iteration and reveal them. Unbiased (Lanctot 2009; Pluribus's search
samples one board per thread). Half a day. Test: Kuhn −1/18 and Leduc unchanged; measure the
regret-increment variance before and after. Risk none.

A3. Exact all-in terminals. Once both are all-in the runout is sampled; replace it with the
expectation: preflop from a suit-aware 1,326 x 1,326 equity table (build once, hours on 8
cores), flop by enumerating the 990 runouts, turn the 44. A Rao-Blackwellised terminal, unbiased
and lower variance, the cheapest slice of VR-MCCFR (https://arxiv.org/abs/1809.03057). It zeroes
the ±100bb board noise at the three-bet-shove nodes the arena found thin. One day in
`nolimit_game.hpp`. Test: expected value equals the mean of sampled values. Risk none.

A4. Skip early averaging. Pluribus stored no average for the first 800 minutes; Modicum ignores
the first half of CFR+ iterations in subgames. Under linear the first tenth carries only 1
percent of the weight, but at rarely reached nodes those are the uniform visits. One line.

A5. Parallel MCCFR, one process, eight threads. Hogwild-style shared table, per-thread RNG and
bucket cache, racy adds on the flat table from A1 (a string-keyed map cannot take concurrent
inserts, so A1 first). Effect: 5 to 6x wall-clock per rung, 20M iterations overnight. One day.
Test: Kuhn and Leduc with 8 threads; log the lost-update rate. Use one atomic iteration counter.

A6. Regret-based pruning. Skip traverser actions with regret below a floor in 95 percent of
iterations, never on the river or into terminals (Pluribus; https://arxiv.org/abs/1609.03234
proves convergence). Speed, path-changing but convergence-preserving. Half a day.

### B. Needs a same-tree head-to-head (40,000 hands x 3 seeds)

B1. Current-strategy fallback for never-averaged nodes: export regret matching's current
strategy where the strategy sum is zero (the 50/50 facing a shove). An hour in `bindings.cpp`.

B2. Exact bucketing: river equity by enumerating 990 opponent hands at the cost of 200
samples; flop through the existing table (port the hash to C++); turn table overnight. At 200
samples the sd of 0.03 against centroid gaps of 0.10 to 0.17 still misplaces a tenth
(inference). Retrains and gates. One to two days.

B3. River solver, then turn to the end. Keep `cfr/river.py` unsafe (at 200 turn buckets unsafe
is 130.4 mbb/g against 424 for Reach-Maxmargin; only the Estimate variants do better and need
per-hand values a six-bucket blueprint cannot supply). Add Modicum's tweaks (ignore the first
half for the average, discount regrets by sqrt(t/(t+1)) for 30 iterations, about a factor of
three on subgame exploitability), port to C++ so 2,000 iterations fit in a second, then solve
the turn plus its 44 rivers to the end. Three to five days. Gate: on against off on the same
tree, and the arena label.

B4. Purification postflop (built): Tartanian7 +17 to +25 mbb/h; raises worst-case
exploitability. Gate only.

B5. Fifty to 200 imperfect-recall buckets once A1 to A5 make 20M iterations affordable. The
20-bucket draw was at equal density and 3M iterations. Two days plus a retrain.

### C. Needs an external measurement

C1. Action translation and an asymmetric tree. Randomised pseudo-harmonic is right
(Ganzfried and Sandholm 2013, Table 2); its residual cost against a many-size opponent (1,465
mbb/g against 119 to 150 for nested re-solving) is what B3 removes on the streets it covers.
More opponent-only sizes or cap-3 change the tree; the cheap instrument is the
translation-distance histogram from the Slumbot logs.

C2. Measurement. ±396 at 10,000 hands is why nothing can be ranked. `slumbot_measure.py`
records Slumbot's baseline winnings, unverified: play 1,000 hands of always-fold, the raw must
read −750, and the differenced column then says what the baseline is. AIVAT
(https://arxiv.org/abs/1612.06915) cut a man-machine sd by 85 percent; a chance-only version
using the blueprint's values is two days.

C3. Exploitation: the ledger is the only instrument; the exploitation review's plan stands.

## 3. The two weeks

Days 1 to 3: A1, A2, A3, A4, A6 with equality and Kuhn/Leduc tests, then A5; retrain the 200bb
cap-2 contender to 20M iterations overnight. Day 4: the always-fold calibration, then the
10,000-hand Slumbot run on the new contender with the miss histogram. Days 5 to 9: B3 in C++,
river first, gated on the same tree and under its own arena label, then the turn. Days 10 to
11: B2 and B1, ladder retrain at the new throughput, B4 and B5 gated. Days 12 to 14: the best
contender against Slumbot, C1 from the histogram, and the arena on C3. Beating Slumbot inside
the fortnight is unlikely on the evidence; the loss under a few hundred and a working turn
solver is realistic, and 2000 on the arena rests on the exploitation the ledger can see.
