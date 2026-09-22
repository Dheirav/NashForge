# Chipzen: the arena, and NashForge's entry in it

What I could verify about the arena in the email, what it would take to enter
NashForge, and what a rating there would and would not tell us. Sources are the
SDK repository (`github.com/chipzen-ai/chipzen-sdk`, Apache-2.0), the PyPI
package `chipzen-bot` 0.4.0 (released 3 September 2026), and the site's own
posts. The season page is a JavaScript application whose data comes from
`/api/v1/...`, and every one of those endpoints answers `403 Access denied`
without a login, so the season's specifics are not in here and I stopped probing
at that point. Open `chipzen.ai/season/6` in a browser for those.

The one thing the page does say to a crawler is its description: **"Weekly
bot-vs-bot poker seasons on Chipzen. Free to enter, prize pool, published fixture
times."** Seasons are weekly. Missing Monday's deadline means waiting a week, not
missing the arena.

## What it is

A heads-up no-limit Hold'em arena for bots, in public beta since 16 June 2026,
run by Chipzen, Inc. The SDK repository dates from 28 April 2026, was last pushed
on 5 September, and has two stars; the site build is `v0.6.33` from 10 September.
Dave, who sent the email, appears as `daveatchipzen` on Kaggle, where the arena
published 247,946 hands from its house bots. So it is real, small and active,
and the email reads as the founder writing to people whose repositories he found.

## The format, which is the part that matters

**Elimination with rising blinds.** Bot-versus-bot matches run "until one bot has
all chips" (developer manual, section 8) and the blinds rise during the match
(the dataset post says so explicitly). Their own house-bot data puts the
**median match at about nineteen hands** before someone busts.

This is not the game our solver plays. Every solver in `results/cfr/` is an
equilibrium approximation for one fixed depth, 100bb or 200bb, with the stacks
reset every hand. In a nineteen-hand elimination match the effective stack is
different on every hand, and once the blinds have risen it is a short-stack
game where the correct play is push or fold. A 100bb strategy played at 15bb is
not a slightly wrong strategy; it opens hands it should jam and bets fractions of
a pot that no longer exist. `NEXT.md` item 5 calls this the `play_match`
stack-drift fix and treats it as a six-max prerequisite. Here it is the whole
game.

The fix is the standard one and it is now cheap: a ladder of solvers at several
depths, selected per hand by effective stack in big blinds. A 250,000-iteration
solver is about 70 seconds on the native path, so a ladder of six or eight
depths is a lunch break. The bridge already knows the stack from the protocol.

**Rating is Glicko-2 on match results**, not big blinds per hundred. A
nineteen-hand match is close to a coin flip between any two competent bots, so
the rating converges over many matches rather than being readable from a few.
The platform schedules and plays them, so that cost is theirs, not ours, on the
container track.

**Three separate ladders**: uploaded containers, remote bots, and the no-code
starter bots, each rated only against its own kind. Ranked challenges across
tracks are refused. One bot per developer per tournament.

## Two ways in, and what each costs us

**Container track.** Docker image, reviewed automatically, then run on their
executor. The constraints that bite:

| constraint | value | why it matters here |
|---|---|---|
| CPU | 0.5 vCPU | numba compiles at first call, on half a core |
| memory | 256 MB | numpy plus numba plus llvmlite is most of that |
| image | 200 MB built, 250 MB compressed | numba alone is about 90 MB |
| root filesystem | read-only, 10 MB tmpfs at `/tmp` | numba's on-disk cache cannot be written |
| attach budget | about 15 s from launch to `hello` | JIT compilation at import would eat it |
| decision timeout | 2,000 ms, ranked bot-versus-bot | a first-call JIT compile is longer than that |

So the container cannot carry the numba path as it is. It can carry the native
extension: `native.equity_vs_random` and the hand evaluator have no JIT, the
pickled centroids are 1.6 MB, and a bucket lookup built on those is pure Python
over a `.so`. That is a small adapter, not a rewrite, and the seccomp profile
should be fine with an ordinary nanobind module.

What the image gives them: the strategy table, since it has to be in the image.
Their terms say they never receive source and take only a licence to run the
container. The Cython recipe in the SDK hides the `.py` files and does nothing
for a pickle.

**Remote track.** Our process stays on this machine, holds a lobby connection
over a token, and plays whatever the dispatcher sends. No review, no image, no
resource caps, and the solver never leaves the machine. The cost is uptime: a
bot that is not in the lobby when a match is dispatched forfeits it, a
connection that drops mid-hand times out to check-or-fold, and in an elimination
format that is the match. This machine was restarted by Windows Update at 04:29
on Wednesday and killed a seven-hour run. That would happen again during a
season. The documentation also routes remote onboarding through
`staging.chipzen.ai` and a Discord allowlist, so the production path for remote
bots is not something I could confirm from the docs.

My reading: remote for the first exhibition matches, because it is the fastest
way to find out whether the bridge is right, and the container for anything
rated, because uptime is what an elimination ladder rewards and the image
constraints are solvable.

## The bridge

The protocol is JSON over WebSocket and the SDK reduces it to one method,
`decide(state) -> Action`. `state` carries hole cards and board as strings like
`"Ah"`, the pot, both stacks, `to_call`, `min_raise`, `max_raise`, and the full
`action_history` for the hand with every amount as a **total bet size**. Outgoing
actions are `fold`, `check`, `call`, or `raise` with a total amount in
`[min_raise, max_raise]`. There is no all-in action; a shove is a raise to
`max_raise`. Timeouts are substituted with check-or-fold and marked in the
history.

That is the same shape as `slumbot/bridge.py`, and easier, because the history
is structured rather than a compact string. The work is:

1. Replay `action_history` into our history key, turning each raise into a pot
   fraction and sending it through the pseudo-harmonic translation, as the
   Slumbot bridge does now. The depth-aware translation from
   `docs/contender-plan.md` step 1 applies here unchanged.
2. Map our six actions out: fold, check or call by `to_call`, a raise to a total
   amount sized off the pot after the call, clamped to `[min_raise, max_raise]`,
   with all-in as `max_raise`.
3. Select the solver by effective stack in big blinds at the start of each hand.
4. Warm everything at process start, before connecting, so the first decision
   is a table lookup.
5. Log every decision with the state it was taken from, because the arena keeps
   the replays and we will want to compare ours to theirs.

With tests, a day. The ladder of solvers is another. Packaging and the first
exhibition matches are a third. Call it three days to a first rated bot, if the
season's configuration is the one in the protocol examples (1,000 chips, blinds
5 and 10, which is 100bb at the start of a match).

## What a rating there would mean

The house field is eleven bots each written by a language model in one pass, plus
whatever other developers have entered. Our solver takes +647 BB/100 off a
calling station and +259 off random, so it would very likely rate well against
that field even with the depth mismatch, and the depth ladder would raise it
further.

But that is the equilibrium-versus-exploitation trade this project has measured
four times, seen from the other side. The 4,000-iteration solver beat the
baselines by more than the converged one does. A field of exploitable bots
rewards exploitation, and our agent has no opponent model, so it plays one
strategy against everyone. A high rating there says "beats amateur bots", which
is worth having and is not the Slumbot question. The two instruments can point
in opposite directions, and we should decide up front that Slumbot is the target
and the arena is a robustness check, or the reverse, and not switch when one
number looks better.

**Entering is publishing.** Every rated hand is public with a replay, and the
arena has already released house-bot hands with hole cards as a dataset. Any
variant we enter to test accumulates a public record while we test it. Match and
hand histories are platform-owned and retained after a bot is deleted. For a
research project that is fine, and it should be a decision rather than a
surprise.

## The platform rules, read logged in (last updated 28 July 2026)

- Matches are elimination, heads-up or 6-max, same starting stack for every
  seat, **blinds escalate on a fixed schedule so matches finish**. No fixed-hands
  mode; a safety cap ends a match past 1,000 hands. The stack and the schedule
  are still not stated anywhere I have read.
- **Decision clock: 5 seconds per action for uploaded bots, 30 seconds for
  remote bots.** The developer manual says 2,000 ms for ranked bot-versus-bot.
  The rules page is older than the manual, so plan for 2 seconds and treat 5 as
  the generous case.
- A timeout or crash folds that action; repeated failures end the match.
- Glicko-2, shown as a number. Unrated until played, provisional until 5 rated
  matches, on the leaderboard after 5.
- No stakes and no entry fees anywhere. Match results, bot names and rankings
  are public.
- You keep the source; they never receive it. Submitting a container grants a
  licence to use it "for any legitimate platform purpose, including matches,
  testing, benchmarking, and promotional use". The strategy table is in the
  image, so that licence covers it.
- "Use only the official SDK and documented APIs."

## Terms, as summarised in the developer manual

One account per person. Bot code must be yours or properly licensed, with
third-party solvers credited in the bot description. By uploading a container
you grant a non-exclusive licence to run it for matches, testing and promotional
demos; you keep ownership of the source and they do not receive it. Bot-versus-
bot matches can carry stakes and entry fees; human-versus-bot play is always
free. The canonical rules are shown in-app at upload and I have not read that
document.

## Season 6, read from the logged-in page on 13 September

- **Format:** one bot per developer, a round-robin against the field, then the
  top finishers in playoffs. Standings are matches played, won, lost.
- **Registration closes Mon 14 Sept 23:59 UTC**, which is **Tue 15 Sept 05:29
  IST**. "You need an active bot to enter." Entry is free.
- **Round robin Tue 15 Sept 00:00 UTC to Fri 18 Sept 23:59 UTC; playoffs Sat 19
  to Sun 20 Sept.** Every fixture has a published start time.
- **Prize:** $200, split $120 / $60 / $10 / $10.
- **Field:** two bots registered at the time of reading, `Sleight-of-Hand` and
  `Blueprint`; "house bots top up the field after the deadline".
- The entry button is "Upload a bot", so the season appears to be on the
  uploaded-container track. The daily tournaments run separately per track:
  Remote brackets have been drawing 2 of 8 entrants, Upload brackets 4 of 8,
  and there is a daily 6-max sit-and-go on the upload track. 316 tournaments
  have run so far.
- The SDK is published for Python, JavaScript and Rust, all alpha, Python
  furthest ahead. There is also an MCP route for agents.

**From a completed daily tournament** ("Daily Upload bracket I - 2026-09-13",
four entrants of eight): every match settles at **+10,000 / −10,000 chips**, so
each bot starts a match with **10,000 chips** and the winner takes the lot.
Three matches ran **53 hands in total**, about eighteen a match, and the final
was **seven hands, won 6 to 1**. Three of the four entrants were house bots
tagged `llmbots` (`Fabulous`, `Chatterbox`, `MercuryRetrograde`); the fourth,
`PluriBot`, lost the final to `Fabulous`. Seven hands is a coin toss with a thumb
on it, which is what a Glicko rating over many such matches is for.

**From that final's replay, the blinds are 50 and 100.** The page does not
print them, but the pots do: a hand where the small blind folds shows "Pot: 100"
(the 50 posted plus the matched 50 of the big blind, the uncalled half returned),
a hand where the big blind folds to a raise shows 200, and hand 7 was an all-in
showdown for 18,080, which is exactly twice the 9,040 the short stack held after
the first six hands at those blinds. So a match starts at **10,000 chips with
blinds 50/100, which is 100 big blinds**, the depth every solver in
`results/cfr/nolimit_strategy.pkl` was fitted for, at a chip scale of 50. Seven
hands showed no escalation; the schedule's rate is still unknown, and with the
1,000-hand safety cap it is presumably slow enough that most matches between
sensible bots end by chips rather than by blinds.

Still not read: whether a remote bot can enter a season at all.

## What was built, 13 September

NashForge is registered for season 6 as a remote bot (`chipzen/`, entry point
`scripts/chipzen_run.py`, background runner `tools/chipzen-run.sh`, progress
reader `tools/chipzen-progress.sh`). The pieces:

- `chipzen/bridge.py`: the arena's structured history into the solver's
  history key and back. Raise fractions measured the engine's way (against the
  pot after the call), translation onto the sizes the raise schedule allows at
  that depth, all-in judged against the bettor's actual stack. Checked against
  the protocol's own worked hand in `tests/test_chipzen_bridge.py`, including
  that our pot-sized open from the small blind is the protocol's "raise to 30".
- `chipzen/player.py`: `evaluation.benchmark.cfr_agent`, the panel's own lookup,
  behind a ladder of solvers chosen by effective stack in big blinds (nearest in
  ratio). An off-tree node, which under one raise per street means any re-raise,
  is put to a **companion** solver with the `(4, 2)` taper first, whose tree has
  the re-raise, and only then to a bucket-threshold rule; the panel's uniform
  random is never used in a match. Misses are still counted, by raise depth.
  The one-raise solver leads rather than the taper because it exploits weak
  opponents far harder (+647 against +202 BB/100 off a calling station).
- `chipzen/client.py`: the WebSocket protocol, adapted from the SDK's reference
  client. Holds the lobby while matches play, reconnects with backoff,
  re-dials a dropped match socket, logs every decision with its state to
  `~/pokerbot-scratch/chipzen/matches/<match_id>.jsonl`, rewrites
  `status.json` on every event.
- `results/cfr/ladder/`: solvers at 70, 50, 35, 25, 18, 12, 8 and 5 big blinds,
  250,000 native iterations each, alongside the shipped 100bb and 200bb.

**First exhibition, 16:57 IST:** an unrated house-bot match on production
(`wss://chipzen.ai`) against `PluriBot`. NashForge won 20,000 to 0 in 13 hands:
12 decisions, one off-tree miss (a three-bet, answered by the fallback with a
fold of 9h3s), no rejected actions, slowest decision 0.9 ms; the server measured
our round trips at 280 to 370 ms, which is the network. The 30-second clock the
casual endpoint grants was never in question. The ladder had only the 100bb rung
at that point, so the hands played at 3 to 4 big blinds effective were answered
by the 100bb strategy; the short rungs were trained afterwards.

**Running it, and seeing it.** `tools/chipzen-run.sh` starts the bot in the
background (it restarts itself if it dies) and `tools/chipzen-run.sh stop` ends
it; `tools/chipzen-progress.sh --watch` shows the lobby state, the current
match, and every decision as it is made. `--house-bot` starts an unrated match
against a house bot, `--challenge NAME...` issues rated challenges to remote
bots that are online (`--list-opponents` says who is), `--accept-inbound`
accepts rated challenges from other remote bots, `--queue` sits in the rated
matchmaking queue. On the site, **Live** shows matches as they play, the bot's
own page (`/bots/<id>`) holds its rating, record and every replay, and the
**Leaderboard** filtered to the remote track is where it stands. Offline,
`scripts/chipzen_review.py` reads the decision logs in `results/chipzen/matches/`
and writes `results/chipzen/review.md`.

**Later on 13 September**, after three rated losses to `mr_hide`, four changes:
the companion's shoves are softened to calls below the top strength class, a
full-size raise-cap-2 companion is trained, the postflop bucket can carry the
board's flush and straight texture (`board_texture`, mirrored in C++, off by
default), and a per-opponent fold-to-bet profile withholds bluffs from a bot
that does not fold. `docs/arena-plan.md` has the detail. Ladders: `results/cfr/
ladder/` (40 samples), `ladder200/` (200 samples), `ladder200t/` (200 samples
plus texture); pick with `--ladder-dir`.

**From the platform's author, by email on 13 September, 19:01 IST.** The
2-second clock in the manual is a mistake; season fixtures give every match
with a remote bot **30 seconds per decision**, written on each fixture as
`decision_clock_seconds` (`GET /api/external-api/fixtures/upcoming`, or
`scripts/chipzen_run.py --fixtures`). A timeout costs the hand, not the match.
Format: 10,000 chips at 50/100, **blinds step up every 20 hands**, stacks carry
over, play to a bust. **Fixtures run one round per evening from Tuesday,
starting 18:00 UTC, which is 23:30 IST, ten minutes apart.** The process must
be in the lobby when a fixture opens: the platform waits about 90 seconds and
re-kicks twice, then it is a walkover for whoever was there.

**From the author, 21:45.** A direct API challenge to another owner's remote
bot lands on that owner's dashboard and needs a human to accept it; nothing is
pushed to their client. So `--accept-inbound` sees nothing today and the rated
queue is the only way two remote bots meet without a person in the loop; he
intends to push challenges over the lobby with an auto-accept option and will
tell us when it exists. The dashboard's own AUTO-ACCEPT switch on the bot page
is the mirror image: with it on, other owners' dashboard challenges to us start
without a click, which is more rated games while the bot is running anyway.

**The ledger.** Every match log carries the bot's version (commit, solver
directory, deep-primary flag, the `--label` given at start) and
`scripts/chipzen_ledger.py` groups matches by it: matches, win rate, hands, net
chips, chips per hand with a standard error, showdowns, per opponent. Matches
older than the stamping are assigned by time from `results/chipzen/epochs.json`.
Chips per hand is the number to compare versions on; a match win rate over
twenty matches has an error of about ±10 points.

## Before a set plays: gate, replay, sweep, burst

Three of the four existed by season 6. The sweep was added on 22 September
after a season 7 fixture was lost to a single node: v5f's 70bb rung held 27
percent of nine-ten suited on an all-in facing a two-blind open, and 98
percent of pocket jacks facing a pot-sized one, so with 77 big blinds it put
the stack in and lost to king-queen. Three sets sharing the same betting tree
held 0 to 1 percent on that line, so it was that solve's convergence rather
than the design. The gate and the replay could not see it: both judge a set by
what it scores over tens of thousands of hands, and this is one node that is
wrong a quarter of the time in a spot that arises once a match.

    tools/xtree-gate.sh <pickle>                       # not broken
    scripts/chipzen_replay.py --ladder-dir <dir>       # covers the hands we have seen
    tools/strategy-sweep.sh <dir>                      # does nothing unexplainable
    burst, then scripts/chipzen_decompose.py           # survives real opponents

The sweep lists, per rung, the nodes where a hand class puts heavy weight on
an all-in although a sized raise is legal, preflop first, and how many entries
are still uniform, which is how undertrained the rung is. A shove is not wrong
by itself; an unexplainable one is. For comparison at 70bb facing an open:
v5f flagged jacks at 98 percent and eights at 93, v5i flagged ace-king suited
at 97, v5x four nodes, v5d six hand classes at 57 percent or less.

## What stays out of the repository

The code is public under PolyForm Noncommercial from 22 September 2026; three things are
not in it. The solved strategies (`results/cfr/experiments/` and the real-file ladders,
gitignored), because they are what plays rated matches. The scout's cache of other bots'
hands, because it is refetched. And the tuned read thresholds, in `~/.chipzen/reads.toml`
(`[thresholds]`, the upper-case names from `chipzen/opponents.py`), because a rival who
knows the exact rate at which we start folding to a "never bluffs" profile can play to it;
the module keeps the documented defaults and the file overrides them at import.
`CHIPZEN_READS` points it elsewhere for a test.

## What has to be true during the season

- The process must be in the lobby when a fixture opens, so
  `tools/chipzen-run.sh` has to be running and this machine awake **every
  evening from 23:15 IST, Tuesday to Friday**, for as long as the round takes
  (matches ten minutes apart), and again for the playoffs on Saturday and
  Sunday. Windows Update restarted this machine at 04:29 one night last week;
  the evening window is safer, and the machine can sleep in between.
  `scripts/chipzen_run.py --fixtures` prints the exact times in IST.
- The runner restarts the process if it dies, and the process reconnects the
  lobby on its own; a full restart mid-match resumes the seat, but the clock
  runs while we are away.
- Auto-accept on the bot page stays off. Season matches are dispatched by the
  platform and do not need it; leaving it on would accept anyone's challenge.

## Recommendation

Enter, but not as a substitute for the contender. The bridge is a day, it
reuses the translation work the contender plan already needs, and the depth
ladder it forces is an improvement the bot should have had anyway. Treat the
rating as a second, cheaper, differently-biased instrument next to Slumbot.

Revised once the season page and a replay had been read. A match starts at
exactly the depth our shipped solver was fitted for, the field is two bots plus
house LLM bots, and the season is round-robin rather than one-loss elimination,
so a single bad match does not end the week. That makes season 6 worth an
attempt with the 100bb solver alone: bridge, native-only bucket path, container,
review, by Mon 14 Sept 23:59 UTC. The depth ladder is the follow-up, because the
uploaded bot is frozen for the week (uploads are not versioned) and there is no
time to validate a ladder before the deadline. If the container fails review,
season 7 with the ladder is the fallback and nothing is lost but the attempt.
