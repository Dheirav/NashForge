"""
How well does a copy predict the bot it was fitted to?

    venv/bin/python scripts/copy_validate.py                       # the table across the named bots
    venv/bin/python scripts/copy_validate.py --names Dronev4 --detail

A copy is a scripted archetype (`chipzen/archetypes.py`) whose parameters were fitted to a real bot's
scouted frequencies (`scripts/fit_archetype.py`), and sets are picked by playing copies. That is only as
good as the copy, and fermat1 showed the gap: v5x beat every fermat1 copy while the real fermat1 won both
real matches. Nobody had measured how well a copy predicts its bot on hands it was not fitted to.

So this splits a bot's cached matches by date, fits a copy on the earlier ones and scores it on the later.

**How the copy is scored.** At every decision the real bot made in a held-out hand, the archetype's chance
of folding, calling or raising is computed exactly from that state (`archetypes.action_probabilities`, the
archetype's own mirror of `decide`, averaged over draws of its 200-runout equity so the copy's own noise is
in it). A statistic's prediction is the sum of those chances over the nodes that count towards it, with the
real path deciding which nodes exist. That sum is the compensator of the real count: if the bot *were* the
archetype, real minus predicted has mean zero for every statistic, path statistics included (a showdown is
a hand neither side folded, so its prediction is one less the predicted bot folds and the real opponent
folds). No simulation and no solver are needed, and the opponents are the bot's real ones, which a duel
against v5i is not.

**How the error is scaled.** Each error is divided by the sampling error of the held-out estimate,
clustered by match because a bot may play each opponent differently. The fidelity score is the root mean
square of those z-scores; about 1 is a copy the held-out sample cannot tell from the bot.

**Stability.** The same z-scores between the first and second half of the held-out matches say how much
the bot moved on its own. A copy is flagged when its error is large and well above that, because then the
copy, not the bot, is the problem.

The fit reuses `fit_archetype.search` and its `distance` over `fit_archetype.COLUMNS`, with this replay as
the measurement instead of a duel against v5i (which needs the 4 GB ladder). The copies the duels actually
used were fitted by that duel; they are scored here too, on the same held-out matches, as `deployed`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chipzen.archetypes as arch  # noqa: E402
from scripts.fit_archetype import COLUMNS, distance, search  # noqa: E402

MAIN = os.path.expanduser("~/Code/PokerBot")
SCOUT = os.path.join(MAIN, "results", "chipzen", "scout")
SINCE = os.path.join(MAIN, "results", "chipzen", "profile_since.json")
SCRATCH = os.path.expanduser("~/pokerbot-scratch")
#: The shapes `tools/panel/choose.py` starts a fit from; the closest one is kept.
BASES = ("nit", "maniac", "foldraise", "station", "bully")
NAMED = ("Blueprint", "Dronev4", "fermat1", "PoetAndCoder", "melly", "mellyy", "Shadow", "wsp", "RiverReasonBot")
STACK = 10000
STREETS = ("preflop", "flop", "turn", "river")

#: (statistic, numerator, denominator, kind). Denominators named `*_p` are predicted too, because the
#: copy's own actions decide them (a call share counts only the answers it did not fold).
STATS = (
    ("vpip", "entered", "hands", "share"),
    ("pfr", "raised", "hands", "share"),
    ("three_bet", "tb", "tb_n", "share"),
    ("fold_to_three_bet", "tbf_fold", "tbf_n", "share"),
    ("fold_to_bet", "bf_fold", "bf_n", "share"),
    ("call_share_of_answers", "bf_call", "bf_ans_p", "share"),
    ("bb_fold_to_open", "bbo_fold", "bbo_n", "share"),
    ("river_bluff_rate", "rv_bluff", "rv_bet_p", "share"),
    ("showdown_rate", "sd", "hands", "share"),
    ("raise_share_preflop", "r_preflop", "d_preflop", "share"),
    ("raise_share_flop", "r_flop", "d_flop", "share"),
    ("raise_share_turn", "r_turn", "d_turn", "share"),
    ("raise_share_river", "r_river", "d_river", "share"),
    ("bet_size", "fb_size", "fb_n_p", "mean"),
    ("big_bet_share", "fb_big", "fb_n_p", "share"),
)
FITTED = tuple(COLUMNS)
#: A statistic is scored only on this many held-out observations; fewer and its error is mostly noise.
MIN_COUNT = 15


# ---------------------------------------------------------------------------------------------- data

def load_matches(name, scout_dir=SCOUT, since=None):
    """The bot's cached matches, oldest first, each with its hands."""
    by_name = json.load(open(os.path.join(scout_dir, "index.json")))["by_name"].get(name) or []
    out, seen = [], set()
    for m in by_name:
        path = os.path.join(scout_dir, "hands", f"{m['id']}.json")
        if m["id"] in seen or not os.path.exists(path):
            continue
        at = dt.datetime.fromisoformat(m["at"].replace("Z", "+00:00"))
        if since is not None and at < since:
            continue
        seen.add(m["id"])
        hands = json.load(open(path))
        # A few cached matches are multi-table tournament starts with seats past 1; the archetype and the
        # scout's counts are heads-up only, so those are left out rather than misread.
        if any(a.get("seat") not in (0, 1) for h in hands for a in h.get("actions") or []):
            continue
        out.append({"id": m["id"], "at": at, "seat": m["seat"], "vs": m.get("vs") or [], "hands": hands})
    return sorted(out, key=lambda m: m["at"])


def profile_since(name, path=SINCE):
    """A bot whose author rewrote it is profiled from the rewrite (Blueprint, 29 Sept)."""
    try:
        cut = json.load(open(path)).get(name)
    except (OSError, ValueError):
        return None
    return dt.datetime.fromisoformat(cut) if cut else None


def split(matches, held_frac=0.5, at=None):
    """Earlier matches to fit on, later ones to test on: by date, never interleaved."""
    if at is not None:
        return [m for m in matches if m["at"] < at], [m for m in matches if m["at"] >= at]
    k = int(round(len(matches) * (1 - held_frac)))
    return matches[:k], matches[k:]


def _cards(items):
    from slumbot.bridge import parse_cards
    if isinstance(items, str):
        items = [items[i:i + 2] for i in range(0, len(items), 2)]
    return [c.index for c in parse_cards(items)]


_RIVER = {}


def river_equity(hole, board):
    """Exact, against every hand the board allows, as the scout counts a river bluff (native evaluator)."""
    key = (tuple(sorted(hole)), tuple(sorted(board)))
    if key not in _RIVER:
        import pokerbot_native as native
        score = lambda cs: native.score_hand_7([c % 13 for c in cs], [c // 13 for c in cs])  # noqa: E731
        ours = score(hole + board)
        deck = [c for c in range(52) if c not in hole and c not in board]
        w = n = 0.0
        for i in range(len(deck)):
            for j in range(i + 1, len(deck)):
                t = score([deck[i], deck[j]] + board)
                w += 1.0 if ours > t else (0.5 if ours == t else 0.0)
                n += 1
        _RIVER[key] = w / n
    return _RIVER[key]


# ---------------------------------------------------------------------------------------------- replay

class Replay:
    """Every decision the bot made in some matches, with the state the archetype would have seen there.

    The walk mirrors `chipzen_scout.profile` line for line on what counts towards what (a test holds the two
    together), so real counts here are the scout's counts and a prediction is scored on the same nodes."""

    def __init__(self, matches, draws=8, seed=0):
        import pokerbot_native as native
        rng = np.random.default_rng(seed)
        self.m = len(matches)
        self.matches = matches
        node = defaultdict(list)
        real = defaultdict(lambda: np.zeros(self.m))
        self.skipped = 0
        for mi, m in enumerate(matches):
            seat = m["seat"]
            stacks = [STACK, STACK]
            for hand in m["hands"]:
                actions = hand.get("actions") or []
                hole_txt = (hand.get("hole_cards") or {}).get(str(seat))
                start = list(stacks)
                stacks = self._settle(hand, actions, stacks)
                if not hole_txt or len(hole_txt) != 2:
                    self.skipped += 1
                    continue
                hole = _cards(hole_txt)
                board_all = _cards(hand.get("board") or "")
                real["hands"][mi] += 1
                pot, previous, street, letters = 0, None, None, ""
                preflop_raises = street_raises = 0
                committed = [0, 0]
                left = list(start)
                bb = 100
                entered = raised = False
                for a in actions:
                    kind = a["action"]
                    amount = int(a.get("amount") or 0)
                    who = a["seat"]
                    if a["phase"] != street:
                        street, previous, letters = a["phase"], None, ""
                        street_raises, committed = 0, [0, 0]
                    if kind.startswith("post"):
                        if kind == "post_big_blind":
                            bb = amount or bb
                        pot += amount
                        committed[who] += amount
                        left[who] -= amount
                        continue
                    if who == seat and kind in ("fold", "check", "call", "raise"):
                        n_board = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}[street]
                        board = board_all[:n_board]
                        to_call = max(0, min(committed[1 - seat] - committed[seat], left[seat]))
                        can_raise = (left[seat] > to_call and left[1 - seat] > 0) or kind == "raise"
                        eq = [native.equity_vs_random(hole, board, 200, int(rng.integers(0, 2 ** 62)))
                              for _ in range(draws)]
                        first_bet = street != "preflop" and previous != "raise" and pot > 0
                        node["match"].append(mi)
                        node["street"].append(STREETS.index(street))
                        node["raises"].append(street_raises)
                        node["facing"].append(to_call > 0)
                        node["price"].append(to_call / (pot + to_call) if to_call > 0 else 0.0)
                        node["can_raise"].append(bool(can_raise))
                        node["eq"].append(eq)
                        node["bf"].append(previous == "raise")
                        node["tb"].append(street == "preflop" and preflop_raises == 1 and kind != "check")
                        node["tbf"].append(street == "preflop" and preflop_raises == 2 and previous == "raise")
                        node["bbo"].append(street == "preflop" and letters == "Ur")
                        node["air"].append(street == "river" and len(board) == 5 and river_equity(hole, board) < 0.5)
                        node["first_bet"].append(first_bet)
                        # The copy's first bet is `_raise_to(state, 0.66)`: the minimum raise (a big blind
                        # on a fresh street) plus two thirds of the pot, never more than the stack.
                        node["size_p"].append(min(bb + 0.66 * pot, left[seat]) / pot if first_bet else 0.0)
                        node["pre_entered"].append(entered)
                        node["pre_raised"].append(raised)
                        code = {"fold": 0, "check": 1, "call": 1, "raise": 2}[kind]
                        node["real"].append(code)
                        # The real counts, as `profile` makes them.
                        if previous == "raise":
                            real["bf_n"][mi] += 1
                            real[("bf_fold", "bf_call", "bf_raise")[code]][mi] += 1
                        if street == "preflop":
                            if kind == "raise" and preflop_raises == 1:
                                real["tb"][mi] += 1
                            if preflop_raises == 1 and kind != "check":
                                real["tb_n"][mi] += 1
                            if preflop_raises == 2 and previous == "raise":
                                real["tbf_n"][mi] += 1
                                real["tbf_fold"][mi] += kind == "fold"
                            if letters == "Ur":
                                real["bbo_n"][mi] += 1
                                real["bbo_fold"][mi] += kind == "fold"
                            entered = entered or kind in ("call", "raise")
                            raised = raised or kind == "raise"
                        real[f"d_{street}"][mi] += 1
                        real[f"r_{street}"][mi] += kind == "raise"
                        if kind == "raise" and street == "river":
                            real["rv_bet_p"][mi] += 1
                            real["rv_bluff"][mi] += node["air"][-1]
                        if kind == "raise" and first_bet:
                            real["fb_n_p"][mi] += 1
                            real["fb_size"][mi] += amount / pot
                            real["fb_big"][mi] += amount / pot >= 0.7
                    elif who != seat and kind == "fold":
                        real["opp_folds"][mi] += 1
                    if kind == "raise":
                        street_raises += 1
                        if street == "preflop":
                            preflop_raises += 1
                    # Platform amounts are chips added, not the level raised to.
                    pot += amount
                    committed[who] += amount
                    left[who] -= amount
                    letters += ("T" if who == seat else "U") + kind[0]
                    previous = kind if who != seat else None
                real["entered"][mi] += entered
                real["raised"][mi] += raised
                last = actions[-1]["action"] if actions else ""
                real["sd"][mi] += last != "fold" and len({a["seat"] for a in actions}) == 2
        # Touch every counter, so a bot that never reached a node (no three-bet faced) counts zero there.
        for key in {k for stat in STATS for k in stat[1:3]} | {"bf_raise", "opp_folds"}:
            real[key]
        real["bf_ans_p"] = real["bf_call"] + real["bf_raise"]
        self.real = dict(real)
        self.node = {k: np.asarray(v) for k, v in node.items()}
        self.n = len(self.node.get("match", []))
        if self.n:
            self._groups()

    @staticmethod
    def _settle(hand, actions, stacks):
        """Stacks after the hand. A fold loses what the folder put in; a showdown moves only the matched
        chips, because the arena returns an uncalled excess. A record with no winner is a chopped pot (the
        duel's recorder lists only seats that netted chips)."""
        put = [0, 0]
        for a in actions:
            put[a["seat"]] += int(a.get("amount") or 0)
        folder = next((a["seat"] for a in reversed(actions) if a["action"] == "fold"), None)
        winners = hand.get("winner_seats") or ([hand["winner_seat"]] if hand.get("winner_seat") is not None else [])
        out = list(stacks)
        if folder is not None:
            out[folder] -= put[folder]
            out[1 - folder] += put[folder]
        elif len(winners) == 1:
            w = winners[0]
            matched = min(put)
            out[w] += matched
            out[1 - w] -= matched
        return [int(min(max(x, 0), 2 * STACK)) for x in out]

    def _groups(self):
        """`action_probabilities` branches on these in Python, so nodes are evaluated a branch at a time."""
        d = self.node
        pre = d["street"] == 0
        rb = np.where(pre, np.minimum(d["raises"], 2), 0)
        key = pre * 100 + rb * 10 + d["facing"] * 2 + d["can_raise"]
        self.groups = [(np.flatnonzero(key == k), bool(k // 100), int(k // 10 % 10), bool(k // 2 % 2), bool(k % 2))
                       for k in np.unique(key)]

    def probabilities(self, params):
        """(fold, passive, raise) for every node, averaged over the copy's equity draws."""
        p = dict(arch.PARAMS["station"], **params)
        out = np.zeros((self.n, 3))
        for idx, preflop, raises, facing, can_raise in self.groups:
            probs = arch.action_probabilities(p, self.node["eq"][idx], facing, self.node["price"][idx][:, None],
                                              preflop, can_raise, raises)
            out[idx] = probs.mean(axis=1)
        return out

    def predicted(self, params):
        """Per-match predicted counts: each real count with the copy's chances in place of the bot's actions."""
        pr = self.probabilities(params)
        f, c, r = pr[:, 0], pr[:, 1], pr[:, 2]
        d = self.node
        mi = d["match"]
        add = lambda w: np.bincount(mi, weights=w, minlength=self.m)  # noqa: E731
        pre = d["street"] == 0
        out = {k: self.real[k] for k in ("hands", "tb_n", "tbf_n", "bbo_n", "bf_n") + tuple(f"d_{s}" for s in STREETS)}
        # A node counts towards VPIP only while the real bot has not entered yet: the compensator of a
        # first-time event. Passive is a check, not an entry, when nothing is owed.
        out["entered"] = add(pre * ~d["pre_entered"] * (r + c * d["facing"]))
        out["raised"] = add(pre * ~d["pre_raised"] * r)
        out["tb"] = add(d["tb"] * r)
        out["tbf_fold"] = add(d["tbf"] * f)
        out["bf_fold"] = add(d["bf"] * f)
        out["bf_call"] = add(d["bf"] * c)
        out["bf_ans_p"] = add(d["bf"] * (c + r))
        out["bbo_fold"] = add(d["bbo"] * f)
        river = d["street"] == 3
        out["rv_bet_p"] = add(river * r)
        out["rv_bluff"] = add(river * d["air"] * r)
        out["sd"] = self.real["hands"] - add(f) - self.real.get("opp_folds", np.zeros(self.m))
        for s, name in enumerate(STREETS):
            out[f"r_{name}"] = add((d["street"] == s) * r)
        out["fb_n_p"] = add(d["first_bet"] * r)
        out["fb_size"] = add(d["first_bet"] * r * d["size_p"])
        out["fb_big"] = add(d["first_bet"] * r * (d["size_p"] >= 0.7))
        return out

    def subset(self, rows):
        """The real counts of some of the matches, for the stability halves."""
        return {k: v[rows] for k, v in self.real.items()}


# ---------------------------------------------------------------------------------------------- scoring

def summary(counts):
    out = {}
    for name, num, den, _ in STATS:
        n = float(np.sum(counts.get(den, 0)))
        out[name] = float(np.sum(counts.get(num, 0))) / n if n > 0 else None
    return out


def stderr(counts, name):
    """Sampling error of a ratio estimate, clustered by match, with a binomial floor so that a rate of zero
    over few observations is not read as certain."""
    _, num, den, kind = next(s for s in STATS if s[0] == name)
    y, n = np.asarray(counts.get(num, 0.0)), np.asarray(counts.get(den, 0.0))
    total = float(n.sum())
    if total <= 0:
        return None
    ratio = float(y.sum()) / total
    m = len(n)
    cluster = math.sqrt(float(np.sum((y - ratio * n) ** 2)) * m / max(m - 1, 1)) / total
    if kind == "share":
        shrunk = (float(y.sum()) + 1) / (total + 2)
        floor = math.sqrt(shrunk * (1 - shrunk) / total)
    else:
        floor = 0.05 / math.sqrt(total)
    return max(cluster, floor)


def count_of(counts, name):
    den = next(s[2] for s in STATS if s[0] == name)
    return float(np.sum(counts.get(den, 0)))


def compare(real, predicted):
    """Per statistic: real, predicted, z. Unscored (None) below MIN_COUNT held-out observations."""
    r, p = summary(real), summary(predicted)
    rows = {}
    for name, *_ in STATS:
        se = stderr(real, name)
        if r[name] is None or p[name] is None or se is None or count_of(real, name) < MIN_COUNT:
            rows[name] = {"real": r[name], "pred": p[name], "n": count_of(real, name), "z": None}
        else:
            rows[name] = {"real": r[name], "pred": p[name], "n": count_of(real, name), "z": (r[name] - p[name]) / se}
    return rows


def stability(replay):
    """First half of the held-out matches against the second: how far the bot moves on its own."""
    k = replay.m // 2
    a, b = replay.subset(np.arange(k)), replay.subset(np.arange(k, replay.m))
    ra, rb = summary(a), summary(b)
    rows = {}
    for name, *_ in STATS:
        sa, sb = stderr(a, name), stderr(b, name)
        ok = None not in (ra[name], rb[name], sa, sb) and min(count_of(a, name), count_of(b, name)) >= MIN_COUNT / 2
        rows[name] = {"a": ra[name], "b": rb[name], "z": (ra[name] - rb[name]) / math.hypot(sa, sb) if ok else None}
    return rows


#: Past this a z-score says only that the copy cannot do the thing at all (a fixed bet size against a bot
#: that never bets big gives z near -1000), and one such statistic would swamp the rest of the average.
Z_CAP = 10.0


def rms(rows, names):
    zs = [max(-Z_CAP, min(Z_CAP, rows[n]["z"])) for n in names if rows[n]["z"] is not None]
    return (math.sqrt(sum(z * z for z in zs) / len(zs)), len(zs)) if zs else (None, 0)


def fit(replay, rounds=150, seed=11, bases=BASES):
    """The copy for these matches: fit_archetype's search from each base shape, the closest kept."""
    want = summary(replay.real)
    best = None
    for i, base in enumerate(bases):
        row, score, _ = search(arch.PARAMS[base], want, lambda params, r: summary(replay.predicted(params)),
                               rounds, np.random.default_rng(seed + 7 + i), label=base, log=False)
        if best is None or score < best[1]:
            best = (row, score, base)
    return best


def deployed_params(name, scratch=SCRATCH):
    """The copy the 2 Oct division duels (which picked v5xRR3) played, if its fit is on disk."""
    if name == "Blueprint":
        path = os.path.join(scratch, "blueprint", "fit_new_station.md")
    else:
        try:
            log = open(os.path.join(scratch, "division", "run.log")).read()
        except OSError:
            return None, None
        hit = re.search(rf"^\S+ \S+ {re.escape(name)}: copy fitted from ([a-z]+),", log, re.M)
        if not hit:
            return None, None
        path = os.path.join(scratch, "division", f"fit_{name}_{hit.group(1)}.md")
    try:
        text = open(path).read()
    except OSError:
        return None, None
    hit = re.search(r"Parameters: `(\{.*?\})`", text)
    return (json.loads(hit.group(1)), path) if hit else (None, None)


# ---------------------------------------------------------------------------------------------- one bot

def validate(name, matches, held_frac=0.5, draws=8, rounds=150, seed=11, deployed=None, min_matches=6, split_at=None):
    train, held = split(matches, held_frac, split_at)
    out = {"name": name, "matches": len(matches), "train_matches": len(train), "held_matches": len(held),
           "train_hands": sum(len(m["hands"]) for m in train), "held_hands": sum(len(m["hands"]) for m in held)}
    if len(train) < 3 or len(held) < min_matches:
        out["verdict"] = "too few matches"
        if deployed is not None and matches:
            # Nothing to hold out, but the deployed copy can still be scored on every hand it was fitted
            # to: a copy that misses its own target at the bot's own decisions is off before any split.
            every = Replay(matches, draws, seed)
            out["deployed_all"] = compare(every.real, every.predicted(deployed))
            out["deployed_all_fit_rms"], _ = rms(out["deployed_all"], FITTED)
        return out
    tr = Replay(train, draws, seed)
    te = Replay(held, draws, seed + 1)
    params, score, base = fit(tr, rounds, seed)
    out.update(base=base, distance=score, params={k: round(v, 3) for k, v in params.items()},
               split_at=held[0]["at"].isoformat())
    out["copy"] = compare(te.real, te.predicted(params))
    out["in_sample"] = compare(tr.real, tr.predicted(params))
    out["stability"] = stability(te)
    if deployed is not None:
        out["deployed"] = compare(te.real, te.predicted(deployed))
    extras = tuple(s[0] for s in STATS if s[0] not in FITTED)
    for key in ("copy", "in_sample", "stability", "deployed"):
        if key in out:
            out[f"{key}_fit_rms"], _ = rms(out[key], FITTED)
            out[f"{key}_extra_rms"], _ = rms(out[key], extras)
    worst = max((n for n in extras if out["copy"][n]["z"] is not None),
                key=lambda n: abs(out["copy"][n]["z"]), default=None)
    out["worst_unfitted"] = worst
    out["verdict"] = verdict(out)
    return out


def judge(c, s):
    """Copy error counts only if it stands clear of how much the bot moves between halves of the same span."""
    if c is None:
        return "n/a"
    if s is not None and s > 2:
        return "off, bot also unstable" if c > 1.5 * s else "bot unstable"
    return "off" if c > 2 and c > 1.5 * (s or 1) else "holds"


def verdict(row):
    if row.get("copy_fit_rms") is None:
        return "too few matches"
    thin = " (thin)" if row["held_hands"] < 600 else ""
    out = "copy " + judge(row["copy_fit_rms"], row.get("stability_fit_rms"))
    if "deployed" in row:
        out += "; deployed " + judge(row["deployed_fit_rms"], row.get("stability_fit_rms"))
    return out + thin


# ---------------------------------------------------------------------------------------------- synthetic

def simulate(params, opponent, matches, seed, base="station", opponent_params=None, start=None):
    """Matches played by an archetype row, in the platform's record format, for the tests and a self-check.

    The duel dealer writes a raise as the level raised to; the platform writes the chips added, and the
    scout's counts (and this file's replay) read the platform's, so the record is converted."""
    from scripts.chipzen_calibrate import play_recorded
    bot = arch.Archetype(base, np.random.default_rng(seed), params=params)
    opp = arch.Archetype(opponent, np.random.default_rng(seed + 1), params=opponent_params)
    rows, hands = play_recorded([opp, bot], np.random.default_rng(seed + 2), matches)
    start = start or dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    out = []
    for i, row in enumerate(rows):
        for hand in hands[row["id"]]:
            street, committed = None, [0, 0]
            for a in hand["actions"]:
                if a["phase"] != street:
                    street, committed = a["phase"], [0, 0]
                if a["action"] == "raise":
                    level = a["amount"]
                    a["amount"] = level - committed[a["seat"]]
                    committed[a["seat"]] = level
                else:
                    committed[a["seat"]] += int(a.get("amount") or 0)
        out.append({"id": f"{row['id']}-{seed}", "at": start + dt.timedelta(hours=i), "seat": 1,
                    "vs": [opponent], "hands": hands[row["id"]]})
    return out


# ---------------------------------------------------------------------------------------------- report

def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def fmt(x, digits=1):
    return "n/a" if x is None else f"{x:.{digits}f}"


def detail(row):
    lines = [f"### {row['name']}", ""]
    if "copy" not in row:
        return lines + [f"{row['verdict']}: {row['matches']} matches.", ""]
    lines += [f"Fitted from `{row['base']}` on {row['train_matches']} matches ({row['train_hands']:,} hands) before "
              f"{row['split_at'][:16]}; scored on {row['held_matches']} later ({row['held_hands']:,} hands).", "",
              "| statistic | n | real | copy | z | deployed | z | half 1 | half 2 | z |", "|---|---|---|---|---|---|---|---|---|---|"]
    for name, *_ in STATS:
        c, s = row["copy"][name], row["stability"][name]
        d = row.get("deployed", {}).get(name, {"pred": None, "z": None})
        mark = "" if name in FITTED else " *"
        lines.append(f"| {name}{mark} | {c['n']:.0f} | {pct(c['real'])} | {pct(c['pred'])} | {fmt(c['z'])} | "
                     f"{pct(d['pred'])} | {fmt(d['z'])} | {pct(s['a'])} | {pct(s['b'])} | {fmt(s['z'])} |"
                     if name != "bet_size" else
                     f"| {name}{mark} | {c['n']:.0f} | {fmt(c['real'], 2)} | {fmt(c['pred'], 2)} | {fmt(c['z'])} | "
                     f"{fmt(d['pred'], 2)} | {fmt(d['z'])} | {fmt(s['a'], 2)} | {fmt(s['b'], 2)} | {fmt(s['z'])} |")
    lines += ["", "`*` not fitted. bet_size is a first postflop bet over the pot before it.",
              "", "Parameters: `" + json.dumps(row["params"]) + "`", ""]
    return lines


def table(rows):
    lines = ["| bot | matches fit / held | held hands | bot stability | copy: fitted / unfitted | "
             "deployed: fitted / unfitted | worst unfitted (real, copy) | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "copy" not in r:
            dep = f"{fmt(r['deployed_all_fit_rms'])} in-sample, all {r['matches']} matches" if "deployed_all" in r else ""
            lines.append(f"| {r['name']} | {r['train_matches']} / {r['held_matches']} | {r['held_hands']:,} | | | {dep} | | "
                         f"{r['verdict']} |")
            continue
        w = r["worst_unfitted"]
        show = (lambda x: fmt(x, 2)) if w == "bet_size" else pct
        worst = f"{w} ({show(r['copy'][w]['real'])}, {show(r['copy'][w]['pred'])})" if w else ""
        dep = f"{fmt(r['deployed_fit_rms'])} / {fmt(r['deployed_extra_rms'])}" if "deployed" in r else "none"
        lines.append(f"| {r['name']} | {r['train_matches']} / {r['held_matches']} | {r['held_hands']:,} | "
                     f"{fmt(r['stability_fit_rms'])} | {fmt(r['copy_fit_rms'])} / {fmt(r['copy_extra_rms'])} | {dep} | "
                     f"{worst} | {r['verdict']} |")
    lines += ["", "Each figure is the RMS of z-scores: an error over the held-out estimate's match-clustered standard "
              f"error, capped at {Z_CAP:.0f}. About 1 is a copy the held-out sample cannot tell from the bot. Fitted stats "
              "are fit_archetype.COLUMNS; unfitted are the rest of the --detail table. *copy* is refitted here on the "
              "earlier matches; *deployed* is the copy the 2 Oct division duels played, scored on the same held-out "
              "matches (its fit may have seen some of them, which flatters it). Bot stability compares the two halves "
              "of the held-out matches over the fitted stats."]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*", help="bots to validate (default: the named ones plus any with "
                                                    "--min-auto cached matches)")
    parser.add_argument("--min-auto", type=int, default=20)
    parser.add_argument("--held-frac", type=float, default=0.5)
    parser.add_argument("--draws", type=int, default=8, help="equity draws per decision")
    parser.add_argument("--rounds", type=int, default=150, help="search rounds per base shape")
    parser.add_argument("--max-matches", type=int, default=120,
                        help="use only the latest this many matches of a bot, to keep a run to minutes")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--scout-dir", default=SCOUT)
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--json")
    parser.add_argument("--out", help="write the markdown report here")
    args = parser.parse_args()

    index = json.load(open(os.path.join(args.scout_dir, "index.json")))["by_name"]
    have = set(f[:-5] for f in os.listdir(os.path.join(args.scout_dir, "hands")))
    cached = {n: sum(1 for m in v if m["id"] in have) for n, v in index.items()}
    names = args.names or list(NAMED) + sorted((n for n, c in cached.items() if c >= args.min_auto and n not in NAMED
                                                and n != "NashForge"), key=lambda n: -cached[n])
    if "Blueprint" in names and not args.names:
        names.insert(names.index("Blueprint") + 1, "Blueprint@rewrite")
    rows = []
    for i, name in enumerate(names, 1):
        cut = None
        if name.endswith("@rewrite"):
            # A copy fitted before the author's rewrite and scored after it: what the stability column and
            # the copy column look like when the bot really changed.
            bot = name.split("@")[0]
            since, cut = None, profile_since(bot)
            every = load_matches(bot, args.scout_dir)
            matches = [m for m in every if m["at"] < cut][-args.max_matches // 2:] + \
                      [m for m in every if m["at"] >= cut][:args.max_matches // 2]
            dep = None
        else:
            since = profile_since(name)
            matches = load_matches(name, args.scout_dir, since)[-args.max_matches:]
            dep, _ = deployed_params(name)
        print(f"[{i}/{len(names)}] {name}: {len(matches)} matches" + (f" since {since:%d %b %H:%M}" if since else ""),
              flush=True)
        row = validate(name, matches, args.held_frac, args.draws, args.rounds, args.seed, dep, split_at=cut)
        row["since"] = since.isoformat() if since else None
        rows.append(row)
        print(f"    {row['verdict']}  copy {fmt(row.get('copy_fit_rms'))}  stability {fmt(row.get('stability_fit_rms'))}",
              flush=True)
    lines = table(rows)
    if args.detail:
        lines += [""] + [l for r in rows for l in detail(r)]
    text = "\n".join(lines)
    print("\n" + text)
    if args.out:
        open(args.out, "w").write(text + "\n")
    if args.json:
        json.dump(rows, open(args.json, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
