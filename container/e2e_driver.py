"""
The upload's side of container/e2e.py: runs inside a copy of container/upload/ with the slim venv, so
only what the zip carries can be imported. Reads one turn per line as the server would send it, builds
the SDK's GameState from it with the SDK's own parser, asks main.NashForge, and writes the action back.
"""
import json
import sys

sys.path.insert(0, ".")
from chipzen.models import GameState  # noqa: E402

# The bot seeds nothing, as it should in play; for the shadow comparison both sides draw from the same
# seed, so reading an off-tree bet (a random choice between neighbouring sizes) comes out alike.
import numpy as np  # noqa: E402
_default_rng = np.random.default_rng
np.random.default_rng = lambda seed=None: _default_rng(int(sys.argv[1]) if seed is None and len(sys.argv) > 1 else seed)
import main  # noqa: E402

bot = main.NashForge()
np.random.default_rng = _default_rng
for line in sys.stdin:
    msg = json.loads(line)
    state = GameState.from_turn_request({"state": msg["state"], "valid_actions": msg["valid"]}, your_seat=msg["seat"])
    action = bot.decide(state)
    sys.stdout.write(json.dumps({"action": action.action, "amount": action.amount}) + "\n")
    sys.stdout.flush()

# Peak memory of this process, the packaged bot's, for the 256 MB cap (read from /proc: test code only).
with open("/proc/self/status") as status:
    peak = [line for line in status if line.startswith("VmHWM")][0].split()[1]
sys.stderr.write(f"packaged bot peak resident: {int(peak) // 1024} MB\n")
