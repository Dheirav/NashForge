# Action abstraction and off-tree translation: is the third raise worth a richer tree?

Written 5 October 2026, read-only. Nothing was trained, duelled or run. Sources are the repo
(`chipzen/bridge.py`, `abstraction/translation.py`, `cfr/lbr.py`, `NEXT.md`,
`~/pokerbot-scratch/fourbet/scope.md`) and the papers listed at the end. Where a claim is mine rather
than a paper's or a measurement's, it is marked **inference**.

## 1. Is "third raise is all-in only" a real hole, and how big?

**What the papers establish.** Off-tree bets are the standard way coarse bots get beaten, and
translation alone does not close it.

- Brown and Sandholm (2017), Table 4: in a flop game where one player lacks the 0.75 pot size, the
  randomized pseudo-harmonic mapping leaves **1,465 mbb/hand** of exploitability, while nested
  subgame solving at the off-tree node brings it to **119 to 150**. That is a tenfold gap, and the
  mapping they beat is the one we already use.
- Lisý and Bowling (2017), Table 3: a bot with no card abstraction but a fold, call, pot, all-in
  tree loses **2,403 mbb/hand** to LBR betting off-tree with hard translation and **1,981** with
  soft translation. Soft translation helps a little and does not fix it. On the ACPC bots most of
  the LBR value came from card abstraction instead, which is the caution: betting holes are real
  but are not automatically the biggest leak.
- Ganzfried (2015) on Claudico: two of the costly hands came from a re-raise mapped to the wrong
  size, after which the bot played on with a wrong idea of the pot. That is the same shape as our
  pseudo all-in continuation.
- Libratus (Science 2018), Table 3: against Baby Tartanian8, nested solving on-tree only won
  59 ± 28 mbb/game and full nested solving including off-tree responses won 63 ± 28. **Against a
  bot that stays near its own sizes, fixing off-tree play barely moves head-to-head results**, even
  though it cuts exploitability by an order of magnitude. That explains why our duels keep tying.

**What our own data says.**

- `chipzen/bridge.py:_as_abstract` reads every third raise as all-in, whatever its size, because
  the schedule has no sized entry there and pseudo-harmonic needs two neighbours to randomise
  between. So the facing decision is answered as if a 0.5 pot raise were a shove.
- The existing LBR **cannot see this hole**. `cfr/lbr.py:_abstract_raises` only considers sized
  raises present in the abstraction; where the tree offers only all-in, the list is empty and LBR
  never probes a small third raise. The +26 to +53 BB/100 "between sizes" increment from 25 Sept
  measures the first and second raise levels only.
- The three 4 Oct hands at about 7,600 chips each were big pots lost at showdown, two of them clear
  coolers (trips against better trips, A6 against A7). They show the hole leads to big pots, not
  that the translation lost the chips. The 1 Oct audit found 5 of 99 misses recoverable by better
  translation. The arena record does not show anyone exploiting it on purpose.
- Slumbot reached a third raise our tree lacked in 69 of about 3,000 hands (the 22 Sept split),
  about 2 percent of hands. A competent opponent gets there often enough for it to matter.

**Inference on size.** Facing a 0.5 pot third raise, the minimum defence is 67 percent of our range,
while the range that continues against a perceived 8 pot shove is much narrower. If we fold 60
percent there, a pure bluff risks 0.5P to win P and gains 0.6P minus 0.2P, so 0.4P, about 8bb in a
20bb three-bet pot. An opponent who builds that node in 5 percent of hands would take on the order of
40 BB/100. Every input there is an assumption (our fold rate at that node, its frequency), which is
why option A measures it before anything is built. My summary: **it is a real, exploitable-in-principle
hole whose size is unmeasured, and the arena field is not currently exploiting it.**

## 2. Options, ranked

### A. Measure first: LBR with third-raise probes (do this first)

Give LBR a sized third raise where the tree has only all-in, perceived as all-in exactly as the
bridge does. Probe 0.4, 0.5, 0.75 and 1.0 pot. LBR's roll-out to showdown after the call is a fair
stand-in for our collapsed continuation, and it keeps the result a lower bound.

- **Cost:** a small change in `cfr/lbr.py` (perceive an off-tree raise as `ALL_IN` when the sized
  list is empty, while still betting the real amount) plus tests, about half a day. The run is the
  existing 16 chunks of 8,000 hands per condition.
- **Measurement:** paired by seed, live set at 70bb and 100bb, "default menu" against "default menu
  plus third-raise probes". The increment is the price of this hole. Run the same on the (4,3,2,1)
  rung: if its increment is near zero while v5x's is large, the richer tree has bought something
  that duels cannot show. **Go/no-go:** an increment inside two standard errors of zero ends the
  question for this season.

### B. A price-aware fallback for small third raises (cheap, bridge only)

When the third raise leaves chips behind and is below a threshold (say under 1.5 pot), stop
answering it as a shove. Keep the tree's ranking of hands facing all-in, but continue with the
top share of the range set by the real price: continue at least 1 − b/(P + b), the minimum defence
frequency. Call by default and keep the jam for the top of that range. This is a rule, not an
equilibrium answer, and it can overcall against a value-heavy re-raiser, which is why it is gated.

- **Cost:** a few hours in `chipzen/bridge.py` and the player, zero training.
- **Measurement:** replay on the match record first (how many of the logged third-raise decisions
  change, and to what), then a duel against the current set with a panel opponent that makes small
  third raises (the panel has none; add one to `tools/panel` or `evaluation`), then option A's LBR
  on both. A burst only after both, and read decomposed.

Pseudo-harmonic randomization by itself is **not** an option here: there is only one abstract raise
at that depth, so there is nothing to randomise between. It is already in place everywhere a pair
exists.

### C. A non-all-in third raise on the deep rungs, chosen from the logs and funded to parity

This is the Libratus self-improver idea: add the size opponents actually use rather than a generic
one. Histogram third-raise sizes by depth from `results/chipzen/matches/*.jsonl`; if 0.5 pot or pot
dominates at 70 and 100bb, add that one size at the third level (with all-in kept), on preflop and
flop first, warm by action from the (4,2,1) rung.

- **Cost:** the (4,3,2,1) tie was at equal iterations with about three times the decision points.
  At the 1 Oct parity rule of about 51 iterations per reached information set, a rung near 3.5M
  reached nodes needs about 180M iterations, roughly 5 hours at 70bb at the measured 105 to 110 s
  per million, more at 100bb, peak about 1.6 to 2 GB warm. A one-size addition on two streets should
  reach far fewer nodes than (4,3,2,1) and cost proportionally less.
- **Measurement:** option A's paired LBR against the matched (4,2,1) control at equal per-node work,
  then a duel against that control. **Expect the duel to tie** (Libratus' +4 says so); the LBR is
  what decides it. The T2 and preflop four-bet ties say the same about head-to-head.

### D. Nested subgame solving at the off-tree node (the real fix, not this season)

Every strong bot handles off-tree raises by solving after them, not by more sizes: Libratus from the
turn and at every off-tree action, DeepStack re-solving every decision with fold, call, two or three
sizes and all-in, Pluribus searching whenever an opponent leaves its 1 to 14 size blueprint. The
papers put this at a tenfold exploitability reduction over translation. For us it is realistic only
postflop, where the planned turn solver and the existing river solver would extend to a re-solve
after an off-tree third raise; preflop needs depth-limited values the blueprint cannot yet supply.

- **Cost:** days to weeks, plus per-decision latency in the arena's clock.
- **Measurement:** same tree with the re-solve on against off, by option A's LBR, then its own label.

### E. Do nothing to the gated set before tonight

The final at 02:30 IST plays the gated set, per the match-day rule. None of A to D is ready, and the
evidence does not justify an untested change.

## 3. Is a richer tree worth its training cost?

Not yet, and not by a duel. Every tree test so far ((4,3,2,1), T2 for exploiters, preflop four-bet,
named sizes) tied or lost head to head, which is what the literature predicts for a change that only
matters when an opponent uses the missing size. The case for a richer tree rests on exploitability,
and the one instrument for that is currently blind at the third raise. Fix the instrument (A), take
the free rule (B) through the gates, and spend the five hours on (C) only if A shows the hole is
worth more than its noise.

## References

- Ganzfried and Sandholm (2013), Action Translation in Extensive-Form Games with Large Action
  Spaces: Axioms, Paradoxes, and the Pseudo-Harmonic Mapping, IJCAI.
  https://mlanthology.org/ijcai/2013/ganzfried2013ijcai-action/ (workshop PDF:
  https://cdn.aaai.org/ocs/ws/ws1109/7185-30512-1-PB.pdf)
- Schnizlein, Bowling and Szafron (2009), Probabilistic State Translation in Extensive Games with
  Large Action Sets, IJCAI. https://mlanthology.org/ijcai/2009/schnizlein2009ijcai-probabilistic/
- Lisý and Bowling (2017), Equilibrium Approximation Quality of Current No-Limit Poker Bots, AAAI
  workshops. https://arxiv.org/abs/1612.07547
- Brown and Sandholm (2017), Safe and Nested Subgame Solving for Imperfect-Information Games,
  NeurIPS. https://arxiv.org/abs/1705.02955
- Brown and Sandholm (2018), Superhuman AI for heads-up no-limit poker: Libratus beats top
  professionals, Science. https://www.science.org/doi/10.1126/science.aao1733 (PDF:
  https://noambrown.com/papers/17-Science-Superhuman.pdf)
- Brown and Sandholm (2019), Superhuman AI for multiplayer poker (Pluribus), Science.
  https://www.science.org/doi/10.1126/science.aay2400 (supplement:
  https://noambrown.github.io/papers/19-Science-Superhuman_Supp.pdf)
- Moravčík et al. (2017), DeepStack: Expert-level artificial intelligence in heads-up no-limit
  poker, Science. https://arxiv.org/abs/1701.01724
- Brown, Sandholm and Amos (2018), Depth-Limited Solving for Imperfect-Information Games, NeurIPS.
  https://arxiv.org/abs/1805.08195
- Ganzfried (2015), My Reflections on the First Man vs. Machine No-Limit Texas Hold 'em
  Competition. https://arxiv.org/abs/1510.08578
- Jackson (2013), Slumbot NL: Solving Large Games with Counterfactual Regret Minimization Using
  Sampling and Distributed Processing. https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf
  (the 11, 8, 3, 1 size taper quoted in `abstraction/betting.py` is the repo's claim; I did not
  verify it against this paper)
- Hawkin, Holte and Szafron (2011), Automated Action Abstraction of Imperfect Information
  Extensive-Form Games, AAAI. https://poker.cs.ualberta.ca/publications/AAAI11.pdf
- Brown and Sandholm (2015), Simultaneous Abstraction and Equilibrium Finding in Games, IJCAI.
  https://dl.acm.org/doi/abs/10.5555/2832249.2832317
