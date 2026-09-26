"""
The brief is only worth reading if it cannot miss a read and would have
flagged the two matches it was built after. Each test is one of those.
"""
import importlib.util
import os

from chipzen.opponents import Profiles

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
spec = importlib.util.spec_from_file_location("opponent_brief", os.path.join(ROOT, "scripts", "opponent_brief.py"))
ob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ob)


def _profiles(rows):
    p = Profiles("/nonexistent/opponents.json", sequential=True, scout_reads=True)
    p.rows = rows
    return p


def _bot(**extra):
    row = {"bets_faced": 200, "folds": 80, "calls": 60, "raises": 60, "hands": 500, "net": 0, "by_history": {}}
    row.update(extra)
    return row


def test_every_read_in_the_player_is_registered():
    """A read the brief does not know about is a read nobody checked before it played."""
    assert ob.player_read_names() - ob.registered_names() == set()
    assert ob.player_read_names(), "found no reads in chipzen/player.py; the pattern has drifted"


def test_the_shadow_case_is_a_conflict():
    """A fold-or-raise bot whose big bets are 30% air: the read's premise is contradicted."""
    shadow = _bot(folds=120, calls=15, raises=65, big_bets=260, big_bets_air=79)
    text = ob.brief("Shadow", _profiles({"Shadow": shadow}))
    assert "### shove call declined  (CONFLICT)" in text


def test_blueprint_like_big_bets_pass_and_missing_ones_are_unmeasured():
    honest = _bot(folds=120, calls=15, raises=65, big_bets=200, big_bets_air=2)
    assert "### shove call declined  (OK)" in ob.brief("Honest", _profiles({"Honest": honest}))
    unknown = _bot(folds=120, calls=15, raises=65)
    assert "### shove call declined  (UNMEASURED)" in ob.brief("Unknown", _profiles({"Unknown": unknown}))


def test_the_wsp_case_is_an_outlier():
    """A three-bet rate below every other bot on file is reported, with its rank."""
    rows = {f"bot{i}": _bot(by_history={"preflop:Ur": {"call": 60, "fold": 40 - i, "raise": 10 + 4 * i}})
            for i in range(8)}
    rows["wsp"] = _bot(by_history={"preflop:Ur": {"call": 217, "fold": 170, "raise": 5}})
    found = {o[1]: o for o in ob.outliers(rows, "wsp", firing=set())}
    assert "three-bets our open" in found
    assert found["three-bets our open"][-1] == "below all 8"


def test_a_street_where_it_folds_is_a_conflict_for_bluff_withheld():
    """Pooled, it never folds; on the river it folds three times in four (Fold-ver-3)."""
    row = _bot(folds=30, calls=150, raises=20,
               by_history={"flop:Ur": {"fold": 10, "call": 90}, "river:Ur": {"fold": 74, "call": 26}})
    text = ob.brief("F3", _profiles({"F3": row}))
    assert "### bluff withheld  (CONFLICT)" in text


def test_wilson():
    lo, hi = ob.wilson(0, 463)
    assert lo == 0.0 and 0.005 < hi < 0.01
    assert ob.wilson(0, 0) == (0.0, 1.0)
