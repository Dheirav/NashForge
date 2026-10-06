# River solving against the opponent model: what exists, what the logs say, what to build

6 October 2026, branch `river-design`. A design only: nothing in the bot changed. It builds on
`2026-10-05-search-and-exploitation.md`, which ranked the options from the literature without running anything, and
adds what our own 576 logged matches say about the river. The analysis is `~/pokerbot-scratch/river/measure.py`
(read only, 10 seconds).

## The short version

The river is not where the bot leaks against the field when it faces a bet. Facing a river bet, the calls we made
returned **+6,729 bb**, and calling every hand we folded instead would have **lost 5,588 bb**. The field bets value
on the river and the tree already defends against it. What is left on the river is our own betting, and it differs
by opponent: against mr_hide, a station, our bluffs lost 152 bb in 13 tries, while wsp folds 79 percent of the time
and never once called a value bet. That is a per-opponent question, so the useful river solve is one that solves
against the opponent's measured responses, not the equilibrium solve we already have, which loses on the exploiters.

## 1. What `--river-solve` does today

`chipzen/player.py` calls `cfr.river.decide_river` on every river decision when `--river-solve` is on.

- **The tree.** Built at decision time from the arena's own pot, outstanding bet and both stacks
  (`build_tree`), rooted at the opponent's actual bet size, so a river solve never misses. Raise sizes are
  half pot, pot and 2x plus all-in, by the primary rung's raise schedule.
- **The hands.** All 1,081 hole-card pairs the board allows, exact, with blockers.
- **The ranges.** Both players' reach is walked along the public history through **our own strategy table**
  (`blueprint_ranges`): the opponent is assumed to have arrived holding what our blueprint would hold. That is
  unsafe re-solving, as every practical bot since 2017 does it. Two other sources exist: `--river-oracle` takes a
  scripted opponent's true range (duels only, `cfr/river_oracle.py`), and `--river-blend X` mixes the blueprint's
  range with every hand the board allows (`X` = 1 is "any two").
- **The objective.** Vector CFR+ with linear averaging in C++ (`native/src/river.hpp`): an equilibrium of the river
  subgame. At 2,000 iterations (the native default) about 1.4 s; 65 of 1,081 hands were still more than 0.1 off a
  6,000-iteration solve (22 Sept).
- **The budget.** 8 s by default (`--river-budget`), and the blueprint's answer stands if a solve fails or overruns.
  The slowest decisions measured were 4.7 s (24 Sept mirror) and 7.0 s (oracle). That matters, because **41 of our
  576 logged matches ran on a 5-second clock**, the fixtures, against 30 s in bursts. A river solve must not play a
  fixture with a budget above about 3 s.
- **The guard bug** the 5 Oct review found, the price guard calling over a river-solve fold because the answered
  history ended in a pseudo all-in, is fixed in main since the 6 Oct merge (`and not river_solved` in the guard,
  pinned by `test_a_river_solve_fold_is_not_second_guessed`). Rules that run after the solve can still change its
  answer, for example `never_bluffs` turning a call into a fold, and that is by design.
- **Why it is off in production.** It has never been shown to help a set we play against the field, and on v5x it
  hurt (below).

## 2. What has been measured

| when | test | result | matches |
|---|---|---|---|
| 19 Sept | v5d + river against v5d | 52.0 ± 5.0 | 100 |
| 22 Sept | v5f + river against the calibrated station / maniac | 59.0 against 56.3 / 60.7 against 62.7 | 300 an arm |
| 24 Sept | **v5i + river against v5i (the mirror)** | **55.4 ± 1.1** | 2,000 |
| 24 Sept | same, against the station / hoops shapes | +1.0 ± 3.5 / +0.7 ± 3.5 | 400 an arm |
| 24 Sept | oracle, v5i against the bully: off / blueprint range / true range | 55.3 / 53.3 / 58.9, ± 1.6 | 1,000 an arm |
| 24 Sept | oracle, v5i against meek: same three | 58.4 / 58.7 / 58.9, ± 1.6 | 1,000 an arm |
| 30 Sept | **v5x** on the RiverReasonBot copy: off / blueprint / blend 0.3 / any two | **66.8** / 55.8 / 59.8 / 57.2 | 1,000 an arm |
| 30 Sept | **v5x** on the wsp copy: same four | **65.5** / 48.3 / 55.6 / 61.4 | 1,000 an arm |
| 30 Sept to 1 Oct | v5iT2 on the RiverReasonBot copy: off / blueprint / blend 0.3 / any two | 56.6 / 58.2 / 56.1 / 54.8, ± 1.6 | 1,000 an arm |
| 30 Sept to 1 Oct | v5iT2 on the wsp copy: off / blueprint / any two | 59.1 / 59.7 / 60.7, ± 1.6 | 1,000 an arm |

What each can and cannot show:

- **The mirror (55.4)** is the published result reproduced: against an opponent that really does play our
  blueprint, exact-hand solving helps. It is also the most favourable test there is, because the solver's model of
  the opponent is exactly right. It says nothing about the field.
- **The oracle** splits range from objective: knowing the bully's true range turned −2.0 into +3.6 ± 2.2 against
  solving off, but against meek even the true range gained nothing. So the range is worth something and the
  equilibrium objective caps the rest. The arms are unpaired, so +3.6 is under two errors.
- **v5x lost 5 to 17 points in every solver arm.** v5x is a restricted best response to a station and a
  re-raiser, and an equilibrium solve with an exploiter's own range throws both away: it bluffs at the rate that
  makes an optimal caller indifferent, against bots that call, and it assumes the opponent holds an exploiter's
  tight range. This is the finding that closed river solving on 1 Oct.
- **v5iT2 moved nothing outside ± 1.6.** A balanced set has no exploit to lose, and an equilibrium solve adds none.
- **The copy duels** are trustworthy for the response to a bet (5 Oct copy validation), which is exactly what a
  river bet tests, so these are better evidence here than copy duels usually are.
- **No real match has played with the solver.** The one fixture it was armed for, pkr-sota on 24 Sept, was a
  walkover; there are 0 river solves in the logs.

Earlier river work: branch `river-blend` (the `--river-blend` and `--river-iterations` flags) and `river-oracle`
are merged; no `archive/*` tag holds river work.

## 3. What the logs say about the river

Every logged match, every version since September, 576 files. The arena shows the winner's cards when a hand ends
in a fold, so for all 989 of our river folds the opponent's hand is known, and our calls go to showdown. On the
river the result of calling is then exact for that deal. One spot is hindsight; a bucket's sum is an estimate of
what calling everything in it is worth against the field's real ranges.

**Who decides the river.** 5,949 river decisions: the tree 5,536, rules 185, companions 126, misses and fallback
102. Facing a bet, 2,000: the tree 1,811, companions 80, misses 66, rules 43 (river bet believed 20, shove call
declined 15, bluff withheld 6, small bet called 2).

**Facing a river bet.**

| bet into the pot | spots | folded | called | raised | the calls returned | the folds, had we called | a call needs | won when called |
|---|---|---|---|---|---|---|---|---|
| under 0.4 pot | 211 | 70 | 108 | 33 | +1,229 bb | +111 bb | 17% | 44% |
| 0.4 to 0.8 | 1,398 | 660 | 577 | 161 | +3,832 | −1,764 | 27% | 46% |
| 0.8 to 1.25 | 203 | 115 | 77 | 11 | +1,455 | −1,200 | 33% | 44% |
| 1.25 to 2.5 | 117 | 88 | 25 | 4 | +95 | −1,157 | 37% | 34% |
| over 2.5 | 71 | 56 | 15 | 0 | +119 | −1,579 | 45% | 43% |

So our calls were profitable at every size and our folds were right at every size but the smallest, where calling
the 70 folds would have won 111 bb, about 1.6 bb a fold. By who decided, the tree's 884 folds would have lost
4,413 bb as calls and its 728 calls won 5,109; the misses' 41 calls won 1,119; the companions' 47 folds would have
lost 700. Every decider defends the river correctly in aggregate.

**Our own river bets, unbet to us (1,549).** Strength is our hand's share of the hands the board allows that we
beat.

| our strength | bets | they folded | called | raised | fold rate | a bluff needs | won when called |
|---|---|---|---|---|---|---|---|
| under 0.30 | 234 | 125 | 77 | 32 | 53% | 47% | 5% |
| 0.30 to 0.60 | 256 | 112 | 121 | 23 | 44% | 38% | 52% |
| 0.60 to 0.85 | 565 | 245 | 265 | 55 | 43% | 44% | 86% |
| 0.85 and up | 494 | 245 | 206 | 43 | 50% | 61% | 92% |

In aggregate the bluffs about break even, but by opponent they do not:

| opponent | bluffs | folded | needed | the bluffs returned | value bets | called | won when called |
|---|---|---|---|---|---|---|---|
| Blueprint | 139 | 53% | 45% | −35 bb | 205 | 25% | 75% |
| r0ckGarden | 41 | 54% | 49% | +36 | 73 | 55% | 100% |
| hoops | 21 | 67% | 47% | +38 | 80 | 41% | 95% |
| wsp | 14 | 79% | 50% | +51 | 14 | 0% | |
| mr_hide | 13 | 15% | 49% | −152 | 107 | 69% | 97% |

The pattern is the textbook one. Against a station (mr_hide) the bluffs lose and the value bets are paid; against
a folder (wsp, hoops) the value bets are not paid and the bluffs work. The blueprint bluffs and value-bets at the
same rate against both. Counts per opponent are small (13 to 205), and these are hindsight per bet, so they show
size and direction, not a fitted value.

## 4. Designs, ranked by expected gain per day

### 1. Recommended: a river solve against the opponent's measured response, kept inside the subgame

This is option 1 of the 5 Oct note, the restricted Nash response at subgame scale, now with the data it needs and a
clearer target. The logs say the value is in **our** bets: how often to bluff and how thin to value-bet, against
this opponent. So the opponent side of the solve should play, with weight p, the response the profile measured
(fold, call or raise to our bet, by bet size), and freely with weight 1 − p, with p following the observation
count (data-biased response, Johanson and Bowling 2009) so a thin profile falls back to the equilibrium. The
inputs now exist: fold counts by our bet size (`by_size`, merged 6 Oct) and posterior reads with a population
prior (`--posterior-reads`, merged 5 Oct). The opponent's arriving range should come from the same model
(`cfr/river_oracle.py` already replays a policy over the public history), not from our own strategy table.

- **Gain.** Bounded by the table above: against mr_hide alone the bluffs cost 152 bb over 13 tries, and wsp's 14
  value bets were never called. Most of the gain is on the exploiters, which is where the equilibrium solve lost.
- **Cost.** 1.5 to 2.5 days. The fixed copy of the opponent needs no regret updates, so a solve should cost 1.3 to 2
  times today's 1.4 s [inference; time it].
- **Risk.** Model error, which SES measured as the failure mode of fixing the opponent's subgame strategy: keep p
  moderate and by count. Latency against the 5-second fixture clock: cap the budget at about 2.5 s with the
  blueprint as the fallback, and log every overrun.
- **Measurement before it plays.** Copy duels are trustworthy for the response to a bet, which is what this changes,
  so they are the right first instrument here: 10,000 matches on the refitted mr_hide, wsp, hoops and Blueprint
  copies, off against p = 0.25 and 0.5. Because the copy is the model, add a mismatch arm, solving with a profile
  fitted before a cut-off date. It must gain against the callers and the folders and lose under 1 point against
  v5iT2 head to head. Then the replay on the logged rivers (how many bets change), and two bursts read through
  `chipzen_decompose.py` with a row for the river-solve hands.

### 2. A first, cheaper step: price the per-opponent river frequencies offline (half a day)

Before building the solve, take each opponent's measured fold rate by our bet size and price, on the logged rivers
in section 3, what a simple best response would have changed: bluff only where the lower bound of the fold rate
clears what the bluff needs, value-bet thinner where the call rate is high. If that offline number is small, the
solve in option 1 is not worth two days. This is measurement, not a rule that plays.

### 3. Turn on the existing equilibrium solve with the bug fixed: not recommended

It is measured: 5 to 17 points lost on v5x, nothing on v5iT2, and the logs now say why there is little to gain
anyway, since our river defence is already right and the solve would move our bets toward balance against a field
that is not balanced. The case for it is a balanced set against a strong, near-equilibrium opponent (the mirror's
+5.4), which is not the field.

### 4. Solve only when facing a large bet: not recommended

The logs answer it directly: facing bets over 1.25 pot, calling our 144 folds would have lost 2,736 bb, and the
calls we made were profitable. There is nothing there for a solve to recover. The only bucket where our folds were
wrong is under 0.4 pot, worth 111 bb over 70 spots.

### 5. Solve off-tree rivers only: low

River misses are 102 of 5,949 decisions and companions 126, and both defended profitably (misses' calls +1,119 bb,
companions' folds right by 700). The 5 Oct note expected translation error here; on the river the logs do not show
it costing.

### 6. Turn solving: defer

3 to 5 days plus native work to fit 44 rivers inside a 5-second clock, and as an equilibrium solve it would repeat
the river's loss on the exploiters over more of the pot. It is the second step after option 1 shows the
model-based objective works, with leaf values that know the opponent's river tendencies.

## Recommendation

Option 2 first, because it is cheap and decides whether option 1 is worth its two days: the per-opponent river
frequencies priced offline on the hands we already have. If it shows real money, build option 1, measured on the
copies (which are trustworthy for exactly this) with a mismatch arm, then the replay and two bursts. Leave the
equilibrium solve off. On ordering: the river defence is a base-solver result and it is sound; the value left on the
river is per-opponent by nature, so in the base-first order this comes after the short-stack rungs' burst and
whatever the histogram stopping bar asks for.

## Limits of the evidence

- The logs pool every set and version since September, so they describe our river play in general, not one set.
- A bucket's "had we called" sum is the value of calling every fold in it, not of a selective change.
- When they fold to our bet their cards are not shown, so bluffs are priced as winning the pot on a fold and
  losing the bet otherwise (bluffs under 0.30 won 5 percent when called, so that is close).
- Per-opponent counts are small (13 to 205 bets), and Blueprint was rewritten on 29 Sept, so its rows mix two bots.
