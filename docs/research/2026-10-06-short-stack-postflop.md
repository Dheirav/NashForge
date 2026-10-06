# Short-stack postflop play: what decides it, what it costs, and what to build

6 October 2026, branch `shortstack-design`. Design only: nothing in the bot changes until a design is approved.
Measured on all 576 logged matches in `results/chipzen/matches` with `~/pokerbot-scratch/shortstack/measure.py`
(read-only, 2 seconds). It builds on the shelved attempt at this problem, `archive/shortstack-postflop`
(5 October), which section 4 summarises, so this does not repeat it.

## 1. What decides a decision below 15bb

The player picks the rung nearest in ratio to the effective stack (`ArenaPlayer.solver_for`). On the live set
(v5xRR3 under `--deep-primary`) the rungs at the bottom are:

| effective stack | rung | tree | training |
|---|---|---|---|
| up to 6.3bb | `nolimit_5bb` | one raise per street (`raise_cap 1`), six classes | 3M iterations, from September's base ladder |
| 6.3 to 9.8bb | `nolimit_8bb` | one raise per street, six classes | 3M iterations, same |
| 9.8 to 14.7bb | `cap2_12bb` | (4,2,1), six classes, station share 0.25 | 20M |
| above 14.7bb | `cap2_18bb` | (4,2,1) | 20M |

Under `--deep-primary` the cap2 rungs are primaries and are dropped from the companions, so v5xRR3 has **no
companion at all** at these depths. When the primary misses, the order is: a collapsed re-read of the same tree,
then for a preflop all-in only the exact push/fold solution (`_short_stack_answer`, up to 14bb, and only on a
miss), then `fallback_choice`. The reads that change a choice at depth are mostly off below 20bb
(`SHOVE_RULE_MIN_BB`); what still fires short is "bluff withheld", "shove call declined", "opened into a folding
blind" and "called for pot odds".

The structural point is the one-raise tree. With one raise per street, once anyone bets, nobody can raise. So:

- **Preflop, the big blind can never shove over an open**, the most important play at 5 to 8bb. A re-raise from
  the opponent is off the tree, and only then does the push/fold table answer (44 times in the logs).
- **Postflop, a bet cannot be raised.** We cannot check-raise all in, and the tree never models the opponent
  raising our bet, so it bets thin hands as if a bet were safe. In the logs the tree faced a bet with chips
  behind and no raise in its tree 58 times at the 5 and 8bb rungs (and 52 at 12bb, where the (4,2,1) schedule
  runs out).

## 2. The 4 October hand, traced

Match 263639e0, hand 88, r0ckGarden, 7.9bb effective, so the `nolimit_8bb` rung. We held 3♣J♦ in the big blind.

| street | history | what happened | decided by |
|---|---|---|---|
| preflop | `1` | they limped, we checked | tree |
| flop A♦5♠3♥ | `11/13` | we checked, they bet 624 into 800, we called | tree (legal: fold or call only) |
| turn 6♣ | `11/121/` | **we bet 1,024 into 2,048** | tree |
| turn | `11/121/25` | they raised all in to 2,146; a miss, no companion, no re-read | `fallback_choice`: fold |

The rule folded because a weak class folds to anything over 15 percent of the pot, and 1,122 into 5,218 is 21.5
percent of the pot (17.7 percent of the final pot, the "18 percent" quoted before). The pair plus "straight draw"
is a pair of threes with no real draw: no single turn card makes a straight with J3 on A536. They held A♥8♥, and
our equity was 11 percent, so the fold saved 402 chips. **The fold was right. The mistake, if any, was the bet
before it:** the one-raise tree bet a pair of threes for half the pot into an opponent with 2,146 behind,
because in its tree that bet could not be raised. That is the structural defect above, showing up as a hand.

## 3. How much play is there, and who decides it

Of 27,683 postflop decisions in all the logs, **1,616 (5.8 percent) were at 15bb or less.** By hands, the 5 and
8bb rungs played 1,056 and the 12bb rung 1,096, against 20,744 deeper, so about one hand in ten. These are the
hands that end matches, so they matter more than their share.

| band | postflop decisions | tree | companion | collapsed | rule | facing a bet with no raise in the tree |
|---|---|---|---|---|---|---|
| 5bb rung | 163 | 149 | 0 | 0 | 14 | 10 |
| 8bb rung | 302 | 274 | 9 | 4 | 15 | 48 |
| 12bb rung | 1,048 | 1,008 | 19 | 0 | 21 | 52 |
| 18bb rung | 103 | 99 | 1 | 0 | 3 | 5 |

The companion rows come from sets other than v5xRR3 (balanced-next played v5iT2p60m, which keeps them).

Off-tree postflop spots (companion, re-read or rule) are 9.0 percent of postflop decisions at the 5 and 8bb rungs
(42 of 465) against 3.8 percent at 12bb (40 of 1,048), because the one-raise tree runs out at the first raise.

**What the price decisions were worth against the hand the arena showed.** Facing a bet, a fold is "priced in"
when calling (capped at our stack, last chip in) would have won against their actual hand. A call is "priced
out" when it lost.

| band | decided by | shown folds | priced-in folds | chips given up | shown calls | priced-out calls | chips lost |
|---|---|---|---|---|---|---|---|
| 5bb | tree | 14 | 5 | +4,472 | 12 | 7 | -3,459 |
| 5bb | rule | 2 | 2 | +2,824 | 3 | 0 | 0 |
| 8bb | tree | 32 | 6 | +3,304 | 32 | 13 | -5,078 |
| 8bb | rule | 7 | 2 | +625 | 6 | 3 | -3,232 |
| 12bb | tree | 132 | 21 | +12,936 | 109 | 58 | -30,145 |
| 12bb | rule | 6 | 1 | +99 | 6 | 4 | -1,929 |

This is hindsight against one hand per spot, so it is not the value of the decision against a range, and calls
that went to showdown are a biased sample. Read it for size, not sign. What it shows:

- **The rule is a small part of this.** Its priced-in folds at the 5 and 8bb rungs come to 3,449 chips over 4
  spots in 576 matches, and the two largest (0ac9fbe8: 700 left facing 16,900; 596b4a9d: 1,050 left facing 15,550)
  are the nominal-bet bug that `--capped-price` now fixes. The shelved branch's audit found the same: +3,413 of its
  +635 came from three such spots, and its range pricing itself lost 2,778.
- **The trees decide almost everything.** At the 5 and 8bb rungs they gave up 7,776 chips over 11 priced-in folds
  and lost 8,537 over 20 priced-out calls. Two of the largest priced-in folds are the 5bb tree folding a pair to a
  flop shove after we checked (`21/15`: 77 on 4♠4♦8♣ against A♦T♥ at 76 percent, and 58 on 6♠8♣2♦ against K♦9♥
  at 76 percent), which is the quality of a 3M one-raise solve rather than anything the rule did.

## 4. What was tried before, and why it was not taken

- **`archive/shortstack-postflop` (5 October), `--shortstack-postflop`.** On a fallback after the flop at 10bb or
  less, it priced the spot against a modelled betting range (top half three to one over the bottom half, a quarter
  bluffs) with exact equities, and shoved, called or folded on that price. 12 tests, a log audit and a 10,000-match
  self-duel. The duel tied (49.6 ± 0.5), because the mirror opponent never makes the off-tree bets that trigger it
  (192 firings in 1.26M decisions). The audit's +635 over 11 changes split into +3,413 from three spots where the
  rule priced a bet far larger than our stack, and -2,778 from the range pricing, which called honest bettors'
  value hands (the 4 October hand among them). **Shelved, and the pricing bug was fixed instead, behind
  `--capped-price` (branch stack-cap, now merged, armed for the 7 October flags-on burst).**
- **`archive/pushfold-primary`, `--pushfold-primary`.** At 8bb and shorter the exact push/fold solution answered
  first. It changed 0.3 to 0.4 percent of decisions, the 12 copies averaged zero, and head to head it was 51.0.
  Neutral, not merged.

So both "a better rule for the rule's spots" and "the push/fold table first" have been measured, and neither
moved anything. What has not been tried is fixing the trees that decide 95 percent of these spots.

## 5. Designs, ranked by gain per day of work

**1. Retrain the 5 and 8bb rungs on the (4,2,1) tree (recommended).** The same six-class (4,2,1) tree the 12bb
rung uses, self-play, at 10M iterations. It gives the big blind a shove over an open, lets both sides raise a
postflop bet, and models the raise behind our own bets, which is what the 4 October bet ignored. It also brings
the two oldest rungs in the ladder (3M iterations, September's base recipe) up to the current recipe.

- Cost: two runs. The 12bb (4,2,1) rung took 2,553 s for 20M on 2 threads; the 8 and 5bb trees are smaller, so
  10M is about 15 to 20 minutes each. Tonight's rule is that 10M is enough on six-class (4,2,1) self-play
  rungs (measured at 70bb, where the tree is far larger); the visit counter (`--count-visits`) confirms it per
  rung at no cost.
- Risk: preflop at 5 to 8bb is close to a solved push/fold game, and a sampled tree can be further from it than
  the one-raise tree that already shoves in the small blind. Measure that directly (below). Whether the rung
  should be self-play or a station exploiter like the 12bb rung is a second question, for after the self-play
  version is shown not to lose.
- Measured, before it plays: (a) preflop against exact play, the chips each version gives up to the exact
  push/fold solution (`scripts/push_fold.py --measure`, the instrument behind the 23 September table);
  (b) an arena head to head with only the 5 and 8bb rungs swapped, purified, 5,000 matches on two seeds, since
  every arena match ends at short stacks; (c) the replay on the match record (`scripts/chipzen_replay.py`), counting
  how many of the 42 off-tree spots become on-tree; (d) the cross-tree gate at 5 and 8bb only as a sanity check,
  because check/call on a miss favours whichever tree misses less. Then the usual gate, replay and burst.

**2. Keep `cap2_12bb` as a companion for the 5 and 8bb rungs.** Under `--deep-primary` the cap2 rungs leave the
companion list, so an 8bb miss has nowhere to go. A companion within ratio 2 (`COMPANION_REACH`) would answer the
re-raises the one-raise tree cannot. No training, a few lines in `ladder_paths`. But the 12bb tree plays its own
stack sizes at 8bb, and translating 8bb sizes onto it is crude. Worth having only if design 1 is delayed; once the
5 and 8bb rungs have their own (4,2,1) trees it adds nothing.

**3. A better rule for the rule's spots.** Measured on 5 October and shelved (section 4). The money was the
pricing bug, now fixed behind `--capped-price`; what remains is about 4 spots in 576 matches. Not worth building
again.

**4. The push/fold solution as primary at 8bb and under.** Measured on `archive/pushfold-primary`: neutral. It
also answers preflop only, so it does nothing for postflop. Not recommended.

## 6. Recommendation

Do design 1: retrain the 5 and 8bb rungs on the (4,2,1) six-class tree at 10M, self-play, and measure them
first against the exact push/fold solution and then in an arena head to head with only those two rungs swapped.
It addresses the cause the logs point to (the one-raise tree decides most short-stack spots, and its first raise
ends the tree), it costs under an hour of training, and the two cheaper ideas that went after the symptom have
already been measured and did not move. `--capped-price`, in the 7 October burst, covers the rule's pricing bug on
its own, so the two changes can be read separately.

## Results of design 1 (6 October, 01:11 to 01:37)

The 5bb and 8bb rungs retrained on the six-class (4,2,1) tree, self-play, 10M each, with the 70bb self-play recipe and
only the stack changed (`results/cfr/experiments/selfplay_{5,8}bb_t421_10m`, untracked; 387 s and 616 s). Measured in
`~/pokerbot-scratch/shortrungs/`:

| test | result |
|---|---|
| gate, new against old, 8bb | +6.0 ± 0.5 BB/100 |
| gate, new against old, 5bb | +0.6 ± 0.4 |
| v5xRR3 with both rungs against v5xRR3, purified, arena, two seeds | 49.8 and 49.4, pooled 49.6 ± 0.5 |
| against the station, the maniac, hoops (2,000 matches each) | 73.6 / 73.6, 75.6 / 76.4, 70.0 / 67.3 |
| misses against those three | 155 to 86, 430 to 242, 430 to 352 |
| replay on 53,053 logged decisions | 120 move onto the tree, none off |

The new rungs fix what they were built for: the 8bb rung clearly beats the old one, and the bot leaves its tree far
less often at short stacks. As a whole bot they are level, because short stacks are a small part of a match. Nothing
measured is worse. They are a candidate for their own burst after the flags-on one. An off-tree map of the same
replay (`~/pokerbot-scratch/offtree/map.txt`) shows the 8bb and 5bb preflop re-raise were the two largest off-tree
holes in the live set (70 and 38 misses); with them closed, the 470 left are spread thinly over deep turns and rivers.
