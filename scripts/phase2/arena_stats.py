"""
Arena numbers recomputed from results/chipzen/matches, shared by the paper and
the slides so both follow the season without retyping.
"""
import glob
import json
import os
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def arena_summary():
    hands = []
    matches = []
    for path in glob.glob(os.path.join(ROOT, "results", "chipzen", "matches", "*.jsonl")):
        seat = opp = None
        rated = None
        cur = None
        nets = []
        for line in open(path):
            r = json.loads(line)
            f = r["frame"]
            if f == "match_start":
                seat = r["seat"]
                rated = r.get("rated")
                opp = next((s["display_name"] for s in r.get("seats") or [] if not s.get("is_self")), None)
            elif f == "round_start":
                cur = {"start": r["state"], "dec": [], "opp": opp}
            elif f == "decision" and cur:
                cur["dec"].append(r)
            elif f == "round_result" and cur and seat is not None:
                cur["net"] = r["result"]["stacks"][seat] - cur["start"]["stacks"][seat]
                sd = r["result"].get("showdown") or []
                cur["showdown"] = len(sd) >= 2
                cur["won"] = seat in r["result"]["winner_seats"]
                hands.append(cur)
                nets.append(cur["net"])
                cur = None
        if nets:
            matches.append({"opp": opp, "rated": rated, "hands": len(nets), "net": sum(nets)})
    per = defaultdict(lambda: {"m": 0, "w": 0, "hands": 0, "net": 0})
    for m in matches:
        row = per[m["opp"] or "unknown"]
        row["m"] += 1
        row["w"] += m["net"] > 0
        row["hands"] += m["hands"]
        row["net"] += m["net"]
    band = defaultdict(lambda: [0, 0])
    for h in hands:
        if h["dec"]:
            e = h["dec"][0]["effective_bb"]
            b = "under 15" if e < 15 else "15 to 35" if e < 35 else "35 to 70" if e < 70 else "70 and over"
            band[b][0] += 1
            band[b][1] += h["net"]
    shove = [h for h in hands if any(d.get("companion") and d["choice"] == 5 for d in h["dec"])]
    decisions = [d for h in hands for d in h["dec"]]
    return {
        "matches": len(matches), "won": sum(m["net"] > 0 for m in matches),
        "rated": sum(1 for m in matches if m["rated"]), "hands": len(hands),
        "net": sum(m["net"] for m in matches), "per": dict(per), "band": dict(band),
        "shove_hands": len(shove), "shove_net": sum(h["net"] for h in shove),
        "shove_lost": sum(1 for h in shove if h["net"] < 0),
        "decisions": len(decisions), "misses": sum(1 for d in decisions if d.get("miss")),
        "companion": sum(1 for d in decisions if d.get("companion")),
        "fallback": sum(1 for d in decisions if d.get("fallback")),
        "slowest_ms": max((d.get("ms", 0) for d in decisions), default=0),
        "sd_won": sum(1 for h in hands if h.get("showdown") and h["won"]),
        "sd_lost": sum(1 for h in hands if h.get("showdown") and not h["won"]),
    }


