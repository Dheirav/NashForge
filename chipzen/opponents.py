"""
What each opponent does when we bet, counted from the arena's own records.

The arena's argument is that exploitation is where its field is beaten. This
project's solver has no opponent model at all: it plays one strategy against
everyone. This module is the smallest honest step toward one: a count, per
opponent, of how they answer our bets, kept across matches, and a single
adjustment with a measured trigger.

The adjustment: **do not bluff a bot that does not fold.** Against `mr_hide`
on 13 September (folded 5 times in 25 hands, called 31, raised 27) the bot lost
three matches and nine of eleven showdowns, several of them river bluffs and
thin bets into a hand that was never folding. When an opponent's fold-to-bet
rate over at least MIN_OBSERVED bets is below FOLD_FLOOR, a raise the solver
chose with a weak hand becomes a check or call instead. Value bets are left
alone: the strength threshold is on the hand, not on the action.

Nothing is guessed from a few hands. Below MIN_OBSERVED bets the profile is
"unknown" and the solver plays as it would against anyone.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, Optional, Tuple

#: Bets faced before a fold rate is believed. A hundred is a week of matches
#: against one bot, and roughly the sample at which a 25% rate is separated
#: from 40% at two standard errors.
MIN_OBSERVED = 100
#: Fold-to-bet below which bluffing is pointless. An equilibrium heads-up
#: strategy folds to a bet somewhere around 40% of the time; a bot under a
#: quarter is calling with everything.
FOLD_FLOOR = 0.25


class Profiles:
    """Per-opponent counts, persisted as JSON, rebuilt from match logs."""

    def __init__(self, path: str):
        self.path = path
        self.rows: Dict[str, Dict[str, int]] = {}
        if os.path.exists(path):
            with open(path) as handle:
                self.rows = json.load(handle)

    def _row(self, name: str) -> Dict[str, int]:
        return self.rows.setdefault(name, {"bets_faced": 0, "folds": 0, "calls": 0,
                                           "raises": 0, "hands": 0})

    def observe(self, result: dict, our_seat: int, opponent: str) -> None:
        """Count the opponent's answers to our bets in one finished hand."""
        row = self._row(opponent)
        row["hands"] += 1
        previous = None
        street = None
        for action in result.get("action_history") or []:
            if action["action"].startswith("post"):
                continue
            if action["phase"] != street:
                street, previous = action["phase"], None
            if action["seat"] != our_seat and previous == "raise":
                row["bets_faced"] += 1
                kind = action["action"]
                row["folds" if kind == "fold" else ("raises" if kind == "raise" else "calls")] += 1
            previous = action["action"] if action["seat"] == our_seat else None

    def fold_to_bet(self, name: Optional[str]) -> Tuple[Optional[float], int]:
        """(rate, bets observed); rate is None until MIN_OBSERVED bets."""
        row = self.rows.get(name or "")
        if not row or row["bets_faced"] < MIN_OBSERVED:
            return None, (row or {}).get("bets_faced", 0)
        return row["folds"] / row["bets_faced"], row["bets_faced"]

    def never_folds(self, name: Optional[str]) -> bool:
        rate, _ = self.fold_to_bet(name)
        return rate is not None and rate < FOLD_FLOOR

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(self.rows, handle, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def rebuild(self, *dirs: str) -> "Profiles":
        """Recount from every match log, so the file is never the only copy."""
        self.rows = {}
        seen = set()
        for directory in dirs:
            for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
                if os.path.basename(path) in seen:
                    continue
                seen.add(os.path.basename(path))
                seat, opponent = None, None
                with open(path) as handle:
                    for line in handle:
                        try:
                            frame = json.loads(line)
                        except ValueError:
                            continue
                        if frame.get("frame") == "match_start":
                            seat = frame.get("seat")
                            opponent = next((s.get("display_name") for s in frame.get("seats") or []
                                             if not s.get("is_self")), None)
                        elif frame.get("frame") == "round_result" and seat is not None and opponent:
                            self.observe(frame["result"], seat, opponent)
        return self
