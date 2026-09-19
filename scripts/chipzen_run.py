"""
Run NashForge as a remote bot on Chipzen.

    venv/bin/python scripts/chipzen_run.py                  # hold the lobby, play what is dispatched
    venv/bin/python scripts/chipzen_run.py --house-bot      # also start one unrated house-bot match
    venv/bin/python scripts/chipzen_run.py --house-bot --once

Credentials come from ~/.chipzen/chipzen.toml (`[external_api] token`, `bot_id`),
overridden by CHIPZEN_EXTBOT_TOKEN / CHIPZEN_BOT_ID / CHIPZEN_BASE_URL, overridden
by flags. The token is never printed.

Long-running: start it through tools/chipzen-run.sh and watch it with
tools/chipzen-progress.sh. Decisions are logged per match under the log
directory, and status.json there is what the progress reader shows.
"""
import argparse
import asyncio
import glob
import logging
import os
import sys
import tomllib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from chipzen.client import (Arena, accept_remote_challenge, challenge_remote,  # noqa: E402
                            house_bot_challenge, join_queue, lobby_opponents,
                            queue_status, remote_challenges, upcoming_fixtures)
from chipzen.opponents import Profiles  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_LADDER = [os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl"),
                  os.path.join(ROOT, "results", "cfr", "nolimit_strategy_200bb_250k.pkl")]
LADDER_DIR = os.path.join(ROOT, "results", "cfr", "ladder")
#: Deeper-tree solvers consulted when the one-raise ladder has no entry.
DEFAULT_COMPANIONS = [os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")]
DEFAULT_LOG_DIR = os.path.join(os.path.expanduser("~"), "pokerbot-scratch", "chipzen")
#: In the repository, because the record of how the bot played is a result.
DEFAULT_MATCHES_DIR = os.path.join(ROOT, "results", "chipzen", "matches")
CONFIG = os.path.join(os.path.expanduser("~"), ".chipzen", "chipzen.toml")


def _commit():
    """The repository's HEAD, short, with a + when the tree is dirty."""
    import subprocess
    try:
        short = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return short + ("+" if dirty else "")
    except Exception:
        return "unknown"


def _config():
    settings = {}
    if os.path.exists(CONFIG):
        with open(CONFIG, "rb") as handle:
            settings = tomllib.load(handle).get("external_api", {})
    return {
        "token": os.environ.get("CHIPZEN_EXTBOT_TOKEN") or settings.get("token"),
        "bot_id": os.environ.get("CHIPZEN_BOT_ID") or settings.get("bot_id"),
        "base_url": os.environ.get("CHIPZEN_BASE_URL") or settings.get("url") or "wss://chipzen.ai",
    }


def ladder_paths(ladder_dir, deep_primary=False, ladder=None, companions=None):
    """
    Which pickles play at which depth, from a ladder directory.

    Shared with `scripts/chipzen_replay.py`, which asks a ladder that has never
    played what it would have done in the logged hands: the two must pick the
    same rung for the same depth or the replay answers a different question.
    """
    ladder_dir = ladder_dir or LADDER_DIR
    # A ladder directory's own 100bb rung replaces the shipped solver, so a
    # 200-sample or texture-aware set is complete on its own; the shipped
    # solvers only fill in what the directory lacks.
    own = sorted(glob.glob(os.path.join(ladder_dir, "nolimit_*bb.pkl")))
    ladder = list(ladder) if ladder else \
        own + [p for p in DEFAULT_LADDER
               if not any(os.path.basename(p).replace("nolimit_strategy", "nolimit_100bb") ==
                          os.path.basename(o) or (p.endswith("200bb_250k.pkl") and o.endswith("nolimit_200bb.pkl"))
                          for o in own)]
    # Companions: a full-size raise-cap-2 solver beats a (4, 2) taper at the
    # same depth, because its re-raises have every size rather than two.
    cap2 = sorted(glob.glob(os.path.join(ladder_dir, "cap2_*bb.pkl")))
    cap2_depths = {os.path.basename(p).split("_")[1] for p in cap2}
    tapers = [p for p in sorted(glob.glob(os.path.join(ladder_dir, "taper42_*bb.pkl")))
              if os.path.basename(p).split("_")[1] not in cap2_depths]
    if ladder_dir == LADDER_DIR:
        tapers = [p for p in DEFAULT_COMPANIONS if os.path.exists(p) and "100bb" not in cap2_depths] + tapers
    companions = list(companions) if companions is not None else cap2 + tapers
    if deep_primary:
        # The full-size raise-cap-2 solvers play first at the depths they exist
        # for, and the one-raise solver only where none exists. This is the
        # direct answer to the deep-stack losses of 13 September: the main
        # solver then knows what a re-raise means instead of delegating it.
        deep = {os.path.basename(p).split("_")[1]: p for p in cap2}
        ladder = [deep.get(os.path.basename(p).split("_")[1], p) for p in ladder]
        # A depth whose main solver has the full tree needs no companion, and
        # loading the same 2-million-set pickle twice cost 1.2 GB on 14 Sept.
        companions = [p for p in companions if p not in deep.values()]
    return ladder_dir, ladder, companions


async def _main(args, config):
    rng = np.random.default_rng(args.seed) if args.seed is not None else np.random.default_rng()
    ladder_dir, ladder, companions = ladder_paths(args.ladder_dir, args.deep_primary,
                                                  args.ladder, args.companions)
    player = ArenaPlayer(ladder, rng, companions=companions, purify=args.purify,
                         river=args.river_solve, river_budget_s=args.river_budget,
                         river_shove_companion=args.river_shove_companion)
    player.profiles = Profiles(os.path.join(ROOT, "results", "chipzen", "opponents.json"),
                               sequential=args.sequential_triggers, bankroll=args.exploit_bankroll,
                               scout_reads=args.scout_reads) \
        .rebuild(args.matches_dir, os.path.join(args.log_dir, "matches"))
    player.profiles.save()
    for name, row in sorted(player.profiles.rows.items(), key=lambda kv: -kv[1]["bets_faced"])[:6]:
        rate, n = player.profiles.fold_to_bet(name)
        logging.info("opponent %-16s %3d hands, %3d bets faced, fold-to-bet %s%s", name, row["hands"], n,
                     f"{rate:.0%}" if rate is not None else "unknown",
                     "  (station: bluffs withheld)" if player.profiles.never_folds(name) else "")
    logging.info("ladder: %s", ", ".join(f"{s.depth_bb:g}bb {s.schedule}" for s in player.ladder))
    logging.info("companions: %s", ", ".join(f"{s.depth_bb:g}bb {s.schedule}" for s in player.companions) or "none")
    logging.info("warm-up: %.2fs", player.warm_up())

    version = {
        "commit": _commit(), "label": args.label,
        "ladder_dir": os.path.relpath(ladder_dir, ROOT), "deep_primary": bool(args.deep_primary),
        "river_shove_companion": bool(args.river_shove_companion),
        "purify": args.purify, "river_solve": bool(args.river_solve),
        "sequential_triggers": bool(args.sequential_triggers), "scout_reads": bool(args.scout_reads),
        "exploit_bankroll": bool(args.exploit_bankroll),
        "ladder": [os.path.basename(p) for p in ladder],
        "companions": [os.path.basename(p) for p in companions],
    }
    logging.info("version: %s", {k: v for k, v in version.items() if k not in ("ladder", "companions")})
    arena = Arena(config["base_url"], config["bot_id"], config["token"], player,
                  log_dir=args.log_dir, once=args.once, matches_dir=args.matches_dir,
                  version=version)
    task = asyncio.create_task(arena.run())

    if args.house_bot is not None:
        for _ in range(60):
            await asyncio.sleep(0.5)
            if arena.status.lobby == "connected":
                break
        else:
            logging.error("lobby never connected; not issuing the challenge")
        if arena.status.lobby == "connected":
            opponent = args.house_bot or None
            reply = await asyncio.to_thread(house_bot_challenge, config["base_url"],
                                            config["token"], opponent)
            logging.info("house-bot challenge: %s", {k: v for k, v in reply.items() if k != "token"})
            if reply.get("http_status") != 200:
                logging.error("challenge refused; nothing to play")
                task.cancel()
                return 2
            # Dispatch can take a minute on a cold pool; a challenge that never
            # turns into a match should not hold an exhibition loop forever.
            for _ in range(360):
                await asyncio.sleep(0.5)
                if arena.status.matches_started:
                    break
            else:
                logging.error("no match arrived within 180s of the challenge")
                task.cancel()
                return 3
    if args.list_opponents:
        reply = await asyncio.to_thread(lobby_opponents, config["base_url"], config["token"])
        for row in reply.get("opponents") or []:
            logging.info("challengeable now: %-24s rating %.0f", row.get("name"), row.get("rating") or 0)
        if not reply.get("opponents"):
            logging.info("nobody challengeable now: %s", reply)

    inbound = asyncio.create_task(_accept_inbound(arena, config)) if args.accept_inbound else None
    queue = asyncio.create_task(_keep_queued(arena, config)) if args.queue else None

    if args.challenge:
        await _wait_for_lobby(arena)
        for name in args.challenge:
            await _rated_challenge(arena, config, name)
        if args.exit_after_challenges:
            for extra in (inbound, queue):
                if extra:
                    extra.cancel()
            task.cancel()
            return 0

    await task
    return 0


async def _wait_for_lobby(arena, seconds=30):
    for _ in range(seconds * 2):
        if arena.status.lobby == "connected":
            return True
        await asyncio.sleep(0.5)
    return False


async def _rated_challenge(arena, config, name):
    """Challenge one remote bot, wait for its answer, then for the match if accepted."""
    reply = await asyncio.to_thread(challenge_remote, config["base_url"], config["token"], name)
    logging.info("rated challenge to %s: %s", name, reply)
    if reply.get("http_status") != 200:
        return
    challenge_id = reply.get("challenge_id")
    finished_before = arena.status.matches_finished
    state = "pending"
    for _ in range(24):                       # the challenge expires after ~60s
        await asyncio.sleep(5)
        listing = await asyncio.to_thread(remote_challenges, config["base_url"], config["token"])
        row = next((c for c in listing.get("outbound") or [] if c.get("challenge_id") == challenge_id), None)
        state = (row or {}).get("status") or state
        if state != "pending":
            break
    logging.info("challenge to %s: %s", name, state)
    if state != "accepted":
        return
    for _ in range(360):                      # a match is seldom longer than 30 min
        await asyncio.sleep(5)
        if arena.status.matches_finished > finished_before:
            return
    logging.warning("challenge to %s accepted but no match finished within 30 min", name)


async def _accept_inbound(arena, config):
    """Accept every rated challenge another remote bot sends us, while in the lobby."""
    seen = set()
    while True:
        await asyncio.sleep(10)
        if arena.status.lobby != "connected":
            continue
        try:
            listing = await asyncio.to_thread(remote_challenges, config["base_url"], config["token"])
        except Exception as error:            # a failed poll is not a reason to stop
            logging.warning("inbound poll failed: %s", error)
            continue
        for row in listing.get("inbound") or []:
            cid = row.get("challenge_id")
            if row.get("status") == "pending" and cid not in seen:
                seen.add(cid)
                reply = await asyncio.to_thread(accept_remote_challenge, config["base_url"],
                                                config["token"], cid)
                logging.info("accepted challenge from %s: %s", row.get("opponent_name"), reply.get("status"))


async def _keep_queued(arena, config):
    """Sit in the rated queue, re-joining after each timeout and after each match."""
    while True:
        if arena.status.lobby == "connected" and not arena.status.matches_active:
            try:
                status = await asyncio.to_thread(queue_status, config["base_url"], config["token"])
                if status.get("status") in ("idle", "timed_out"):
                    reply = await asyncio.to_thread(join_queue, config["base_url"], config["token"])
                    if reply.get("error_code") == "EXT_BOT_OFFLINE":
                        # The platform's view wins over ours: the lobby socket
                        # is dead however connected it looks from here.
                        await arena.drop_lobby("platform reports EXT_BOT_OFFLINE")
                    elif reply.get("error_code") == "CHALLENGE_QUOTA_EXCEEDED":
                        # Twenty challenge matches a day on the free tier. The
                        # quota resets at midnight UTC; asking every 20 s until
                        # then is noise. Season fixtures are not challenges.
                        logging.info("rated queue: daily quota used (%s); trying again in 30 min", reply.get("message"))
                        await asyncio.sleep(1800)
                        continue
                    elif reply.get("status") is None:
                        logging.warning("rated queue: %s", reply)
                    else:
                        logging.info("rated queue: %s", {k: reply.get(k) for k in ("status", "position", "queue_ttl_seconds")})
            except Exception as error:
                logging.warning("queue poll failed: %s", error)
        await asyncio.sleep(20)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url")
    parser.add_argument("--bot-id")
    parser.add_argument("--ladder", nargs="*", help="solver pickles; default is the shipped "
                        "100bb and 200bb solvers plus results/cfr/ladder/*.pkl")
    parser.add_argument("--purify", default="none", choices=["none", "postflop", "all"],
                        help="play the most probable action instead of sampling (postflop: "
                             "preflop stays mixed). Off by default; see evaluation.benchmark.cfr_agent")
    parser.add_argument("--river-solve", action="store_true",
                        help="re-solve every river on the exact hand from the blueprint's ranges "
                             "(cfr/river.py); off by default, unmeasured")
    parser.add_argument("--river-budget", type=float, default=8.0,
                        help="seconds a river solve may take before the blueprint's answer stands")
    parser.add_argument("--sequential-triggers", action="store_true",
                        help="fire the opponent rules as soon as the 95%% interval excludes the "
                             "equilibrium baseline (from 40 bets) rather than at a fixed 100; off by default")
    parser.add_argument("--scout-reads", action="store_true",
                        help="use the two reads that need scouted counts: open into a blind that folds "
                             "to 70%% of opens, and believe the river bets of a bot that never bluffs")
    parser.add_argument("--exploit-bankroll", action="store_true",
                        help="fire the opponent rules only while our net against that opponent is "
                             "not negative (risk what you have won); off by default")
    parser.add_argument("--river-shove-companion", action="store_true",
                        help="facing an all-in on the river, take the cap-2 companion's answer over the "
                             "one-raise primary's (its river calling range comes from a game without re-raises)")
    parser.add_argument("--deep-primary", action="store_true",
                        help="play the cap2_*bb.pkl solvers as the main solver at their depths")
    parser.add_argument("--ladder-dir", help="use this directory's nolimit_*bb.pkl, cap2_*bb.pkl "
                        "and taper42_*bb.pkl instead of results/cfr/ladder (e.g. ladder200, ladder200t)")
    parser.add_argument("--companions", nargs="*", default=None,
                        help="deeper-tree solvers asked when the ladder misses; default is "
                             "results/cfr/nolimit_taper_42.pkl plus results/cfr/ladder/taper42_*bb.pkl")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR)
    parser.add_argument("--matches-dir", default=DEFAULT_MATCHES_DIR,
                        help="per-match decision logs; scripts/chipzen_review.py reads them")
    parser.add_argument("--house-bot", nargs="?", const="", default=None,
                        help="start one unrated match against a house bot (optionally named)")
    parser.add_argument("--once", action="store_true", help="exit after one match")
    parser.add_argument("--label", default="",
                        help="one line naming the change this run tests, kept with every match it plays")
    parser.add_argument("--fixtures", action="store_true",
                        help="print this bot's upcoming season fixtures, in IST, and exit")
    parser.add_argument("--list-opponents", action="store_true",
                        help="log which remote bots can be challenged for a rated match now")
    parser.add_argument("--challenge", nargs="+", metavar="BOT",
                        help="rated challenges to these remote bots, one after another")
    parser.add_argument("--exit-after-challenges", action="store_true")
    parser.add_argument("--accept-inbound", action="store_true",
                        help="accept rated challenges from other remote bots while in the lobby")
    parser.add_argument("--queue", action="store_true",
                        help="sit in the rated matchmaking queue whenever idle")
    parser.add_argument("--seed", type=int)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    config = _config()
    if args.base_url:
        config["base_url"] = args.base_url
    if args.bot_id:
        config["bot_id"] = args.bot_id
    missing = [k for k in ("token", "bot_id") if not config.get(k)]
    if missing:
        sys.exit(f"missing {', '.join(missing)}: put them in {CONFIG} or the environment")

    if args.fixtures:
        # Times in IST first, the UTC the platform uses in brackets.
        import datetime
        reply = upcoming_fixtures(config["base_url"], config["token"])
        rows = reply.get("fixtures") or []
        if not rows:
            print(f"no upcoming fixtures for this bot ({reply.get('http_status')})")
        ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        for row in rows:
            when = row.get("starts_at") or row.get("scheduled_at") or row.get("start_time") or ""
            try:
                t = datetime.datetime.fromisoformat(when.replace("Z", "+00:00"))
                when = f"{t.astimezone(ist):%a %d %b %H:%M IST} [{t.astimezone(datetime.timezone.utc):%H:%M} UTC]"
            except ValueError:
                pass
            print(f"{when}  vs {row.get('opponent_bot_name') or row.get('opponent') or row.get('opponent_name') or '?'}  "
                  f"clock {row.get('decision_clock_seconds', '?')}s  "
                  f"{row.get('stage') or row.get('round') or ''}  {row.get('status') or ''}")
        return

    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        sys.exit(asyncio.run(_main(args, config)) or 0)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
