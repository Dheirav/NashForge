# NashForge, Chipzen season 8: champions

Season 8 ran from 29 September to 5 October 2026. NashForge finished the round robin 7 and 1, joint top with
Blueprint, then won all three playoff matches. The final was against Blueprint at 02:30 IST on 5 October, and we
took all 20,000 chips in 51 hands.

## The record

| Round | Opponent | Result | Hands | Set played |
|---|---|---|---|---|
| Round robin | fermat1 | lost by walkover (not connected) | 0 | none |
| Round robin | lil-bot-v2 | won | 8 | v5x |
| Round robin | RiverReasonBot | won | 31 | v5x |
| Round robin | HRT | won | 42 | v5x |
| Round robin | wsp | won | 63 | v5x |
| Round robin | Sleight-of-Hand_v3 | won | 16 | v5x |
| Round robin | Shadow | won | 2 | v5xRR3 |
| Round robin | PoetAndCoder | won | 46 | v5x |
| Quarter-final | melly | won | 50 | v5xRR3 purified |
| Semi-final | PoetAndCoder | won | 6 | v5xRR3 purified |
| Final | Blueprint | won | 51 | v5xRR3 purified |

Every match we actually played, we won. The only loss was a walkover: the bot was not connected for fermat1, and
the strongest opponent we never had to beat was our own operations.

## The sets, and why each one played

The bot plays precomputed CFR strategies, one per stack depth, and picks the nearest depth each hand. The three
sets that played this season come from one family:

- **v5x** is a best response trained partly against a calling station (a 25 percent share), on six card classes. It
  played the first six round-robin fixtures because it beat the balanced sets on copies of the division's bots.
- **v5xRR3** is v5x with its 18, 25 and 35bb strategies retrained against a re-raiser too. It fixed v5x's biggest
  leak, which was folding about 80 percent of its opens to a re-raise. Its first burst won 13 of 20 against the
  rewritten Blueprint.
- **v5xRR3 purified** plays v5xRR3's most likely action everywhere instead of sampling. It was 3.4 points better
  across eight copies and won 14 of 20 against Blueprint in its burst, still +70 ± 41 chips a hand once the luck in
  called all-ins is taken out. It played all three playoff matches.

Each set went live only after a cross-tree gate, a replay on the match record and a burst, and nothing changed on
a match day.

## The final, briefly

We were behind for most of it. A slow bleed at deep stacks and one expensive hand (bet, bet, then a river call with
a pair of nines into pocket tens) took us down to about 22 percent of the chips by hand 36. Hand 37 brought us
back: our K6 offsuit called Blueprint's shove and hit against its A9 suited, from roughly a third of the equity.
After that, steady preflop steals took us to 11,850. In hand 51 our straight check-raised the river all in, and
Blueprint called its last 4,600 with a pair of fives.

So the final was won by one lucky call and one large mistake by the opponent, while our bot made none. All 139 of
its decisions came straight from the strategy tables, with no misses and no fallbacks.

## What the season taught us

**Operations cost more than any opponent.** The fermat1 walkover, two WSL restarts that silently killed armed
timers, and a memory squeeze an hour before the semi-final were all bigger threats than anything at the table. What
worked was dry-running every timer before arming it, keeping a list of intended fixtures that a restart hook
re-arms, and on the last night a poller that armed the final as soon as its slot appeared.

**Most of our tests could not see what we changed.** This is the main finding of the post-season research
(`docs/research/2026-10-05-synthesis.md`):

- Copy duels score an exploiter against scripts like the ones it was trained on. Copy validation then showed that
  the copies we used do not behave like their bots. None gets bet sizes or postflop betting right.
- A 20-match burst is decided by two or three big pots.
- Our LBR could not see the third-raise hole, where any third raise on a street is read as all in.

**Several measurement and read bugs were found and fixed:**

- The burst decomposition had read +100 to +190 chips a hand too high.
- The never-calls read fired on a normal bot. Fixing it was worth about 10 points against Dronev4's copy.
- Opponent profiles were counting our own matches again at every bot start.

**On strength, the levers that worked were specific.** Convergence fixes in the solver, cap-2 trees, 20-class
cards for the balanced sets, a targeted retrain (RR3) and purification all helped. Three things never moved the
number: more card classes, river solving and bigger trees at equal training.

## What comes next

The post-season order, from the research notes:

1. **Better instruments first.** Four are already built on branches, each with passing tests:
   - all-in luck removal for bursts;
   - a stopping rule that stays valid however often it is checked;
   - copy validation;
   - LBR probes for the third-raise hole.
2. **Merge the fixes.** That means the never-calls threshold and the profile counting fix, and replacing the
   inflated profiles with a clean rebuild.
3. **Refit the copies** to the bots' real decisions, then re-run the division duels.
4. **Measure the third-raise hole with LBR** before training a bigger tree to close it.
5. **Strength work.** Exploiters trained with less of their time against scripts, river solving against the
   opponent model rather than the balanced answer, then bigger trees given proportionally more training.
6. **A Slumbot benchmark** on a 200bb strategy built from the current balanced recipe, for the write-up.
