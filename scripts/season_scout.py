"""
Scout the season field from their own games: results, how each bot plays now,
and how that differs from the profile our reads act on.

    venv/bin/python scripts/season_scout.py --since 2026-09-19 --out report.md

`chipzen_scout.py` profiles one bot from its last matches. This asks the
season's questions of the whole division at once:

- **Results.** Every completed match between two division bots since
  `--since`, with the winner from the platform's `net_chips`. The platform does
  not mark a season fixture, so one is inferred: a rated match between two
  division bots that started within `SLOT_SECONDS` of a ten-minute mark. Our
  own fixtures started 0.9 to 44 seconds after theirs; practice challenges
  start at any second. The report says "inferred" wherever it relies on it.
- **Style now.** Each bot's counts over its matches since `--since`, all
  types, by `chipzen_scout.profile`, so they are the same counts
  `opponents.json` holds and the reads use.
- **Drift.** The same statistics beside the bot's row in `opponents.json`.
  A bot that changed since it was profiled is one our reads will misjudge, and
  the Shadow near-bust was a read acting on a statistic that did not say what
  it assumed. A read acting on a stale one is the next version of that.

Network: the match list is paged newest first and stops at `--since`; hands
are fetched through the scout's cache, so a re-run costs only new matches.
Nothing here writes `opponents.json`: the live bot reads that file, and
seeding it is a separate, deliberate step (`chipzen_scout.py --seed-profiles`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.path.expanduser("~/Code/PokerBot")

#: The season 7 division, from the fixture list (NEXT.md, 22 Sept).
DIVISION = ["NashForge", "lil-bot-v2", "RiverReasonBot", "wsp", "Fold-ver-3", "pkr-sota", "Shadow", "PoetAndCoder"]
#: A fixture starts this close after a ten-minute mark (ours: 0.9 to 44 s).
SLOT_SECONDS = 90

#: (label, key in chipzen_scout.summarise, key in opponents.json or a function of the row)
DRIFT = [
    ("plays a hand (VPIP)", "vpip", None),
    ("raises preflop (PFR)", "pfr", None),
    ("three-bets", "three_bet", None),
    ("folds to a bet", "fold_to_bet", lambda r: r["folds"] / r["bets_faced"] if r.get("bets_faced") else None),
    ("calls, of its answers", "call_share_of_answers",
     lambda r: r["calls"] / (r["calls"] + r["raises"]) if (r.get("calls", 0) + r.get("raises", 0)) else None),
    ("river bets that were bluffs", "river_bluff_rate",
     lambda r: r["river_bluffs"] / r["river_bets"] if r.get("river_bets") else None),
    ("big bets that were air", "big_bet_air_rate",
     lambda r: r["big_bets_air"] / r["big_bets"] if r.get("big_bets") else None),
    ("small bets that were air", "small_bet_air_rate",
     lambda r: r["small_bets_air"] / r["small_bets"] if r.get("small_bets") else None),
    ("folds its blind to an open", "bb_fold_to_open",
     lambda r: (lambda n: n.get("fold", 0) / sum(n.values()) if sum(n.values()) else None)(
         (r.get("by_history") or {}).get("preflop:Ur", {}))),
    ("showdown win rate", "showdown_win", None),
]


def _scout(scout_dir):
    spec = importlib.util.spec_from_file_location("chipzen_scout", os.path.join(ROOT, "scripts", "chipzen_scout.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = scout_dir                      # the cache lives in the main tree, not a worktree
    return module


#: Pause between requests, and the waits after a rate limit. The first run on
#: 25 Sept hit Chipzen's limit (RATE_001) 57 times in about a minute and a half.
PAUSE_S = 0.6
BACKOFF_S = (10, 20, 40, 60, 90)


def _limited(response) -> bool:
    return isinstance(response, dict) and response.get("error_code") == "RATE_001"


def polite_get(sc, cfg, path):
    """`chipzen_scout.get`, paced, and waiting out a rate limit instead of reading it as an empty page."""
    for wait in BACKOFF_S + (None,):
        time.sleep(PAUSE_S)
        response = sc.get(cfg, path)
        if not _limited(response):
            return response
        if wait is None:
            raise RuntimeError(f"still rate limited after {sum(BACKOFF_S)} s of waiting: {path}")
        print(f"  rate limited; waiting {wait} s", flush=True)
        time.sleep(wait)


def polite_hands(sc, cfg, match_id):
    """`chipzen_scout.hands_of`, retried through a rate limit; it raises on one rather than returning it."""
    for wait in BACKOFF_S + (None,):
        time.sleep(PAUSE_S)
        try:
            return sc.hands_of(cfg, match_id)
        except RuntimeError as error:
            if "RATE_001" not in str(error) or wait is None:
                raise
            print(f"  rate limited on {match_id[:8]}; waiting {wait} s", flush=True)
            time.sleep(wait)


def _when(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def season_matches(sc, cfg, since, cache_path, names, ids):
    """
    Each division bot's completed poker matches since `since`, with
    participants and net chips; cached by id.

    Per bot, through `/api/matches?bot_id=`, which filters (checked 25 Sept:
    20 of 20 listed matches were Shadow's, 81 in all). That is the bot's
    profile page as the API has it, and a few pages a bot instead of the
    whole platform's list.
    """
    cache = {}
    if os.path.exists(cache_path):
        cache = json.load(open(cache_path))
    started, fresh = time.time(), 0
    for k, name in enumerate(names, 1):
        bot_id = ids.get(name)
        if not bot_id:
            print(f"  {name}: no bot id in the scout index; skipped", flush=True)
            continue
        page = 1
        while True:
            rows = polite_get(sc, cfg, f"/api/matches?bot_id={bot_id}&page={page}&page_size=100").get("matches", [])
            oldest = None
            for m in rows:
                at = _when(m.get("started_at"))
                oldest = at if oldest is None or (at and at < oldest) else oldest
                if m.get("game_type") != "poker" or m.get("status") != "completed" or not at or at < since:
                    continue
                fresh += m["id"] not in cache
                cache[m["id"]] = {"id": m["id"], "at": m["started_at"], "rated": m.get("rated"),
                                  "type": m.get("match_type"),
                                  "participants": [{"name": p.get("name"), "seat": p.get("seat"),
                                                    "net": p.get("net_chips"), "bot_id": p.get("bot_id")}
                                                   for p in m.get("participants", [])]}
            if not rows or len(rows) < 100 or (oldest is not None and oldest < since):
                break
            page += 1
        print(f"  match lists {k}/{len(names)} ({name}), {fresh} new, {time.time() - started:.0f}s", flush=True)
    with open(cache_path, "w") as handle:
        json.dump(cache, handle)
    return sorted(cache.values(), key=lambda m: m["at"], reverse=True)


def is_fixture(m, division):
    names = {p["name"] for p in m["participants"]}
    if len(names & set(division)) < 2 or not m.get("rated"):
        return False
    at = _when(m["at"])
    return (at.minute % 10) * 60 + at.second + at.microsecond / 1e6 <= SLOT_SECONDS


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default="2026-09-19")
    parser.add_argument("--names", nargs="*", default=DIVISION)
    parser.add_argument("--max-matches", type=int, default=40, help="most recent matches profiled per bot")
    parser.add_argument("--scout-dir", default=os.path.join(MAIN, "results", "chipzen", "scout"))
    parser.add_argument("--profiles", default=os.path.join(MAIN, "results", "chipzen", "opponents.json"))
    parser.add_argument("--offline", action="store_true", help="use only the cached match list and hands")
    parser.add_argument("--out")
    args = parser.parse_args()

    sc = _scout(args.scout_dir)
    cfg = None if args.offline else sc.run._config()
    since = dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc)
    cache_path = os.path.join(args.scout_dir, "season_matches.json")
    if args.offline:
        matches = sorted((m for m in json.load(open(cache_path)).values() if _when(m["at"]) >= since),
                         key=lambda m: m["at"], reverse=True)
    else:
        print(f"match list since {args.since}", flush=True)
        ids = json.load(open(os.path.join(args.scout_dir, "index.json")))["ids"]
        matches = season_matches(sc, cfg, since, cache_path, args.names, ids)
    profiles = json.load(open(args.profiles)) if os.path.exists(args.profiles) else {}

    out = [f"# Season scouting: the division since {args.since}", "",
           f"Built {dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))):%d %B %Y, %H:%M} IST from "
           f"{len(matches):,} completed matches on the platform since then.", ""]

    # --- results -------------------------------------------------------------
    fixtures = [m for m in matches if is_fixture(m, args.names)]
    record = defaultdict(lambda: [0, 0])
    lines = []
    for m in sorted(fixtures, key=lambda m: m["at"]):
        a, b = m["participants"]
        winner = a if (a["net"] or 0) > (b["net"] or 0) else b
        loser = b if winner is a else a
        record[winner["name"]][0] += 1
        record[loser["name"]][1] += 1
        lines.append(f"| {_when(m['at']):%a %d %H:%M} | {winner['name']} | {loser['name']} | {abs(winner['net'] or 0):,.0f} |")
    out += ["## Results (fixtures inferred)", "",
            f"A rated match between two division bots starting within {SLOT_SECONDS} s of a ten-minute mark. "
            "Walkovers leave no match record, so they are missing here.", ""]
    if record:
        out += ["| bot | won | lost |", "|---|---|---|"]
        out += [f"| {n} | {w} | {l} |" for n, (w, l) in sorted(record.items(), key=lambda t: (-t[1][0], t[1][1]))]
        out += ["", "| started (UTC) | winner | loser | chips |", "|---|---|---|---|"] + lines
    else:
        out.append("No fixtures found.")
    out.append("")

    # --- style now, and drift --------------------------------------------------
    out += ["## How each bot plays now, against its profile", "",
            "Now: its matches since the start date, all types, counted as `chipzen_scout.profile` counts them. "
            "Profile: its row in `opponents.json`, which is what our reads act on. **Bold** marks a change of "
            "ten points or more on a sample of at least 100 hands now.", ""]
    for name in args.names:
        if name == "NashForge":
            continue
        mine = [m for m in matches if name in {p["name"] for p in m["participants"]}][:args.max_matches]
        items, hands_by_match = [], {}
        t0 = time.time()
        for k, m in enumerate(mine, 1):
            seat = next(p["seat"] for p in m["participants"] if p["name"] == name)
            items.append({"id": m["id"], "at": m["at"], "rated": m["rated"], "type": m["type"], "seat": seat,
                          "vs": [p["name"] for p in m["participants"] if p["name"] != name]})
            path = os.path.join(args.scout_dir, "hands", f"{m['id']}.json")
            try:
                hands_by_match[m["id"]] = json.load(open(path)) if (args.offline or os.path.exists(path)) \
                    else polite_hands(sc, cfg, m["id"])
            except Exception as error:          # one bad match must not cost the bot
                print(f"  {name} {m['id'][:8]}: {error}", flush=True)
            if not args.offline and (k % 10 == 0 or k == len(mine)):
                el = time.time() - t0
                print(f"  {name}: {k}/{len(mine)} matches, {el:.0f}s, eta {(len(mine) - k) * el / k:.0f}s", flush=True)
        row = sc.profile(name, items, hands_by_match)
        now = sc.summarise(row, {})
        stored = profiles.get(name) or {}
        kinds = Counter(i["type"] for i in items)
        out += [f"### {name}", "",
                f"{row['matches']} matches since {args.since} ({', '.join(f'{v} {k}' for k, v in kinds.items()) or 'none'}), "
                f"{row['hands']:,} hands. Profile: {stored.get('hands', 0):,} hands"
                f"{', scouted' if stored.get('scouted') else ''}.", ""]
        if not row["hands"]:
            out += ["Nothing to count.", ""]
            continue
        out += ["| statistic | now | profile |", "|---|---|---|"]
        for label, key, from_row in DRIFT:
            new = now.get(key)
            old = from_row(stored) if (from_row and stored) else None
            moved = new is not None and old is not None and abs(new - old) >= 0.10 and row["hands"] >= 100
            cell = f"{100 * new:.0f}%" if new is not None else "n/a"
            out.append(f"| {label} | {'**' + cell + '**' if moved else cell} | "
                       f"{f'{100 * old:.0f}%' if old is not None else 'n/a'} |")
        top = ", ".join(f"{o} {n}" for o, n in row["opponents"].most_common(4))
        out += ["", f"Played most: {top}.", ""]

    text = "\n".join(out)
    print("\n" + text)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text)


if __name__ == "__main__":
    main()
