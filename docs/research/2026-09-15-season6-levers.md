# Season 6: what moves our chances, from three reviews and an audit

Written 15 September 2026, 13:05 IST, the afternoon before the first fixture. The three
reports and the audit sit beside this file: `2026-09-15-season6-matchwin-review.md` (the
format), `2026-09-15-scouted-opponents-analysis.md` (the five opponents, decision by decision
with their cards), and the arena-path audit, whose findings are recorded here because they
were acted on the same hour. Chances before this work: about two wins of five and one in ten
for the title; the reasoning is in NEXT.md.

## The format decides where the match is played

Blinds rise every twenty hands from 100bb, so even stacks pass through 100, 50, 25, 12 and 6
big blinds, half of all matches end during the 50 and 25bb levels, and the median match is 30
to 43 hands. The deep rungs get twenty hands at most. That puts the whole weight on the short
rungs, which is exactly where v4 leaked: the hand rule that folded good hands to shoves
(fixed this morning, 20bb floor), and the one-raise tree between 12 and 35bb that cannot
re-jam over a raise or call a shove after opening. The match-win review ranks re-raise
support on the short rungs as the largest gain available; it is the first job after the swap.

Match-win is not chip-EV once there is a skill edge: the stronger side should decline a
near-even flip for most of the stack in the first two levels, worth 6 to 24 points of
match-win probability in the simulation, and the weaker side should seek one. Over a season
that is worth a point or three, and it flips sign against a stronger bot, so no utility
wrapper goes in this week; the one safe rule is no zero-EV full-stack call in levels one and
two when the solver is indifferent.

## The audit: the bot was asking the solver about lines it never took

The bridge read a call's amount as a total bet level. The arena sends calls as increments,
in 3,128 of 3,128 logged calls. So the pot was undercounted in 60 percent of decisions, the
history key was wrong in 23 percent (a pot-sized bet keyed as two times pot, and so on), the
effective stack shrank inside a hand and dropped the ladder a rung in 97 hands, and the
inflated bet fractions drove most of the 693 misses and 145 fallbacks in the logs. Fixed and
tested, with a real hand pinned. Every result before v5 was measured with this in place,
which means v5 is the first version whose solver sees the hand it is in.

Seven smaller technicalities from the same audit, all fixed with tests: a raise clamp that
could send more chips than we had when the minimum raise exceeded the maximum; a rejection
fallback that turned a rejected raise into a call of the whole bet, and could loop; a
mid-match clean close that abandoned the match instead of re-dialling inside the platform's
grace window; a short blind post that read as a 1bb stack; an all-in for a fraction of a blind
folded at 33 to 1; the last-resort legality guard folding instead of checking; and the bluff
rule turning a bluff into a call when facing a bet.

## The five opponents, and what fires against them

The scouted hand histories carry both players' cards, so each bot's play could be read
decision by decision (4,853 / 2,883 / 1,992 / 1,785 decisions). What the profiles say and
what the bot now does, with the reads seeded from the scout and kept through restarts:

| opponent | what the data says | fires from hand one |
|---|---|---|
| runner1, Wed 00:10 | a threshold bot: raises 2 percent, never bluffs (0 of 76 river bets under half equity), calls flop and turn bets with median equity 0.48 | station (sequential trigger): bluffs withheld; never-bluffs: its river bets are paid off only by the top two classes, 20bb and deeper |
| mellyy, Wed 01:50 | folds the big blind to 79 percent of opens regardless of size or depth, folds to 86 percent of three-bets, calls the river only with the nuts | folds-blind: every button is opened for the minimum instead of folded |
| v003, Thu 00:00 | no hand on record | nothing: equilibrium |
| Shadow, Thu 23:50 | close to hand-independent: raises flop bets with mean equity 0.50, folds to a shove 20 of 20 under 15bb, folds to 62 percent of three-bets | fold-or-raise: the shove rule from 20bb |
| PoetAndCoder, Fri 23:40 | a sizing tell on 1,509 bets: three-quarter-pot bets are never air (0 percent no pair, mean equity 0.84) and half-pot bets are 39 percent under 0.40 equity; never folds to a three-bet; calls shoves short with any two | station: bluffs withheld |

Not done, and why: a response to PoetAndCoder's sizing tell (fold below two pair to the big
size, raise the small size) is the largest single read in the data and is worth tens of
bb/100, but it is a new mechanism, so it gets built on Wednesday and gated on the replay for
Friday. Three-betting Shadow wide rests on n = 60 and it calls 35 percent with good hands.
Nothing adapts in-match: nothing in the literature works in forty hands.

## What this week can still add, in order

1. Cap-2 trees on the 12, 18, 25 and 35bb rungs (the largest gain named by the review; needs
   its own 40,000-hand gate).
2. The PoetAndCoder sizing response, gated on the replay, for Friday.
3. Three-bet pressure on Shadow at 25bb and below, if a gate can be found.
4. The 20-bucket postflop rung, already queued.

## The chances, restated

With v5, the bridge fix, the short-stack rule fix and the four reads: runner1 about 60
percent, mellyy about 35, v003 50, Shadow about 60, PoetAndCoder about 40. Roughly two and a
half wins expected, playoffs better than even, the title about one in six. The bridge fix is
the part of that I trust least to quantify and most to matter: a solver that finally sees the
right pot and the right line plays every street differently, and only the ledger will say by
how much.
