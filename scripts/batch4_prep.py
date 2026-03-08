"""
Batch 4 Preparation Script
===========================
1. Archive poor-performing B3 checkpoint directories
2. Update Hall of Fame with top B3 performers
3. (Informational) Report on what was done
"""

import os
import shutil
import numpy as np
from pathlib import Path

BASE = Path("/home/dheirav/Code/PokerBot")
CHECKPOINTS = BASE / "checkpoints"
HOF_CHAMPIONS = BASE / "hall_of_fame" / "champions"
HOF_ARCHIVED = BASE / "hall_of_fame" / "archived"
ARCHIVE_DEST = CHECKPOINTS / "archived_configs" / "batch3_poor_performers"

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1: Archive poor-performing checkpoints
# ─────────────────────────────────────────────────────────────────────────────

ARCHIVE_DEST.mkdir(parents=True, exist_ok=True)
HOF_ARCHIVED.mkdir(parents=True, exist_ok=True)

# Rules for what to archive:
# 1. All m=9 configs (worst matchup count across every format, every metric)
# 2. Confirmed dead-zone configs: h=750 + p>=40 + g200
# 3. Superseded m=6 configs (B1/B2 era, all outperformed by m=7/m=8)
# 4. Specific known bad performers from B3 bottom list

ARCHIVE_PATTERNS = []

# m=9 configs
for pop in [12, 20, 40]:
    for hand in [375, 500, 750]:
        for sig in ["0.08", "0.09", "0.1"]:
            for gen in ["g50", "g200"]:
                ARCHIVE_PATTERNS.append(f"deep_p{pop}_m9_h{hand}_s{sig}_hof3_{gen}")

# h=750 + p40 + g200 dead zone (NOT g50 — g50 is fine per B3 results)
for m in [7, 8]:
    for sig in ["0.07", "0.08", "0.09", "0.1"]:
        ARCHIVE_PATTERNS.append(f"deep_p40_m{m}_h750_s{sig}_hof3_g200")

# p40_m8_h500_s0.1_g200 — 25.2% combined, specific bottom performer
ARCHIVE_PATTERNS.append("deep_p40_m8_h500_s0.1_hof3_g200")

# Superseded m=6 configs
for pop in [12, 20, 40]:
    for hand in [375, 500, 750]:
        for sig in ["0.08", "0.09", "0.1", "0.12"]:
            for gen in ["g50", "g200", "g100"]:
                ARCHIVE_PATTERNS.append(f"deep_p{pop}_m6_h{hand}_s{sig}_hof3_{gen}")

archived = []
skipped = []

for pattern in ARCHIVE_PATTERNS:
    src = CHECKPOINTS / pattern
    if src.exists() and src.is_dir():
        dst = ARCHIVE_DEST / pattern
        if dst.exists():
            print(f"  [SKIP - already archived] {pattern}")
            skipped.append(pattern)
        else:
            shutil.move(str(src), str(dst))
            archived.append(pattern)
            print(f"  [ARCHIVED] {pattern}")

print(f"\n✓ Archived {len(archived)} directories, skipped {len(skipped)} (already archived)")

# Report remaining active configs
active = sorted([d.name for d in CHECKPOINTS.iterdir()
                 if d.is_dir() and d.name.startswith("deep_")])
print(f"\n=== Active checkpoint configs remaining ({len(active)}) ===")
for name in active:
    print(f"  {name}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2: Update Hall of Fame with top B3 performers
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("TASK 2: Updating Hall of Fame")
print("="*60)

# Top B3 performers to promote to HoF champions:
# Selected for diversity across formats and hyperparameter space
HOF_PROMOTIONS = [
    {
        "checkpoint_dir": "deep_p12_m8_h500_s0.09_hof3_g200",
        "out_name": "p12_m8_h500_s0.09_g200_b3_champion.npy",
        "reason": "#1 HeadsUp (81.3%), #2 Combined — best generalist / HU specialist"
    },
    {
        "checkpoint_dir": "deep_p12_m8_h750_s0.1_hof3_g200",
        "out_name": "p12_m8_h750_s0.1_g200_b3_champion.npy",
        "reason": "#1 MultiTable (57.7%), #1 Combined — dominant 6-player specialist"
    },
    {
        "checkpoint_dir": "deep_p12_m7_h500_s0.08_hof3_g200",
        "out_name": "p12_m7_h500_s0.08_g200_b3_champion.npy",
        "reason": "#3 Combined (46.1%), #7 HeadsUp — strong format-generalist with m=7"
    },
    {
        "checkpoint_dir": "deep_p40_m8_h750_s0.07_hof3_g200",
        "out_name": "p40_m8_h750_s0.07_g200_b3_champion.npy",
        "reason": "#4 Combined (45.8%) — only σ=0.07 agent, injects new weight-space diversity"
    },
]

# Find best_genome.npy inside a checkpoint dir (walks into runs subdirs)
def find_best_genome(chk_dir: Path) -> Path | None:
    # Prefer runs/<latest_run>/best_genome.npy
    runs_dir = chk_dir / "runs"
    if runs_dir.exists():
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
        for run_dir in reversed(run_dirs):  # latest first
            candidate = run_dir / "best_genome.npy"
            if candidate.exists():
                return candidate
    # Fallback: any best_genome.npy in the tree
    for candidate in chk_dir.rglob("best_genome.npy"):
        return candidate
    return None

hof_updated = []
hof_failed = []

for promo in HOF_PROMOTIONS:
    chk_dir = CHECKPOINTS / promo["checkpoint_dir"]
    if not chk_dir.exists():
        print(f"  [MISSING] {promo['checkpoint_dir']} — not found in checkpoints")
        hof_failed.append(promo["checkpoint_dir"])
        continue

    src_weights = find_best_genome(chk_dir)
    if src_weights is None:
        print(f"  [NO GENOME] {promo['checkpoint_dir']} — best_genome.npy not found")
        hof_failed.append(promo["checkpoint_dir"])
        continue

    dst = HOF_CHAMPIONS / promo["out_name"]

    # Load and validate weights
    try:
        w = np.load(str(src_weights))
        print(f"  [LOADING] {promo['checkpoint_dir']} → weights shape {w.shape}")
    except Exception as e:
        print(f"  [ERROR] Could not load {src_weights}: {e}")
        hof_failed.append(promo["checkpoint_dir"])
        continue

    # Copy to HoF champions
    shutil.copy2(str(src_weights), str(dst))
    print(f"  [HOF ADDED] {promo['out_name']}")
    print(f"             {promo['reason']}")
    hof_updated.append(promo["out_name"])

print(f"\n✓ Added {len(hof_updated)} new champions to HoF")
if hof_failed:
    print(f"✗ Failed: {hof_failed}")

# Archive old HoF champions that are now superseded (pre-B3)
OLD_HOF = [
    ("p12_m6_h750_s0.1_g200_champion.npy", "B1/B2 era m=6 champion — superseded"),
    ("p12_m6_h750_s0.1_g50_champion.npy",  "B1/B2 era m=6 champion — superseded"),
]
print("\n--- Archiving old HoF champions ---")
for fname, reason in OLD_HOF:
    src = HOF_CHAMPIONS / fname
    if src.exists():
        dst = HOF_ARCHIVED / fname
        shutil.move(str(src), str(dst))
        print(f"  [ARCHIVED HOF] {fname} — {reason}")
    else:
        print(f"  [SKIP] {fname} — not present")

print("\n--- Current HoF Champions ---")
for f in sorted(HOF_CHAMPIONS.iterdir()):
    if f.suffix == ".npy":
        w = np.load(str(f))
        print(f"  {f.name}  (shape: {w.shape})")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 3: Summary report
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Checkpoints archived:  {len(archived)}")
print(f"Active configs left:   {len(active)}")
print(f"HoF champions added:   {len(hof_updated)}")
print(f"HoF champions current: {len(list(HOF_CHAMPIONS.glob('*.npy')))}")
print("\nReady for Batch 4 training.")
