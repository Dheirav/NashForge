# Review: what would move NashForge's strength, ranked

Written 15 September 2026 from a literature and competition-history search. Sources are
linked inline. Claims marked [inference] are the reviewer's, not documented.

## A diagnostic that outranks every improvement

Always-fold loses 750 mbb/hand heads-up. NashForge is at −997 ± 396 against Slumbot, so
even at the favourable end of the interval the bot is roughly as bad as folding everything:
it is bleeding chips with the hands it plays, not merely playing a coarse equilibrium.
[inference] Before any abstraction or iteration change, split the loss by (a) hands with a
lookup miss against hands without, (b) the street the hand ended on, (c) position. The 11.9
percent miss rate is the first suspect: if misses land on a poor default, 12 percent of
decisions can explain most of the gap. Half a day, and it orders everything below.

## Ranked

| # | item | expected gain | days | compute here | risk |
|---|---|---|---|---|---|
| 1 | Never miss: raise cap 2, third raise = all-in, translate every re-raise | large vs Slumbot, unknown until (a) is measured | 0.5 to 1 | one retrain | low |
| 2 | River endgame re-solve on the exact hand (unsafe, CFR+) | +29 to +87 mbb/h on river hands (documented); removes river card abstraction | 2 to 3 | 1 to 10 s per river decision | medium |
| 3 | Purification postflop, preflop left mixed | +17 mbb/h vs top bots (documented); more vs weak fields | 0.25 | none | low vs static bots |
| 4 | Linear or discounted CFR plus far more iterations | converged blueprint; bounded by the abstraction | 0.5 | 7 to 70 CPU-hours | low |
| 5 | 50 to 200 imperfect-recall buckets, 169 preflop | documented +25 mbb/g in limit; needs 4 first | 1 to 2 | days, RAM-bound | medium |
| 6 | Asymmetric action abstraction (more opponent sizes) | less translation loss vs many-size opponents | 0.5 to 1 | proportional retrain | low |
| 7 | Turn then flop depth-limited re-solving, Modicum style | −11 to +11 mbb/g vs Slumbot on a 4-core laptop (documented) | 10+ | ~700 core-hours blueprint | high, month scale |
| — | Potential-aware EMD buckets, board texture at 6 buckets | +2.2 to +2.6 mbb/h at 5,000 buckets; nothing at ours | 2+ | days | not worth it |

## 1. Card abstraction

What the winners used. Slumbot 2013: 169 preflop, then 3,904 / 3,602 / 2,173
imperfect-recall buckets in a 5.7 billion infoset tree
(https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf). Pluribus's blueprint: 169 then
200 per postflop street, 500 in search
(https://noambrown.com/papers/19-Science-Superhuman_Supp.pdf). DecisionHoldem: 169 / 50,000
/ 5,000 / 1,000 (https://arxiv.org/pdf/2201.11580). Modicum: 169 then 30,000
(https://arxiv.org/pdf/1805.08195). Six buckets is one to three orders of magnitude below
any published bot. Jackson: "quality card abstraction can be achieved with relatively few
buckets, but the ability to understand the difference between various bet sizes is vital",
and "relatively few" still meant thousands.

Imperfect recall. Johanson et al. 2013: IR abstractions beat equal-size PR ones by up to
25.7 mbb/g and had lower CFR-BR exploitability (64.8 vs 84.0 mbb/g) in limit
(https://www.ifaamas.org/Proceedings/aamas2013/docs/p271.pdf). IR is what lets 169 preflop
sit beside thousands on later streets at the same tree size.

EMD / potential-aware. Ganzfried and Sandholm 2014: +2.58 ± 1.56 and +2.22 ± 1.28 mbb/h
over distribution-aware buckets at 5,000 per street, flop only
(https://cdn.aaai.org/ojs/8816/8816-13-12344-1-2-20201228.pdf). Second-order for bots at
thousands of buckets; expectation-based buckets are stronger at small counts. At 6 buckets
plain equity is the right metric. Texture: Slumbot's public buckets subdivide thousands of
private ones; folding texture into 6 buckets multiplies the key space and thins each key.
[inference]

Why "6 vs 20 moved nothing" is not evidence buckets do not matter: measured at ~150k
iterations, a 20-bucket tree has ~3x the infosets and both were compared unconverged.
[inference]

## 2. Action abstraction

Current sizes (½, 1, 2, all-in) match what strong bots use on turn and river: Pluribus's
blueprint allows at most three first-raise sizes there and two afterwards; DecisionHoldem
uses ½P, P, 2P, 4P, A for the first two actions, P, 2P, 4P, A for actions 3 to 5, then
fold/call/all-in. The number of sizes is fine; the one-raise cap is not. Every published tree
allows re-raises and closes with all-in, and the 11.9 percent miss rate is the direct cost.

The cost of few sizes against an opponent with many: pseudo-harmonic translation was
exploitable for 1,465 mbb/h where nested re-solving held it to 119 to 150
(https://arxiv.org/pdf/1705.02955, Table 4). LBR with fold/call/pot/all-in exploited Slumbot
2016 for 4,020 mbb/h (https://arxiv.org/pdf/1701.01724). GTO Wizard AI beat Slumbot by 19.4
bb/100 over 150k hands (https://blog.gtowizard.com/crushing-a-top-hunl-poker-bot/). The cheap
mitigation is an asymmetric abstraction, Baby Tartanian8 style
(https://www.cs.cmu.edu/~sandholm/BabyTartanian8.ijcai16demo.pdf): the opponent's nodes get
more sizes than ours.

## 3. Real-time search

River-only endgame solving is the simplest version with most of the gain. Ganzfried and
Sandholm 2015 solved the exact river on the reached hand with the blueprint's ranges as
priors: +87 ± 50 vs Hyperborean and +29 ± 25 vs Slumbot on hands reaching the river, 7 s per
hand in 2015 (https://www.cs.cmu.edu/~sandholm/endgame.aamas15.fromACM.pdf). Their base
agent was purified and heavily trained; ours has a 6-bucket river, so the gain should be
larger. [inference] Two things come free: the off-tree problem on the river disappears (add
the opponent's actual size to the river tree), and river card abstraction disappears (solve
on the 1,081 exact hands).

Feasibility here. A river tree with four sizes and a two-raise cap has on the order of 100 to
200 betting sequences; CFR+ over 1,081 x 1,081 hand pairs with sorted-hand terminal
evaluation is O(hands log hands) per terminal, so 1,000 to 2,000 iterations should be seconds
in C++. Modicum ran 300 to 2,000 river CFR+ iterations on a 4-core laptop within 20 s/hand.
A 30 s clock is generous for the river; the turn is plausible but needs turn-to-river
rollouts of 49 cards, so budget it for the month. [inference on timings for this codebase]

Safe vs unsafe. Unsafe re-solving cut turn exploitability from 684.6 to 130.4 mbb/h at 200
buckets and beat every safe variant except with a very fine abstraction (Brown and Sandholm
2017, Table 3). Pluribus, Modicum and DecisionHoldem all use unsafe. Use unsafe.

Modicum is the proof this scale works: blueprint alone −11 ± 8 vs Slumbot; with
depth-limited search +11 ± 9. 700 core-hours, 16 GB, 4 cores, no neural net.

## 4. Blueprint quality

Iteration counts: Modicum 700 core-hours of MCCFR on 30,000 buckets; DecisionHoldem ~200
million linear CFR iterations; slumbot2019's examples use 100 million MCCFR iterations
(https://github.com/ericgjackson/slumbot2019); Pluribus 12,400 core-hours. At 2.5
ms/iteration, 100 million iterations is 70 CPU-hours, about 9 wall-hours across 8 cores. The
saturation measured at 150k iterations is consistent with the 6-bucket tree being near
converged within its abstraction: more iterations alone will not help, more iterations plus
more buckets will. Switch to linear or discounted averaging first (Pluribus, DecisionHoldem).

## 5. Cheap, well-attested extras

Purification. Tartanian7: no threshold +30/+10, purification +55/+19, threshold-0.15 +35/+19
mbb/h vs Hyperborean/Slumbot
(https://www.cs.cmu.edu/~sandholm/Tartanian7_AAAI15_demo_cr_1.pdf). Tartanian4-TBR beat its
thresholded twin by 80 mbb/h and won the 2010 ACPC bankroll division
(https://www.cs.cmu.edu/~sandholm/StrategyPurification_AAMAS2012_camera_ready_2.pdf). Its
stated purpose is to compensate for an unconverged blueprint, which is our situation. Caveat:
it raised Hyperborean's worst-case exploitability (244 to 437). Baby Tartanian8 purified
everything except preflop; do the same. Translation: pseudo-harmonic, randomised, as now.

## Next 4 days (the reviewer's plan)

1. Day 1 morning: split the Slumbot loss by miss/hit, street and position; run always-fold
   and always-call baselines on the same panel.
2. Day 1 afternoon: cap 2 with all-in as the third raise, translate every re-raise, purify
   postflop. Retrain with linear CFR to 10M+ iterations overnight on 8 cores. Endpoint test
   at 40k hands.
3. Days 2 to 4: river endgame solver in C++ (exact hands, blueprint ranges, opponent's
   actual size in the tree, ~1,000 CFR+ iterations, 5 s cap). Behind a flag; A/B on the
   arena with one label.

## Next month

Buckets to 50 to 200 per street with 169 preflop and imperfect recall (RAM check first: 200
buckets is ~3 GB of regrets), 100M+ discounted-CFR iterations, then the re-solver to the
turn Modicum-style. Asymmetric opponent action set. Skip EMD and texture at this scale.

Also used: Supremus (https://arxiv.org/pdf/2007.10442), Pluribus
(https://www.science.org/doi/10.1126/science.aay2400), Ganzfried 2013 translation
(https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
