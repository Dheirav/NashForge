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
#: Calls as a share of the opponent's non-fold answers below which it is a
#: fold-or-raise bot whose raises mean it. Measured 14 September: Blueprint
#: 0.34 (38 calls, 73 raises), the three bots that call us down 0.81 to 0.90.
CALL_FLOOR = 0.5

#: The sequential trigger (opt in, `Profiles(sequential=True)`): act as soon as
#: the 95 percent interval of the observed rate excludes the equilibrium-ish
#: baseline, from SEQ_MIN_OBSERVED bets on, rather than waiting for a fixed
#: hundred. Binomial arithmetic on 15 September: separating a 25 percent
#: folder from a 45 percent one at power 0.8 needs 45 bets, and 15 percent
#: needs 19, so the hundred was two to four times more than the evidence
#: required. The baselines are what a heads-up equilibrium does against a bet.
SEQ_MIN_OBSERVED = 40
#: The scouted reads' thresholds (see `folds_blind`, `never_bluffs`).
FOLD_BLIND_MIN = 100
FOLD_BLIND_RATE = 0.70
NEVER_BLUFF_MIN = 40
NEVER_BLUFF_RATE = 0.05
THREE_BET_MIN = 25
THREE_BET_FOLD_RATE = 0.75
BIG_BET_MIN = 100
BIG_BET_AIR_RATE = 0.05
SMALL_BET_AIR_RATE = 0.20
EQUILIBRIUM_FOLD = 0.40
EQUILIBRIUM_CALL_SHARE = 0.5


def _private_overrides() -> dict:
    """
    Tuned thresholds from outside the repository.

    The values above are the documented defaults and the reasoning behind
    them. The numbers the live bot plays with are the exploitable part of it:
    a rival who knows we fold to river bets from anyone profiled as never
    bluffing can bluff us once it has built that profile. So, like the solved
    strategies, the tuned values live outside the public tree, in
    `~/.chipzen/reads.toml` (`[thresholds]`, upper-case keys as here), and
    override the defaults at import. Absent file, defaults; unknown key, an
    error, so a typo cannot silently leave a read on its default.
    """
    path = os.environ.get("CHIPZEN_READS") or os.path.expanduser("~/.chipzen/reads.toml")
    if not os.path.exists(path):
        return {}
    import tomllib
    with open(path, "rb") as handle:
        table = tomllib.load(handle).get("thresholds", {})
    known = {k for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}
    unknown = set(table) - known
    if unknown:
        raise ValueError(f"{path}: unknown threshold(s) {sorted(unknown)}; known: {sorted(known)}")
    return table


globals().update(_private_overrides())


def _upper_bound(successes: int, trials: int) -> float:
    """Upper end of the 95 percent Wald interval of a rate."""
    if trials <= 0:
        return 1.0
    rate = successes / trials
    return rate + 1.96 * (rate * (1.0 - rate) / trials) ** 0.5


class Profiles:
    """Per-opponent counts, persisted as JSON, rebuilt from match logs."""

    def __init__(self, path: str, sequential: bool = False, bankroll: bool = False,
                 scout_reads: bool = False):
        self.path = path
        #: The two reads that need the scout's counts (`scripts/chipzen_scout.py`):
        #: a big blind that folds to most opens, and a bot whose river bets are
        #: never bluffs. Off by default; measured on thousands of decisions with
        #: both players' cards, 15 September.
        self.scout_reads = scout_reads
        #: Sequential triggers, see SEQ_MIN_OBSERVED. Off by default.
        self.sequential = sequential
        #: Risk what you have won (Ganzfried and Sandholm 2015): with this on,
        #: an exploit fires only while our net against that opponent is not
        #: negative, so a wrong read cannot keep costing chips. Off by default.
        self.bankroll = bankroll
        self.rows: Dict[str, Dict] = {}
        if os.path.exists(path):
            with open(path) as handle:
                self.rows = json.load(handle)

    def _row(self, name: str) -> Dict:
        row = self.rows.setdefault(name, {"bets_faced": 0, "folds": 0, "calls": 0,
                                          "raises": 0, "hands": 0})
        row.setdefault("net", 0)
        row.setdefault("by_history", {})
        return row

    def observe(self, result: dict, our_seat: int, opponent: str, net: int = 0) -> None:
        """
        Count the opponent's answers to our bets in one finished hand, our net
        chips from it, and every action of theirs by the public history it was
        taken at.

        `by_history` is the raw material for a data-biased response (Johanson
        and Bowling 2009): a frequency model per public history, mixed with
        the equilibrium as a prior. The key is the street and the letters of
        the actions so far on it, U for ours and T for theirs, so "flop:UrTc"
        is the opponent acting after our raise and their call. Counts only;
        nothing reads them yet.
        """
        row = self._row(opponent)
        row["hands"] += 1
        row["net"] += int(net)
        previous = None
        street = None
        letters = ""
        for action in result.get("action_history") or []:
            if action["action"].startswith("post"):
                continue
            if action["phase"] != street:
                street, previous, letters = action["phase"], None, ""
            kind = action["action"]
            if action["seat"] != our_seat:
                node = row["by_history"].setdefault(f"{street}:{letters}", {})
                node[kind] = node.get(kind, 0) + 1
                if previous == "raise":
                    row["bets_faced"] += 1
                    row["folds" if kind == "fold" else ("raises" if kind == "raise" else "calls")] += 1
            letters += ("U" if action["seat"] == our_seat else "T") + kind[0]
            previous = kind if action["seat"] == our_seat else None

    def folds_blind(self, name: Optional[str]) -> bool:
        """
        A big blind that folds to at least FOLD_BLIND_RATE of opens over
        FOLD_BLIND_MIN of them. mellyy, scouted: 497 of 631, flat with depth
        and size; each fold is a blind won by a minimum raise.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:Ur", {})
        n = sum(node.values())
        return n >= FOLD_BLIND_MIN and node.get("fold", 0) / n >= FOLD_BLIND_RATE

    def never_bluffs(self, name: Optional[str]) -> bool:
        """
        River bets that were bluffs (under half equity against a random hand)
        in fewer than NEVER_BLUFF_RATE of at least NEVER_BLUFF_MIN river bets.
        runner1, scouted: 0 of 63; its minimum postflop betting equity was 0.58.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "") or {}
        bets = row.get("river_bets", 0)
        return bets >= NEVER_BLUFF_MIN and row.get("river_bluffs", 0) / bets < NEVER_BLUFF_RATE

    def folds_to_three_bet(self, name: Optional[str]) -> bool:
        """
        Folds to at least THREE_BET_FOLD_RATE of three-bets over THREE_BET_MIN of
        them: the public history "they open, we re-raise, they act". mellyy,
        scouted: 25 of 29. A small three-bet breaks even at about 67 percent.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:TrUr", {})
        n = sum(node.values())
        return n >= THREE_BET_MIN and node.get("fold", 0) / n >= THREE_BET_FOLD_RATE

    def big_bets_are_value(self, name: Optional[str]) -> bool:
        """
        A sizing tell: first bets of 0.7 pot and up that were air (under 0.4
        equity) in fewer than BIG_BET_AIR_RATE of at least BIG_BET_MIN, while
        the small bets were air often enough (SMALL_BET_AIR_RATE) that the split
        is a tell and not tightness. PoetAndCoder, scouted: 0 of 429 big, 39
        percent of 1,080 small.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "") or {}
        big, small = row.get("big_bets", 0), row.get("small_bets", 0)
        return big >= BIG_BET_MIN and row.get("big_bets_air", 0) / big < BIG_BET_AIR_RATE \
            and small >= BIG_BET_MIN and row.get("small_bets_air", 0) / small >= SMALL_BET_AIR_RATE

    def exploits_allowed(self, name: Optional[str]) -> bool:
        """With the bankroll rule on, only while we are not behind against them."""
        if not self.bankroll:
            return True
        row = self.rows.get(name or "")
        return bool(row) and row.get("net", 0) >= 0

    def fold_to_bet(self, name: Optional[str]) -> Tuple[Optional[float], int]:
        """(rate, bets observed); rate is None until MIN_OBSERVED bets."""
        row = self.rows.get(name or "")
        if not row or row["bets_faced"] < MIN_OBSERVED:
            return None, (row or {}).get("bets_faced", 0)
        return row["folds"] / row["bets_faced"], row["bets_faced"]

    def never_folds(self, name: Optional[str]) -> bool:
        if not self.exploits_allowed(name):
            return False
        if self.sequential:
            row = self.rows.get(name or "")
            if row and row["bets_faced"] >= SEQ_MIN_OBSERVED and \
                    _upper_bound(row["folds"], row["bets_faced"]) < EQUILIBRIUM_FOLD:
                return True
        rate, _ = self.fold_to_bet(name)
        return rate is not None and rate < FOLD_FLOOR

    def never_calls(self, name: Optional[str]) -> bool:
        """
        A fold-or-raise opponent: it answers a bet by folding or raising and
        almost never by calling. Against `Blueprint` on 14 September (1,005
        folds, 322 raises, 39 calls) every big pot lost was a call of its
        all-in with a hand that was not the best; a bot like that only raises
        when it has it, so a shove from it is answered by the top strength
        class alone.
        """
        if not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "")
        if not row:
            return False
        answered = row["calls"] + row["raises"]
        if self.sequential and answered >= SEQ_MIN_OBSERVED // 2 and \
                _upper_bound(row["calls"], answered) < EQUILIBRIUM_CALL_SHARE:
            return True
        if row["bets_faced"] < MIN_OBSERVED:
            return False
        return answered >= 40 and row["calls"] / answered < CALL_FLOOR

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(self.rows, handle, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def rebuild(self, *dirs: str) -> "Profiles":
        """
        Recount from every match log, so the file is never the only copy.

        Rows marked `scouted` (written by `scripts/chipzen_scout.py` from the
        platform's records of a bot's matches against others) are kept as the
        starting point, and live hands accumulate on top of them: a round-robin
        meets each opponent once, so a read that starts at hand one is the
        only kind that helps.
        """
        self.rows = {name: row for name, row in self.rows.items() if row.get("scouted")}
        seen = set()
        for directory in dirs:
            for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
                if os.path.basename(path) in seen:
                    continue
                seen.add(os.path.basename(path))
                seat, opponent, before = None, None, None
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
                        elif frame.get("frame") == "round_start":
                            before = (frame.get("state") or {}).get("stacks")
                        elif frame.get("frame") == "round_result" and seat is not None and opponent:
                            result = frame["result"]
                            after = result.get("stacks")
                            net = after[seat] - before[seat] if before and after else 0
                            self.observe(result, seat, opponent, net)
        return self
