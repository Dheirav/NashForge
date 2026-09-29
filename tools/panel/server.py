"""
NashForge's control panel: the arena operations done so far by hand, behind a local web page.

    ~/Code/PokerBot/venv/bin/python tools/panel/server.py          # then open http://localhost:8765

Four tabs. Dashboard: the next fixture with a countdown, every fixture's state (armed, not armed, died), the timers
with the set each will play, memory, the challenge quota (shared by every bot on the account; fixtures exempt),
lobby hours, running jobs. Fixtures: arm (dry run, then the timer: `arm_fixture.sh`) and disarm. Scout: the paced
scout and the profiles it writes. Choose a set: fit a copy of an opponent and play sets against it.

Every action runs a script this project already uses, as a background job with its own log and exit status. The
wrapped scripts are not edited here: two timers were running from them when this was written, and bash reads a
running script from disk as it goes.

Safety, as the 29 Sept review asked:
- Requests are served only for Host localhost/127.0.0.1 (DNS rebinding) and actions need the page's token.
- Arming never runs a dry run inside another timer's window: a dry run ends by stopping "the bot", and inside a
  live fixture's window that bot is the fixture's (a walkover). One arm at a time; a fixture is keyed by opponent
  and slot; the set is copied at arm time to frozen/ and the timer plays the copy, so editing a set file later
  cannot change a fixture (fixture2.sh reads its set only at connect time).
- Heavy jobs are refused inside a fixture's quiet window, from 30 minutes before its connect until it has stopped.
Standard library only.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import http.server
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import threading
import time
import tomllib
import urllib.request

HOME = os.path.expanduser("~")
MAIN = f"{HOME}/Code/PokerBot"                       # the tree the bot and the timers run from
TOOLS = os.path.dirname(os.path.abspath(__file__))
SCRATCH = f"{HOME}/pokerbot-scratch"
CHIPZEN = f"{SCRATCH}/chipzen"
PANEL = f"{SCRATCH}/panel"
JOBS, ARMED = f"{PANEL}/jobs", f"{PANEL}/armed"
PY = f"{MAIN}/venv/bin/python"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PORT = int(os.environ.get("PANEL_PORT", "8765"))
TOKEN = secrets.token_hex(16)
HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}
ORIGINS = {f"http://{h}" for h in HOSTS}
#: OptimumPoker, the uploaded bot: its challenges count against the same daily quota as NashForge's.
OTHER_BOTS = {"OptimumPoker": "b704860e-821e-4716-9f90-d6bfa1ceeffb"}
QUOTA, LOBBY_HOURS = 20, 8.0
HEAVY_MIN_MB = 2500
#: A timer's bot lives from its connect until its match is over: past the 40-minute deadline when a match runs
#: long. The quiet window covers that and some margin; a timer that has logged "stopping" frees it early.
QUIET_BEFORE_CONNECT, QUIET_AFTER_SLOT = 30, 120
DRY_RUN_SPAN = 10                                    # minutes a dry run can hold the bot
NAME = re.compile(r"^[A-Za-z0-9][\w.\-]{0,63}$")
ARM_LOCK = threading.Lock()
SEEN_LOCK = threading.Lock()

os.makedirs(JOBS, exist_ok=True)
os.makedirs(ARMED, exist_ok=True)
os.makedirs(f"{CHIPZEN}/frozen", exist_ok=True)


def atomic_json(path: str, obj) -> None:
    # per thread: two tabs polling at once used to share one temp file and could tear fixtures_seen.json
    tmp = f"{path}.tmp{os.getpid()}.{threading.get_ident()}"
    with open(tmp, "w") as handle:
        json.dump(obj, handle, default=str)
    os.replace(tmp, path)


def read_json(path: str, default=None):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def minutes(n: float) -> dt.timedelta:
    return dt.timedelta(minutes=n)


def parse_local(text: str) -> dt.datetime:
    """A timer's wall-clock string, which it compares against this machine's clock, as an aware instant."""
    return dt.datetime.strptime(text, "%Y-%m-%d %H:%M").astimezone()


# The machine runs on Oman time, and that is how the operator reads the second clock since 22 Sept; "+04" was not.
MACHINE_ZONE = "Oman" if os.path.realpath("/etc/localtime").endswith("Muscat") else None


def clocks(t: dt.datetime) -> dict:
    t = t.astimezone()
    return {"arm": t.strftime("%Y-%m-%d %H:%M"), "machine": t.strftime("%a %d %b %H:%M"),
            "machine_tz": MACHINE_ZONE or t.strftime("%Z"), "ist": t.astimezone(IST).strftime("%a %d %b %H:%M"),
            "utc": t.astimezone(dt.timezone.utc).strftime("%a %H:%M"), "epoch": t.timestamp()}


# --- the platform ------------------------------------------------------------------------------------------------

def _config():
    with open(f"{HOME}/.chipzen/chipzen.toml", "rb") as handle:
        api = tomllib.load(handle).get("external_api", {})
    base = (api.get("url") or "wss://chipzen.ai").replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
    return base, api["token"], api.get("bot_id")


_CACHE: dict = {}                                    # path -> (fetched at, latest reply, good or error)
_GOOD: dict = {}                                     # path -> (fetched at, last good reply)
_INFLIGHT: set = set()
_CACHE_LOCK = threading.Lock()


def api_get(path: str, ttl: float = 120.0, background: bool = False) -> dict:
    """A GET on the documented external API. Answers are cached for `ttl`, errors for ten seconds only.

    With `background`, a stale answer is returned at once and refreshed on a thread: the dashboard and arm must never
    wait out a 20-second timeout on a hung platform, since the fixture banners are what matter on match night.
    Only the first call ever blocks."""
    with _CACHE_LOCK:
        hit = _CACHE.get(path)
        if hit and time.time() - hit[0] < (ttl if "error" not in hit[1] else 10):
            # a caller that blocks (the quota) must see the error, never a stale count passed off as current
            return _GOOD[path][1] if "error" in hit[1] and background and path in _GOOD else hit[1]
        if background and path in _GOOD:
            if path not in _INFLIGHT:
                _INFLIGHT.add(path)
                threading.Thread(target=_fetch, args=(path,), daemon=True).start()
            return _GOOD[path][1]
    return _fetch(path)


def api_health(path: str) -> dict:
    """Whether the latest fetch of `path` failed, and how old the answer being shown is."""
    with _CACHE_LOCK:
        hit, good = _CACHE.get(path), _GOOD.get(path)
    return {"error": hit[1].get("error") if hit and "error" in hit[1] else None,
            "age_s": round(time.time() - good[0]) if good else None}


def _fetch(path: str) -> dict:
    base, token, _ = _config()
    # Named, not urllib's default "Python-urllib": the platform's front door refused that with a 403 on 29 Sept.
    request = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {token}",
                                                           "User-Agent": "nashforge-panel/1.1",
                                                           "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except Exception as error:
        payload = {"error": str(error)}
    if not isinstance(payload, dict):
        payload = {"body": payload}
    with _CACHE_LOCK:
        _CACHE[path] = (time.time(), payload)
        if "error" not in payload:
            _GOOD[path] = (time.time(), payload)
        _INFLIGHT.discard(path)
    return payload


def fixtures() -> dict:
    """Upcoming fixtures, remembered in fixtures_seen.json so the quota can recognise them once they are played."""
    path = "/api/external-api/fixtures/upcoming"
    reply = api_get(path, ttl=300, background=True)
    if "error" in reply:
        return {"error": reply["error"], "rows": []}
    health = api_health(path)
    stale = (f"showing fixtures fetched {health['age_s'] // 60} min ago; the latest fetch failed: {health['error']}"
             if health["error"] else None)
    rows = []
    for row in reply.get("fixtures") or []:
        when = row.get("starts_at") or row.get("scheduled_at") or row.get("start_time")
        who = row.get("opponent_bot_name") or row.get("opponent") or row.get("opponent_name")
        if when and who:
            try:
                rows.append({"opponent": who, "when": dt.datetime.fromisoformat(when.replace("Z", "+00:00"))})
            except (TypeError, ValueError, AttributeError):
                continue
    with SEEN_LOCK:
        seen = read_json(f"{PANEL}/fixtures_seen.json", {})
        fresh = {f"{r['opponent']}@{r['when'].isoformat()}": {"opponent": r["opponent"], "when": r["when"].isoformat()}
                 for r in rows}
        if any(k not in seen for k in fresh):
            atomic_json(f"{PANEL}/fixtures_seen.json", {**seen, **fresh})
    return {"rows": sorted(rows, key=lambda r: r["when"]), "stale": stale}


def is_fixture(match: dict, seen: dict) -> bool:
    """A match played against a season opponent within an hour of its published slot."""
    started = match.get("started_at")
    if not started:
        return False
    t = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
    names = {p.get("name") for p in match.get("participants") or []}
    for f in seen.values():
        slot = dt.datetime.fromisoformat(f["when"])
        if f["opponent"] in names and slot - minutes(5) <= t <= slot + minutes(60):
            return True
    return False


def quota_today() -> dict:
    """Challenges since UTC midnight across the account's bots, season fixtures excluded (they are exempt)."""
    _, _, own = _config()
    now = dt.datetime.now(dt.timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seen = read_json(f"{PANEL}/fixtures_seen.json", {})
    counts, fixtures_today = {}, 0
    for name, bot_id in [("NashForge", own)] + list(OTHER_BOTS.items()):
        today = []
        for page in range(1, 6):
            reply = api_get(f"/api/matches?bot_id={bot_id}&page={page}&page_size=100")
            if "matches" not in reply:          # a failed call must not read as a quota of zero
                return {"error": f"{name}: {reply.get('error') or reply}", "limit": QUOTA}
            rows = reply["matches"]
            # Only challenges count: OptimumPoker's upload-track tournament at 09:30 IST on 29 Sept read as a
            # challenge and showed the quota full at 19.
            fresh = [m for m in rows if str(m.get("started_at") or "") >= midnight.isoformat()[:19]]
            fresh_challenges = [m for m in fresh if m.get("match_type", "challenge") == "challenge"]
            today += fresh_challenges
            if len(rows) < 100 or len(fresh) < len(rows):
                break
        season = [m for m in today if is_fixture(m, seen)]
        fixtures_today += len(season)
        counts[name] = len(today) - len(season)
    reset = midnight + dt.timedelta(days=1)
    return {"used": sum(counts.values()), "limit": QUOTA, "by_bot": counts, "fixtures_excluded": fixtures_today,
            "reset": clocks(reset), "resets_in_min": int((reset - now).total_seconds() // 60)}


# --- this machine ------------------------------------------------------------------------------------------------

def memory_mb() -> int:
    with open("/proc/meminfo") as handle:
        info = dict(line.split(":", 1) for line in handle)
    return int(info["MemAvailable"].split()[0]) // 1024


def proc_ticks(pid: int):
    """The process's start time in clock ticks: with the pid, it tells a live process from a recycled pid."""
    try:
        with open(f"/proc/{pid}/stat") as handle:
            return int(handle.read().rsplit(")", 1)[1].split()[19])
    except (OSError, IndexError, ValueError):
        return None


def proc_started_epoch(pid: int):
    ticks = proc_ticks(pid)
    if ticks is None:
        return None
    with open("/proc/uptime") as handle:
        uptime = float(handle.read().split()[0])
    return time.time() - uptime + ticks / os.sysconf("SC_CLK_TCK")


def cmdline(pid: int) -> list:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            return [a.decode(errors="replace") for a in handle.read().split(b"\0") if a]
    except OSError:
        return []


def environ(pid: int) -> dict:
    try:
        with open(f"/proc/{pid}/environ", "rb") as handle:
            pairs = [a.decode(errors="replace").split("=", 1) for a in handle.read().split(b"\0") if b"=" in a]
        return dict(pairs)
    except OSError:
        return {}


def set_info(path: str) -> dict:
    lines = []
    try:
        lines = open(path).read().splitlines()
    except OSError:
        pass
    return {"file": os.path.relpath(path, CHIPZEN) if path.startswith(CHIPZEN) else path,
            "label": lines[1] if len(lines) > 1 else "?", "ladder": lines[0] if lines else "?",
            "frozen": "/frozen/" in path}


def timer_log(who: str) -> dict:
    """What the timer's own log says: armed only, connected, or stopped."""
    try:
        text = open(f"{CHIPZEN}/fixture_{who}.log").read()
    except OSError:
        return {"phase": "no log", "tail": []}
    phase = "stopped" if "; stopping" in text else ("connected" if "connecting as" in text else "waiting")
    deadline = re.search(r"walkover deadline (\d{4}-\d\d-\d\d \d\d:\d\d)", text)
    return {"phase": phase, "tail": text.splitlines()[-3:],
            "deadline": clocks(parse_local(deadline.group(1))) if deadline else None}


def timers() -> list:
    """The fixture timers alive now, with the set each will play (from its own environment)."""
    out = []
    for line in subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout.splitlines()[1:]:
        parts = line.split(None, 1)
        if len(parts) < 2 or "fixture2.sh" not in parts[1]:
            continue
        pid = int(parts[0])
        argv = cmdline(pid)
        script = next((i for i, a in enumerate(argv) if a.endswith("fixture2.sh")), None)
        if script is None or len(argv) < script + 4 or argv[script + 3].startswith("dryrun_"):
            continue
        connect, slot, who = argv[script + 1], argv[script + 2], argv[script + 3]
        set_path = environ(pid).get("SET", "")
        info = set_info(set_path)
        started = proc_started_epoch(pid)
        changed = False
        try:
            changed = not info["frozen"] and started is not None and os.path.getmtime(set_path) > started
        except OSError:
            changed = True
        try:
            t_connect, t_slot = parse_local(connect), parse_local(slot)
        except ValueError:
            continue
        out.append({"pid": pid, "opponent": who, "connect": clocks(t_connect), "slot": clocks(t_slot),
                    "set": info, "set_changed_since_arm": changed, "log": timer_log(who)})
    return sorted(out, key=lambda t: t["slot"]["epoch"])


def quiet_windows(live: list) -> list:
    """Each live timer's window: 30 minutes before its connect until it logs that it stopped (or 2 h after the slot)."""
    windows = []
    for t in live:
        if t["log"]["phase"] == "stopped":
            continue
        start = t["connect"]["epoch"] - QUIET_BEFORE_CONNECT * 60
        end = t["slot"]["epoch"] + QUIET_AFTER_SLOT * 60
        windows.append({"opponent": t["opponent"], "start": start, "end": end})
    return windows


def in_quiet(windows: list, start: float, end: float):
    return next((w for w in windows if start < w["end"] and end > w["start"]), None)


def bot_running() -> bool:
    """botcheck.sh, the check arm_fixture.sh itself trusts: a real chipzen_run.py process, not a pid file."""
    return subprocess.run([f"{SCRATCH}/hist/botcheck.sh"], capture_output=True).returncode == 0


def bot_status() -> dict:
    status = read_json(f"{CHIPZEN}/status.json", {}) or {}
    return {"running": bot_running(), "lobby": status.get("lobby"), "active": status.get("matches_active")}


def lobby_hours_today(live: list) -> dict:
    """Lobby time on this UTC day: each bot process from its first 'lobby: connected' until the stop recorded by
    whatever started it (a fixture timer's "; stopping", a burst's "burst over", or "ended at N matches"), or its
    last lobby event when no stop was recorded. Still an estimate. Armed timers that have not played yet are
    reserved from their connect to 45 minutes past the slot."""
    now = dt.datetime.now(dt.timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stamp = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)")
    local = lambda text: dt.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").astimezone()
    stops = []
    for path in glob.glob(f"{CHIPZEN}/*.log"):
        try:
            for line in open(path, errors="replace"):
                m = stamp.match(line)
                if m and re.search(r"; stopping$|burst over:|ended at \d+ matches", line.rstrip()):
                    stops.append(local(m.group(1)))
        except OSError:
            continue
    stops.sort()
    try:
        lines = open(f"{CHIPZEN}/run.log", errors="replace").read().splitlines()[-20000:]
    except OSError:
        lines = []
    sessions, start, last_event, new_process = [], None, None, True
    for line in lines:
        m = stamp.match(line)
        if not m:
            continue
        t = local(m.group(1))
        if "root: version:" in line:
            if start:
                sessions.append((start, last_event))
            start, new_process = None, True
        elif "lobby: connected" in line and new_process:
            start, new_process = t, False
        if "chipzen:" in line:
            last_event = t
    if start:
        sessions.append((start, None))
    running = bot_running()
    used = 0.0
    for i, (s_, fallback) in enumerate(sessions):
        nxt = sessions[i + 1][0] if i + 1 < len(sessions) else None
        stop = next((x for x in stops if x > s_ and (nxt is None or x < nxt)), None)
        e = stop or (now if (nxt is None and running) else (fallback or s_))
        if e > midnight:
            used += max(0.0, (min(e, now) - max(s_, midnight)).total_seconds())
    used /= 3600
    reserved = 0.0
    for t in live:
        if t["log"]["phase"] == "waiting":
            s_ = max(dt.datetime.fromtimestamp(t["connect"]["epoch"], dt.timezone.utc), now)
            e = min(dt.datetime.fromtimestamp(t["slot"]["epoch"], dt.timezone.utc) + minutes(45),
                    midnight + dt.timedelta(days=1))
            reserved += max(0.0, (e - s_).total_seconds()) / 3600
    return {"used": round(used, 1), "reserved": round(reserved, 1), "limit": LOBBY_HOURS,
            "free": round(LOBBY_HOURS - used - reserved, 1)}


def set_files() -> list:
    """The set files a fixture or a duel can play: line 1 the ladder, line 2 the label, line 3 the flags."""
    out = []
    for path in sorted(glob.glob(f"{CHIPZEN}/*set*")):
        if path.endswith((".prev", ".log")) or not os.path.isfile(path):
            continue
        lines = open(path).read().splitlines()
        if len(lines) >= 2 and (lines[0].startswith("/") or lines[0].startswith("results/")):
            out.append({"file": os.path.basename(path), "ladder": lines[0], "label": lines[1],
                        "flags": lines[2] if len(lines) > 2 else ""})
    return out


# --- jobs --------------------------------------------------------------------------------------------------------

def start_job(kind: str, title: str, command: list, cwd: str = MAIN, env: dict | None = None, extra=None) -> dict:
    """A detached background process whose log ends with its exit status; it outlives the page and the server."""
    job_id = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
    log = f"{JOBS}/{job_id}.log"
    with open(log, "w") as handle:
        handle.write("$ " + " ".join(command) + "\n")
    wrapped = ["bash", "-c", '"$@"; echo "EXIT $?"', "job", *command]
    with open(log, "a") as handle:
        proc = subprocess.Popen(wrapped, cwd=cwd, env=dict(os.environ, **(env or {})), stdout=handle,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    record = {"id": job_id, "kind": kind, "title": title, "pid": proc.pid, "ticks": proc_ticks(proc.pid),
              "started": time.time(), "log": log, **(extra or {})}
    atomic_json(f"{JOBS}/{job_id}.json", record)
    return record


def job_state(record: dict) -> dict:
    # Jobs are this server's children: reap a finished one, or it stays a zombie that still reads as running.
    try:
        os.waitpid(record["pid"], os.WNOHANG)
    except ChildProcessError:
        pass
    alive = proc_ticks(record["pid"]) is not None and proc_ticks(record["pid"]) == record.get("ticks")
    try:
        lines = open(record["log"]).read().splitlines()
    except OSError:
        lines = []
    code = next((int(l.split()[1]) for l in reversed(lines) if re.fullmatch(r"EXIT \d+", l)), None)
    state = "running" if alive else ("ok" if code == 0 else ("failed" if code is not None else "ended"))
    step = next((re.match(r"STEP (\d+)/(\d+)", l) for l in reversed(lines) if l.startswith("STEP ")), None)
    return dict(record, state=state, exit=code, tail=[l for l in lines if not l.startswith("EXIT ")][-3:],
                step=[int(step.group(1)), int(step.group(2))] if step else None)


def jobs(limit: int = 30) -> list:
    rows = []
    for path in sorted(glob.glob(f"{JOBS}/*.json"), reverse=True)[:limit]:
        record = read_json(path)
        if record and "pid" in record:
            rows.append(job_state(record))
    return rows


def running_jobs(kind: str) -> list:
    return [j for j in jobs(50) if j["kind"] == kind and j["state"] == "running"]


# --- real results, sets and their evidence --------------------------------------------------------------------

SETS_REGISTRY = f"{CHIPZEN}/sets.json"
OPTIMUM = OTHER_BOTS["OptimumPoker"]
# The last 100 are enough for the records the panel shows; older ones are in the scout's archive.
OPTIMUM_MATCHES = f"/api/matches?bot_id={OPTIMUM}&page=1&page_size=100"
# What the uploaded image plays, in version_key's form so its record lines up with the set of the same version.
# Change it with each upload (image v2, 29 Sept: v5x purified with the reads).
UPLOAD_VERSION = "v5x purified"
_REAL: dict = {}


def version_key(v: dict) -> str:
    """A version's short name from what the bot recorded at match start: its ladder, purification and river solver."""
    ladder = os.path.basename((v.get("ladder_dir") or "").rstrip("/")).replace("ladder169l_", "") or "not recorded"
    name = {"v5iT2full": "v5iT2"}.get(ladder, ladder)
    purify = v.get("purify") or "none"
    if purify != "none":
        name += " purified" if purify == "all" else f" {purify}"
    if v.get("river_solve"):
        name += " + river"
    # Same ladder, different bot: v5d and v7b share v5c's rungs and differ in these two (29 Sept review).
    if v.get("deep_primary") is False:
        name += " one-raise primary"
    if v.get("companions"):
        name += " + companions"
    return name


def label_name(label) -> str:
    """The name a version goes by (v5d, v7b): its label up to the colon."""
    text = str(label or "")
    return text.split(":", 1)[0].strip()[:40] if ":" in text else text.split(" ", 1)[0][:40]


def set_version_key(s: dict) -> str:
    flags = s.get("flags", "").split()
    purify = flags[flags.index("--purify") + 1] if "--purify" in flags and flags.index("--purify") + 1 < len(flags) else "none"
    return version_key({"ladder_dir": s["ladder"], "purify": purify, "river_solve": "--river-solve" in flags,
                        "deep_primary": "--deep-primary" in flags,
                        "companions": [f for f in flags if f.startswith("--companion")]})


def real_matches() -> list:
    """Every finished match: NashForge's from its logs (cached by file mtime), OptimumPoker's from the API."""
    out = []
    paths = glob.glob(f"{MAIN}/results/chipzen/matches/*.jsonl")
    for gone in set(_REAL) - set(paths):
        _REAL.pop(gone, None)
    for path in paths:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        hit = _REAL.get(path)
        if hit and hit[0] == mtime:
            record = hit[1]
        else:
            record, start, end = None, None, None
            try:
                with open(path, errors="replace") as handle:
                    for line in handle:
                        try:                  # per line: one torn line must not drop the whole match
                            if '"frame": "match_start"' in line:
                                start = json.loads(line)
                            elif '"frame": "match_end"' in line and json.loads(line).get("results"):
                                end = json.loads(line)
                        except ValueError:
                            continue
            except OSError:
                pass
            if start and end:
                results = end.get("results") or []
                me = next((r for r in results if r.get("seat") == start.get("seat")), None)
                opp = next((r for r in results if r.get("seat") != start.get("seat")), None)
                if me and opp:
                    version = start.get("version") or {}
                    label = version.get("label")
                    record = {"at": start.get("at"), "opponent": opp.get("name"), "version": version_key(version),
                              "label": str(label) if label is not None else None, "name": label_name(label),
                              "won": (me.get("net_chips") or 0) > 0, "bot": "NashForge",
                              "rated": start.get("rated") is not False,
                              # a win by the opponent's crash says nothing about the set (Blueprint, 29 Sept)
                              "forfeit": any("forfeit" in str(e) for e in opp.get("bot_errors") or [])}
            _REAL[path] = (mtime, record)
        if record:
            out.append(record)
    reply = api_get(OPTIMUM_MATCHES, ttl=600, background=True)
    for m in reply.get("matches") or []:
        if not isinstance(m, dict):
            continue
        people = m.get("participants") or []
        me = next((p for p in people if p.get("bot_id") == OPTIMUM), None)
        opp = next((p for p in people if p.get("bot_id") != OPTIMUM), None)
        if m.get("status") == "completed" and me and opp and len(people) == 2:
            try:
                at = dt.datetime.fromisoformat(str(m.get("started_at")).replace("Z", "+00:00")).timestamp()
            except ValueError:
                at = None
            # Only challenges: the upload track's tournaments are a different game from a fixture's heads-up.
            if m.get("match_type") != "challenge":
                continue
            out.append({"at": at, "opponent": opp.get("name"), "version": UPLOAD_VERSION, "label": "OptimumPoker",
                        "name": "OptimumPoker", "won": (me.get("net_chips") or 0) > 0, "bot": "OptimumPoker",
                        "rated": m.get("rated") is not False, "forfeit": False})
    return out


def tally(rows: list) -> dict:
    """Won of played, forfeits left out. Under ten matches no rate is given: 1 of 1 shown as 100% ± 0 reads as
    certainty, when twenty matches is still ±11 points."""
    played = [r for r in rows if r.get("rated", True) and not r.get("forfeit")]
    n, w = len(played), sum(1 for r in played if r["won"])
    enough = n >= 10
    return {"matches": n, "won": w, "rate": round(w / n, 3) if enough else None,
            "stderr": round((w / n * (1 - w / n) / n) ** 0.5, 3) if enough else None,
            "forfeits": sum(1 for r in rows if r.get("forfeit")), "bots": sorted({r["bot"] for r in rows})}


def record_vs(opponent: str) -> list:
    rows = [r for r in real_matches() if r["opponent"] == opponent]
    versions = sorted({r["version"] for r in rows})
    return [dict(version=v, names=sorted({r["name"] for r in rows if r["version"] == v}),
                 **tally([r for r in rows if r["version"] == v])) for v in versions]


def registry() -> tuple:
    """sets.json, checked entry by entry. It is edited by hand, so a bad entry fails closed alone and is reported,
    rather than silently making every set ineligible or breaking the page."""
    path = SETS_REGISTRY
    try:
        raw = json.load(open(path))
    except OSError:
        return {}, "sets.json is missing: no set is eligible for a fixture"
    except ValueError as error:
        return {}, f"sets.json does not parse ({error}): no set is eligible for a fixture"
    if not isinstance(raw, dict):
        return {}, "sets.json is not an object: no set is eligible for a fixture"
    good, bad = {}, []
    for key, entry in raw.items():
        if key.startswith("_"):
            continue
        ok = isinstance(entry, dict) and all(entry.get(k) is None or isinstance(entry[k], str)
                                             for k in ("name", "version", "gate", "replay", "note", "same_as"))
        ok = ok and isinstance(entry.get("bursts", []), list) and all(isinstance(b, str) for b in entry.get("bursts", []))
        if ok:
            good[key] = entry
        else:
            bad.append(key)
    return good, (f"sets.json entries with the wrong shape, treated as having no evidence: {', '.join(bad)}" if bad else None)


def set_evidence() -> tuple:
    """Each set file with the evidence for it. Evidence counts only for the version it was measured on: a set file is
    edited to choose a burst, and a copy of v5x's evidence must not follow the file name onto another ladder."""
    reg, error = registry()
    files = {s["file"]: s for s in set_files()}
    out = []
    for s in files.values():
        key = set_version_key(s)
        entry = reg.get(s["file"], {})
        canonical = entry.get("same_as")
        base = reg.get(canonical, {}) if canonical else entry
        problems = []
        if canonical and canonical in files and set_version_key(files[canonical]) != key:
            problems.append(f"it plays {key} but is marked the same as {canonical}, which plays "
                            f"{set_version_key(files[canonical])}")
            base = {}
        if base.get("version") and base["version"] != key:
            problems.append(f"the evidence was recorded on {base['version']} and the file now plays {key}")
            base = {}
        if not base.get("version") and base:
            problems.append("the evidence does not say which version it was measured on")
            base = {}
        bursts = base.get("bursts") or []
        missing = [k for k in ("gate", "replay") if not base.get(k)] + ([] if bursts else ["a burst"])
        try:
            edited_h = round((time.time() - os.path.getmtime(f"{CHIPZEN}/{s['file']}")) / 3600, 1)
        except OSError:
            edited_h = None
        out.append(dict(s, name=base.get("name") or entry.get("name") or s["file"], same_as=canonical,
                        gate=base.get("gate"), replay=base.get("replay"), bursts=bursts,
                        note=base.get("note") or entry.get("note"), version=key, problems=problems,
                        eligible=not missing and not problems, missing=missing, believed=len(bursts) >= 2,
                        edited_h=edited_h))
    out.sort(key=lambda x: (not x["eligible"], x["same_as"] is not None, not x["believed"], x["file"]))
    return out, error


def sets() -> list:
    """The set files with their evidence and the rated matches each version played."""
    real = [r for r in real_matches() if r["bot"] == "NashForge"]
    return [dict(s, rated=tally([r for r in real if r["version"] == s["version"]])) for s in set_evidence()[0]]


def fit_verdict(result: dict) -> dict:
    """Whether a copy is good enough to decide on: which statistics it misses by more than 8 points, and on how much."""
    misses = []
    for line in (result.get("fit_table") or "").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 3 and cells[1].endswith("%") and cells[2].endswith("%"):
            real, fitted = float(cells[1][:-1]), float(cells[2][:-1])
            if abs(real - fitted) > 8:
                misses.append(f"{cells[0]} {real:.0f}% against {fitted:.0f}%")
    try:
        hands = int(str(result.get("fit", {}).get("hands", "0")).replace(",", ""))
    except ValueError:
        hands = 0
    summary = (read_json(f"{MAIN}/results/chipzen/scout/{result.get('opponent')}.json", {}) or {}).get("summary", {})
    rating = (summary.get("platform") or {}).get("rating")
    verdict = "close" if not misses and hands >= 1000 else ("rough" if len(misses) <= 2 and hands >= 300 else "poor")
    return {"verdict": verdict, "misses": misses, "hands": hands, "rating": round(rating) if rating else None,
            "strong": bool(rating and rating >= 1900)}


def enrich_choice(result: dict, all_sets: list | None = None) -> dict:
    if result.get("error"):
        return result
    set_info = {s["file"]: s for s in (all_sets if all_sets is not None else sets())}
    real = record_vs(result["opponent"])
    ranked = sorted([r for r in result["results"] if r.get("win") is not None], key=lambda r: -r["win"])
    for r in result["results"]:
        info = set_info.get(r["set"], {})
        key = info.get("version")
        r["version"], r["name"] = key, info.get("name")
        r["eligible"], r["believed"] = info.get("eligible"), info.get("believed")
        r["real"] = next((x for x in real if x["version"] == key), None)
    tie = len(ranked) >= 2 and (ranked[0]["win"] - ranked[1]["win"]) < 2 * ((ranked[0]["stderr"] ** 2 + ranked[1]["stderr"] ** 2) ** 0.5)
    leader = ranked[0] if ranked else None
    quality = fit_verdict(result)
    # When the copy cannot decide: a rough copy, a strong opponent (copies flatter the exploiter most there),
    # a tie, or a run under the floor.
    reasons = ([f"copy {quality['verdict']}"] if quality["verdict"] != "close" else []) + \
              (["strong opponent"] if quality["strong"] else []) + (["a tie"] if tie else []) + \
              ([f"{result.get('matches', 0):,} matches, under 5,000"] if (result.get("matches") or 0) < 5000 else [])
    warning = None
    if leader and leader.get("real") and leader["real"]["matches"] >= 2 and leader["real"]["won"] * 2 < leader["real"]["matches"]:
        warning = (f"{leader['set']} leads against the copy but is {leader['real']['won']} of {leader['real']['matches']} "
                   f"against the real {result['opponent']}")
    return dict(result, quality=quality, leader=leader["set"] if leader else None, tie=tie,
                decisive=not reasons, not_decisive=reasons, warning=warning, real=real)


def scout_age(name: str):
    path = f"{MAIN}/results/chipzen/scout/{name}.json"
    return round((time.time() - os.path.getmtime(path)) / 86400, 1) if os.path.exists(path) else None


def season_index_matches(name: str) -> int:
    """Matches both scout indexes hold for `name`, which is what choose.py fits from: a paced scout's zero is not the whole story."""
    season = read_json(f"{MAIN}/results/chipzen/scout/season_matches.json", {}) or {}
    ids = {m.get("id") for m in season.values() if isinstance(m, dict) and
           any(p.get("name") == name for p in m.get("participants") or [])}
    other = ((read_json(f"{MAIN}/results/chipzen/scout/index.json", {}) or {}).get("by_name") or {}).get(name) or []
    return len(ids | {m.get("id") for m in other if isinstance(m, dict)})


def opponent_page(name: str) -> dict:
    all_sets = sets()
    prof = profiles([name]).get(name, {})
    path = f"{MAIN}/results/chipzen/scout/{name}.json"
    fresh = round((time.time() - os.path.getmtime(path)) / 86400, 1) if os.path.exists(path) else None
    row = prof.get("profile") or {}
    reads = "no profile: no read can fire" if not row else (
        f"{row.get('bets_faced')} bets faced: " + ("enough for the reads" if (row.get("bets_faced") or 0) >= 100
                                                 else "too few for most reads"))
    return {"name": name, "profile": prof, "scouted_days_ago": fresh, "reads": reads, "record": record_vs(name),
            "season_index_matches": season_index_matches(name),
            "choices": [enrich_choice(c, all_sets) for c in choices() if c.get("opponent") == name][:5]}


def results_summary() -> dict:
    rows = real_matches()
    since = time.time() - 14 * 86400
    versions = {}
    for r in rows:
        if (r.get("at") or 0) < since:
            continue
        v = versions.setdefault(r["version"], {"rows": [], "labels": set()})
        v["rows"].append(r)
        if r.get("label"):
            v["labels"].add(r["label"])
    out = []
    for key, v in sorted(versions.items(), key=lambda kv: -len(kv[1]["rows"])):
        opps = {}
        for r in v["rows"]:
            opps.setdefault(r["opponent"], []).append(r)
        out.append(dict(version=key, labels=sorted(v["labels"]), names=sorted({r["name"] for r in v["rows"]}),
                        first=min(r.get("at") or 0 for r in v["rows"]), last=max(r.get("at") or 0 for r in v["rows"]),
                        label_counts={l: sum(1 for r in v["rows"] if r.get("label") == l) for l in v["labels"]},
                        **tally(v["rows"]),
                        opponents=sorted(({"opponent": o, **tally(rs)} for o, rs in opps.items()), key=lambda x: -x["matches"])[:8]))
    return {"since_days": 14, "versions": out}


# --- the overview: fixtures, timers and their states -------------------------------------------------------------

def connect_alarms(live: list, bot: dict, now: float) -> list:
    """A fixture whose connect time has passed without the bot in the lobby. The Shadow fixture (17 Sept) was a
    walkover to a timer that never connected, and nothing on screen said so; three minutes allows for the start-up."""
    out = []
    status = read_json(f"{CHIPZEN}/status.json", {}) or {}
    for t in live:
        connect, deadline = t["connect"]["epoch"], (t["log"].get("deadline") or t["slot"])["epoch"]
        if not connect + 180 < now < deadline or t["log"]["phase"] == "stopped":
            continue
        # status.json outlives the bot, so its lobby state counts only if this run wrote it
        fresh = (status.get("started_at") or 0) >= connect - 120
        problem = ("the timer has not logged a connect" if t["log"]["phase"] != "connected" else
                   "no bot process is running" if not bot["running"] else
                   "the bot has not reached the lobby" if not fresh or status.get("lobby") != "connected" else None)
        if problem:
            out.append({"opponent": t["opponent"], "problem": problem, "connect": t["connect"],
                        "deadline": t["log"].get("deadline")})
    return out


def overview() -> dict:
    live = timers()
    windows = quiet_windows(live)
    fx = fixtures()
    now = time.time()
    registry = [r for r in (read_json(p) for p in glob.glob(f"{ARMED}/*.json")) if r]
    rows, matched = [], set()
    all_sets = sets()
    recent = [enrich_choice(c, all_sets) for c in choices()]
    for f in fx["rows"]:
        c = clocks(f["when"])
        timer = next((t for t in live if t["opponent"] == f["opponent"] and t["slot"]["arm"] == c["arm"]), None)
        if timer:
            matched.add(timer["pid"])
        record = next((r for r in registry if r.get("opponent") == f["opponent"] and r.get("slot") == c["arm"]
                       and not r.get("disarmed")), None)
        left_h = (c["epoch"] - now) / 3600
        if timer:
            state = "armed"
        elif record and record.get("armed_pid") and left_h > -1 and timer_log(f["opponent"])["phase"] != "stopped":
            state = "died"                       # the panel armed it and the timer is gone before playing
        elif left_h < 2:
            state = "unarmed-urgent"
        elif left_h < 36:
            state = "unarmed-soon"
        else:
            state = "unarmed"
        last = next((x for x in recent if x.get("opponent") == f["opponent"]), None)
        rows.append({"opponent": f["opponent"], "slot": c, "state": state, "timer": timer, "hours_left": round(left_h, 2),
                     "scouted_days_ago": scout_age(f["opponent"]),
                     "last_choice": {"at": last["at"], "decisive": last.get("decisive"), "leader": last.get("leader"),
                                     "not_decisive": last.get("not_decisive")} if last and not last.get("error") else None})
    orphans = [t for t in live if t["pid"] not in matched]
    bot = bot_status()
    alarms = connect_alarms(live, bot, now)
    return {"now": clocks(dt.datetime.now().astimezone()), "fixtures": rows, "fixtures_error": fx.get("error"),
            "timers": live, "orphans": orphans, "quiet": windows,
            "quiet_now": in_quiet(windows, now, now + 1), "bot": bot, "memory_mb": memory_mb(),
            "lobby": lobby_hours_today(live), "jobs": jobs(10), "sets": all_sets, "alarms": alarms,
            "fixtures_stale": fx.get("stale"), "sets_error": set_evidence()[1],
            "matches_error": api_health(OPTIMUM_MATCHES)["error"]}


# --- actions ------------------------------------------------------------------------------------------------------

def arm(body: dict) -> dict:
    slot, opponent, setfile = str(body.get("slot", "")), str(body.get("opponent", "")), str(body.get("set", ""))
    if not re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d", slot) or not NAME.fullmatch(opponent):
        return {"error": "bad slot or opponent"}
    known = {s["file"]: s for s in set_evidence()[0]}
    if setfile not in known:
        return {"error": f"{setfile!r} is not one of the set files"}
    chosen = known[setfile]
    if not chosen["eligible"]:
        why = "; ".join(chosen["problems"]) or f"missing {', '.join(chosen['missing'])}"
        return {"error": f"{chosen['name']} is not eligible for a fixture: {why} (arena rules: gate, replay and a "
                         f"burst, on this version). Record the evidence in sets.json first."}
    with ARM_LOCK:
        if running_jobs("arm"):
            return {"error": "another arm is still running its dry run; one at a time"}
        live = timers()
        if any(t["opponent"] == opponent and t["log"]["phase"] != "stopped" for t in live):
            return {"error": f"a timer for {opponent} is already alive; disarm it first"}
        now = time.time()
        clash = in_quiet(quiet_windows(live), now, now + DRY_RUN_SPAN * 60)
        if clash:
            return {"error": f"a dry run now would overlap the {clash['opponent']} fixture's window and could stop "
                             f"its bot; arm after it has stopped"}
        if bot_running():
            return {"error": "a bot is running; arm_fixture.sh refuses to dry-run over it, and so does this"}
        if parse_local(slot).timestamp() - now < 25 * 60:
            return {"error": "the slot is less than 25 minutes away; arm it by hand"}
        # Freeze the set: fixture2.sh reads its set file only at connect time, so the timer plays a copy.
        name = f"{slot.replace('-', '').replace(' ', '-').replace(':', '')}_{opponent}.set"
        frozen = f"{CHIPZEN}/frozen/{name}"
        shutil.copyfile(f"{CHIPZEN}/{setfile}", frozen)
        digest = hashlib.sha256(open(frozen, "rb").read()).hexdigest()
        job = start_job("arm", f"arm {opponent} at {slot} with {setfile}", [f"{CHIPZEN}/arm_fixture.sh", slot, opponent,
                        f"frozen/{name}"], cwd=CHIPZEN, env={"ARM": "1"},
                        extra={"opponent": opponent, "slot": slot, "set": setfile})
        atomic_json(f"{ARMED}/{name}.json", {"opponent": opponent, "slot": slot, "set": setfile, "frozen": frozen,
                                             "sha256": digest, "job": job["id"], "armed_at": time.time(),
                                             "armed_pid": None})
        return job


def note_armed_pids() -> None:
    """Record each panel-armed timer's pid once it appears, so a timer that later vanishes reads as died."""
    live = timers()
    for path in glob.glob(f"{ARMED}/*.json"):
        record = read_json(path)
        if not record or record.get("armed_pid") or record.get("disarmed"):
            continue
        timer = next((t for t in live if t["opponent"] == record["opponent"] and t["slot"]["arm"] == record["slot"]), None)
        if timer:
            record["armed_pid"] = timer["pid"]
            atomic_json(path, record)


def disarm(body: dict) -> dict:
    pid = int(body.get("pid", 0))
    timer = next((t for t in timers() if t["pid"] == pid), None)
    if not timer or not any(a.endswith("fixture2.sh") for a in cmdline(pid)):
        return {"error": "no fixture timer with that pid"}
    if time.time() >= timer["connect"]["epoch"]:
        return {"error": "this timer has already connected; stop it by hand, a match may be live"}
    try:
        if os.getpgid(pid) == pid:                   # a timer armed by setsid leads its own group
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"error": "the timer had already exited"}
    for path in glob.glob(f"{ARMED}/*.json"):
        record = read_json(path)
        if record and record.get("opponent") == timer["opponent"] and record.get("slot") == timer["slot"]["arm"]:
            record["disarmed"] = time.time()
            atomic_json(path, record)
    return {"ok": f"disarmed {timer['opponent']} at {timer['slot']['ist']} IST"}


def scout(body: dict) -> dict:
    names = [str(n) for n in body.get("names", []) if NAME.fullmatch(str(n))]
    if not names:
        return {"error": "no valid bot names"}
    matches = max(10, min(200, int(body.get("matches", 60))))
    command = [PY, "scripts/chipzen_scout.py", "--names", *names, "--max-matches", str(matches),
               "--pace", "1.5", "--seed-profiles"] + (["--refresh"] if body.get("refresh") else [])
    return start_job("scout", f"scout {', '.join(names)}", command)


def choose(body: dict) -> dict:
    opponent = str(body.get("opponent", ""))
    valid = {s["file"] for s in set_files()}
    sets = [str(s) for s in body.get("sets", []) if str(s) in valid]
    if not NAME.fullmatch(opponent) or not sets:
        return {"error": "need a valid opponent and at least one set file"}
    # 5,000 at least: 500 matches is ±2 points, too wide to choose between two sets.
    matches = max(5000, min(40000, int(body.get("matches", 10000))))
    if memory_mb() < HEAVY_MIN_MB:
        return {"error": f"only {memory_mb()} MB available; duels need {HEAVY_MIN_MB}"}
    # About 1.5 minutes per 10,000 matches per set on two workers, measured 29 Sept, plus about 3 minutes of fits.
    now = time.time()
    span = (3 + len(sets) * 1.5 * matches / 10000) * 60 * 1.5
    clash = in_quiet(quiet_windows(timers()), now, now + span)
    if clash:
        return {"error": f"this would run into the {clash['opponent']} fixture's quiet window; run it after the fixture"}
    command = [PY, f"{TOOLS}/choose.py", "--opponent", opponent, "--matches", str(matches), "--sets", *sets]
    return start_job("choose", f"choose a set against {opponent}", command)


def decompose(body: dict) -> dict:
    label, opponent = str(body.get("label", "")), str(body.get("opponent", ""))
    labels = {r.get("label") for r in real_matches() if r.get("label") and r["bot"] == "NashForge"}
    if label not in labels or label.startswith("-"):
        return {"error": "no matches recorded under that label"}
    if running_jobs("decompose"):
        return {"error": "a decomposition is already running; one at a time"}
    now = time.time()
    clash = in_quiet(quiet_windows(timers()), now, now + 10 * 60)
    if clash:
        return {"error": f"not inside the {clash['opponent']} fixture's window: it reads every match log and would "
                         f"compete with the live bot for the CPU"}
    command = [PY, "scripts/chipzen_decompose.py", "--label", label]
    if opponent:
        if not NAME.fullmatch(opponent):
            return {"error": "bad opponent name"}
        command += ["--opponent", opponent]
    return start_job("decompose", f"decompose {label[:50]}{' against ' + opponent if opponent else ''}", command,
                     extra={"label": label, "opponent": opponent})


def profiles(names: list) -> dict:
    rows = read_json(f"{MAIN}/results/chipzen/opponents.json", {}) or {}
    out = {}
    for name in names:
        if not NAME.fullmatch(name):
            continue
        row = rows.get(name)
        summary = (read_json(f"{MAIN}/results/chipzen/scout/{name}.json", {}) or {}).get("summary", {})
        out[name] = {"profile": {k: row.get(k) for k in ("bets_faced", "folds", "calls", "raises", "hands", "river_bets",
                                                          "river_bluffs", "scouted")} if row else None,
                     "scout": {k: summary.get(k) for k in ("matches", "hands", "vpip", "pfr", "three_bet",
                                                            "fold_to_three_bet", "fold_to_bet", "showdown_rate")},
                     "platform": summary.get("platform") or {}}
    return out


def choices() -> list:
    rows = []
    for path in sorted(glob.glob(f"{PANEL}/choose/*/result.json"), reverse=True)[:20]:
        record = read_json(path)
        if record:
            rows.append(record)
    return rows


# --- the server ---------------------------------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, payload, kind="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self) -> bool:
        # DNS rebinding: a site that points its own name at 127.0.0.1 would otherwise read the page and its token.
        return self.headers.get("Host") in HOSTS

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "bad host"})
        try:
            path, _, query = self.path.partition("?")
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            # Reads need the token too: any site open in the browser could otherwise make this machine run ps,
            # the bot check and the match-log parse in a loop, during a fixture, without reading the answers.
            if path.startswith("/api/") and self.headers.get("X-Panel-Token") != TOKEN:
                return self._send(403, {"error": "bad token"})
            if path == "/":
                page = open(f"{TOOLS}/index.html").read().replace("__TOKEN__", TOKEN)
                return self._send(200, page.encode(), "text/html; charset=utf-8")
            if path == "/api/overview":
                note_armed_pids()
                return self._send(200, overview())
            if path == "/api/quota":
                return self._send(200, quota_today())
            if path == "/api/jobs":
                return self._send(200, jobs())
            if path == "/api/log":
                job_id = params.get("id", "")
                if not re.fullmatch(r"[\w\-]+", job_id):
                    return self._send(400, {"error": "bad id"})
                record = read_json(f"{JOBS}/{job_id}.json")
                if not record:
                    return self._send(404, {"error": "no such job"})
                return self._send(200, {"log": open(record["log"]).read()[-20000:]})
            if path == "/api/profiles":
                names = [n for n in urllib.request.unquote(params.get("names", "")).split(",") if n]
                return self._send(200, profiles(names))
            if path == "/api/choices":
                all_sets = sets()
                return self._send(200, [enrich_choice(c, all_sets) for c in choices()])
            if path == "/api/opponent":
                name = urllib.request.unquote(params.get("name", ""))
                if not NAME.fullmatch(name):
                    return self._send(400, {"error": "bad name"})
                return self._send(200, opponent_page(name))
            if path == "/api/results":
                return self._send(200, results_summary())
            return self._send(404, {"error": "not found"})
        except Exception as error:
            return self._send(500, {"error": repr(error)})

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "bad host"})
        origin = self.headers.get("Origin")
        if origin is not None and origin not in ORIGINS:
            return self._send(403, {"error": "bad origin"})
        if self.headers.get("X-Panel-Token") != TOKEN:
            return self._send(403, {"error": "bad token"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            action = {"/api/arm": arm, "/api/disarm": disarm, "/api/scout": scout, "/api/choose": choose,
                      "/api/decompose": decompose}.get(self.path)
            if not action:
                return self._send(404, {"error": "not found"})
            return self._send(200, action(body))
        except Exception as error:
            return self._send(500, {"error": repr(error)})


def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"NashForge panel on http://localhost:{PORT} (this machine only)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
