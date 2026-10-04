"""
The opponent profile: its two measured triggers, the sequential and bankroll
variants behind flags, and the per-history counts kept for a later response.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chipzen.opponents import (EQUILIBRIUM_FOLD, MIN_OBSERVED, SEQ_MIN_OBSERVED,  # noqa: E402
                               Profiles, _upper_bound)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def profile(**flags):
    return Profiles("/nonexistent/opponents.json", **flags)


def test_the_fixed_trigger_waits_for_a_hundred_bets():
    p = profile()
    p.rows["x"] = {"bets_faced": 99, "folds": 5, "calls": 90, "raises": 4, "hands": 50}
    assert not p.never_folds("x")
    p.rows["x"]["bets_faced"] = 100
    assert p.never_folds("x")


def test_the_sequential_trigger_fires_when_the_interval_excludes_the_baseline():
    """
    Ten folds in forty bets: rate 0.25, upper bound 0.38, under the 0.40 an
    equilibrium folds at, so the read is separated and fires sixty bets early.
    Fourteen in forty: upper bound 0.50, not separated, so it waits.
    """
    p = profile(sequential=True)
    p.rows["x"] = {"bets_faced": SEQ_MIN_OBSERVED, "folds": 10, "calls": 25, "raises": 5, "hands": 30}
    assert _upper_bound(10, 40) < EQUILIBRIUM_FOLD
    assert p.never_folds("x")
    p.rows["x"]["folds"] = 14
    assert not p.never_folds("x")
    # Below the sequential floor nothing fires, however clear the rate.
    p.rows["x"].update(bets_faced=20, folds=0)
    assert not p.never_folds("x")
    # And the fixed rule is still there underneath.
    assert not profile().never_folds("x")


def test_the_sequential_trigger_also_covers_the_fold_or_raise_read():
    p = profile(sequential=True)
    p.rows["x"] = {"bets_faced": 60, "folds": 40, "calls": 2, "raises": 18, "hands": 30}
    assert p.never_calls("x")
    assert not profile().never_calls("x")          # 60 bets is under the fixed hundred


def test_the_bankroll_rule_blocks_exploits_while_we_are_behind():
    p = profile(bankroll=True)
    p.rows["x"] = {"bets_faced": 200, "folds": 10, "calls": 150, "raises": 40, "hands": 100, "net": -5000}
    assert not p.never_folds("x") and not p.never_calls("x")
    p.rows["x"]["net"] = 0
    assert p.never_folds("x")


def test_observe_counts_net_chips_and_every_opponent_action_by_public_history():
    p = profile()
    result = {"action_history": [
        {"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
        {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop"},
        {"seat": 0, "action": "raise", "amount": 300, "phase": "preflop"},
        {"seat": 1, "action": "call", "amount": 200, "phase": "preflop"},
        {"seat": 1, "action": "check", "amount": 0, "phase": "flop"},
        {"seat": 0, "action": "raise", "amount": 300, "phase": "flop"},
        {"seat": 1, "action": "fold", "amount": 0, "phase": "flop"},
    ]}
    p.observe(result, our_seat=0, opponent="x", net=+300)
    row = p.rows["x"]
    assert row["net"] == 300 and row["bets_faced"] == 2 and row["calls"] == 1 and row["folds"] == 1
    assert row["by_history"] == {"preflop:Ur": {"call": 1}, "flop:": {"check": 1}, "flop:TcUr": {"fold": 1}}


def test_rebuild_recovers_the_net_from_the_match_logs():
    """The rebuilt net must agree with the review's own accounting of a match."""
    from scripts.chipzen_review import hands_of, load, net
    logs = sorted(glob.glob(os.path.join(ROOT, "results", "chipzen", "matches", "*.jsonl")))
    if not logs:
        return
    path = logs[0]
    seat, opponent, hands, _ = hands_of(load(path))
    expected = sum(net(h, seat) for h in hands if h["result"])
    tmp = os.path.join(os.path.dirname(path), "..", "tmp_one_match")
    os.makedirs(tmp, exist_ok=True)
    link = os.path.join(tmp, os.path.basename(path))
    if not os.path.exists(link):
        os.symlink(os.path.abspath(path), link)
    try:
        p = profile().rebuild(tmp)
        assert p.rows[opponent]["net"] == expected
        assert p.rows[opponent]["by_history"]
    finally:
        os.remove(link)
        os.rmdir(tmp)


def test_rebuild_keeps_scouted_rows_as_the_prior(tmp_path):
    """A scouted row must survive the recount the bot does at start-up."""
    import json
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"stranger": {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50,
                                             "hands": 600, "net": 0, "by_history": {}, "scouted": True},
                                "old": {"bets_faced": 9, "folds": 1, "calls": 8, "raises": 0, "hands": 5}}))
    p = Profiles(str(path)).rebuild(str(tmp_path))         # no logs in tmp_path
    assert "stranger" in p.rows and p.rows["stranger"]["bets_faced"] == 500
    assert "old" not in p.rows                              # unscouted rows come only from logs
    assert p.never_folds("stranger")


def test_the_scouted_reads_need_the_flag_and_the_counts():
    row = {"bets_faced": 908, "folds": 688, "calls": 141, "raises": 79, "hands": 2053,
           "by_history": {"preflop:Ur": {"fold": 497, "call": 100, "raise": 34}},
           "river_bets": 63, "river_bluffs": 0, "scouted": True}
    off = profile(); off.rows["x"] = row
    assert not off.folds_blind("x") and not off.never_bluffs("x")
    on = profile(scout_reads=True); on.rows["x"] = row
    assert on.folds_blind("x") and on.never_bluffs("x")
    on.rows["y"] = {"bets_faced": 50, "folds": 40, "calls": 5, "raises": 5, "hands": 60,
                    "by_history": {"preflop:Ur": {"fold": 30, "call": 10}}, "river_bets": 10, "river_bluffs": 0}
    assert not on.folds_blind("y") and not on.never_bluffs("y")    # too few opens, too few bets


def test_the_sizing_tell_needs_both_halves():
    """Big bets never air AND small bets often air: tightness alone is not a tell."""
    on = profile(scout_reads=True)
    on.rows["poet"] = {"bets_faced": 966, "folds": 234, "calls": 581, "raises": 151, "hands": 1362,
                       "by_history": {}, "big_bets": 429, "big_bets_air": 0, "small_bets": 1080, "small_bets_air": 421}
    on.rows["nit"] = {"bets_faced": 900, "folds": 700, "calls": 150, "raises": 50, "hands": 2000,
                      "by_history": {}, "big_bets": 200, "big_bets_air": 2, "small_bets": 300, "small_bets_air": 10}
    assert on.big_bets_are_value("poet")
    assert not on.big_bets_are_value("nit")
    assert not profile().big_bets_are_value("poet")


def _match_log(directory, opponent="stranger", hands=3):
    """A minimal logged match: we raise preflop each hand and the opponent calls."""
    import json
    rows = [{"frame": "match_start", "seat": 0, "at": 1_800_000_000,
             "seats": [{"display_name": "us", "is_self": True}, {"display_name": opponent, "is_self": False}]}]
    for h in range(1, hands + 1):
        rows.append({"frame": "round_start", "state": {"stacks": [10000, 10000]}})
        rows.append({"frame": "round_result", "result": {"hand_number": h, "stacks": [10100, 9900], "action_history": [
            {"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
            {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop"},
            {"seat": 0, "action": "raise", "amount": 300, "phase": "preflop"},
            {"seat": 1, "action": "call", "amount": 200, "phase": "preflop"}]}})
    (directory / "m1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_every_start_counts_the_live_hands_once_not_once_more(tmp_path):
    """
    4 Oct: the rebuild started from the saved row, which already held the live
    hands, so each bot start added them again (Blueprint +2,916 hands a start
    with no new match). Three starts in a row must leave the row where one did.
    """
    import json
    logs = tmp_path / "logs"; logs.mkdir()
    _match_log(logs, hands=3)
    path = tmp_path / "opponents.json"
    base = {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50, "hands": 600, "net": 0,
            "by_history": {"preflop:Ur": {"call": 350}}, "scouted": True}
    path.write_text(json.dumps({"stranger": dict(base, scout_base=dict(base))}))
    seen = []
    for _ in range(3):
        p = Profiles(str(path)).rebuild(str(logs))
        p.save()
        row = p.rows["stranger"]
        seen.append((row["hands"], row["bets_faced"], row["calls"], row["net"], row["by_history"]["preflop:Ur"]["call"]))
    assert seen[0] == (603, 503, 353, 300, 353)               # the scout's counts plus the three live hands, once
    assert seen[1] == seen[0] and seen[2] == seen[0]
    assert Profiles(str(path)).rows["stranger"]["scout_base"]["hands"] == 600


def test_a_row_from_before_the_fix_stops_growing(tmp_path):
    """A saved row with no `scout_base` becomes its own base once, then holds still."""
    import json
    logs = tmp_path / "logs"; logs.mkdir()
    _match_log(logs, hands=2)
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"stranger": {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50,
                                             "hands": 600, "net": 0, "by_history": {}, "scouted": True}}))
    first = Profiles(str(path)).rebuild(str(logs)); first.save()
    second = Profiles(str(path)).rebuild(str(logs)); second.save()
    assert first.rows["stranger"]["hands"] == second.rows["stranger"]["hands"] == 602
    assert second.rows["stranger"]["scout_base"]["hands"] == 600
