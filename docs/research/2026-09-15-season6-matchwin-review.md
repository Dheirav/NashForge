# Review: match-win play under rising blinds, for season 6

Written 15 September 2026 from a literature search plus a small Monte Carlo of a
10,000-chip match with blinds doubling every 20 hands (per-hand results drawn as
Normal(edge x BB, sd x BB), scratchpad only). Everything marked inference is the reviewer's.

## 1. Chip EV versus match-win probability

Documented: for winner-take-all heads-up, chip EV and prize EV coincide, but only with no
skill edge in the remaining hands. With an edge, win probability as a function of stack is a
gambler's-ruin curve with drift: concave for the stronger player, convex for the weaker one,
so the stronger side should decline zero-EV gambles for a large share of the stack and the
weaker side should seek them. Hyper-turbo practice says the same: short stacks cap the good
player's edge (https://upswingpoker.com/heads-up-hyper-turbo-sit-gos-strategy-hu-sng/).

Inference with numbers. Our +71 chips/hand is measured over matches whose average big blind is
roughly 200 to 400, so the per-hand edge is about 0.2 to 0.35 bb. Simulation (sd 8 to 12
bb/hand): base match-win probability 0.56 at 0.3 bb/hand, 0.65 to 0.74 at 0.71. A full-stack
coin flip on hand 1 costs 6 points at the small edge and 15 to 24 at the large one; a half-stack
flip 1.5 to 5; a fifth-of-stack flip under 1. A full-stack call at 55 percent equity still costs
1 to 10 points; at 60 percent it gains 4 at the small edge and loses 5 at the large one. A leak
of 0.2 bb/hand costs about 4 points over a match; 0.5 bb/hand costs 11. Median match length
30 to 43 hands. So the effect is real but concentrated in one situation, an all-in for most of
the stack during the first two levels at near-50 percent equity, and worth perhaps 1 to 3
points across a season. Against an opponent rated above us the sign flips.

The more important consequence of the schedule: even stacks pass through 100, 50, 25, 12.5
and 6 bb, and half the matches end during the 50 and 25 bb levels. The deep rungs get at most
20 hands; the match is decided where the known leaks were.

## 2. Push/fold and the ladder

Documented: Miltersen and Sørensen computed the exact jam/fold equilibrium at about 6.7 bb
with a rigorous win-probability guarantee (https://dl.acm.org/doi/10.1145/1329125.1329357).
Practitioner consensus: push/fold up to about 10 bb, sometimes 12 to 15 for the small blind,
and a bad idea above 20 (https://www.holdemresources.net/hune). Min-raise strategies dominate
at 15 to 25 bb because they keep raise/fold as an option. No bb/100 figure for raise/fold
versus push/fold exists in the literature.

Inference: a solver with all-in in its action set finds push/fold on its own at 5 and 8 bb, so
those rungs are fine. The costly gap is the one-raise tree between 12 and 25 bb, which cannot
re-jam over a raise or call a shove after opening, exactly the 15 to 25 bb game. Rung by
effective stack at the current level is right; two refinements: round down between rungs at
25 bb and below, and weight training toward the 50, 25, 12 and 8 rungs, which even stacks
pass through.

## 3. One adjustment per opponent (magnitudes are the reviewer's arithmetic)

- runner1 (never raises, calls 89 percent): never bluff, size up with value. A bluff against an
  inelastic 89 percent caller loses 0.89 of the bet; a pot-sized value bet good 65 percent of
  the time earns +0.27 pot. Open every hand from the small blind.
- mellyy (folds 76 percent to bets, 86 to three-bets): three-bet every hand small and fold to
  four-bets; breakeven fold rate for a three-bet to 8bb over a 2.5bb open is about 67 percent,
  so at 86 the three-bet earns about +1 bb per hand. Then bet 25 to 33 percent pot at 100
  percent and fold to raises (https://blog.gtowizard.com/exploiting-profiles-episode-ii-the-nit/).
- v003 (unknown): equilibrium. Implicit modelling needed 3,000-hand matches to pay off; 40
  hands identify nothing.
- Shadow (raises 41 percent at 1 to 2x pot, folds to half of bets): tighten before he acts,
  call down and raise wider after; against a pot bet from a 41 percent range any pair calls; at
  25 bb and below re-jam over his raises with the top 20 to 25 percent
  (https://blog.gtowizard.com/exploiting-profiles-episode-iii-the-maniac/).
- PoetAndCoder (78 percent VPIP, folds 24 percent to bets): cut bluffs, a pot-sized bluff
  needs 50 percent folds and gets 24, losing about 0.26 pot each; its win rate almost certainly
  comes from weak bots bluffing into it. Value-bet top pair and better at full size.

## 4. The spare seconds

Documented: river re-solving was Claudico's strongest component; depth-limited re-solving
took Modicum from −57 to +6 against Baby Tartanian8 and −11 to +11 against Slumbot at 20 s
per hand on four cores; unsafe re-solving from blueprint ranges can blow up (397 versus 30
mbb/h in the large test, https://ar5iv.labs.arxiv.org/html/1705.02955). In-match opponent
refits have no short-horizon track record. Inference: spend the time on river and later turn
re-solving, and commit the opponent profile before the match.

## 5. Bot arenas

Documented: ACPC total bankroll rewards exploitation; instant run-off rewards
equilibrium-based agents; the formats pick different winners (Baby Tartanian8 first in one,
third in the other). Even ACPC winners were exploitable by 400 to 1,000 mbb/h to a local best
response, so an unknown bot may be far from equilibrium and still win. Inference: a round
robin scored by wins is closer to run-off. At 0.76 per match P(4 or better of 5) is 0.65 and
three playoff wins 0.44; at 0.85 those become 0.84 and 0.61.

## Ranked recommendations (gain per engineering day)

1. Re-raise support below 35 bb (all-in as the second raise at the 12, 18, 25 rungs). Largest
   gain; it is where matches end. Needs the preflight and a 40,000-hand gate: it changes the tree.
2. Pre-match static profiles for the four scouted bots, as action filters on the solver's mixed
   strategy: no bluffs and large value sizes for runner1 and PoetAndCoder; any-two small
   three-bet and 100 percent small continuation bet for mellyy; wider call-down and re-jam for
   Shadow. Safe without a gate for runner1 and mellyy, whose stats are extreme on many hands;
   gate Shadow and PoetAndCoder.
3. River re-solving stays on with the blueprint fallback; a max-margin safety later.
4. No win-probability utility wrapper during the season: worth 1 to 3 points and easy to get
   wrong. The one safe rule: no zero-EV full-stack call in levels 1 and 2 when the solver's EV
   is within about 2 bb of folding.
5. No in-match adaptation: nothing in the literature works in 40 hands.
