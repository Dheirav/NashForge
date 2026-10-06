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
