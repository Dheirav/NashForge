"""
The reads' tuned thresholds live outside the repository (chipzen/opponents.py,
`_private_overrides`); the module must load the file when it exists, refuse a
key it does not know, and fall back to its documented defaults otherwise.
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _reload(monkeypatch, path):
    monkeypatch.setenv("CHIPZEN_READS", path)
    import chipzen.opponents as opponents
    return importlib.reload(opponents)


def test_the_private_file_overrides_a_threshold_and_a_typo_is_refused(tmp_path, monkeypatch):
    good = tmp_path / "reads.toml"
    good.write_text("[thresholds]\nNEVER_BLUFF_RATE = 0.03\nMIN_OBSERVED = 120\n")
    module = _reload(monkeypatch, str(good))
    assert module.NEVER_BLUFF_RATE == 0.03 and module.MIN_OBSERVED == 120
    bad = tmp_path / "bad.toml"
    bad.write_text("[thresholds]\nNEVER_BLUF_RATE = 0.03\n")
    with pytest.raises(ValueError, match="unknown threshold"):
        _reload(monkeypatch, str(bad))
    module = _reload(monkeypatch, str(tmp_path / "absent.toml"))
    assert module.NEVER_BLUFF_RATE == 0.05 and module.MIN_OBSERVED == 100
