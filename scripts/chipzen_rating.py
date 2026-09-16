"""
Our platform rating over time, by version.

    venv/bin/python scripts/chipzen_rating.py

The platform exposes no rating history, so `chipzen/client.py` records the
rating after every match into `results/chipzen/rating_history.jsonl`, stamped
with the version label. This prints the trace: per version, the rating at its
first and last match and the matches it spanned. A rating carries an
uncertainty of about 60 points after a hundred matches, so a version's effect
shows here only when it is large; the ledger's chips per hand is the finer
instrument, and this is the coarse one the platform itself ranks by.
"""
import json
import os
import sys
import time
from collections import OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATH = os.path.join(ROOT, "results", "chipzen", "rating_history.jsonl")


def main():
    if not os.path.exists(PATH):
        sys.exit("no rating history yet")
    rows = [json.loads(line) for line in open(PATH) if line.strip()]
    by = OrderedDict()
    for r in rows:
        by.setdefault((r.get("label") or "?")[:12], []).append(r)
    print("| version | matches (platform count) | rating first | rating last | ± | bb/100 (platform) |")
    print("|---|---|---|---|---|---|")
    for label, rs in by.items():
        f, l = rs[0], rs[-1]
        print(f"| {label} | {f.get('matches_played')} to {l.get('matches_played')} | {f['rating']:.0f} | {l['rating']:.0f} "
              f"| {l.get('rating_deviation') or 0:.0f} | {l.get('bb_per_100') if l.get('bb_per_100') is None else round(l['bb_per_100'], 1)} |")
    last = rows[-1]
    print(f"\nlast reading {time.strftime('%d %b %H:%M IST', time.localtime(last['at']))}: "
          f"{last['rating']:.0f} ± {last.get('rating_deviation') or 0:.0f}, {last.get('wins')} and {last.get('losses')}")


if __name__ == "__main__":
    main()
