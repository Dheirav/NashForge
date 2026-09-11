# What strong poker engines do, and where ours differs

Written 11 September 2026, after the 200bb Slumbot measurement came back at
**−997.8 ± 396 mbb/hand** and both the training lever and the stack-depth lever
turned out to be spent. The question this answers is narrow: given that we lose
to Slumbot by about a thousand millibigblinds per hand, what specifically are
the strong engines doing that we are not, and which of those differences is
worth acting on first.

Sources are listed at the end. Every number attributed to another system comes
from its own paper.

---

## The three engines side by side

| | **NashForge (ours)** | **Slumbot** | **Modicum** |
|---|---|---|---|
| Bet sizes, initial bet | 3 (½, 1, 2× pot) + all-in | **11** (0.25 to 50× pot) + all-in | not published |
| Bet sizes, raises | same 3 | **8** for raises, **3** for three-bets, 1 for four-bets and beyond | |
| Raises per street | **1** | **unlimited** | |
| Betting sequences | ~8,200 | **~6,000,000** | |
| Preflop card buckets | **6** | **169** (every distinct hand) | |
| Postflop card buckets | **6** per street | **3,904 / 3,602 / 2,173** (flop/turn/river), imperfect recall | |
| Information sets | **49,200** (23,970 reached) | **5,700,000,000** | |
| Compute to build | ~3.5 core hours | 250,000 core hours, 2 TB RAM | **<1,000 core hours, 16 GB** |
| Real-time solving | none | none | **depth-limited subgame solving** |
| vs Slumbot | **−998 ± 396** | — | blueprint alone **−11 ± 8**, with solving **+11 ± 9** |

Two things jump out of that table before any analysis. Our betting abstraction
is about **700 times smaller** than Slumbot's measured in betting sequences,
while our card abstraction is roughly 500 times smaller measured in buckets. And
Modicum reached parity with Slumbot on **less than 1,000 core hours**, which is
laptop compute, so the gap is not primarily a hardware gap.

---

## Finding 1: the betting abstraction is the gap, and Slumbot's author says so

Jackson states the design judgment directly in the Slumbot NL paper, section 5.3:

> Note that we devote most of our capacity to the betting abstraction as opposed
> to the card abstraction. [...] It also reflects our judgment that a reasonably
> high quality card abstraction can be achieved with relatively few buckets, but
> that **the ability to understand the difference between various bet sizes is
> vital.**

That is the same conclusion our own bucket sweep reached from the other
direction on 11 September: six buckets beat twenty and fifty at every budget
across a 128-fold range, so card resolution is not what is holding us back.

The concrete shape of the gap is worth stating precisely, because "more bet
sizes" understates it. Slumbot allows eleven sizes for an initial bet, eight for
a raise, three for a three-bet, and a pot-size bet for four-bets and beyond,
with an all-in always available and **no cap on how many raises a street can
contain**. We allow three sizes plus all-in and **one raise per street**.

A single raise cap does not merely coarsen the bet sizes. It removes whole
categories of play: there is no three-bet, no four-bet, no check-raise followed
by a re-raise, and no way to build a pot across a street in more than two steps.
Against an opponent whose tree contains all of those, every one of them is an
off-tree node for us, which is what the lookup miss rate has been saying all
along as it climbed from 8.7 to 11.9 percent.

---

## Finding 2: our bucket result may itself be a consequence of the raise cap

This is the part that changes what to do next, and it is a caution about our own
finding rather than about anyone else's.

Jackson's "relatively few buckets" means about 3,000 per street plus an exact
preflop. Ours means six. Our sweep showed that going from six to twenty to fifty
makes play *worse* at every budget we tested, which agrees with him in direction
and disagrees wildly in magnitude.

The likely reason is that **finer card distinctions have nowhere to express
themselves in a betting tree this small.** With one raise per street and three
sizes, the strategy space at any node is six actions wide and shallow. Two hands
that a fifty-bucket abstraction separates can only act differently if some
available action distinguishes them, and there are barely any. Spending the
partition on cards the betting tree cannot act on is pure cost.

If that is right, the bucket sweep answered "how many buckets, given this
betting abstraction" rather than "how many buckets". **The sweep should be
re-run after the raise cap is lifted**, and the answer may well flip. Quoting
the current result as "six buckets is correct" outside that context would be
wrong, and `NEXT.md` already words it narrowly for this reason.

---

## Finding 3: our LBR failed for a diagnosable and fixable reason

The project closed its Local Best Response investigation with no usable bound,
after four defects fixed and three valuation models, because LBR could not beat
a converged strategy. The published record says that is not how LBR normally
behaves. Lisý and Bowling used it to show that abstraction-based no-limit agents
are "remarkably poor Nash equilibrium approximations", and Modicum's paper notes
that similar forms of LBR "have been shown to defeat prior top poker AIs that do
not use real-time solving by hundreds or thousands of mbb/g".

The mechanism is in how LBR is given its actions. From Lisý and Bowling:

> An agent using no card abstraction and the F,C,P,A action abstraction, when LBR
> considers **only these actions**, there is no translation issue and LBR indeed
> **fails to exploit** this agent, but once LBR considers **more actions**, it also
> exploits this agent.

Modicum's LBR opponent bet `0.33 × 2^x` times the pot for x in 0 to 10 on the
flop, which is eleven sizes its blueprint did not contain.

**That is NOT our problem, and this section was wrong until 11 September.**

`cfr/lbr.py` already bets off-abstraction. `DEFAULT_BET_SIZES` is eleven
fractions from 0.25 to 3.5 pot, "deliberately finer than the abstraction's
0.5 / 1.0 / 2.0, and extending past both ends" — the same construction Modicum
uses. The phrase in `head_to_head.py`'s docstring, that LBR "is confined to the
same abstraction", means the *card* abstraction, which it must share to model
the opponent at all. I read it as the action abstraction and wrote a fix plan
around a cause that did not exist.

Measured that evening, 1,500 hands each:

    [4]   100bb   -0.418 chips/hand   ci95 [-2.18, +1.34]   slack
    [4]   200bb   -2.647 chips/hand   ci95 [-5.48, +0.19]   slack
    [4,2] 100bb   -0.352 chips/hand   ci95 [-2.10, +1.39]   slack

All three negative and straddling zero. A negative LBR value is not negative
exploitability, which cannot exist: it means this greedy exploiter lost money,
so the bound proves nothing. Deeper stacks, which should give an exploiter more
room, made it worse rather than better, so "our game is too shallow" does not
explain it either.

**What is known:** our LBR cannot beat our own solvers, and those solvers lose
about a thousand mbb/hand to Slumbot, so they are certainly exploitable. The
failure is in the exploiter, not the bound's logic.

**What is not known is why**, and two explanations offered on the spot did not
survive contact with the data. The published results come from a different
implementation against bots five orders of magnitude larger. Reconciling that is
real work, and the honest status remains what `CODEBASE_AUDIT.md` already said:
no-limit has no exploitability figure here.

It also gives us a second reason to care about it. Lisý and Bowling found that
Act1 and Slumbot were statistically indistinguishable head to head, within 20
mbb/g, while Act1 was **1,300 mbb/g less exploitable** under LBR. Head-to-head
play and exploitability are close to independent. Every ranking this project
has produced is head to head.

---

## Finding 4: real-time solving is the biggest single lever, and it is laptop-scale

Modicum's results table is the most important number in this document:

| | vs Baby Tartanian8 | vs Slumbot |
|---|---|---|
| Blueprint only, no real-time solving | −57 ± 13 | −11 ± 8 |
| Naïve depth-limited solving | −10 ± 8 | −1 ± 15 |
| **Depth-limited solving** | **+6 ± 5** | **+11 ± 9** |

Adding search at play time moved it by about 22 mbb/hand against Slumbot and
turned a loss into a win, on **a 4-core CPU with 16 GB of memory**, taking about
20 seconds per hand.

The idea is specific and worth stating, because the naïve version does not work
and the table shows it. When you truncate a subgame at a depth limit you need a
value for the leaf, and in an imperfect-information game a state does not have a
single value: what the position is worth depends on the strategy played
elsewhere. Assuming the blueprint's value at the leaf is the naïve version, and
it is worth almost nothing (−1 ± 15). Modicum instead lets the **opponent choose
among several continuation strategies** at the depth limit, so the leaf carries
multiple values and the solver has to be robust against all of them.

For us this is a project rather than a change, and it presupposes a blueprint
worth refining. It is the right long-term target, not the next step.

---

## Finding 5: the literature's CFR variant advice does not transfer here, and we already measured that

CFR+, Linear CFR and Discounted CFR are all reported as converging dramatically
faster than vanilla CFR. That result is proven and measured for **exhaustive
tree traversal**. We use external-sampling Monte Carlo CFR, and
`scripts/cfr/compare_update_rules.py` settled the question on Leduc, where
exploitability is computed exactly rather than estimated:

| iterations | vanilla | cfr+ | dcfr | linear |
|---|---|---|---|---|
| 1,000 | 0.7769 | 0.6843 | 0.6926 | 0.7213 |
| 16,000 | 0.1313 | 0.1542 | 0.1673 | 0.1072 |
| 64,000 | 0.0615 | 0.0819 | 0.0930 | **0.0559** |

Under sampling, CFR+ and DCFR are **worse** than vanilla, which is the opposite
of the exhaustive-traversal result, and the reason is in the script's own
docstring: flooring cumulative regret at zero discards sampling noise
asymmetrically rather than averaging it away.

Linear CFR is about 10 percent better than vanilla at 64,000 iterations and
`train_nolimit.py` still uses `VANILLA`. That is a small free improvement
sitting unused, worth taking when something else is being changed anyway, and
not worth a dedicated run.

---

## Modicum in detail, since it is the closest thing to a template for us

Read carefully, Modicum is not a story about a better blueprint. It is a story
about what you do at play time, and its blueprint is deliberately ordinary.

**The blueprint is the ordinary part.** Standard abstraction techniques, stored
as 4-byte floats in **5 GB**, solved by plain Monte Carlo CFR for **700 core
hours**. That blueprint on its own loses to Slumbot by 11 ± 8 mbb/hand, which is
already ninety times closer than we are, but the paper treats it as a component
rather than a result. Everything that makes Modicum competitive happens after
the cards are dealt.

**The problem it solves.** If you want to search during play, you have to stop
somewhere and put a value on the position you stopped at. In chess that is fine,
a position has a value. In poker it does not: what a position is worth depends
on the strategy being played everywhere else, including parts of the game you
are not searching. Their Rock-Paper-Scissors example makes it concrete, and the
consequence is that the obvious approach does not merely underperform, it is
**worse than not searching at all**.

**Their fix, in one sentence.** At the depth limit, let the *opponent* pick
which of several continuation strategies they will play for the rest of the
hand. The leaf then carries several values instead of one, and your solution has
to be good against all of them.

**How many values, and where they come from.** This is the practical core.

- On the **first betting round** they generate **ten** continuation strategies by
  a self-generative loop: solve the depth-limited subgame against the current
  set, compute the opponent's best response to that solution, add it to the set,
  repeat. The resulting table of state values is **240 MB**.
- On the **second betting round** they use the cheaper **bias approach**: take
  the blueprint and distort it four ways, giving the blueprint itself, one biased
  toward folding (fold probabilities multiplied by 10 and renormalised), one
  biased toward checking and calling, and one biased toward betting and raising.
  Values are estimated by Monte Carlo rollouts of each.
- From the **third betting round onward** the remaining game is small enough to
  solve to the end exactly, with an enhanced CFR+. No depth limit is needed.

**The warning in their Figure 2, which matters if we ever try this.**
Exploitability against an off-tree bet, measured in flop hold'em: with **one**
value at the depth limit it is about 12 mbb/g, which is *worse* than the roughly
9.7 of plain action translation. At 4 values it is under 3, at 16 values about
1.4, against 0.9 for having had the action in the abstraction all along. So a
naive implementation is a step backwards, and the whole technique only pays from
about four values upward.

**What this does to action translation, which is our 11.9 percent miss rate.**
Their words: depth-limited solving "makes nested solving feasible even in the
early game, so it is possible to play without acting according to a precomputed
strategy or **using action translation**". When the opponent bets a size our
abstraction does not contain, we currently map it to a nearby size we do have,
which is exactly the weakness LBR is designed to punish. Modicum instead builds
and solves a new subgame following the actual bet, so the off-tree action stops
being off-tree.

**Their variance reduction, which we could use immediately.** Modicum's
evaluation used **AIVAT** to reduce variance. Our Slumbot measurement is
−997.8 ± 396 mbb/hand over 9,999 hands, and that interval is wide enough that
it could not detect the 200bb retrain's effect even if the effect had been
substantial. AIVAT is the principled version of the idea we correctly rejected
when we found that differencing Slumbot's own `baseline_winnings` changes what
is being estimated rather than its precision. It is unbiased by construction.
This is a **measurement** change, not a training change: it makes every future
external number sharper without touching an agent.

**For scale, the ladder Modicum sits on**, all from the same paper: Baby
Tartanian8 beat Slumbot by 36 ± 12, Libratus beat Baby Tartanian8 by 63 ± 28,
and Libratus beat top humans by 147 ± 77 mbb/g. Modicum beat Slumbot by 11 ± 9
using less than 0.1 percent of Libratus's compute.

### The cheapest thing in here that we could actually build

Not the full technique. **River and turn solving.** Modicum needs a depth limit
only for the first two betting rounds, because from the third onward the
remaining game is small enough to solve exactly. That part requires no
multi-valued states, no self-generative strategy sets, and no neural network. It
is ordinary CFR on a small tree, run at play time, and it would replace our
blueprint lookup on precisely the streets where our abstraction is coarsest and
the pot is largest.

## What to do, in order

**1. Lift the raise cap, and add bet sizes.** This is where the 700-fold gap is,
it is the dimension Slumbot's author identifies as the one that matters, and it
is the only untested lever we have left. `results/cfr/abstraction_size.json`
already prices it: at raise cap 2 and six buckets the tree is roughly 7.4
million information sets against today's 49,200. That is a real jump but not an
impossible one, and the bucket cache fix of 11 September removed the memory
ceiling that would otherwise have made it impossible to train.

Start by measuring the tree rather than launching a run. Raise cap 3 is 495
million information sets and 47 GB, so cap 2 is the only reachable rung.

**2. Fix LBR by letting it bet off-abstraction.** It is a measurement, not a
training run, it is hours rather than days, and it would give this project the
one number it has never had. The change is to give the LBR agent bet sizes the
solver's abstraction does not contain, following Modicum's `0.33 × 2^x` ladder,
rather than restricting it to the same six actions.

**3. Re-run the bucket sweep after (1).** The current result may be a
consequence of the betting tree being too small for card resolution to matter.
That is cheap to re-test and the answer could flip.

**4. Switch production training to `LINEAR`.** Already measured here, about 10
percent, free, and currently unused.

**5. Depth-limited solving, eventually.** The largest single lever in the
literature and demonstrably laptop-scale, but it presupposes a blueprint worth
refining and is a project in its own right.

---

## One thing to keep in perspective

Modicum's blueprint alone, with no real-time solving, loses to Slumbot by
**11 ± 8 mbb/hand**. We lose by **998 ± 396**. The distance is not mysterious
and it is not mainly about compute: Modicum built its blueprint in under a
thousand core hours. It is about what the abstraction can express, and the
evidence from three independent directions now points at the same dimension.

## Sources

- [Slumbot NL: Solving Large Games with Counterfactual Regret Minimization Using Sampling and Distributed Processing](https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf), Eric Jackson, AAAI 2013 Workshop. Betting and card abstraction, sizes of both, PCS sampling.
- [Depth-Limited Solving for Imperfect-Information Games](https://proceedings.neurips.cc/paper_files/paper/2018/file/34306d99c63613fad5b2a140398c0420-Paper.pdf), Brown, Sandholm and Amos, NeurIPS 2018. Modicum, its results table, and its LBR construction.
- [Equilibrium Approximation Quality of Current No-Limit Poker Bots](https://poker.cs.ualberta.ca/publications/aaai17ws-lisy-lbr.pdf), Lisý and Bowling. LBR, the translation issue, and the Act1 versus Slumbot exploitability comparison.
- [Superhuman AI for heads-up no-limit poker: Libratus beats top professionals](https://www.science.org/doi/10.1126/science.aao1733), Brown and Sandholm, Science 2017. Nested subgame solving and self-improvement against off-tree bet sizes.
- [RL-CFR: Improving Action Abstraction for Imperfect Information Extensive-Form Games with Reinforcement Learning](https://arxiv.org/abs/2403.04344), Li et al., ICML 2024. Learned action abstraction, beats Slumbot by 84 ± 17 mbb/hand.
- [Solving Imperfect-Information Games via Discounted Regret Minimization](https://arxiv.org/pdf/1809.04040), Brown and Sandholm. DCFR and Linear CFR.
