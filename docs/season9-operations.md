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

**Burst days before the playoffs: 7, 8 and 9 Oct, one change each on top of the last that passed.** **10 Oct's quota (from 05:30 IST) goes to the balanced set** (decided 7 Oct, after B2's no-go freed it): v5iT2p60m purified on the pin, the playoff answer to aggressive bluffers like Shadow. Check the playoff slots first: the playoffs start 10 Oct 00:00 UTC (05:30 IST), so the burst must not overlap a playoff match. The exploiter set
(v5xRR3 purified) plays the fixtures from a pinned checkout; a change reaches a fixture only after gate, replay and a
burst.

**1. Season operations (fixed dates, IST)**
- [x] Before 00:00 tonight: `ps` shows both fixture timers (479643 Shadow, 481311 PoetAndCoder); a WSL restart kills them, `rearm.sh` re-arms from `intended.txt`.
- [x] 7 Oct 00:20 **Shadow: lost** (44 hands, -10,000; luck removed -302 ± 154 all-in adjusted, -321 ± 175 AIVAT, deep -360 ± 90, so skill, not variance). 18 hands called preflop then folded to a later bet, -13,250, Shadow holding air in about half; no read fired; one made straight folded by the covering-bet bug (E7). [ ] 02:40 PoetAndCoder: armed, pinned `~/Code/PokerBot-fixture` (b605dd7).
- [x] 7 Oct 09:00 flags-on burst (E1): armed, `burst_flags7oct.sh`, pinned `~/Code/PokerBot-burst7oct` (13b0007). Read it decomposed (`chipzen_decompose.py --aivat`, `burst_verdict.py`) only once it has finished.
- [x] 7 Oct after the burst: re-scout fermat53 and RiverReasonBot (thin samples, both play tonight); choose, pin and arm the 8 Oct 00:40 fermat53 and 02:50 RiverReasonBot fixtures, each with a dry run.
- [ ] 8 and 9 Oct: the same each day (re-scout the night's opponents, pin, arm). 9 Oct: 00:30 riverline_v2, 02:30 lil-bot-v4; 10 Oct: 00:10 Phineas-III, 02:10 Blueprint. Playoffs 10 to 11 Oct UTC.
- [x] After the 7 Oct burst: give `burst_flags7oct.sh` the DRY_ONLY own-marker fix (not while it is armed).

**2. Exploiter set (v5xRR3), in burst order**
- [x] **E1, 7 Oct:** flags-on rules (`--capped-price --price-misread --offtree-preflop --posterior-reads`). Copies: no harm (+0.3 average).
- [x] **E3, no-go (6 Oct 21:41, `~/pokerbot-scratch/e3mid/`).** Mid rungs retrained with station 0.20 + reraiser 0.10 + nit 0.10 (from station 0.25 + reraiser 0.15). The 35bb rung still jams A2 to A9 over a three-bet 100% (the reraiser three-bets far more often than the nit, so the three-bets it faced in training were still mostly light); Blueprint's copy -1.3, copies' average -0.4, station at 25bb -8.1, reraiser -54 / -89 at 25 / 35bb, nit +6.7 / +13.5; gate new against old +11.2 / +9.8 / +14.2, arena 51.2 / 51.6, replay clean. One rung cannot be right against both the reraiser and Blueprint: the leak is opponent-specific.
- [ ] E2, after the season (the burst days went to E7 and E6): the new 5bb and 8bb rungs (`results/cfr/experiments/selfplay_{5,8}bb_t421_10m`). Real but small: 8bb gate +6.0, 120 off-tree spots fixed, whole bot level (49.6).
- [ ] **E6, burst 9 Oct (in time for Blueprint, 10 Oct 02:10). Built 7 Oct, branch `threebet-holds` 3e8a731 (`--threebet-holds`, off by default):** `Profiles.three_bets_hold` reads a three-bet that never folds to our four-bet (preflop:UrTrUr, Wilson upper bound of folds at most 10%; Blueprint 0 of 86, PoetAndCoder 0 of 49) and the player keeps a four-bet only at half the equity against its re-raise floor, else calls at the price plus 3% or folds. 9 tests, planted bugs caught. Replay on the 28 logged four-bets over a three-bet (`~/pokerbot-scratch/e6/`): it changes 15 against Blueprint, the 4 folds saving about 4,200 chips in expectation and the 11 calls replacing jams worth -17,784 against Blueprint's shown hands (folding: -8,900); it keeps the 6 good jams and fires on no light three-bettor. **Copies (7 Oct):** the fitted copies fold 88% (Blueprint) and 100% (PoetAndCoder) of their three-bets to a four-bet, where the bots folded 0 of 86 and 0 of 49, so on them E6 gives up fold equity that is not there: Blueprint -1.9 ± 0.7, PoetAndCoder -1.0 ± 0.6. On holding copies (each fit with the new `defend4_eq` 0 and `fold4_margin` -1 in `chipzen/archetypes.py` on the branch, uncommitted: they keep the whole three-bet range against a four-bet, as the bots do) E6 gains **Blueprint +1.7 ± 0.7, PoetAndCoder +1.1 ± 0.6**. Hoops, Shadow, mr_hide and wsp copies identical on and off. Original plan: a read that stops jamming light over a three-bet from a bot whose three-bets are shown to be value (Blueprint called 8 of 8 jams, QQ QQ TT AA ATs ATo A9o 33; extend the player's "their re-raise is value" rule). Test: replay on the logged jam spots, the copies, and that it does not fire against light three-bettors (reraiser shape, hoops).
- [ ] **E7, top base fix, burst 8 Oct: the covering-bet bug.** Facing a bet with only fold and call legal (it covers our stack), `cfr_agent` masked the table's raise and all-in mass away and renormalised; purified, a fold/call tie folds. Shadow hand 41: a made straight (fold 0.17, call 0.17, raise or jam 0.66) folded. 145 logged decisions turn call to fold that way, 18 played as folds (`~/pokerbot-scratch/maskbug/`). Fix on branch `covering-call` (9c8d9ca, not merged): `--covering-call` moves that mass to the call, off by default, threaded through `cfr_agent`, `load_solver`, `ArenaPlayer`, `chipzen_run.py`, `chipzen_duel.py` and the replay (`--covering-call`, new set only); 6 tests, 4 planted bugs caught, 80 related tests pass. **Replay and duels passed (7 Oct 01:14 to 01:45, `~/pokerbot-scratch/e7/`):** over 55,651 logged decisions the most likely action changes in 34, every one fold to call, and nothing else moves (new-set misses 1,619 against 1,711, the all-raise rows now answered; the scan's 145 used a looser test and is not reconciled yet). Copies and 13 shapes, 10,000 matches a row with E1's flags in both arms: every fix-minus-off inside 2 SE, from -0.8 ± 0.6 (meek) to +0.9 (PoetAndCoder, RiverReasonBot). Next: the 8 Oct burst on top of E1. **E1's burst (7 Oct 09:06 to 10:01, v5xRR3p-flags7oct): 9 of 20 against Blueprint, -26 ± 51 chips a decision hand (882), against the flags-off burst's +35 ± 48; anytime-valid verdict undecided (difference -65, interval -440 to +240). None of the four flags made a decision in the 20 matches, so the burst is the base set plus variance and says nothing against them; E7 goes on top as planned.** **E7's burst armed 7 Oct 18:26** (`~/pokerbot-scratch/chipzen/burst_e7_8oct.sh`, pid 20199, start 8 Oct 09:00, stop by 11:30; label v5xRR3p-e7-8oct; set `fixture_set_e7_8oct`: v5xRR3 purified with E1's four flags and `--covering-call`), from the pinned checkout `~/Code/PokerBot-burst8oct` at covering-call 7e6afba (9c8d9ca plus the flag in the match version record). Dry run clean, all five flags recorded on; the dry run has its own done-markers and its watchdog exited. Its one big hand (-9,950) was a table miss on the 100bb river (`31/141/241/15`) answered by the fallback's pot-odds call: A8 on A K 9 5 J with three clubs, into Blueprint's nut flush (a base item, B-list). **Taken apart (`~/pokerbot-scratch/e1deep/`):** not luck in the AIVAT sense (raw -26, all-in adjusted -54 ± 37, AIVAT -66 ± 38, against the flags-off burst's +59, a gap of 125 ± 53), and not code: the fixture and burst pins play the same 2,000-match duel to the decimal, and both players' frequencies match the flags-off burst. The gap is in river showdowns alone (-8,704 per 100 hands against +1,732 and +4,198; every other way a hand ended is level), where we put 81,575 in behind and 17,850 ahead (flags off: 44,575 and 73,925). We jammed the river at the usual rate (27, against 29 and 27) and won 1 of 5 called, against 10 of 15. Over the line's five Blueprint bursts, river jams with strong hands (0.85+ against random) are +55,950 over 127 and **with medium hands (0.6 to 0.85) -23,850 over 19, 1 of 6 called won**: the station recipe's thin value, which Blueprint calls only with better. Also: Blueprint changed about 1 Oct, from VPIP 30% to about 65%, so September's Blueprint numbers describe another bot.
- [ ] E4, after the season unless E3 shows a big gain: the deep rungs (50 to 100bb) against a field mix.
- [ ] E5, after the season: a cold histogram (4,3,2,1) station exploiter (is the histogram exploiter's weaker exploit its recipe or its tree and cards?).

**3. Balanced set (v5iT2p60m)**
- [x] B1, done 6 Oct 19:41, **no-go by the rule set before the run.** LBR paired, (4,3,2,1) minus T2: default menu -5.4 ± 6.2, between our sizes +9.0 ± 10.5 (neither 10 BB/100 at 2 SE). T2 is already about as hard to exploit (+27.1 against (4,3,2,1)'s +21.6, where plain (4,2,1) read +51.3): its half-pot re-raise captured most of what the extra depth buys, at a fraction of the training. Copies level (+0.2). (4,3,2,1) is better against every scripted shape at a fixed 70bb (thirdraiser +26.7, reraiser +21.3, maniac +25.8, station +10.3, bully +3.0) and +7.8 ± 3.4 head to head there, level in the arena; a lead to revisit if a real aggressive bot shows a gap, not a reason to build. `~/pokerbot-scratch/c4321_vs_t2/`.
- [x] B2, 7 Oct daytime (E3 is done, so B2 has the cores beside E6, which is code work): the merged tree, T2's menu plus a sized third raise and a fourth raise (preflop to turn `half,pot,2x,jam / half,2x,jam / 2x,jam / jam`, river `half,pot,2x,jam / 2x,jam / 2x,jam / jam`), warm from the T2 70bb rung, counted, about 120M with snapshots. Smoke test passed 6 Oct (20,000 iterations: schedule saved as written, warm start 2,811,689 entries 0 dropped, the player plays it; peak 2.9 GB). **Go rule, set before the run:** against T2, no more exploitable on either LBR menu (difference at most +3), at least 15 BB/100 better against the thirdraiser and the reraiser, and no more than 1 point worse on the copies' average. `~/pokerbot-scratch/b2merge/`. **Trained 7 Oct 03:00 to 06:52** (`~/pokerbot-scratch/b2run/`, `results/cfr/experiments/hist20_70bb_t2x4_120m_counted.pkl`): 120M at 0.115 ms/it, 3.08M infosets, 1.5 GB; the visit bar passes at every snapshot, worst line turn d4 at 1,000 (60M), 1,554 (90M), 2,254 (120M). **Measured 7 Oct 08:14 to 08:52 (`~/pokerbot-scratch/b2_vs_t2/`, both arms re-run on the same seeds): NO-GO.** LBR B2 minus T2, 8 seeds of 8,000 hands: default -6.9 ± 6.1 (B2 +20.2, T2 +27.1), between-sizes **+8.8 ± 7.1** (over the +3 bar); 70bb duplicate deals: reraiser +16.8 (87.4 against 70.6) but **thirdraiser -6.3** (53.6 against 59.9), the shape the sized third raise was for; copies' average -0.1 (Shadow +0.6, PoetAndCoder -0.3, Blueprint -1.7, hoops +0.9); head to head level (50.3 and 49.3, duplicate +5.8 ± 3.1). T2 stays the balanced set's 70bb rung.
- [x] B3: dropped (B1 no-go).

**4. Base solver and instruments (no burst needed)**
- [x] S1 (6 Oct 21:35, `~/pokerbot-scratch/s1bar25/`): six-class 25bb self-play, 10M (worst line 1,847, snapshot 1,920) against 20M (4,461): gate -0.4 ± 0.5 on 12 seeds, level. The "enough" side of the bar holds at a second depth; the short side was not probed there.
- [ ] S2: the clean "bigger menus need fine cards" test: six-class (4,3,2,1) against six-class (4,2,1), both self-play past the bar, paired LBR.
- [ ] S3: binary compact format (the JSON load peak; about 460 MB of disk and the duel's peak memory).
- [ ] S4, low priority: re-check September's cap-2 numbers on today's gate (nothing in play depends on them).

**5. Opponent-specific (after the base solver)**
- [ ] **B3 (7 Oct, `~/pokerbot-scratch/b3run/`, `results/cfr/experiments/hist20_70bb_t2x4h_120m_counted.pkl`): NO-GO, on exploitability only.** B2 with a half-pot third raise in place of 2x. It fixed what B2 missed: the half-pot thirdraiser +21.9 (seeds +20.4, +33.5, +11.7), the reraiser +30.5, copies level (+0.0), head to head level (50.0, 49.8), visit bar passed (worst line 1,870 at 120M). But LBR over the +3 bar on both menus: +6.4 ± 5.5 and +6.9 ± 6.8, each about 1.2 SE. The menu was the right fix; whether its LBR cost is real needs LBR at 16 chunks, not a new solve.
- [ ] **B3 LBR at 16 chunks** (7 Oct 22:00, `~/pokerbot-scratch/b3lbr16/`, same +3 bar, seeds 9 to 16 added to both arms): pass puts B3's 70bb rung into the balanced set for its 10 Oct burst; fail leaves T2.
- [ ] B4, an option after B3's answer: the third raise as half, pot and jam (real third raises: under 0.75 pot 60 to 76%, 0.75 to 1.5 pot 17 to 26%, 2x 4 to 8%). About 4 hours on B3's recipe, the same go rule. Only if B3's LBR cost proves to be noise; if it is real, fix the training before adding sizes.
- [ ] B5, base: the fallback's pot-odds call of a river shove with one pair on a three-flush or worse (E1 burst, A8 into the nut flush, -9,950): a table miss on a deep river line should not call off with one pair.
- [ ] E6's 9 Oct burst: merge `threebet-holds` (3e8a731 plus the uncommitted `defend4_eq` archetype option) on top of `covering-call` once E7's burst has passed, pin, dry-run, arm 9 Oct 09:00; it must be live for Blueprint, 10 Oct 02:10.
- [ ] 10 Oct burst: the balanced set (with B3's rung if it passes), fitted around the playoff slots once the bracket is out; the E7 burst is not in `intended.txt`, so re-arm it by hand after any restart.
- [ ] **O1, pulled forward for the playoffs:** choose the set per opponent. Rule from tonight: a bot that raises a lot or bluffs its big bets gets the balanced set (v5iT2p60m purified, LBR +27 against the exploiter's +100); a bot that calls a lot and rarely bluffs gets the exploiter. From the profiles: balanced for Shadow (raises 29%, big bets 32% air, river 51% bluffs), fermat53 (raises 33%, three-bets 45%), HRT (big bets 38% air, river 68%), lil-bot-v4 borderline (raises 43%, folds 12%); exploiter for PoetAndCoder, riverline_v2, wsp, RiverReasonBot, Phineas-III, v003, Dushyant, mellyy and Blueprint (proven in real play). Untested as a rule (the copies favoured the exploiter even against Shadow). First use: fermat53, 8 Oct 00:40. **Decided 7 Oct 08:55: the exploiter**, by the rule set before the re-scout (balanced only if the scout confirms an aggressive bluffer and the copy does not have balanced over 2 points behind). Re-scout, 16 matches: VPIP 64%, PFR 49%, three-bets 42%, but folds to 49% of bets and 62% of three-bets, call share 37%, read fold-or-raise: aggressive preflop, not a bot that calls down. Its copy (refit on those 16, station base): exploiter 64.1% against balanced 60.9%. The balanced set is ready on the pin for a later use (`fixture_set_s9r3_balanced`, ladder linked into `~/Code/PokerBot-fixture`, replay clean: 449 misses against the exploiter's 599); its Shadow replay three-bets the hands the exploiter flat-called and gives up a street earlier.
- [ ] O2: river bluffs and value bets per opponent (`docs/research/2026-10-06-river-solving.md`: price offline first, about half a day, then the restricted river solve).
- [ ] **E8, from the E1 burst (7 Oct):** no river jam with a medium hand (0.6 to 0.85 against random) into a bot whose river calls are value: Blueprint, 19 such jams over five bursts, -23,850, 1 of 6 called won, while strong hands' jams are +55,950. A read like E6's from the scout cache's showdowns (what it calls our river bets with). Thin sample: build after E6's burst, test on the logged jams first.
- [ ] O3: the hoops read, a postflop never-folds read, a false-fire budget, change-point detection.
- [x] **LAG exploiter (7 Oct, `results/cfr/ladder169l_v5xLAG`, `~/pokerbot-scratch/setchoice/`):** v5xRR3's recipe at every cap2 depth against maniac 0.10, bully 0.10 and reraiser 0.10. **By its go rule, NO-GO** (aggressive copies: Shadow +5.6, fermat53 +4.3 over the better of the other two sets, mean +1.9, but hoops -4.1, under the -2 bar). What the table shows beyond the rule: it beats the balanced set on all 13 rows (copies and shapes, by 1.7 to 10.4 points) at an LBR near the balanced set's (default +32.1 ± 8.2, between +14.0 ± 11.2; T2 +27.1 and +12.1, the exploiter +100.3 and +119.2), so the station share, not the tree, is what makes the exploiter exploitable. Against the exploiter it wins on Shadow, fermat53, reraiser, thirdraiser and bully and loses on stations (-8.5), hoops and PoetAndCoder. A new question, not a verdict: LAG as the safe set in the balanced set's place. Its rule, before anything is measured: head to head against v5iT2p60m at least 50% on two seeds, the cross-tree gate, and LBR within +10 of the balanced set on both menus at the same 8 seeds; only then does it take the 10 Oct slot.
  **Tested 7 Oct 18:03 to 19:14 (`~/pokerbot-scratch/lagtest/`): NO-GO as the safe set.** Head to head it **loses to the balanced set, 41.3% and 41.0%**, and to the exploiter, 45.2% and 44.4% (5,000 matches a seed). Gate passed (purified, against the one-raise rung: +193, +260, +337 at 50/70/100bb, the exploiter +151, +210, +347). LBR against the balanced set: 70bb default +28.3 against +27.1, between +23.6 against +12.1; 35bb +27.9 and +18.2 against +16.9 and +15.5; 100bb +22.9 and +26.2 against +10.4 and +9.4, so over the +10 bar in four of six cells, while far under the exploiter's (+51 to +115). Against the scripted shapes it is enormous (reraiser +317 to +478 BB/100 at 50 to 100bb, the exploiter +67 to +180) and against stations it trails the exploiter at every depth. **What this corrects:** LAG beating the balanced set on all 13 copies and shapes was the copies, not LAG. The copies are fitted archetype scripts, the same family LAG was trained against, so a set trained on those scripts flatters itself on them (the exploiter, trained on the station script, beat the balanced set on all 13 too). Against sound play it loses. It stays a specialist for aggressive bots, behind a read, never the default.
- [ ] O4: a read for aggressive bluffers (Shadow's shape): call down lighter with medium hands, three-bet its wide opens instead of flat-calling (Shadow folds to a three-bet 61%; we three-bet twice in 44 hands). Playoffs, if Shadow or a bot like it comes up.
- [ ] O5: are opponents adapting to us? Compare each regular opponent's play against us with its play against the rest of the field, from the scout cache (folds to our bets, bluffs into us, three-bets); a gap is a bot modelling us. About an hour, offline.
- [ ] **O6, from the loss study (7 Oct 00:45, `~/pokerbot-scratch/lossanat/`; split by version the same night):** every version is ahead after all-in luck except v6 (-24 ± 27), so most losses are variance. **The current set's line (v5xRR3 and its variants) has 85 matches, 81 of them against Blueprint (+37 ± 17): against the rest of the field it is unmeasured in real play**, so each fixture is its first real test and the copies (wrong about Shadow) are the only other evidence. The pooled "hoops is level" was older versions: v5x, the current set's base, beat hoops +184 ± 73 over 10, while balanced-next lost -56 ± 67 (a note for O1). **The card-level split is withdrawn as evidence of a leak.** "Behind in 78% of all-ins" counted only lost hands; over every called all-in, won and lost, it is 44 of 91 (48%), mean equity 0.50 (`scripts/loss_anatomy.py` now counts both), and calling an all-in averaged equity 0.54 against a price of 0.29. "Paid off 89 against 29" compares lost matches with won ones, which differ by losing the big showdowns by definition. Over all logged rivers (`~/pokerbot-scratch/lossanat/river_by_family.py`) a river raise shown down wins 65% in both training families (+22 and +24 bb a hand), so river raises are not a leak and not a station-training effect. Station training does bet the river thinner (a called bet wins 77% against 90% outside Blueprint) and earns more for it (+20.9 against +15.8 bb). One thin line to watch: against Blueprint, calling its raise of our river bet won 8 of 26 (-17 to -21 bb a hand, both families); too few hands to act on, so it goes with E6's Blueprint reads.

**6. Housekeeping**
- [x] H1 (6 Oct 20:05): fold-cost, river-design, shared-tables, shortstack-design archived (tags pushed), worktrees removed.
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
