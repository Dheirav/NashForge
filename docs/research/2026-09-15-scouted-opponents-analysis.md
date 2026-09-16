# Analysis: the scouted opponents' hand histories, decision by decision

Written 15 September 2026 from `results/chipzen/scout/hands/*.json`, each bot's own seat,
85 / 29 / 49 / 19 matches (PoetAndCoder / mellyy / Shadow / runner1), 4,853 / 2,883 / 1,992 /
1,785 decisions. Every hand carries both hole cards, so hand-dependence is measured on all
decisions. "Equity" is win probability against a random hand on the street of the decision
(200-sample Monte Carlo, exact on the river). Stacks were reconstructed from 10,000 each; five
matches (65 decisions) drift, so depth splits carry that caveat.

## 1. Determinism by public situation

Key = (street, position, action sequence with raise sizes as pot fractions to 0.25). Among
situations seen at least twice, the share with a single action, and the "concordance": across
pairs in the same situation that took different actions, the share where the more aggressive
action held the higher equity (0.5 = mixing independent of the hand, 1.0 = pure threshold).

| bot | repeated keys | single-action share | with an equity quintile | concordance |
|---|---|---|---|---|
| PoetAndCoder | 254 | 30% | 47% | 0.79 (0.63 on the turn) |
| mellyy | 94 | 41% | 62% | 0.84 (0.97 to 0.99 postflop) |
| Shadow | 100 | 33% | 32% | 0.60 (0.53 with equity) |
| runner1 | 124 | 31% | 77% | 0.99 |

runner1 is a threshold bot: its actions are a function of hand strength and almost nothing
else. mellyy is hand-dependent postflop and near-threshold. PoetAndCoder is hand-dependent but
mixed: same situation, same hand band, still two actions 53 percent of the time. Shadow is
close to hand-independent: its bet-size bands carry equity 0.49 to 0.56 whatever the size, and
it raises flop bets with mean equity 0.50, calls with 0.50, folds with 0.38.

PoetAndCoder does fold to a bet, by equity: river facing a bet, equity under 0.30 folded
30/30, 0.30 to 0.40 folded 19/27, 0.40 and up called or raised 92/92.

## 2. Leaks with counts

**PoetAndCoder.** Fold to continuation bet: flop 38/104, turn 19/50, river 10/24. Check-raise 5
of 172. **The sizing tell:** its postflop first bets are 0.5 to 0.6 pot (n = 1,080, mean equity
0.46, 39 percent under 0.40, 54 percent no pair on the flop) or 0.75 pot (n = 429, mean equity
0.84, 0 percent under 0.40, 0 percent no pair on any street, 84 percent two pair or better on
the river). After a small bet it folds to a raise 18/45; after a big bet 2/45. Preflop it never
folds to a three-bet (0/36: calls 21 with Chen 5.8, four-bets 15 with Chen 7.9), calls opens
from the big blind 211/261 (Chen 3.6), limps 75 percent of buttons. Under 15bb (73 hands) it
limps 45/67 from the small blind and calls a shove 9/11 with any two. Three barrels at showdown
(n = 177): 44 percent one pair or worse, 18 percent under 0.5 equity, wins 67 percent. River bets
35 percent under 0.5 equity (n = 474).

**mellyy.** Folds the button 536/1,022 (52 percent): a walk half the time. Big blind against an
open: folds 497/631 (79 percent), flat with depth (79 at 60bb+, 86 at 30 to 60, 76 to a min-raise,
88 to 2x+), and folded 24 of 126 hands with Chen 7 or more. Facing a three-bet after opening:
folds 25/29 (86 percent). Fold to any bet: flop 86/128, turn 34/53, river 46/64. Check-raise 0 of
84. After it bets and is raised: folds 11/23 on the flop. Its bets are 90 to 100 percent pair or
better; river bets 8 percent under 0.5 equity (n = 63); river calls median equity 0.84 (n = 14),
so it calls only with the nuts. Under 15bb: shoves 22/41 from the small blind (Chen 4.1) and
folds the rest; from the big blind folds 18/32; facing a shove folded 2/2. Three-bets 10 percent
of opens with Chen 10.1.

**Shadow.** Opens 421/714 buttons, shoves preflop at 20bb or less (37 shoves). Fold to a
three-bet after opening 37/60 (62 percent), calls with Chen 7.6. Big blind against an open folds
203/323. Fold to a flop bet 51/162, raises 80/162 (33 of them all-in) with equity 0.50. Re-raised
after raising: fold 11, call 9, raise 18. Check-raises 11/27 on the flop. Fold to a shove at 15bb
or less: 20/20. Three barrels (n = 15): 67 percent one pair or worse, 53 percent under 0.5
equity; river bets 46 percent under 0.5 (n = 41). 220 of its 1,198 hands are at 15bb or less
because it loses.

**runner1.** Raised preflop 3/290 from the small blind (Chen 16.7, aces or kings), 9/109 against
a limp. Calls opens 74/95 (Chen 3.6). **Never bluffs:** minimum equity of any postflop bet 0.58,
95 to 100 percent pair or better, river bets 0/63 under 0.5 equity (28 two pair, 7 straights,
6 flushes, 17 pairs). Check-raise 0/92. Fold to a flop bet 41/138, turn 17/78, river 34/82; river
folds 27/35 when its equity is under 0.35. Calls flop bets with median equity 0.48. Raised after
betting: folds 4/20, holding 0.69 to 0.93 equity. Under 15bb (32 hands): limps 18/22, called
shoves 2/2.

## 3. What the literature says to build

Do not play a raw best response to counts: brittle, and it gives up the equilibrium guarantee.
Restricted Nash / data-biased response (Johanson and Bowling 2009,
https://proceedings.mlr.press/v5/johanson09a.html): pin the opponent to the observed frequency
at each information set with probability p_I rising with the count there, free elsewhere. DBBR
(Ganzfried and Sandholm 2011): start from the equilibrium's action distributions, shift toward
observed frequencies by count, best-respond. Safe exploitation (2015): deviate only up to the
gifts already received. Implicit modelling (Bard et al. 2013): a small portfolio of robust
responses, validated offline. Recommended build: freeze each bot's frequency table by our
information set, re-solve with the opponent pinned at p_I, validate by replaying the scouted
hands against response and equilibrium from our seat, cap the deviation. The simplest version
that captures most of the gain: frequency overrides at the highest-count nodes (preflop open
and defend, fold-to-bet by street, bet-size response), only where n is 30 or more.

## 4. The one adjustment per bot

- **PoetAndCoder: read its 0.75-pot bets as value and its 0.5 to 0.6-pot bets as air.** Fold
  below two pair to the big size (429 bets, 0 percent no pair, folds 2/45 to a raise); raise or
  call down the small size (1,080 bets, 39 percent under 0.40 equity, folds 18/45 to a raise).
  Tens of bb/100. Risk: a sizing change by its author.
- **mellyy: min-raise every button.** It folds the big blind 79 percent regardless of depth or
  size; each fold is +1bb; its continue range is Chen 6.9 to 10.1, so fold to its three-bet
  unless premium. Perhaps +10 to +20 bb/100 over an equilibrium that already opens most buttons.
  Risk nearly none at min-raise size.
- **Shadow: three-bet its opens wide, and shove over them at 15bb or less.** Fold to three-bet
  62 percent (37/60), fold to a shove 20/20 short. About 30 chances per 100 hands at +1.5bb
  each. Risk: n = 60 and it calls 35 percent with good hands.
- **runner1: fold to its bets unless we beat a strong one pair, and value-bet thin.** 0/63
  river bets under 0.5 equity, minimum postflop bet equity 0.58; it calls flop and turn bets
  with median equity 0.48 and the river with 0.43. Risk: if it starts bluffing we would see it
  within ten bets.
