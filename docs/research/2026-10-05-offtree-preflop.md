# The small preflop four-bet, and the companion's history

Written 5 October 2026 on branch `offtree-preflop` (cut from main at fbeff2c). Behind `--offtree-preflop`, off by
default. Tested on `tests/test_offtree_preflop.py` and the four arena test files only; no duel, burst or full suite
was run, and section 5 says why a duel could not measure this.

## 1. The leak

The price-guard audit of this morning (`docs/research/2026-10-05-price-guard.md`) found seven preflop folds of one
shape. The opponent opens, we three-bet, they four-bet small (to 937 over our 500 in f1a0b755 hand 2), and we fold
K♣T♣ at a price of 23 percent. The live ladders' cap-2 rungs run the `(4, 2, 1)` schedule, so the third preflop
raise has all-in and nothing else. `_as_abstract` therefore reads a four-bet of any size as all-in and records it as a
pseudo all-in, and the strategy answers the question "call a 100bb shove with king-ten?", which is a fold. The
question the arena asked was "call 437 into 1,437?", which against almost any range is a call.

The price guard covers some of these, but by a proxy: equity against a *random* hand of at least 0.5. That is the
wrong comparison for a four-bet, because a four-bettor is the opposite of random, and it lets through a hand like
king-jack (61 percent against random, 22 percent against aces to ace-king).

## 2. The choice: answer at the real price against the solution's range

Two designs were on the table.

**Map the raise to the tree size that matches its price.** This does not exist. At the third raise the schedule has
no sized action on any rung, live or old, so there is no node whose price is the real one. The only on-tree re-reads
are the two the bridge already makes: all-in (what goes wrong now), or collapsing the four-bet and our call into a
single call, which `_close_street` does after we have called. Collapsing it *now* would ask the strategy about a
node where we have nothing to decide. A companion with a sized third raise would answer it, but the main set has no
companions (`--deep-primary` drops them where a cap-2 rung exists), and building one is a training run. The clean fix
is still a sized third raise on the preflop schedule, after the season.

**Answer at the real price against a range.** This is what the branch does. The question is which range. A top-x
percent range has a free parameter, and whatever x is picked would be fitted to the seven hands we already know
about. The solution itself has an opinion, though: the rung that answered knows how often every one of the 169
classes takes the bettor's line. `ArenaPlayer.raise_reach` multiplies, for each class, the probability of each action
the bettor took (their open, then their four-bet), straight from the stored strategy, and our equity against that
range comes from the push-fold table's 169 by 169 all-in matrix, with our own cards taken out of the opponent's
combos (`ShortStackRanges.equity_against`). We call when that equity beats the real price by `OFFTREE_MARGIN`, five
points.

Why this range is defensible: it has no parameter, it moves with depth and with the line (an open-pot four-bet and
an open-half one have different ranges), and it errs towards folding. The solution's four-bet range is the range of
a 100bb *shove*, the strongest a four-bettor can have. On the main set's 100bb rung it is 0.7 percent of hands
(queens, ace-king, tens, jacks, a little aces and kings), and the bettors who made these small four-bets showed 33,
55, TT, JJ, A6o and AJs. A rule that calls against the shove range calls only with hands that are fine against
the real one.

The rule fires only where it applies:

- preflop, the strategy folded, there is a bet to call and the arena offers a call;
- no read changed the choice (the same test the price guard uses);
- the history that answered ends in all-in, the bettor still has chips, and calling leaves us chips too
  (`to_call < our stack`). When their raise covers what we have left, the call puts us all in, so the tree's all-in
  is the bet we actually face and the fold priced it correctly. The first version checked only the bettor's chips;
  the review caught it, and adding the check left the audit's 14 firings unchanged;
- that all-in sits at a depth where the answering solver's schedule offers all-in and nothing else
  (`_unnamed_raise`). Where sized raises exist, a pseudo all-in is a raise half again larger than the biggest of
  them, a big bet whose price is close to the shove's anyway. The first version of the rule priced those too, and
  on the i-series replay it called a 44bb open shove at a price of 0.49 against the solution's whole opening range,
  which is the wrong model of a near-all-in open. The restriction removed it.

It records `adjusted = "priced an off-tree raise"`, counts `Stats.offtree_preflop_calls`, and logs the evaluation
(`record["offtree"]`: equity, price, the range's share of hands and the line) whenever the rule priced a spot,
fired or not. With `--price-misread` also on, a spot this rule priced is left to it: the guard's random-hand test is
the cruder of the two, and it would call king-jack where the range says fold.

The margin is there because the call is not all in. About ninety blinds stay behind at 100bb, the flop is played on
the collapsed history, and against a range that is ahead of us we realise less than our equity. The audit's scoring
ignores all of that, which flatters calling, so the sweep in section 3 cannot pick the margin by itself.

Cost: one pass of 169 classes over the bettor's nodes, about a millisecond, memoised per solver and line. The record
gains a few short strings.

## 3. The audit

`scripts/audit_offtree_preflop.py` reads every match file in `~/Code/PokerBot/results/chipzen/matches` (576 files)
and every preflop decision that faced a bet while the bettor kept chips (20,863). It makes two passes.

**As logged.** Across every version that played, the bot folded 17 times to a preflop raise read as all-in with the
bettor holding chips, every one answered by a primary. Of the seven preflop firings in the price-guard audit, the
main set (v5xRR3, deep primary, stack cap, purified) calls three by this rule (b5b90d8e hand 22, f1dd11ec hands 6
and 20), calls three by its own strategy (ba45b472 37, f1a0b755 2, fe2158ec 34), and folds one: cefb7663 hand 57,
A♣3♥ at 0.22 with 24 percent against the range (they had jacks).

**Replayed.** Every one of the 20,863 decisions is put through `ArenaPlayer.decide` on one set with the flag on and
no profiles, so only the strategy and this rule act. A firing is a fold the rule turned into a call, which is the
first divergence in the hand and therefore real. Its value is scored as the price-guard audit scores it: exact
equity against their shown hand, times the pot after the call, less the call. **That treats the call as the last
chip in, which it is not.**

On the main set, `ladder169l_v5xRR3`:

| Margin | Fired | Cards shown | Estimated chips | A firing | Worst |
|---|---|---|---|---|---|
| 0.00 | 25 | 24 | +13,019 | +542 | -194 |
| 0.03 | 18 | 17 | +10,731 | +631 | -141 |
| **0.05** | **14** | **13** | **+7,726** | **+594** | **-141** |
| 0.08 | 6 | 6 | +4,412 | +735 | +198 |
| 0.10 | 4 | 4 | +2,527 | +632 | +430 |

The 14 firings at 0.05, 30 folds priced in all:

| Match | Hand | Opponent | Depth | Line | Ours | Theirs | Pot | Call | Price | Eq. vs range | Eq. vs theirs | Value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01a9fdae | 45 | r0ckGarden | 16bb | 1245 | 5♦T♦ | 9♣9♦ | 3,360 | 1,760 | 0.34 | 0.40 | 0.32 | -141 |
| 051e42cc | 6 | mr_hide | 98bb | 245 | 4♠6♠ | A♦3♦ | 2,000 | 500 | 0.20 | 0.26 | 0.43 | +582 |
| 215cc92d | 5 | Blueprint | 97bb | 345 | J♦T♦ | K♥K♠ | 3,350 | 950 | 0.22 | 0.30 | 0.20 | -77 |
| 5c98a499 | 48 | Blueprint | 46bb | 345 | T♦J♦ | T♣T♥ | 4,350 | 1,350 | 0.24 | 0.29 | 0.39 | +855 |
| 8255fffc | 22 | mr_hide | 60bb | 245 | 5♣6♣ | 8♣A♥ | 1,875 | 375 | 0.17 | 0.28 | 0.41 | +539 |
| 8c7e657b | 6 | mr_hide | 98bb | 245 | 3♥A♥ | 2♥A♦ | 2,000 | 500 | 0.20 | 0.31 | 0.55 | +878 |
| 8c7e657b | 8 | mr_hide | 94bb | 345 | K♦7♦ | not shown | 2,000 | 500 | 0.20 | 0.28 | | |
| 97131196 | 2 | mr_hide | 97bb | 345 | 2♦A♦ | T♠K♥ | 3,500 | 1,000 | 0.22 | 0.31 | 0.60 | +1,687 |
| b5b90d8e | 22 | mr_hide | 61bb | 245 | 8♦A♠ | 3♦3♣ | 1,875 | 375 | 0.17 | 0.28 | 0.47 | +680 |
| bde772c0 | 12 | mr_hide | 88bb | 245 | A♠8♥ | T♦7♦ | 2,000 | 500 | 0.20 | 0.27 | 0.58 | +939 |
| bde772c0 | 18 | mr_hide | 62bb | 245 | 7♦A♣ | A♥J♣ | 2,000 | 500 | 0.20 | 0.29 | 0.28 | +198 |
| f1dd11ec | 6 | mr_hide | 84bb | 345 | Q♣K♦ | T♥T♣ | 1,437 | 437 | 0.23 | 0.30 | 0.44 | +378 |
| f1dd11ec | 20 | mr_hide | 62bb | 245 | K♣7♦ | 6♠A♣ | 3,500 | 1,000 | 0.22 | 0.28 | 0.39 | +777 |
| f1dd11ec | 60 | mr_hide | 32bb | 245 | J♥T♣ | J♦A♥ | 4,000 | 1,000 | 0.20 | 0.41 | 0.29 | +430 |

Eleven of the fourteen are mr_hide, which min-four-bets with hands like 55, A3s and T7s. The two losses are small
(jack-ten into kings, five-ten into nines at 16bb), and the biggest gains are calls against hands the solution's
range does not contain at all (king-ten offsuit, ten-seven suited, ace-deuce offsuit). Over 576 matches the rule fires about once every 40.

The i-series set that played five of the seven guard firings (`ladder169l_v5iT2p60m`) prices 44 folds and fires on
41 at 0.05, an estimated +19,203 (+505 a firing, worst -470), and the margin hardly matters there between 0.03 and
0.08. Its four-bet ranges carry bluffs, so the equities against them run 0.31 to 0.47, where the main set's
station-trained rungs four-bet value only and the equities run 0.26 to 0.31 at 60bb and deeper. The same rule is therefore much more
conservative on the set that plays, and that is the right direction: it is the tighter model.

**The last-chip caveat, checked as far as the logs allow.** The logged bots called a raise of this shape five times
where we later saw the cards. Scored as the last chip in they were worth +7,631; what they actually won from that
decision on was +15,730. Two big pots (kings against eights, ace-queen running down queens) make most of that, and
five hands say nothing in either direction. So the estimate above is an estimate of the call alone, and whether the
flop play on a collapsed history gives some of it back is not measured.

**Choosing the margin.** On the main set every step down the table adds firings, and the score of each added one is
biased up by the same assumption. At 0.08 all six firings gained; at 0.05 there are two small losses and eight more
gains; at 0 the worst is -194 and the gains keep coming. Five points is the middle of the range where nothing large
was lost, and it is a margin for realisation, which the sweep cannot see. These are a few dozen hands across many
versions, so the table says which way the margin leans, not where it should sit.

## 4. The companion's history in the record

Since this branch every decision record carries `answered_history`: the history the strategy that chose was
actually asked about (the primary's, the companion's own translation, the collapsed re-read when that answered, or
null when the rule or the short-stack table answered). When a companion was asked, hit or miss, the record also
carries `companion_history`, its translation of the hand, and when the bridge re-read a street, `alt_history`, the
primary's re-read. All three are additive and always on; the log readers in `scripts/` read records with `.get` or by
named keys, so none of them chokes on new ones. `opponent_brief.py` registers the new `adjusted` value, which its
test requires of every read.

`scripts/audit_price_guard.py` now uses `answered_history` when the record has it, and for older records rebuilds
the companion's translation from the arena's actions on the schedule the `companion` field names
(`answered_history()` there, shared with the new audit). A size between two of the companion's is translated at
random and the live draw is not logged, so a rebuilt history can differ in its middle; whether its last action is a
pseudo all-in is a deterministic test, which is what both audits read. A test checks that the rebuild lands on the
history the live bot asked.

That closes the price-guard audit's open gap. The 453 companion folds facing a bet are now judged: 163 faced a real
all-in (the pot-odds rule's case), 290 faced a bet the companion read as a sized raise, 260 of which the primary had
read as all-in, and **none was a misread**. The guard's audit is unchanged (8 firings, +23,404 chips). The companion
was doing what it is there for.

## 5. Tests

`tests/test_offtree_preflop.py`, 13 tests. No shipped tree has an all-in-only preflop level, so the rule's tests play
a stand-in `(4, 2, 1)` solver whose strategy is a dict holding the bettor's two nodes (an open-pot from every class,
a four-bet from aces, kings, queens and ace-king) and whose own answer is a fold, as the 5 Oct rungs' was. The
record's fields are tested on the shipped solvers.

| Test | State | Expected |
|---|---|---|
| range | the stand-in with ace-king opening half the time and kings never | reach 1, 0.5, 0, 0; a line with no node is None |
| unnamed raise | `345`, `35`, `5` on `(4, 2, 1)`; `35` on one raise | only the first |
| fires | A♥K♦ facing 300, 1,500, 2,600 with 7,400 behind, price 0.21 | call, `priced an off-tree raise`, counter +1 |
| flag off | the same | fold, nothing recorded |
| weak hand | 7♥2♦, 21 percent against the range | fold, the evaluation recorded |
| big four-bet | to 6,000, price 0.375 | fold |
| real all-in | the four-bet is their whole stack | fold, not evaluated |
| postflop | a small third raise on the flop | not evaluated |
| with the guard | K♥J♦: 61 percent against random, 22 against the range | guard alone calls; with both, fold |
| record, primary | a plain flop bet | `answered_history` is `history`, no companion fields |
| record, companion | their min-raise of our flop bet | `companion_history` is the taper's sized read and answered |
| audit rebuild | the same record without the new fields | the rebuild equals the live history |
| record, collapsed | a called preflop third raise, then a flop bet | `alt_history`, the collapsed answer, the taper's translation |

Run on 5 October: `venv/bin/python -m pytest tests/test_offtree_preflop.py tests/test_chipzen_player.py
tests/test_chipzen_bridge.py tests/test_price_guard.py tests/test_opponent_brief.py -q` printed `91 passed in
2.07s`. The first run failed `test_every_read_in_the_player_is_registered` until the read was registered in
`opponent_brief.py`.

**No duel was run, on purpose.** Self-play never makes a small four-bet, which is why the price guard's duel fired 0
times in a million decisions, and the archetype copies shove every third raise (`allin=... or raises >= 2` in
`chipzen/archetypes.py`). A duel would score the flag as exactly neutral and say nothing. A burst cannot measure it
either at one firing in 40 matches.

## 6. Recommendation

Merge behind the flag, off by default, at a margin of 0.05. The design is the narrow one: it changes only folds that
priced a shove the opponent did not make, it prices them against the strategy's own idea of the bettor, and on the
main set that idea is the tightest range a four-bettor can have. On the logs it fires 14 times in 576 matches for an
estimated +7,726 chips, mostly against mr_hide's min-four-bets, with two small losses.

Turn it on together with `--price-misread`. The guard keeps the collapsed postflop cases, which this rule does not
touch, and gives up the preflop four-bets this rule prices better.

Order, as for the guard: the cross-tree gate with the flag on and off (it should read identical, since self-play never
fires it, and a difference would be a bug), a replay on f1dd11ec hand 20 and b5b90d8e hand 22 to see the calls, then a
burst labelled for this one change and read decomposed. The audit, with its last-chip caveat, is a better guide to the
size of this than a burst will be.

Two things this does not fix. The flop after the call is still played on the collapsed history, where the tree's pot
is smaller than the arena's; the guard covers the folds that causes, but nothing covers the bets. And the real fix is
a sized third raise on the preflop schedule, which LBR put at +1.5 BB/100 at 100bb and which is a retraining job.

Files: `chipzen/player.py` (the rule, `raise_reach`, `_unnamed_raise`, `_offtree_price`, the record fields),
`chipzen/pushfold.py` (`combos_left`, `equity_against`), `scripts/chipzen_run.py` (flag and version frame),
`scripts/chipzen_duel.py`, `scripts/audit_price_guard.py` (reads or rebuilds the answered history),
`scripts/audit_offtree_preflop.py` (this audit), `scripts/opponent_brief.py`, `tests/test_offtree_preflop.py`.
