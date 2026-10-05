"""
A set of arena-shaped matches where both strategies are known, to check that AIVAT is unbiased.

    venv/bin/python scripts/aivat_sim.py --matches 300 --out /tmp/aivat_sim --progress /tmp/aivat_sim.progress

On the real logs nothing can say whether the AIVAT mean is right, because the true win rate is unknown. Here the
logs are written by a dealer with the arena's rules (scripts/chipzen_duel.Dealer: its blinds, its history format)
between two scripted bots, so the check is direct: the control terms must average zero, within their own standard
error, and the AIVAT mean must agree with the raw one. Our seat plays a mixed strategy whose distribution is a fixed
function of the cards (a softmax on a seeded equity estimate) and is written into each decision row as `probs`, so
the decision terms are exercised too; the real bursts are purified and have none. The opponent is a scripted
archetype whose play depends strongly on its cards, which is what would expose the one approximation in the chance
terms, taking the expectation over cards the opponent may be holding.

The logs land in --out in chipzen.client's format, label "sim", so scripts/chipzen_decompose.py reads them as it
reads a burst.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.equity import FULL_DECK  # noqa: E402
from chipzen.archetypes import Archetype  # noqa: E402
from scripts.chipzen_duel import ARENA_STACK, Dealer, arena_big_blind  # noqa: E402

RAISE_FRACTIONS = (0.5, 1.0, 2.0)


def _s(cards):
    return [str(FULL_DECK[c]) for c in cards]


class MixedHero:
    """
    Our seat: a softmax over the six abstract actions on an equity estimate, sampled, and logged with its odds.

    The equity is the native sampler seeded by the cards, so the distribution is a fixed function of what this seat
    can see, which is what makes it "known". It is not meant to be good, only to mix and to depend on its cards.
    """

    def __init__(self, rng, log_seat, opponent, temperature=0.08):
        self.rng = rng
        self.log_seat = log_seat
        self.opponent = opponent
        self.temperature = temperature
        self.rows = []
        self.hand = 0

    def probs(self, e, to_call, pot, legal):
        price = to_call / (pot + to_call) if to_call > 0 else 0.0
        u = np.array([0.0, e - price, e - 0.58, e - 0.62, e - 0.68, e - 0.78])
        z = np.where(legal > 0, u / self.temperature, -np.inf)
        p = np.exp(z - z.max())
        return p / p.sum()

    def decide(self, state, valid, seat):  # noqa: ARG002 (the dealer passes its own index)
        import pokerbot_native as native
        hole = [_index(c) for c in state["your_hole_cards"]]
        board = [_index(c) for c in state["board"]]
        seed = sum(c * 53 ** i for i, c in enumerate(sorted(hole) + sorted(board))) % (2 ** 61)
        e = float(native.equity_vs_random(hole, board, 400, seed))
        to_call, pot = int(state["to_call"]), int(state["pot"])
        legal = np.zeros(6)
        legal[0] = 1.0 if "fold" in valid else 0.0
        legal[1] = 1.0
        if "raise" in valid:
            legal[2:6] = 1.0
        p = self.probs(e, to_call, pot, legal)
        choice = int(self.rng.choice(6, p=p))
        high, low = int(state["max_raise"]), int(state["min_raise"])
        committed = high - int(state["your_stack"])
        if choice == 0:
            sent = {"action": "fold", "params": {}}
        elif choice == 1:
            sent = {"action": "check" if to_call <= 0 else "call", "params": {}}
        elif choice == 5:
            sent = {"action": "raise", "params": {"amount": high}}
        else:
            level = committed + to_call + int(round((pot + to_call) * RAISE_FRACTIONS[choice - 2]))
            sent = {"action": "raise", "params": {"amount": min(high, max(low, level))}}
        bb = max((a["amount"] for a in state["action_history"] if a["action"] == "post_big_blind"), default=100)
        eff = min(int(state["your_stack"]) + committed, int(state["opponent_stacks"][0]) + to_call + committed)
        self.rows.append({"frame": "decision", "hand": self.hand, "phase": state["phase"], "seat": self.log_seat,
                          "hole": state["your_hole_cards"], "board": state["board"], "pot": pot, "to_call": to_call,
                          "history": "", "effective_bb": eff / bb, "solver": "100bb" if eff / bb >= 40 else "12bb",
                          "miss": False, "companion": None, "fallback": False, "adjusted": None,
                          "opponent": self.opponent, "legal": [int(x) for x in legal], "choice": choice,
                          "probs": [float(x) for x in p], "sent": sent})
        return sent


def _index(card):
    from evaluation.aivat import card_index
    return card_index(card)


def play_logged_match(match_id, kind, rng, hero_seat):
    """One match to a bust (or 400 hands), as the JSONL chipzen.client writes."""
    hero = MixedHero(np.random.default_rng(rng.integers(2 ** 62)), hero_seat, kind)
    villain = Archetype(kind, np.random.default_rng(rng.integers(2 ** 62)))
    by_seat = {hero_seat: hero, 1 - hero_seat: villain}
    rows = [{"frame": "match_start", "seat": hero_seat, "match_id": match_id, "at": 0.0,
             "version": {"label": f"sim: mixed hero against {kind}"}, "rated": False}]
    stacks = [ARENA_STACK, ARENA_STACK]
    deck = np.arange(52)
    hand = 0
    while min(stacks) > 0 and hand < 400:
        hand += 1
        hero.hand = hand
        bb = arena_big_blind(hand)
        rng.shuffle(deck)
        cards = [int(c) for c in deck[:9]]
        # Odd hands: log seat 0 posts the small blind, which the dealer always seats at index 0.
        order = [0, 1] if hand % 2 == 1 else [1, 0]
        dealer = Dealer([by_seat[order[0]], by_seat[order[1]]], cards, [stacks[order[0]], stacks[order[1]]],
                        bb // 2, bb, hand, (None, None))
        hero_hole = dealer.hole[order.index(hero_seat)]
        # The opponent's cards are written for the card-removal check only; nothing the estimator reads uses them.
        rows.append({"frame": "round_start", "state": {"hand_number": hand, "your_hole_cards": _s(hero_hole),
                                                        "stacks": list(stacks),
                                                        "sim_opponent_hole": _s(dealer.hole[1 - order.index(hero_seat)])}})
        start = len(hero.rows)
        net_d = dealer.play()
        rows.extend(hero.rows[start:])
        net = [0, 0]
        for i, s in enumerate(order):
            net[s] = net_d[i]
        history = [dict(a, seat=order[a["seat"]], is_timeout=False) for a in dealer.history]
        if dealer.folded is None:
            showdown = [{"seat": order[i], "hole_cards": _s(dealer.hole[i]), "best_hand": _s(dealer.board_cards)}
                        for i in (0, 1)]
        else:
            w = 1 - dealer.folded
            showdown = [{"seat": order[w], "hole_cards": _s(dealer.hole[w])}]
        stacks = [stacks[0] + net[0], stacks[1] + net[1]]
        rows.append({"frame": "round_result", "result": {"hand_number": hand, "action_history": history,
                                                         "showdown": showdown, "stacks": list(stacks)}})
    return rows


def removal_bias(paths, vf, limit=None, progress=None):
    """
    The one approximation in the chance terms, measured exactly where the opponent's cards are known.

    A turn or river term takes its expectation over every card we have not seen, n of them, while the card really
    came from the n - 2 the opponent is not holding. Since E over all n of the next equity is the equity now, the
    true expectation differs from ours by (2 * equity now - eq(h + o1) - eq(h + o2)) / (n - 2), times the street's g;
    that is the term's bias on this hand, and its mean over hands is the bias of the estimator. The flop's version
    would need the equity of all 1,176 flops through each opposing card, so it is left out.
    """
    from evaluation.aivat import BOARD_AT, card_index, trace_hand
    out = {"turn": [], "river": []}
    started, seen = time.time(), 0
    for path in paths:
        with open(path) as handle:
            rows = [json.loads(line) for line in handle]
        seat = rows[0]["seat"]
        decisions = {}
        for r in rows:
            if r.get("frame") == "decision":
                decisions.setdefault(r["hand"], []).append(r)
        start = None
        for r in rows:
            if r.get("frame") == "round_start":
                start = r["state"]
            elif r.get("frame") == "round_result" and start and decisions.get(r["result"]["hand_number"]):
                res = r["result"]
                t = trace_hand(res, start["stacks"], decisions[res["hand_number"]], seat, start["your_hole_cards"])
                opp = [card_index(c) for c in start["sim_opponent_hole"]]
                previous = None
                for node in t["chance"]:
                    board = node["board"]
                    if board is None or len(board) != BOARD_AT[node["street"]]:
                        break
                    if node["street"] in out and previous is not None:
                        eq_now = vf.equity(t["hole"], previous)
                        n = 52 - 2 - len(previous)
                        gap = (2 * eq_now - sum(vf.equity(t["hole"], previous + [o]) for o in opp)) / (n - 2)
                        out[node["street"]].append(vf.scale(node["street"], node["pot"], node["eff"]) * gap)
                    previous = board
                seen += 1
                if progress and seen % 200 == 0:
                    elapsed = time.time() - started
                    with open(progress, "w") as handle:
                        handle.write(f"{seen} of {limit or '?'} hands checked, elapsed {elapsed / 60:.1f} min"
                                     + (f", ETA {elapsed / seen * (limit - seen) / 60:.1f} min" if limit else "") + "\n")
                if limit and seen >= limit:
                    return out
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matches", type=int, default=300)
    parser.add_argument("--opponents", nargs="+", default=["foldraise", "station", "maniac"])
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--out", required=True)
    parser.add_argument("--progress", help="rewritten after every match: done, total, elapsed, ETA")
    parser.add_argument("--removal-check", type=int, metavar="HANDS",
                        help="instead of simulating, measure the card-removal bias of the turn and river terms on "
                             "the first HANDS decision hands already in --out")
    args = parser.parse_args()
    if args.removal_check:
        import glob
        from evaluation.aivat import ValueFunction
        out = removal_bias(sorted(glob.glob(os.path.join(args.out, "*.jsonl"))), ValueFunction.load(),
                           args.removal_check, args.progress)
        for street, x in out.items():
            x = np.array(x)
            print(f"{street}: {x.size} terms, card-removal bias {x.mean():+.2f} ± {x.std() / np.sqrt(x.size):.2f} "
                  f"chips per term (sd {x.std():.1f}, largest {np.abs(x).max():.0f})")
        return
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    start = time.time()
    for k in range(args.matches):
        kind = args.opponents[k % len(args.opponents)]
        rows = play_logged_match(f"sim-{k:05d}", kind, rng, hero_seat=k % 2)
        with open(os.path.join(args.out, f"sim-{k:05d}.jsonl"), "w") as handle:
            handle.write("\n".join(json.dumps(r) for r in rows) + "\n")
        if args.progress:
            elapsed = time.time() - start
            with open(args.progress, "w") as handle:
                handle.write(f"{k + 1} of {args.matches} matches simulated, elapsed {elapsed / 60:.1f} min, ETA "
                             f"{elapsed / (k + 1) * (args.matches - k - 1) / 60:.1f} min at the measured rate\n")
    print(f"wrote {args.matches} matches to {args.out} in {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
