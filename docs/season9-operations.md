# Season 9: how the fixtures run

Chipzen season 9, 16 bots. Round robin Tue 6 Oct 00:00 UTC to Fri 9 Oct 23:59 UTC, playoffs Sat 10 to Sun 11 Oct UTC.
Every fixture falls just after midnight IST, so every night of the week is a match night, and the arena rule "play
the gated set and do not touch it on match day" applies daily.

## Our slots (IST, from `scripts/chipzen_run.py --fixtures`, clock 30 s)

| round | opponent | slot |
|---|---|---|
| 1 | Shadow | Wed 7 Oct 00:20 |
| 2 | PoetAndCoder | Wed 7 Oct 02:40 |
| 3 | fermat53 | Thu 8 Oct 00:40 |
| 4 | RiverReasonBot | Thu 8 Oct 02:50 |
| 5 | riverline_v2 | Fri 9 Oct 00:30 |
| 6 | lil-bot-v4 | Fri 9 Oct 02:30 |
| 7 | Phineas-III | Sat 10 Oct 00:10 |
| 8 | Blueprint | Sat 10 Oct 02:10 |

## Fixtures play a pinned commit

Development continues on main through the week, so the fixture bot does not run from main. It runs from a checkout
pinned at the commit a burst tested: `~/Code/PokerBot-fixture` (detached at b605dd7, the commit of the 6 Oct 07:53
burst). The checkout has its own copy of the native module, so a rebuild on main cannot reach it, and its
`results/chipzen` is a link to main's, so there is one match record and one profile file. A burst that tests a newer
commit runs from its own pinned checkout the same way (`~/Code/PokerBot-burst7oct` at 13b0007 for the 7 Oct flags-on
burst), so a winning set's checkout can become the next fixture pin unchanged.

The scripts (in `~/pokerbot-scratch/chipzen/`) carry the checkout as `ROOT`:

- `fixture2.sh` changes into `$ROOT` (default main) and logs the commit it runs.
- `arm_fixture.sh` passes `ROOT` to the dry run and the timer, and checks the armed timer's environment has it, as it
  already checked the set file. It backgrounds the timer as a simple command, so no subshell is left waiting in the
  session that armed it.
- `intended.txt` lines are `SLOT|OPPONENT|SETFILE|ROOT`; `rearm.sh`, which re-arms timers a restart killed, passes the
  fourth field on. Without it, a re-arm after a WSL restart would have played main.

All three were tested end to end against a fake 12 Oct fixture (dry run from the pinned checkout, a real timer armed
with the pinned `ROOT`, then stopped).

## Two traps found on 6 Oct

- A `DRY_ONLY` burst run shared its done-marker with the armed run. Arming deleted the marker, so the dry run's
  watchdog never saw it and would have stopped whatever bot was up at the dry run's stop time. The template
  (`burst_rr3p_main.sh`) now gives a dry-only run its own marker; tested.
- Jobs started as harness background tasks live in the harness's session and can die with it. Timers, bursts and long
  trainings are started with `setsid nohup ... &` as a simple command, and checked to have their own session.

## Scouting (6 Oct, `~/pokerbot-scratch/scout9/`)

All 15 season bots, the fixture opponents first (200 matches each where they have that many), then the rest (120).
The clean-profiles builder rebuilt 42 rows from the scout cache plus our own logs counted once (five new: fermat53,
lil-bot-v4, Phineas-III, BonnieBlue, Dushyant_PokerCoach), and three bot-start rebuilds left every row unchanged.

| opponent | sample | the shape |
|---|---|---|
| Shadow | 97 matches | aggressive preflop (VPIP 54, PFR 45, three-bet 18), folds to a three-bet 61% and to a bet 49% |
| PoetAndCoder | 200 | station: folds to a bet 25%, to a three-bet 3% |
| fermat53 | 12 | hyper-aggressive: three-bets 45%, folds to a bet 48% |
| RiverReasonBot | 20 | folds to a bet 45%, large raises |
| riverline_v2 | 36 | calls 91% of its responses, never bluffs |
| lil-bot-v4 | 16 | extreme station: folded to no postflop bet at any size (208 faced) |
| Phineas-III | 23 | folds to a bet 53%, raises two to four times the pot |
| Blueprint | 200 | folds to a bet 55%, to an all-in 75% |

Four fixture opponents have 12 to 23 matches; re-scout each the day before we meet it.

## The work list

A copy of the list at the top of `NEXT.md` (which is not tracked), as of 6 Oct 19:15 IST. `NEXT.md` is the
live one; this copy is refreshed when items land.

**Burst days before the playoffs: 7, 8 and 9 Oct, one change each on top of the last that passed.** The exploiter set
(v5xRR3 purified) plays the fixtures from a pinned checkout; a change reaches a fixture only after gate, replay and a
burst.

**1. Season operations (fixed dates, IST)**
- [ ] Before 00:00 tonight: `ps` shows both fixture timers (479643 Shadow, 481311 PoetAndCoder); a WSL restart kills them, `rearm.sh` re-arms from `intended.txt`.
- [ ] 7 Oct 00:20 Shadow, 02:40 PoetAndCoder: armed, pinned `~/Code/PokerBot-fixture` (b605dd7).
- [ ] 7 Oct 09:00 flags-on burst (E1): armed, `burst_flags7oct.sh`, pinned `~/Code/PokerBot-burst7oct` (13b0007). Read it decomposed (`chipzen_decompose.py --aivat`, `burst_verdict.py`) only once it has finished.
- [ ] 7 Oct after the burst: re-scout fermat53 and RiverReasonBot (thin samples, both play tonight); choose, pin and arm the 8 Oct 00:40 fermat53 and 02:50 RiverReasonBot fixtures, each with a dry run.
- [ ] 8 and 9 Oct: the same each day (re-scout the night's opponents, pin, arm). 9 Oct: 00:30 riverline_v2, 02:30 lil-bot-v4; 10 Oct: 00:10 Phineas-III, 02:10 Blueprint. Playoffs 10 to 11 Oct UTC.
- [ ] After the 7 Oct burst: give `burst_flags7oct.sh` the DRY_ONLY own-marker fix (not while it is armed).

**2. Exploiter set (v5xRR3), in burst order**
- [ ] **E1, 7 Oct:** flags-on rules (`--capped-price --price-misread --offtree-preflop --posterior-reads`). Copies: no harm (+0.3 average).
- [ ] **E3, 8 Oct:** retrain the mid rungs (18 to 35bb) against a field mix that includes a tight three-bettor. Fixes the measured leak against Blueprint: the 35bb rung jams A2 to A9 over a three-bet, Blueprint called 8 of 8 (QQ, QQ, TT, AA, ATs, ATo, A9o, 33), worth about -10bb a jam. Train on 7 Oct after the burst (six-class, about an hour a rung), test on copies, shapes and the jam spot, gate, replay, arm by the evening.
- [ ] **E2, 9 Oct, if the slot is free:** the new 5bb and 8bb rungs (`results/cfr/experiments/selfplay_{5,8}bb_t421_10m`). Real but small: 8bb gate +6.0, 120 off-tree spots fixed, whole bot level (49.6), so a burst mostly confirms nothing breaks. If E3 does not test well, E2 moves to 8 Oct.
- [ ] E6, fallback for E3: a Blueprint-only read, "its three-bets are value, do not jam light" (the player already has a "their re-raise is value" rule to extend).
- [ ] E4, after the season unless E3 shows a big gain: the deep rungs (50 to 100bb) against a field mix.
- [ ] E5, after the season: a cold histogram (4,3,2,1) station exploiter (is the histogram exploiter's weaker exploit its recipe or its tree and cards?).

**3. Balanced set (v5iT2p60m)**
- [x] B1, done 6 Oct 19:41, **no-go by the rule set before the run.** LBR paired, (4,3,2,1) minus T2: default menu -5.4 ± 6.2, between our sizes +9.0 ± 10.5 (neither 10 BB/100 at 2 SE). T2 is already about as hard to exploit (+27.1 against (4,3,2,1)'s +21.6, where plain (4,2,1) read +51.3): its half-pot re-raise captured most of what the extra depth buys, at a fraction of the training. Copies level (+0.2). (4,3,2,1) is better against every scripted shape at a fixed 70bb (thirdraiser +26.7, reraiser +21.3, maniac +25.8, station +10.3, bully +3.0) and +7.8 ± 3.4 head to head there, level in the arena; a lead to revisit if a real aggressive bot shows a gap, not a reason to build. `~/pokerbot-scratch/c4321_vs_t2/`.
- [ ] B2, 7 Oct daytime beside E3 (E3 has the cores first): the merged tree, T2's menu plus a sized third raise and a fourth raise (preflop to turn `half,pot,2x,jam / half,2x,jam / 2x,jam / jam`, river `half,pot,2x,jam / 2x,jam / 2x,jam / jam`), warm from the T2 70bb rung, counted, about 120M with snapshots. Smoke test passed 6 Oct (20,000 iterations: schedule saved as written, warm start 2,811,689 entries 0 dropped, the player plays it; peak 2.9 GB). **Go rule, set before the run:** against T2, no more exploitable on either LBR menu (difference at most +3), at least 15 BB/100 better against the thirdraiser and the reraiser, and no more than 1 point worse on the copies' average. `~/pokerbot-scratch/b2merge/`.
- [x] B3: dropped (B1 no-go).

**4. Base solver and instruments (no burst needed)**
- [ ] S1: the visit bar at another depth (25 or 50bb, T against 2T with counts, gate on 9+ seeds).
- [ ] S2: the clean "bigger menus need fine cards" test: six-class (4,3,2,1) against six-class (4,2,1), both self-play past the bar, paired LBR.
- [ ] S3: binary compact format (the JSON load peak; about 460 MB of disk and the duel's peak memory).
- [ ] S4, low priority: re-check September's cap-2 numbers on today's gate (nothing in play depends on them).

**5. Opponent-specific (after the base solver)**
- [ ] O1: choose the set per opponent (the histogram (4,3,2,1) exploiter is stronger against Blueprint-like bots, the live rung against stations).
- [ ] O2: river bluffs and value bets per opponent (`docs/research/2026-10-06-river-solving.md`: price offline first, about half a day, then the restricted river solve).
- [ ] O3: the hoops read, a postflop never-folds read, a false-fire budget, change-point detection.

**6. Housekeeping**
- [ ] H1: archive the merged worktrees `fold-cost`, `river-design`, `shared-tables`, `shortstack-design` (tag `archive/*`, push the tags, remove).
- [ ] H2: decide whether to push `archive/shortstack-postflop` (an earlier attempt, never merged).

## The plan for improving the bot (6 Oct)

What the week measured, and the order to act on it.

**Where the bot loses now**

1. **The exploiter is trained against stations, not the field.** It wins big against weak bots and leaks against
   tight or aggressive ones: the 35bb rung jams weak aces over a three-bet, which Blueprint called 8 of 8, about -10bb
   a jam.
2. **It is very exploitable by design** (LBR about +100 at 70bb), the price of its station edge.
3. **Its tree is coarse.** The (4,2,1) tree cannot express a sized third raise and its re-raise menu is thin; the
   (4,3,2,1) tree on histogram cards was less than half as exploitable (`research/2026-10-06-cap4321.md`).
4. **Its cards are coarse.** Six classes, where histogram cards were worth +11.7 BB/100 on the same tree, and seem to be
   what makes a bigger menu pay off (untested in isolation).
5. **The short-stack rungs were stale** one-raise trees: fixed, waiting for a burst.
6. **Opponent-specific money is left on the table:** river bluffs and value bets against particular bots, and which
   set to play against which bot.

**Phase 1, this season (to 11 Oct): fix measured leaks, one burst at a time.** E1 flags-on (7 Oct), E3 mid-rung
retrain against a field mix with a tight three-bettor (8 Oct), E2 short-stack rungs (9 Oct, if the slot is free); each
night's opponents re-scouted and the fixtures pinned and armed.

**Phase 2, after the season: rebuild both sets on the better foundations (base solver).**
- The next exploiter: histogram cards, (4,3,2,1) deep rungs and field-mixed training, each rung trained to the visit
  bar. It combines points 1, 3 and 4 and should keep the weak-bot edge while losing far less to good bots. That is a
  hypothesis; E5 (a cold histogram (4,3,2,1) station exploiter) tests it first.
- The next balanced bot: B1 said no to a fourth raise level (T2 is already about as hard to exploit), so the
  balanced set keeps T2; its next step is training and card quality rather than a bigger menu.
- The instruments: the visit bar at more depths (S1), the "bigger menus need fine cards" test (S2), faster duels (S3).

**Phase 3, after that: opponent-specific work.** Choose the set per opponent (a balanced or histogram set against
strong bots, the exploiter against stations), river bluffs and value bets per opponent, and the remaining reads.

**How every step is judged:** LBR, the scripted shapes (the thirdraiser included), the field copies, the gate at a
fixed depth, and a burst read decomposed. Not a one-rung arena duel, not a solver head to head alone, and not a short
learning curve: each of those has hidden or invented an effect this week.

None of the Phase 2 combination has been built together yet; each part has to earn its place against the live set on
those instruments.
