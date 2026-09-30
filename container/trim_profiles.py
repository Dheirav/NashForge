"""
The opponent profiles, trimmed to what the reads use, for the uploaded bot.

    venv/bin/python container/trim_profiles.py IN.json OUT.json

A profile row keeps every action of the opponent by public history (`by_history`, the raw material
for a frequency model nothing reads yet); the reads in chipzen/opponents.py use ten counters and six
of those nodes. Only they ship: the in-match counting (`Profiles.observe`) adds the rest back as the
bot plays, in memory, on a read-only filesystem.
"""
import json
import sys

#: The counters the reads consult (chipzen/opponents.py, `row["..."]` and `row.get("...")`).
FIELDS = ("bets_faced", "folds", "calls", "raises", "hands", "net", "scouted",
          "river_bets", "river_bluffs", "big_bets", "big_bets_air", "small_bets", "small_bets_air")
#: The public histories they consult: our open (and its re-raise), and our first flop and turn bets.
NODES = ("preflop:Ur", "preflop:TrUr", "flop:Ur", "flop:TcUr", "turn:Ur", "turn:TcUr")


def trim(rows: dict) -> dict:
    out = {}
    for name, row in rows.items():
        kept = {k: row[k] for k in FIELDS if k in row}
        nodes = {k: row["by_history"][k] for k in NODES if k in (row.get("by_history") or {})}
        kept["by_history"] = nodes
        out[name] = kept
    return out


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    rows = json.load(open(source))
    with open(target, "w") as handle:
        json.dump(trim(rows), handle, separators=(",", ":"), sort_keys=True)
    import os
    print(f"{len(rows)} profiles: {os.path.getsize(source):,} bytes -> {os.path.getsize(target):,}")
