"""
A copy of a real bot built from its own decisions, not from a scripted archetype.

The archetype copies (`chipzen/archetypes.py` with fitted parameters) play on hard equity thresholds with fixed sizes,
so they are confidently wrong: on 8 Oct, scored on each bot's later matches, their log-loss was worse than knowing
nothing about the bot (1.5 to 3.4 against a field baseline of 0.75 to 1.09), and the Shadow copy, which re-raises the
pot, never made the small three-bets that beat us. A table of the bot's own action frequencies by situation and hand
strength, backed off to coarser situations and then to the field where thin, scored 0.35 to 0.94 on the same matches
and named the bot's action 65 to 84% of the time, Shadow included on 15 matches (`~/pokerbot-scratch/copyfit/`).

The scout cache holds both hole cards for every hand, folds included, which is what makes this possible: every
decision can be keyed by the hand's strength, not only the ones that reached a showdown.

A situation is the street, whether a bet is faced, the raises already made on the street (0 to 3, 3 meaning three or
more), and the hand's equity against a random hand on the board at that moment, in five bands. Raise sizes are binned
by the raise over the pot after the call and drawn from the bot's own bins per street and facing, again backed off to
the field. Position and earlier streets are not in the key, so a plan across streets is only partly captured.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

ACTIONS = ("fold", "passive", "raise")
#: Raise sizes by the raise over the pot after the call: under half, half to pot, pot to 2x, over 2x.
SIZE_EDGES = (0.45, 1.05, 2.05)
#: What each bin is played as, in `Archetype._raise_to`'s terms: the arena's minimum raise plus this share of the pot
#: after the call. The minimum already carries about one raise's worth, so the smallest bin is the minimum itself
#: (Shadow's three-bets, 19 of 19 at a price of 0.25 or better); 0.33 on top of it made every small raise too big for
#: the small-raise defence to meet (8 Oct, identical on and off against the Shadow copy).
SIZE_PLAY = (0.0, 0.45, 1.1, 2.5)
BOARD_AT = (0, 3, 4, 5)
STREETS = ("preflop", "flop", "turn", "river")
#: How many field observations a bot's own counts are pulled towards, at each step of the back-off.
PRIOR_WEIGHT = 4.0
#: The price of a call faced (the call over the pot after it), in bands: without it a copy folds to a min-bet as
#: often as to a shove, so a set that bets big against it wins far more than against the bot (8 Oct: 83% against the
#: Blueprint copy, about 55% against Blueprint). Band 0 is nothing faced.
PRICE_EDGES = (0.2, 0.3, 0.4)


def size_bin(fraction: float) -> int:
    return sum(fraction >= edge for edge in SIZE_EDGES)


def band(equity: float) -> int:
    return min(int(equity * 5), 4)


def price_band(facing: bool, price: float) -> int:
    return 0 if not facing else 1 + sum(price >= edge for edge in PRICE_EDGES)


def coarse_key(street: int, facing: bool, raises: int) -> str:
    return f"{street}|{int(facing)}|{min(raises, 3)}"


def scout_decisions(match_meta: dict, hands: Iterable[dict]) -> Dict[str, List[dict]]:
    """Every decision in one cached match, by the deciding seat's name: the situation, the action, the size bin."""
    names = {p["seat"]: p["name"] for p in match_meta["participants"]}
    out: Dict[str, List[dict]] = defaultdict(list)
    for h in hands:
        hole = h.get("hole_cards") or {}
        board_text = h.get("board") or ""
        board = [board_text[i:i + 2] for i in range(0, len(board_text), 2)]
        street, pot, street_in, raises = -1, 0, {}, 0
        for a in h.get("actions") or []:
            st = STREETS.index(a["phase"])
            if st != street:
                pot += sum(street_in.values()); street_in = {}; street = st; raises = 0
            seat, amount, kind = int(a.get("seat", 0)), int(a.get("amount") or 0), a["action"]
            if kind.startswith("post"):
                street_in[seat] = street_in.get(seat, 0) + amount
                continue
            other = max([v for s, v in street_in.items() if s != seat], default=0)
            mine = street_in.get(seat, 0)
            to_call, pot_now = max(0, other - mine), pot + sum(street_in.values())
            cards = hole.get(str(seat))
            if cards and len(board) >= BOARD_AT[st]:
                action = "fold" if kind == "fold" else ("raise" if kind == "raise" else "passive")
                size = size_bin(max(mine + amount - other, 0) / max(pot_now + to_call, 1)) if kind == "raise" else None
                out[names.get(seat, "?")].append({"street": st, "facing": to_call > 0, "raises": min(raises, 3),
                                                  "price": to_call / max(pot_now + to_call, 1),
                                                  "cards": cards, "board": board[:BOARD_AT[st]],
                                                  "action": action, "size": size})
            if kind == "raise":
                street_in[seat] = street_in.get(seat, 0) + amount; raises += 1
            elif kind == "call":
                street_in[seat] = street_in.get(seat, 0) + amount
    return out


def fit_table(bot: List[dict], field: List[dict], equity) -> dict:
    """The counts a copy plays from. `equity(decision)` gives the hand's strength for the bot's own decisions."""
    t = {"fine": defaultdict(lambda: [0, 0, 0]), "coarse": defaultdict(lambda: [0, 0, 0]),
         "priced": defaultdict(lambda: [0, 0, 0]), "field": defaultdict(lambda: [1, 1, 1]),
         "field_priced": defaultdict(lambda: [0, 0, 0]), "sizes": defaultdict(lambda: [0, 0, 0, 0]),
         "field_sizes": defaultdict(lambda: [1, 1, 1, 1])}
    for d in field:
        key = coarse_key(d["street"], d["facing"], d["raises"])
        pb = price_band(d["facing"], d.get("price", 0.0))
        t["field"][key][ACTIONS.index(d["action"])] += 1
        t["field_priced"][f"{key}|{pb}"][ACTIONS.index(d["action"])] += 1
        if d["size"] is not None:
            t["field_sizes"][f"{d['street']}|{int(d['facing'])}"][d["size"]] += 1
    for d in bot:
        key = coarse_key(d["street"], d["facing"], d["raises"])
        pb = price_band(d["facing"], d.get("price", 0.0))
        t["coarse"][key][ACTIONS.index(d["action"])] += 1
        t["priced"][f"{key}|{pb}"][ACTIONS.index(d["action"])] += 1
        t["fine"][f"{key}|{pb}|{band(equity(d))}"][ACTIONS.index(d["action"])] += 1
        if d["size"] is not None:
            t["sizes"][f"{d['street']}|{int(d['facing'])}"][d["size"]] += 1
    return {k: dict(v) for k, v in t.items()} | {"decisions": len(bot)}


def _pull(counts, prior: np.ndarray, weight: float = None) -> np.ndarray:
    c = np.asarray(counts, float)
    w = PRIOR_WEIGHT if weight is None else weight
    return (c + w * prior) / (c.sum() + w)


def action_distribution(table: dict, street: int, facing: bool, raises: int, equity: float,
                        price: float = 0.0) -> np.ndarray:
    """
    Fold, passive, raise. Each step pulls the next one's counts towards it: the field in this situation, the field at
    this price, the bot in this situation, the bot at this price, the bot at this price and hand strength. A table
    fitted before the price bands (no "priced") skips their two steps.
    """
    key = coarse_key(street, facing, raises)
    w = table.get("prior_weight")
    field = np.asarray(table["field"].get(key, [1, 1, 1]), float)
    p = field / field.sum()
    pb = price_band(facing, price)
    if "priced" in table:
        p = _pull(table["field_priced"].get(f"{key}|{pb}", [0, 0, 0]), p, w)
    p = _pull(table["coarse"].get(key, [0, 0, 0]), p, w)
    if "priced" in table and table.get("use_price", True):
        p = _pull(table["priced"].get(f"{key}|{pb}", [0, 0, 0]), p, w)
        return _pull(table["fine"].get(f"{key}|{pb}|{band(equity)}", [0, 0, 0]), p, w)
    if "priced" in table:
        # Price off: the band counts summed over the price bands, so the key is the one without the price.
        fine = np.zeros(3)
        for b in range(1 + len(PRICE_EDGES) + 1):
            fine += np.asarray(table["fine"].get(f"{key}|{b}|{band(equity)}", [0, 0, 0]), float)
        return _pull(fine, p, w)
    return _pull(table["fine"].get(f"{key}|{band(equity)}", [0, 0, 0]), p, w)


def choose_settings(bot_by_match: List[List[dict]], field: List[dict], equity) -> dict:
    """
    The price and back-off settings for one bot, chosen on its own training matches only: fit on their earlier half,
    score the later half, keep the best log-loss. On 8 Oct the price bands helped every bot with thousands of decisions
    and hurt Shadow's 234, and a stronger back-off did the reverse, so no one setting fits both.
    """
    import math
    if len(bot_by_match) < 4:
        return {"use_price": False, "prior_weight": 16.0}
    cut = len(bot_by_match) // 2
    early = [d for ds in bot_by_match[:cut] for d in ds]; late = [d for ds in bot_by_match[cut:] for d in ds]
    t = json.loads(json.dumps(fit_table(early, field, equity)))
    best = None
    for use_price in (True, False):
        for weight in (4.0, 16.0):
            t["use_price"], t["prior_weight"] = use_price, weight
            ll = sum(-math.log(max(action_distribution(t, d["street"], d["facing"], d["raises"], equity(d),
                                                       d.get("price", 0.0))[ACTIONS.index(d["action"])], 1e-4))
                     for d in late) / max(len(late), 1)
            if best is None or ll < best[0]:
                best = (ll, use_price, weight)
    return {"use_price": best[1], "prior_weight": best[2], "inner_logloss": round(best[0], 4)}


def size_distribution(table: dict, street: int, facing: bool) -> np.ndarray:
    key = f"{street}|{int(facing)}"
    field = np.asarray(table["field_sizes"].get(key, [1, 1, 1, 1]), float)
    own = np.asarray(table["sizes"].get(key, [0, 0, 0, 0]), float)
    return (own + PRIOR_WEIGHT * field / field.sum()) / (own.sum() + PRIOR_WEIGHT)


class DataCopy:
    """A duel opponent that plays a bot's own frequencies (see the module docstring)."""

    def __init__(self, table: dict, rng: np.random.Generator, samples: int = 150, name: str = "datacopy"):
        from chipzen.archetypes import ArchetypeStats
        self.table, self.rng, self.samples, self.kind = table, rng, samples, name
        self.stats = ArchetypeStats()
        self.profiles = None

    @classmethod
    def from_file(cls, path: str, rng: np.random.Generator) -> "DataCopy":
        with open(path) as handle:
            table = json.load(handle)
        return cls(table, rng, name=table.get("name", "datacopy"))

    def _equity(self, state: dict) -> float:
        import pokerbot_native as native
        from chipzen.bridge import parse_cards
        hole = [c.index for c in parse_cards(state["your_hole_cards"])]
        board = [c.index for c in parse_cards(state.get("board") or [])]
        return float(native.equity_vs_random(hole, board, self.samples, int(self.rng.integers(0, 2 ** 62))))

    @staticmethod
    def _raises_before(state: dict) -> int:
        phase = state.get("phase") or "preflop"
        return sum(1 for a in state.get("action_history") or [] if a.get("phase") == phase and a.get("action") == "raise")

    def decide(self, state: dict, valid: Sequence[str], seat: int) -> dict:  # noqa: ARG002 (the duel passes it)
        from chipzen.archetypes import Archetype
        self.stats.decisions += 1
        to_call = int(state["to_call"])
        street = len(state.get("board") or []) and BOARD_AT.index(len(state["board"]))
        pot = int(state.get("pot") or 0)
        p = action_distribution(self.table, street, to_call > 0, self._raises_before(state), self._equity(state),
                                to_call / max(pot + to_call, 1))
        # Only what the arena offers: no fold when nothing is faced (that is a check), no raise when none is legal.
        legal = np.array([("fold" in valid) and to_call > 0, True, "raise" in valid], float)
        p = p * legal
        if p.sum() <= 0:
            p = legal
        action = ACTIONS[int(self.rng.choice(3, p=p / p.sum()))]
        if action == "fold":
            return {"action": "fold", "params": {}}
        if action == "passive":
            return {"action": "check" if "check" in valid else "call", "params": {}}
        sizes = size_distribution(self.table, street, to_call > 0)
        fraction = SIZE_PLAY[int(self.rng.choice(4, p=sizes / sizes.sum()))]
        return Archetype._raise_to(state, fraction)


def match_meta(scout_dir: str) -> Dict[str, dict]:
    """
    Every cached match's time and seats: the season index (season_matches.json) merged with the scout's full index
    (index.json, by bot name with the bot's seat). The season index alone stops at the season it was built for, so a
    copy fitted on it alone missed every October match: Blueprint's copy was the bot before its 1 Oct change.
    """
    import os
    meta: Dict[str, dict] = {}
    season = os.path.join(scout_dir, "season_matches.json")
    if os.path.exists(season):
        meta.update(json.load(open(season)))
    full = os.path.join(scout_dir, "index.json")
    if os.path.exists(full):
        for bot, entries in json.load(open(full)).get("by_name", {}).items():
            for e in entries:
                m = meta.setdefault(e["id"], {"id": e["id"], "at": e.get("at") or "", "participants": []})
                if e.get("seat") is not None and all(p.get("name") != bot for p in m["participants"]):
                    m["participants"].append({"name": bot, "seat": e["seat"]})
    return meta


def build_table(name: str, scout_dir: str, until: Optional[str] = None, samples: int = 150,
                since: Optional[str] = None) -> dict:
    """The table for `name` from the scout cache, its matches up to `until` (an ISO time) if given."""
    import os
    import pokerbot_native as native
    from chipzen.bridge import parse_cards
    meta = match_meta(scout_dir)
    bot_by_match, field = [], []
    for mid, m in sorted(meta.items(), key=lambda kv: kv[1]["at"]):
        path = os.path.join(scout_dir, "hands", f"{mid}.json")
        if not os.path.exists(path) or (until and m["at"] > until) or (since and m["at"] < since):
            continue
        for seat_name, ds in scout_decisions(m, json.load(open(path))).items():
            if seat_name == name:
                bot_by_match.append(ds)
            else:
                field.extend(ds)
    cache: Dict[tuple, float] = {}

    def equity(d):
        key = (tuple(d["cards"]), tuple(d["board"]))
        if key not in cache:
            cache[key] = float(native.equity_vs_random([c.index for c in parse_cards(d["cards"])],
                                                       [c.index for c in parse_cards(d["board"])], samples, 3))
        return cache[key]
    table = fit_table([d for ds in bot_by_match for d in ds], field, equity)
    table.update(choose_settings(bot_by_match, field, equity))
    table["name"] = name
    table["until"], table["since"] = until, since
    return table
