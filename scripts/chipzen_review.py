"""
What the arena logs say about how NashForge played, and where it lost chips.

    venv/bin/python scripts/chipzen_review.py                # every match logged
    venv/bin/python scripts/chipzen_review.py --opponent PluriBot --last 5

Reads the per-match JSONL that `chipzen.client` writes (one line per decision
with the state it was taken from, one per hand result with the showdown) and
writes `results/chipzen/review.md`. The point is shortcomings, so the report
leads with the hands that cost the most and what the bot did in them, then
the off-tree rate by street and raise depth, then what opponents did to us.
Everything is counted from the logs; nothing here is a judgement about
whether a play was right, which the logs cannot know.
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIRS = [os.path.join(ROOT, "results", "chipzen", "matches"),
        os.path.join(os.path.expanduser("~"), "pokerbot-scratch", "chipzen", "matches")]
OUT = os.path.join(ROOT, "results", "chipzen", "review.md")

ACTION = {0: "fold", 1: "check/call", 2: "raise ½", 3: "raise pot", 4: "raise 2×", 5: "all-in"}


def load(path):
    rows = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def hands_of(rows):
    """Group a match's frames into hands: start state, our decisions, result."""
    seat = next((r["seat"] for r in rows if r["frame"] == "match_start"), None)
    opponent = next((s["display_name"] for r in rows if r["frame"] == "match_start"
                     for s in r.get("seats") or [] if not s.get("is_self")), "?")
    hands, current = [], None
    for r in rows:
        if r["frame"] == "round_start":
            current = {"start": r["state"], "decisions": [], "result": None}
            hands.append(current)
        elif r["frame"] == "decision" and current is not None:
            current["decisions"].append(r)
        elif r["frame"] == "round_result" and current is not None:
            current["result"] = r["result"]
    end = next((r for r in rows if r["frame"] == "match_end"), None)
    return seat, opponent, hands, end


def net(hand, seat):
    before = hand["start"]["stacks"][seat]
    after = hand["result"]["stacks"][seat] if hand["result"] else before
    return after - before


def street_raises(history_line):
    """Raise depth of the last street in a solver history key."""
    street = history_line.split("/")[-1]
    return sum(1 for c in street if c in "2345")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--opponent", help="only matches against this bot")
    parser.add_argument("--last", type=int, help="only the most recent N matches")
    parser.add_argument("--worst", type=int, default=8, help="how many losing hands to show")
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    # One file per match id; the repository copy wins over a scratch copy of
    # the same match, so a log that was moved in is not counted twice.
    unique = {}
    for directory in DIRS:
        for path in glob.glob(os.path.join(directory, "*.jsonl")):
            unique.setdefault(os.path.basename(path), path)
    files = sorted(unique.values(), key=os.path.getmtime)
    matches = []
    for path in files:
        seat, opponent, hands, end = hands_of(load(path))
        if seat is None or not hands:
            continue
        if args.opponent and opponent != args.opponent:
            continue
        matches.append((path, seat, opponent, hands, end))
    if args.last:
        matches = matches[-args.last:]
    if not matches:
        print("no matches logged")
        return

    lines = ["# NashForge on Chipzen: review", ""]
    # ---- matches -----------------------------------------------------------
    wins = losses = 0
    per_opp = defaultdict(lambda: {"m": 0, "w": 0, "hands": 0, "net": 0})
    all_hands = []
    for path, seat, opponent, hands, end in matches:
        total = sum(net(h, seat) for h in hands if h["result"])
        won = total > 0
        wins += won
        losses += (not won)
        row = per_opp[opponent]
        row["m"] += 1
        row["w"] += won
        row["hands"] += len(hands)
        row["net"] += total
        for h in hands:
            all_hands.append((h, seat, opponent, os.path.basename(path)[:8]))
    lines += [f"{len(matches)} matches, {wins} won, {losses} lost, {len(all_hands)} hands.", "",
              "| opponent | matches | won | hands | net chips |", "|---|---|---|---|---|"]
    for opp, row in sorted(per_opp.items(), key=lambda kv: -kv[1]["m"]):
        lines.append(f"| {opp} | {row['m']} | {row['w']} | {row['hands']} | {row['net']:+,} |")

    # ---- the hands that cost the most -------------------------------------
    lost = sorted((x for x in all_hands if x[0]["result"] and net(x[0], x[1]) < 0),
                  key=lambda x: net(x[0], x[1]))[:args.worst]
    lines += ["", f"## The {len(lost)} most expensive hands", ""]
    for h, seat, opponent, tag in lost:
        start, result = h["start"], h["result"]
        showdown = {s["seat"]: s.get("hole_cards") or s.get("cards") for s in result.get("showdown") or []}
        theirs = showdown.get(1 - seat)
        lines.append(f"**{net(h, seat):+,} vs {opponent}**, hand {start['hand_number']} ({tag}), "
                     f"we held {' '.join(start['your_hole_cards'])}"
                     + (f", they showed {' '.join(theirs)}" if theirs else ", no showdown")
                     + f", pot {result['pot']:,}, stacks before {start['stacks']}.")
        for d in h["decisions"]:
            how = "companion" if d.get("companion") else ("FALLBACK" if d.get("fallback") else "solver")
            board = " ".join(d.get("board") or []) or "-"
            lines.append(f"  - {d['phase']:7} board {board:14} key `{d['history']}` pot {d['pot']:,} "
                         f"to call {d['to_call']:,} → **{d['sent']['action']}"
                         f"{(' ' + format(d['sent']['params'].get('amount'), ',')) if d['sent'].get('params', {}).get('amount') else ''}** "
                         f"({ACTION.get(d['choice'], d['choice'])}, {how}, {d['solver']}, {d['effective_bb']}bb)")
        lines.append("")

    # ---- off-tree, by street and depth ------------------------------------
    by_street = defaultdict(Counter)
    by_depth = Counter()
    decided = [d for h, *_ in all_hands for d in h["decisions"]]
    for d in decided:
        by_street[d["phase"]]["decisions"] += 1
        by_street[d["phase"]]["miss"] += int(d.get("miss", False))
        by_street[d["phase"]]["companion"] += int(bool(d.get("companion")))
        by_street[d["phase"]]["fallback"] += int(d.get("fallback", False))
        if d.get("miss"):
            by_depth[street_raises(d["history"])] += 1
    lines += ["## Off-tree decisions", "",
              f"{len(decided)} decisions; {sum(c['miss'] for c in by_street.values())} had no entry in the "
              f"one-raise solver ({100 * sum(c['miss'] for c in by_street.values()) / max(len(decided), 1):.0f}%).", "",
              "| street | decisions | no entry | companion answered | rule answered |", "|---|---|---|---|---|"]
    for street in ("preflop", "flop", "turn", "river"):
        c = by_street.get(street)
        if c:
            lines.append(f"| {street} | {c['decisions']} | {c['miss']} | {c['companion']} | {c['fallback']} |")
    if by_depth:
        lines += ["", "Misses by raises already on the street: "
                  + ", ".join(f"{k} raises: {v}" for k, v in sorted(by_depth.items()))]

    # ---- how we act, and how they act against us --------------------------
    ours = defaultdict(Counter)
    theirs = Counter()
    for h, seat, opponent, _ in all_hands:
        for d in h["decisions"]:
            ours[d["phase"]][d["sent"]["action"]] += 1
        if not h["result"]:
            continue
        raises_on_street, street = 0, None
        for a in h["result"].get("action_history") or []:
            if a["action"].startswith("post"):
                continue
            if a["phase"] != street:
                street, raises_on_street = a["phase"], 0
            if a["seat"] != seat:
                theirs[a["action"]] += 1
                if a["action"] == "raise":
                    theirs["re-raise" if raises_on_street else "open"] += 1
                if a.get("is_timeout"):
                    theirs["timeout"] += 1
            elif a.get("is_timeout"):
                theirs["OUR TIMEOUT"] += 1
            if a["action"] == "raise":
                raises_on_street += 1
    lines += ["", "## Action mix", "", "Ours, by street:", ""]
    for street in ("preflop", "flop", "turn", "river"):
        c = ours.get(street)
        if c:
            total = sum(c.values())
            lines.append(f"- {street}: " + ", ".join(f"{k} {100 * v / total:.0f}%" for k, v in c.most_common()))
    lines += ["", "Theirs, over every hand: " + ", ".join(f"{k} {v}" for k, v in theirs.most_common()), ""]

    # ---- showdowns and timing ---------------------------------------------
    sd_won = sd_lost = 0
    for h, seat, *_ in all_hands:
        r = h["result"]
        if r and len(r.get("showdown") or []) >= 2:
            if seat in r["winner_seats"]:
                sd_won += 1
            else:
                sd_lost += 1
    slow = sorted(decided, key=lambda d: -d.get("ms", 0))[:3]
    lines += [f"## Showdowns: {sd_won} won, {sd_lost} lost", "",
              "Slowest decisions: " + ", ".join(f"{d['ms']} ms ({d['phase']})" for d in slow), ""]

    text = "\n".join(lines)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as handle:
        handle.write(text + "\n")
    print(text)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
