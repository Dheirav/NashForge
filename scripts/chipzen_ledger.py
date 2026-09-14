"""
Win rate against every change made to the arena bot.

    venv/bin/python scripts/chipzen_ledger.py            # writes results/chipzen/ledger.md

Every match log carries the bot's version (commit, solver set, flags, label)
from the moment the client started stamping it. Matches older than that are
assigned by time from results/chipzen/epochs.json, a hand-kept list of when
each change went live. The ledger groups matches by version in the order they
were first seen and reports, per version and per opponent within it: matches,
won, hands, net chips, chips per hand with its standard error, and the
showdown record. Chips per hand is the honest number; a match is a coin toss
of nineteen hands and its win rate needs many of them to mean anything.
"""
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
EPOCHS = os.path.join(ROOT, "results", "chipzen", "epochs.json")
OUT = os.path.join(ROOT, "results", "chipzen", "ledger.md")


def epoch_label(when, epochs):
    label = "before any recorded epoch"
    for e in epochs:
        if when >= e["from"]:
            label = e["label"]
    return label


def version_key(frame, when, epochs):
    v = frame.get("version") or {}
    if v:
        parts = [v.get("commit", "?"), v.get("ladder_dir", "")]
        if v.get("deep_primary"):
            parts.append("deep-primary")
        if v.get("label"):
            parts.append(v["label"])
        return " | ".join(p for p in parts if p)
    return epoch_label(when, epochs)


def main():
    epochs = json.load(open(EPOCHS)) if os.path.exists(EPOCHS) else []
    epochs = [{"from": datetime.fromisoformat(e["from"]).astimezone(timezone.utc), "label": e["label"]} for e in epochs]
    versions = {}
    for path in sorted(glob.glob(os.path.join(MATCHES, "*.jsonl")), key=os.path.getmtime):
        seat = opp = None
        when = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        key = None
        stacks_before = None
        nets = []
        sd = [0, 0]
        for line in open(path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            f = r["frame"]
            if f == "match_start":
                seat = r["seat"]
                if r.get("at"):
                    when = datetime.fromtimestamp(r["at"], tz=timezone.utc)
                opp = next((s["display_name"] for s in r.get("seats") or [] if not s.get("is_self")), None)
                key = version_key(r, when, epochs)
            elif f == "round_start":
                stacks_before = r["state"]["stacks"]
            elif f == "round_result" and seat is not None and stacks_before:
                net = r["result"]["stacks"][seat] - stacks_before[seat]
                nets.append(net)
                if len(r["result"].get("showdown") or []) >= 2:
                    sd[0 if seat in r["result"]["winner_seats"] else 1] += 1
        if not nets or key is None:
            continue
        v = versions.setdefault(key, {"first": when, "matches": [], "per": defaultdict(lambda: {"m": 0, "w": 0, "hands": 0, "net": 0})})
        v["first"] = min(v["first"], when)
        v["matches"].append({"opp": opp or "?", "hands": len(nets), "net": sum(nets), "nets": nets, "sd": sd})
        row = v["per"][opp or "?"]
        row["m"] += 1
        row["w"] += sum(nets) > 0
        row["hands"] += len(nets)
        row["net"] += sum(nets)

    lines = ["# Arena ledger: win rate by version", "",
             "Versions in the order they first played. Chips per hand carries a standard error; the match win "
             "rate does not, because a match is about nineteen hands.", ""]
    ist = timezone.utc
    for key, v in sorted(versions.items(), key=lambda kv: kv[1]["first"]):
        ms = v["matches"]
        hands = [n for m in ms for n in m["nets"]]
        mean = sum(hands) / len(hands)
        se = (sum((n - mean) ** 2 for n in hands) / max(len(hands) - 1, 1)) ** 0.5 / len(hands) ** 0.5
        won = sum(m["net"] > 0 for m in ms)
        sd_w = sum(m["sd"][0] for m in ms)
        sd_l = sum(m["sd"][1] for m in ms)
        first = v["first"].astimezone().strftime("%d %b %H:%M")
        lines += [f"## {key}", "",
                  f"first match {first} IST. **{len(ms)} matches, {won} won ({100 * won / len(ms):.0f}%), "
                  f"{len(hands):,} hands, net {sum(hands):+,} chips, {mean:+.0f} ± {se:.0f} chips/hand**, "
                  f"showdowns {sd_w} won / {sd_l} lost.", "",
                  "| opponent | matches | won | hands | net | chips/hand |", "|---|---|---|---|---|---|"]
        for opp, row in sorted(v["per"].items(), key=lambda kv: -kv[1]["m"]):
            lines.append(f"| {opp} | {row['m']} | {row['w']} | {row['hands']} | {row['net']:+,} | {row['net'] / row['hands']:+.0f} |")
        lines.append("")
    text = "\n".join(lines)
    with open(OUT, "w") as handle:
        handle.write(text + "\n")
    print(text)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
