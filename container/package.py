"""
Assemble the upload: container/upload/ and container/nashforge_upload.zip.

    .cvenv/bin/python container/package.py

Run with the slim venv (numpy and the SDK only), because the first step is to find which of our
modules the bot really loads, and that has to be measured where numba and the native module are
absent, as they are in the image. It plays matches against every scripted shape, so the lazy imports
in rarely taken branches load too, then ships exactly the modules that were loaded.

Our `chipzen` package ships as `nfarena`: the SDK's package has the same name and would shadow it.
Every shipped file is then checked for a module-level import of anything the sandbox blocks (pickle,
urllib, multiprocessing and the rest); imports inside functions are listed, since they are only a
problem if that code runs.
"""
import ast
import json
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "container", "upload")
ZIP = os.path.join(ROOT, "container", "nashforge_upload.zip")
DATA = ("results/cfr/chance/push_fold_ranges.npz",)
#: The main tree: results are not tracked in a worktree, so data comes from where it was made.
MAIN_RESULTS_ROOT = os.path.expanduser("~/Code/PokerBot")
PACKAGES = ("abstraction", "cfr", "chipzen", "engine", "evaluation", "games", "slumbot", "training", "utils")
BLOCKED = {"subprocess", "shutil", "ctypes", "multiprocessing", "signal", "resource", "_thread", "http",
           "urllib", "requests", "httpx", "aiohttp", "flask", "django", "fastapi", "socketserver", "xmlrpc",
           "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "pickle", "shelve", "marshal", "tempfile",
           "webbrowser", "code", "codeop", "compileall", "py_compile",
           "pokerbot_native"}   # not blocked, but not in the image either: the compiled module does not ship


def loaded_modules():
    """Our modules the bot loads while playing every scripted shape, without numba or the native module."""
    # numba is absent as in the image. The native module cannot be blocked here, because the scripted
    # opponents of this harness use it; the audit below treats it as blocked in shipped files instead.
    sys.modules["numba"] = None
    sys.path.insert(0, ROOT)
    import glob
    import numpy as np
    import scripts.chipzen_duel as duel
    from chipzen.archetypes import ARCHETYPES
    from chipzen.player import ArenaPlayer
    rungs = sorted(p[:-len(".rung.json")] + ".pkl"
                   for p in glob.glob(os.path.join(ROOT, "container", "ladder", "*.rung.json")))
    bot = ArenaPlayer(rungs, np.random.default_rng(1), companions=[], purify="all", stack_cap=True)
    bot.label = "NashForge"
    rng = np.random.default_rng(2)
    for kind in ARCHETYPES:
        other = duel.build(f"archetype:{kind}", "", kind, np.random.default_rng(3), None)
        for _ in range(15):
            duel.play_match([bot, other], rng, ("NashForge", kind))
    ours = set()
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None) or ""
        if path.startswith(ROOT + os.sep) and name.split(".")[0] in PACKAGES:
            ours.add(os.path.relpath(path, ROOT))
    # The dealer and the archetypes are this discovery's harness, not the bot's.
    harness = {"scripts/chipzen_duel.py", "chipzen/archetypes.py", "chipzen/client.py"}
    return sorted(ours - harness)


def rename(path: str) -> str:
    return "nfarena" + path[len("chipzen"):] if path.split(os.sep)[0] == "chipzen" else path


def rewrite_imports(source: str) -> str:
    source = re.sub(r"^(\s*)from chipzen(\.| import)", r"\1from nfarena\2", source, flags=re.M)
    return re.sub(r"^(\s*)import chipzen\.", r"\1import nfarena.", source, flags=re.M)


def audit(path: str):
    """Blocked modules imported at module level (fatal) and inside functions (listed)."""
    tree = ast.parse(open(path).read(), filename=path)
    top, inner = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            hit = {n.split(".")[0] for n in names} & BLOCKED
            if hit:
                (top if node.col_offset == 0 else inner).update(hit)
    return top, inner


def main():
    files = loaded_modules()
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    fatal = []
    for rel in files:
        target = os.path.join(OUT, rename(rel))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(os.path.join(ROOT, rel)) as handle:
            source = handle.read()
        with open(target, "w") as handle:
            handle.write(rewrite_imports(source))
        top, inner = audit(target)
        if top:
            fatal.append(f"{rename(rel)}: {sorted(top)}")
        elif inner:
            print(f"  lazy only, {rename(rel)}: {sorted(inner)}")
    shutil.copy(os.path.join(ROOT, "container", "main.py"), os.path.join(OUT, "main.py"))
    shutil.copy(os.path.join(ROOT, "container", "Dockerfile"), os.path.join(OUT, "Dockerfile"))
    # The reads: the profiles trimmed to what they use, and the private thresholds they fire at.
    sys.path.insert(0, os.path.join(ROOT, "container"))
    from trim_profiles import trim
    with open(os.path.join(MAIN_RESULTS_ROOT, "results", "chipzen", "opponents.json")) as handle:
        profiles = trim(json.load(handle))
    with open(os.path.join(OUT, "profiles.json"), "w") as handle:
        json.dump(profiles, handle, separators=(",", ":"), sort_keys=True)
    shutil.copy(os.path.expanduser("~/.chipzen/reads.toml"), os.path.join(OUT, "reads.toml"))
    shutil.copy(os.path.join(ROOT, "container", "dockerignore"), os.path.join(OUT, ".dockerignore"))
    with open(os.path.join(OUT, "requirements.txt"), "w") as handle:
        handle.write("numpy\nchipzen-bot\n")
    shutil.copytree(os.path.join(ROOT, "container", "ladder"), os.path.join(OUT, "ladder"))
    # Data the shipped modules open by a path relative to themselves. The push/fold ranges answer short
    # stacks (nfarena/pushfold.py); without them the loader returns None and the bot quietly plays a
    # rule instead, which an end-to-end run caught (one decision in 4,978, a call played as a fold).
    for rel in DATA:
        target = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(os.path.join(MAIN_RESULTS_ROOT, rel), target)
    top, _ = audit(os.path.join(OUT, "main.py"))
    if top:
        fatal.append(f"main.py: {sorted(top)}")
    if fatal:
        raise SystemExit("blocked modules imported at module level:\n  " + "\n  ".join(fatal))
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for base, _, names in os.walk(OUT):
            for name in names:
                path = os.path.join(base, name)
                archive.write(path, os.path.relpath(path, OUT))
    size = sum(os.path.getsize(os.path.join(b, n)) for b, _, ns in os.walk(OUT) for n in ns)
    print(f"{len(files)} modules, main.py, requirements.txt and the ladder: {size / 1e6:.1f} MB in {OUT}")
    print(f"zip: {os.path.getsize(ZIP) / 1e6:.1f} MB at {ZIP}")


if __name__ == "__main__":
    main()
