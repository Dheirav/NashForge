"""
Scout the season's opponents from the platform's own match records.

    venv/bin/python scripts/chipzen_scout.py                       # the bots on our fixture list
    venv/bin/python scripts/chipzen_scout.py --names mellyy Shadow --max-matches 60
    venv/bin/python scripts/chipzen_scout.py --seed-profiles       # also write rows into opponents.json

The arena's page shows nothing about other bots, but its API answers our token
with every match ever played (`/api/matches`, paged) and every hand of any
match with both players' cards (`/api/matches/<id>/hands`). A round-robin
meets each opponent once, so a profile learnt during the match arrives too
late; one learnt from their last hundred matches is there at hand one.

What is counted, from the scouted bot's seat: how it answers a bet (fold,
call, raise; the same counts `chipzen/opponents.py` keeps), how often it
enters a pot and raises preflop, how it sizes its raises against the pot, how
often it goes to showdown and wins there, and the strength of the hands it
showed down. `--seed-profiles` writes those counts as rows of
`results/chipzen/opponents.json` marked `scouted`, so the two measured rules
and the sequential trigger can fire against a bot we have never played.

Everything fetched is cached under `results/chipzen/scout/`, so a re-run costs
only the new matches. Indexing the whole platform is about 200 requests.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chipzen.client as client  # noqa: E402
import chipzen.opponents as opponents  # noqa: E402
import scripts.chipzen_run as run  # noqa: E402
from engine.cards import Card  # noqa: E402
from engine.features import chen_formula  # noqa: E402
from engine.hand_eval_fast import score_hand_7_fast  # noqa: E402
from abstraction.equity import equity_vs_random  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "chipzen", "scout")
PROFILES = os.path.join(ROOT, "results", "chipzen", "opponents.json")


#: Seconds between requests (--pace). The platform rate-limits a burst of hand downloads (RATE_001):
#: on 28 Sept a back-to-back scan had 227 refused, and the rows built from what got through were
#: thinner than the ones they replaced.
PACE = 0.0


def get(cfg, path, attempts=4):
    """One GET, paced and retried: dropped connections, and RATE_001 replies with a long back-off."""
    for attempt in range(attempts):
        if PACE:
            time.sleep(PACE)
        try:
            reply = client._http(cfg["base_url"], cfg["token"], "GET", path)
        except Exception as error:               # requests' ConnectionError and friends
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))
            continue
        if "RATE_001" in json.dumps(reply)[:300] and attempt < attempts - 1:
            time.sleep(30 * 2 ** attempt)        # 30, 60, 120 s: the limit clears in minutes, not seconds
            continue
        return reply


def index_matches(cfg, refresh=False):
    """Every poker match on the platform, by participant name. Cached."""
    path = os.path.join(OUT, "index.json")
    cached = {}
    if os.path.exists(path) and not refresh:
        with open(path) as handle:
            cached = json.load(handle)
    first = get(cfg, "/api/matches?page=1&page_size=100")
    total = first.get("total") or 0
    if cached.get("total") == total:
        return cached
    # Incremental: the list is newest first, so only the pages holding matches
    # added since the cache need reading, plus one for safety.
    by_name = defaultdict(list, {k: list(v) for k, v in cached.get("by_name", {}).items()})
    ids = dict(cached.get("ids", {}))
    known = {m["id"] for ms in by_name.values() for m in ms}
    pages = (total + 99) // 100
    if cached:
        pages = min(pages, (total - cached.get("total", 0) + 99) // 100 + 1)
    started = time.time()
    for page in range(1, pages + 1):
        rows = first if page == 1 else get(cfg, f"/api/matches?page={page}&page_size=100")
        for m in rows.get("matches", []):
            if m.get("game_type") != "poker" or m.get("status") != "completed" or m["id"] in known:
                continue
            names = [p.get("name") for p in m.get("participants", [])]
            for p in m.get("participants", []):
                if p.get("bot_id"):
                    ids[p["name"]] = p["bot_id"]
                by_name[p.get("name")].append({"id": m["id"], "at": m.get("started_at"),
                                               "vs": [n for n in names if n != p.get("name")],
                                               "rated": m.get("rated"), "type": m.get("match_type"),
                                               "seat": p.get("seat")})
        if page % 20 == 0 or page == pages:
            elapsed = time.time() - started
            print(f"  index page {page}/{pages}  {elapsed:.0f}s  eta {(pages - page) * elapsed / page / 60:.1f} min", flush=True)
    data = {"total": total, "ids": ids, "by_name": by_name}
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w") as handle:
        json.dump(data, handle)
    return data


def hands_of(cfg, match_id):
    path = os.path.join(OUT, "hands", f"{match_id}.json")
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)
    hands = []
    page = 1
    while True:                      # the endpoint caps a page at 200 hands
        rows = get(cfg, f"/api/matches/{match_id}/hands?page={page}&page_size=200")
        if "hands" not in rows:
            raise RuntimeError(f"hands for {match_id}: {json.dumps(rows)[:120]}")
        hands.extend(rows["hands"])
        if len(rows["hands"]) < 200 or len(hands) >= (rows.get("total") or 0):
            break
        page += 1
    with open(path, "w") as handle:
        json.dump(hands, handle)
    return hands


def _card(text):
    return Card(text[0].upper(), text[1].lower())


def river_equity(hole, board):
    """Exact win probability on the river against every hand the board allows."""
    import numpy as np
    used = {c.index for c in hole + board}
    ranks = np.array([c.index % 13 for c in board + hole], dtype=np.int64)
    suits = np.array([c.index // 13 for c in board + hole], dtype=np.int64)
    ours = int(score_hand_7_fast(ranks, suits))
    deck = [i for i in range(52) if i not in used]
    wins = ties = n = 0
    b_r = np.array([c.index % 13 for c in board], dtype=np.int64)
    b_s = np.array([c.index // 13 for c in board], dtype=np.int64)
    for x in range(len(deck)):
        for y in range(x + 1, len(deck)):
            r = np.concatenate((b_r, [deck[x] % 13, deck[y] % 13]))
            su = np.concatenate((b_s, [deck[x] // 13, deck[y] // 13]))
            theirs = int(score_hand_7_fast(r, su))
            wins += ours > theirs
            ties += ours == theirs
            n += 1
    return (wins + 0.5 * ties) / n


def profile(name, matches, hands_by_match):
    """Counts from the scouted bot's seat, in the shape `chipzen.opponents` reads."""
    row = {"name": name, "matches": 0, "hands": 0, "bets_faced": 0, "folds": 0, "calls": 0, "raises": 0,
           "by_history": {}, "vpip": 0, "pfr": 0, "three_bet": 0, "three_bet_chances": 0,
           "fold_to_three_bet": 0, "three_bets_faced": 0, "showdowns": 0, "showdowns_won": 0,
           "raise_sizes": Counter(), "shown_chen": [], "opponents": Counter(), "net_chips": 0,
           "river_bets": 0, "river_bluffs": 0,
           # Postflop bets by size against the pot before them: big (0.7 pot
           # and up) and small (0.6 and under), and how many of each held under
           # 0.4 equity against a random hand. PoetAndCoder's tell, 15 Sept:
           # 0 of 429 big bets were air, 39 percent of 1,080 small ones were.
           "big_bets": 0, "big_bets_air": 0, "small_bets": 0, "small_bets_air": 0,
           # Its answers to bets by their size, keyed as chipzen.opponents.size_key: the bets are its
           # opponents', so a scouted row says how it answers a half-pot bet before we have made one.
           "by_size": {}}
    for m in matches:
        hands = hands_by_match.get(m["id"])
        if hands is None:
            continue
        # Multi-table tournament starts seat three or more, and every count here is heads-up shaped: the size of a
        # re-raise, the U/T letters, three-bet chances and showdowns all assume one other seat. The whole match is
        # left out, as copy_validate.load_matches does, rather than sized over the wrong bet.
        if any(a.get("seat") not in (0, 1) for h in hands for a in h.get("actions") or []):
            continue
        row["matches"] += 1
        for o in m["vs"]:
            row["opponents"][o] += 1
        for hand in hands:
            actions = hand.get("actions") or []
            seats = {a["seat"] for a in actions}
            # Which seat is the scouted bot: the participants' order is not in
            # the hand, so use the match record's seat for this name.
            seat = m.get("seat")
            if seat is None:
                continue
            row["hands"] += 1
            pot = 0
            # Each seat's chips on this street, for sizing a bet against the call it makes. Unlike our own
            # logs, the platform's hand records give a raise's amount as the chips it adds, so a running sum
            # is the street total and `pot` is already right.
            street_in = Counter()
            sized = None
            previous = None
            street = None
            letters = ""
            preflop_raises = 0
            entered = raised = False
            for a in actions:
                kind = a["action"]
                amount = int(a.get("amount") or 0)
                if a["phase"] != street:
                    street, previous, letters = a["phase"], None, ""
                    street_in = Counter()
                if kind.startswith("post"):
                    pot += amount
                    street_in[a["seat"]] += amount
                    continue
                mine = a["seat"] == seat
                if mine:
                    node = row["by_history"].setdefault(f"{street}:{letters}", {})
                    node[kind] = node.get(kind, 0) + 1
                    if previous == "raise":
                        row["bets_faced"] += 1
                        row["folds" if kind == "fold" else ("raises" if kind == "raise" else "calls")] += 1
                        if sized is not None:
                            bucket = row["by_size"].setdefault(sized, {})
                            bucket[kind] = bucket.get(kind, 0) + 1
                    if street == "preflop":
                        if kind in ("call", "raise"):
                            entered = True
                        if kind == "raise":
                            raised = True
                            if preflop_raises == 1:
                                row["three_bet"] += 1
                        if preflop_raises == 1 and kind in ("fold", "call", "raise"):
                            row["three_bet_chances"] += 1
                        if preflop_raises == 2 and previous == "raise":
                            row["three_bets_faced"] += 1
                            if kind == "fold":
                                row["fold_to_three_bet"] += 1
                    if kind == "raise" and street == "river":
                        # A river bet with under half equity against a random
                        # hand is a bluff; hole cards are in every history.
                        cards = (hand.get("hole_cards") or {}).get(str(seat))
                        board = hand.get("board") or ""
                        if cards and len(cards) == 2 and len(board) == 10:
                            hole = [_card(cards[0]), _card(cards[1])]
                            table = [_card(board[i:i + 2]) for i in range(0, 10, 2)]
                            row["river_bets"] += 1
                            if river_equity(hole, table) < 0.5:
                                row["river_bluffs"] += 1
                    if kind == "raise" and pot > 0 and street != "preflop" and previous != "raise":
                        # A first bet on the street (not a raise of a bet), sized against the pot.
                        cards = (hand.get("hole_cards") or {}).get(str(seat))
                        board = hand.get("board") or ""
                        size = amount / pot
                        n_board = {"flop": 6, "turn": 8, "river": 10}.get(street, 0)
                        if cards and len(cards) == 2 and len(board) >= n_board and n_board:
                            hole = [_card(cards[0]), _card(cards[1])]
                            table = [_card(board[i:i + 2]) for i in range(0, n_board, 2)]
                            eq = river_equity(hole, table) if street == "river" else \
                                equity_vs_random(hole, table, 200, np.random.default_rng(len(row["by_history"])))
                            if size >= 0.7:
                                row["big_bets"] += 1
                                row["big_bets_air"] += int(eq < 0.4)
                            elif size <= 0.6:
                                row["small_bets"] += 1
                                row["small_bets_air"] += int(eq < 0.4)
                    if kind == "raise" and pot > 0:
                        fraction = amount / pot
                        band = "<½" if fraction < 0.5 else ("½-1" if fraction < 1 else ("1-2" if fraction < 2 else ("2-4" if fraction < 4 else "4+")))
                        row["raise_sizes"][band] += 1
                if kind == "raise" and not mine:
                    to_call = max(0, street_in[seat] - street_in[a["seat"]])
                    sized = opponents.size_key(opponents.size_fraction(amount - to_call, pot + to_call),
                                               street == "preflop")
                if kind == "raise" and street == "preflop":
                    preflop_raises += 1
                pot += amount
                street_in[a["seat"]] += amount
                letters += ("T" if mine else "U") + kind[0]
                previous = kind if not mine else None
            row["vpip"] += int(entered)
            row["pfr"] += int(raised)
            winners = hand.get("winner_seats") or []
            last = actions[-1]["action"] if actions else ""
            if last != "fold" and len(seats) == 2:
                row["showdowns"] += 1
                row["showdowns_won"] += int(seat in winners)
                cards = (hand.get("hole_cards") or {}).get(str(seat))
                if cards and len(cards) == 2:
                    row["shown_chen"].append(chen_formula([Card(cards[0][0].upper(), cards[0][1].lower()),
                                                           Card(cards[1][0].upper(), cards[1][1].lower())]))
    return row


def seed_row(row):
    """
    A `profile()` row as `opponents.json` holds it: the counts the reads use, marked scouted, with the same counts
    again as its `scout_base`, which `Profiles.rebuild` starts from so live hands are added once. Anything else that
    seeds rows from the scout (the clean-profile rebuild) should go through here, so a new count is not left out
    of one of them.
    """
    seeded = {"bets_faced": row["bets_faced"], "folds": row["folds"], "calls": row["calls"],
              "raises": row["raises"], "hands": row["hands"], "matches": row["matches"], "net": 0,
              "by_history": row["by_history"], "by_size": row["by_size"], "scouted": True,
              "river_bets": row["river_bets"], "river_bluffs": row["river_bluffs"],
              "big_bets": row["big_bets"], "big_bets_air": row["big_bets_air"],
              "small_bets": row["small_bets"], "small_bets_air": row["small_bets_air"]}
    seeded = json.loads(json.dumps(seeded))         # its own copy, so the base and the live counts never share a dict
    seeded["scout_base"] = json.loads(json.dumps(seeded))
    return seeded


def summarise(row, stats):
    h = max(row["hands"], 1)
    bf = max(row["bets_faced"], 1)
    answered = max(row["calls"] + row["raises"], 1)
    sizes = row["raise_sizes"]
    total_sizes = max(sum(sizes.values()), 1)
    chen = row["shown_chen"]
    return {
        "name": row["name"], "matches": row["matches"], "hands": row["hands"],
        "platform": {k: stats.get(k) for k in ("rating", "matches_played", "wins", "losses", "bb_per_100", "bb_hands_counted", "llm_author_model", "bot_kind")},
        "vpip": row["vpip"] / h, "pfr": row["pfr"] / h,
        "three_bet": row["three_bet"] / max(row["three_bet_chances"], 1),
        "fold_to_three_bet": row["fold_to_three_bet"] / max(row["three_bets_faced"], 1),
        "fold_to_bet": row["folds"] / bf, "call_share_of_answers": row["calls"] / answered,
        "bets_faced": row["bets_faced"],
        "raise_sizes": {k: round(v / total_sizes, 2) for k, v in sorted(sizes.items())},
        "showdown_rate": row["showdowns"] / h, "showdown_win": row["showdowns_won"] / max(row["showdowns"], 1),
        "river_bets": row["river_bets"], "river_bluff_rate": row["river_bluffs"] / max(row["river_bets"], 1),
        "big_bets": row["big_bets"], "big_bet_air_rate": row["big_bets_air"] / max(row["big_bets"], 1),
        "small_bets": row["small_bets"], "small_bet_air_rate": row["small_bets_air"] / max(row["small_bets"], 1),
        "bb_fold_to_open": (lambda n: n.get("fold", 0) / max(sum(n.values()), 1))(row["by_history"].get("preflop:Ur", {})),
        "bb_opens_faced": sum(row["by_history"].get("preflop:Ur", {}).values()),
        "shown_chen_mean": sum(chen) / len(chen) if chen else None,
        "station": row["bets_faced"] >= 100 and row["folds"] / bf < 0.25,
        "fold_or_raise": answered >= 40 and row["calls"] / answered < 0.5,
        "top_opponents": row["opponents"].most_common(5),
        "fold_by_size": {k: [v.get("fold", 0), sum(v.values())] for k, v in sorted(row["by_size"].items())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*")
    parser.add_argument("--pace", type=float, default=0.0, help="seconds between requests (1.5 keeps under the limit)")
    parser.add_argument("--max-matches", type=int, default=80)
    parser.add_argument("--refresh", action="store_true", help="re-index the platform's match list")
    parser.add_argument("--seed-profiles", action="store_true",
                        help="write the scouted counts into results/chipzen/opponents.json")
    parser.add_argument("--reseed", action="store_true",
                        help="with --seed-profiles, replace a row even if the scout is smaller: the way to clean a row "
                             "inflated by the pre-4 Oct rebuild, which counted live hands once per bot start")
    args = parser.parse_args()
    global PACE
    PACE = args.pace
    cfg = run._config()

    names = args.names
    if not names:
        fx = client.upcoming_fixtures(cfg["base_url"], cfg["token"]).get("fixtures") or []
        names = sorted({f.get("opponent_bot_name") for f in fx if f.get("opponent_bot_name")})
    print("scouting:", ", ".join(names), flush=True)
    index = index_matches(cfg, args.refresh)
    summaries = []
    for name in names:
        matches = sorted(index["by_name"].get(name, []), key=lambda m: m["at"] or "", reverse=True)[:args.max_matches]
        bot_id = index["ids"].get(name)
        stats = get(cfg, f"/api/bots/{bot_id}") if bot_id else {}
        print(f"\n{name}: {len(index['by_name'].get(name, []))} poker matches on record, fetching {len(matches)}", flush=True)
        hands_by_match = {}
        started = time.time()
        for k, m in enumerate(matches, 1):
            try:
                hands = hands_of(cfg, m["id"])
            except Exception as error:
                print(f"  {m['id'][:8]}: {error}", flush=True)
                continue
            # The scouted bot's seat in this match, from the actions' seats and the
            # match list (participants carry seat and name).
            hands_by_match[m["id"]] = hands
            if k % 20 == 0 or k == len(matches):
                elapsed = time.time() - started
                print(f"  {k}/{len(matches)} matches  {elapsed:.0f}s  eta {(len(matches) - k) * elapsed / k:.0f}s", flush=True)
        # The seat comes with the index; the match record is the fallback.
        for m in matches:
            if m["id"] in hands_by_match and m.get("seat") is None:
                rec = get(cfg, f"/api/matches/{m['id']}")
                m["seat"] = next((p["seat"] for p in rec.get("participants", []) if p.get("name") == name), None)
        row = profile(name, matches, hands_by_match)
        summary = summarise(row, stats)
        summaries.append(summary)
        with open(os.path.join(OUT, f"{name}.json"), "w") as handle:
            json.dump({"summary": summary, "counts": {k: (dict(v) if isinstance(v, Counter) else v)
                                                      for k, v in row.items() if k != "shown_chen"}}, handle, indent=1)
        if args.seed_profiles and row["hands"]:
            rows = {}
            if os.path.exists(PROFILES):
                with open(PROFILES) as handle:
                    rows = json.load(handle)
            existing = rows.get(name, {})
            # Never shrink a row: a scout of the last 60 matches replaced wsp's 15,266 bets faced with 4,049 on
            # 30 Sept (and five rows on 28 Sept). A fresh, smaller sample is kept in scout/<name>.json instead.
            # Compared with the scout's own counts in the row (`scout_base`), not its total: the total holds our
            # live hands as well, and until 4 Oct counted them once per bot start, so it outgrew every fresh scout.
            if existing and not args.reseed and \
                    row["bets_faced"] < ((existing.get("scout_base") or existing).get("bets_faced") or 0):
                print(f"  kept {name}'s profile ({existing.get('bets_faced')} bets faced; this scout has "
                      f"{row['bets_faced']})", flush=True)
            elif not existing or existing.get("scouted"):
                # `matches` lets the posterior reads count clustering from the real match count rather
                # than hands over a typical match length (chipzen.opponents.matches_of).
                rows[name] = seed_row(row)
                tmp = PROFILES + ".tmp"
                with open(tmp, "w") as handle:
                    json.dump(rows, handle, indent=1, sort_keys=True)
                os.replace(tmp, PROFILES)
                print(f"  seeded {name} into opponents.json ({row['bets_faced']} bets faced)", flush=True)

    lines = ["# Scouted opponents", "",
             "| bot | matches / hands | rating | platform bb/100 | VPIP | PFR | 3-bet | fold to 3-bet | fold to bet | call share | showdown rate | won at showdown | shown Chen | reads |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        p = s["platform"]
        reads = ", ".join(r for r, on in (("station", s["station"]), ("fold-or-raise", s["fold_or_raise"]),
                                          ("folds blind", s["bb_opens_faced"] >= 100 and s["bb_fold_to_open"] >= 0.7),
                                          ("never bluffs", s["river_bets"] >= 40 and s["river_bluff_rate"] < 0.05),
                                          ("big bets are value", s["big_bets"] >= 100 and s["big_bet_air_rate"] < 0.05 and s["small_bet_air_rate"] >= 0.2)) if on) or "none"
        lines.append(f"| {s['name']} | {s['matches']} / {s['hands']} | {p.get('rating') or 0:.0f} | {p.get('bb_per_100') if p.get('bb_per_100') is not None else '?'} "
                     f"| {s['vpip']:.0%} | {s['pfr']:.0%} | {s['three_bet']:.0%} | {s['fold_to_three_bet']:.0%} | {s['fold_to_bet']:.0%} ({s['bets_faced']}) "
                     f"| {s['call_share_of_answers']:.0%} | {s['showdown_rate']:.0%} | {s['showdown_win']:.0%} | "
                     f"{s['shown_chen_mean']:.1f} | {reads} |" if s["shown_chen_mean"] is not None else
                     f"| {s['name']} | {s['matches']} / {s['hands']} | {p.get('rating') or 0:.0f} | {p.get('bb_per_100')} | {s['vpip']:.0%} | {s['pfr']:.0%} | {s['three_bet']:.0%} | {s['fold_to_three_bet']:.0%} | {s['fold_to_bet']:.0%} ({s['bets_faced']}) | {s['call_share_of_answers']:.0%} | {s['showdown_rate']:.0%} | {s['showdown_win']:.0%} | ? | {reads} |")
        lines.append(f"|  | raise sizes vs pot: {s['raise_sizes']} | | | | | | | | | | | | |")
        sized = ", ".join(f"{k} {f / n:.0%} ({n})" for k, (f, n) in s["fold_by_size"].items() if k.startswith("post:"))
        lines.append(f"|  | folds to bets by size, postflop: {sized or 'none'} | | | | | | | | | | | | |")
    text = "\n".join(lines)
    with open(os.path.join(OUT, "scout.md"), "w") as handle:
        handle.write(text + "\n")
    print("\n" + text)
    print(f"\nWrote {os.path.join(OUT, 'scout.md')}")


if __name__ == "__main__":
    main()
