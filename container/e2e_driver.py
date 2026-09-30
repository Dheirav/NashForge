"""
The upload's side of container/e2e.py: runs inside a copy of container/upload/ with the slim venv, so
only what the zip carries can be imported. Reads one turn per line as the server would send it, builds
the SDK's GameState from it with the SDK's own parser, asks main.NashForge, and writes the action back.
"""
import json
import sys
import time

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
# The harness names the opponent and, for a read test, hands over its profile file (already trimmed).
if len(sys.argv) > 2:
    from nfarena.opponents import Profiles
    bot.player.opponent = sys.argv[2]
    if len(sys.argv) > 3:
        bot.player.profiles = Profiles(sys.argv[3], sequential=True, scout_reads=True)
for line in sys.stdin:
    msg = json.loads(line)
    state = GameState.from_turn_request({"state": msg["state"], "valid_actions": msg["valid"]}, your_seat=msg["seat"])
    started = time.perf_counter()
    action = bot.decide(state)
    took = (time.perf_counter() - started) * 1000
    decided = globals().setdefault("decided", [])
    decided.append(took)
    if len(decided) <= 3:
        sys.stderr.write(f"decide() inside the container, decision {len(decided)}: {took:.1f} ms\n")
    sys.stdout.write(json.dumps({"action": action.action, "amount": action.amount}) + "\n")
    sys.stdout.flush()

# Peak memory of this process, the packaged bot's, for the 256 MB cap (read from /proc: test code only).
with open("/proc/self/status") as status:
    peak = [line for line in status if line.startswith("VmHWM")][0].split()[1]
sys.stderr.write(f"packaged bot peak resident: {int(peak) // 1024} MB; decide() max {max(decided):.1f} ms "
                 f"over {len(decided):,} decisions\n")
