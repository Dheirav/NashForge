#!/usr/bin/env python3
"""
Run Batch 6 aggfix tournament: B6 aggfix configs vs B5 champions.
Saves results to tournament_reports/Batch6/

Purpose: Direct A/B comparison of the features[15] aggression fix.
  B5 baseline:  features[15] = 0.5  (constant dead signal)
  B6 aggfix:    features[15] = 1.0 if facing_raise else 0.0  (real signal)

Included agents:
  B6 aggfix  — 2 new configs with the feature fix applied
  B5 champs  — their direct B5 counterparts as baseline comparison
  Top B5     — broader B5 field for context (if checkpoints exist)

Usage:
  python run_b6_tournament.py                    # 10 rounds, both modes
  python run_b6_tournament.py --mode multi-table # MT only
  python run_b6_tournament.py --rounds 5         # 5 rounds each
  python run_b6_tournament.py --b6-only          # only B6 aggfix agents
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime


def get_valid_checkpoints(b6_only: bool = False):
    """
    Return checkpoint directory names that have actual trained weights.

    Priority order:
      1. B6 aggfix configs (required — skip if missing)
      2. B5 direct counterparts (for A/B baseline)
      3. Broader B5 field (for tournament context, if --b6-only not set)
    """
    checkpoints = Path("checkpoints")

    # ── B6 aggfix configs — the test subjects ────────────────────────────────
    b6_configs = [
        # MT aggfix: σ=0.04, m=8, h=500, seeded — B5 MT champion rerun w/ fix
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,
         'seeded': True, 'aggfix': True, 'batch': 'B6'},
        # HU aggfix: σ=0.06, m=7, h=375, hu100, seeded — B5 HU champion rerun w/ fix
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,
         'seeded': True, 'aggfix': True, 'hu': True, 'batch': 'B6'},
    ]

    # ── B5 direct counterparts — baseline for the A/B comparison ─────────────
    b5_baseline_configs = [
        # Same params as B6 MT aggfix, but without the fix
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,
         'seeded': True, 'batch': 'B5'},
        # Same params as B6 HU aggfix, but without the fix
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,
         'seeded': True, 'hu': True, 'batch': 'B5'},
    ]

    # ── Broader B5 field — context agents, included unless --b6-only ─────────
    b5_field_configs = [
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.045, 'seeded': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,  'seeded': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06,  'seeded': True},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.05,  'seeded': True, 'hu': True},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.07,  'seeded': True, 'hu': True},
    ]

    def make_name(cfg):
        seed_sfx  = "_seeded" if cfg.get('seeded') else ""
        hu_sfx    = "_hu100"  if cfg.get('hu') else ""
        fix_sfx   = "_aggfix" if cfg.get('aggfix') else ""
        hof_sfx   = "_hof4"   if cfg.get('aggfix') else "_hof3"
        return (
            f"deep_p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}"
            f"_s{cfg['sigma']}{hu_sfx}{fix_sfx}{seed_sfx}{hof_sfx}_g50"
        )

    valid = []
    seen  = set()
    b6_present = []

    def _check(cfgs, label, required=False):
        for cfg in cfgs:
            name = make_name(cfg)
            if name in seen:
                continue
            seen.add(name)
            runs_dir = checkpoints / name / "runs"
            if runs_dir.exists() and any(runs_dir.rglob("best_genome.npy")):
                valid.append(name)
                if label == 'B6':
                    b6_present.append(name)
            else:
                marker = "❌ MISSING (B6 aggfix — run experiment first!)" if required else "⚠️  Skipping (no weights)"
                print(f"  {marker}: {name}")

    _check(b6_configs,        'B6', required=True)
    _check(b5_baseline_configs, 'B5 baseline')
    if not b6_only:
        _check(b5_field_configs, 'B5 field')

    if not b6_present:
        print(
            "\n❌ No B6 aggfix checkpoints found.\n"
            "   Run  python run_b6_aggfix_experiment.py  first, then come back."
        )
        return []

    return valid


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Batch 6 aggfix tournament — B6 vs B5 A/B comparison'
    )
    parser.add_argument('--rounds', type=int, default=10,
                        help='Tournament rounds per mode (default: 10)')
    parser.add_argument('--mode', type=str,
                        choices=['heads-up', 'multi-table', 'both'],
                        default='both',
                        help='Tournament mode (default: both)')
    parser.add_argument('--hands', type=int, default=10000,
                        help='Hands per matchup (default: 10000)')
    parser.add_argument('--table-size', type=int, default=6,
                        help='Players per table for multi-table (default: 6)')
    parser.add_argument('--min-encounters', type=int, default=50,
                        help='Min encounters per pair in multi-table (default: 50)')
    parser.add_argument('--b6-only', action='store_true',
                        help='Include only B6 aggfix configs (no B5 field)')
    args = parser.parse_args()

    print("=" * 80)
    print("BATCH 6 TOURNAMENT — Aggression Fix A/B Comparison")
    print("  B5 baseline : features[15] = 0.5  (dead constant)")
    print("  B6 aggfix   : features[15] = facing_raise  (real signal)")
    print("=" * 80)

    checkpoint_dirs = get_valid_checkpoints(b6_only=args.b6_only)

    if not checkpoint_dirs:
        sys.exit(1)

    print(f"\nValid checkpoints ({len(checkpoint_dirs)}):")
    for d in checkpoint_dirs:
        tag = " [aggfix]" if "_aggfix_" in d else ""
        print(f"  ✅  {d}{tag}")

    print(f"\nRounds per mode : {args.rounds}")
    print(f"Mode            : {args.mode}")
    print(f"Hands/matchup   : {args.hands}")
    if args.mode in ['multi-table', 'both']:
        print(f"Table size      : {args.table_size}")
        print(f"Min encounters  : {args.min_encounters}")
    print("=" * 80)

    batch6_dir = Path("tournament_reports/Batch6")
    batch6_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == 'both':
        modes_to_run = [('HeadsUp', 'heads-up'), ('MultiTable', 'multi-table')]
    elif args.mode == 'heads-up':
        modes_to_run = [('HeadsUp', 'heads-up')]
    else:
        modes_to_run = [('MultiTable', 'multi-table')]

    for mode_name, mode_type in modes_to_run:
        print(f"\n{'='*80}")
        print(f"STARTING {mode_name.upper()} ROUNDS")
        print(f"{'='*80}\n")

        mode_dir = batch6_dir / mode_name
        mode_dir.mkdir(parents=True, exist_ok=True)

        for round_num in range(1, args.rounds + 1):
            print(f"\n{'='*80}")
            print(f"{mode_name.upper()} — ROUND {round_num}/{args.rounds}")
            print(f"{'='*80}\n")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = mode_dir / f"round_{round_num:02d}_{timestamp}"

            cmd = [
                'python3', 'scripts/evaluation/round_robin_agents_config.py',
                '--mode',  mode_type,
                '--hands', str(args.hands),
                '--output', str(output_dir),
                '--checkpoints',
            ] + checkpoint_dirs

            if mode_type == 'multi-table':
                cmd += [
                    '--table-size',      str(args.table_size),
                    '--min-encounters',  str(args.min_encounters),
                ]

            print(f"Running {mode_name} round {round_num}...")
            print(f"Output: {output_dir}\n")

            try:
                subprocess.run(cmd, check=True)
                print(f"\n✅ {mode_name} Round {round_num} completed!")
            except subprocess.CalledProcessError as e:
                print(f"\n❌ {mode_name} Round {round_num} failed (exit {e.returncode})")
                print("   Continuing with remaining rounds...")
            except KeyboardInterrupt:
                print(f"\n⚠️  Interrupted at {mode_name} round {round_num}")
                print(f"   Completed: {round_num - 1}/{args.rounds}")
                sys.exit(1)

    # ── Final summary ────────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print("BATCH 6 TOURNAMENT COMPLETE!")
    print(f"{'='*80}")

    if args.mode == 'both':
        print(f"Completed {args.rounds} HeadsUp + {args.rounds} MultiTable rounds")
    else:
        print(f"Completed {args.rounds} {args.mode} rounds")

    print(f"\nResults saved to: {batch6_dir}")
    print()
    for mode_subdir in sorted(batch6_dir.iterdir()):
        if mode_subdir.is_dir() and mode_subdir.name in ['HeadsUp', 'MultiTable']:
            rounds = sorted(mode_subdir.glob("round_*"))
            print(f"{mode_subdir.name} Results ({len(rounds)} rounds):")
            for r in rounds:
                print(f"  - {r.name}")
    print()

    summary = {
        'batch': 'Batch6',
        'description': (
            'Aggression fix A/B: features[15]=facing_raise (B6) vs '
            'features[15]=0.5 constant (B5 baseline)'
        ),
        'date': datetime.now().isoformat(),
        'num_configs': len(checkpoint_dirs),
        'num_rounds_per_mode': args.rounds,
        'mode': args.mode,
        'hands_per_matchup': args.hands,
        'headsup_rounds': args.rounds if args.mode in ['heads-up', 'both'] else 0,
        'multitable_rounds': args.rounds if args.mode in ['multi-table', 'both'] else 0,
        'configs': checkpoint_dirs,
    }
    summary_file = batch6_dir / 'tournament_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Summary JSON: {summary_file}")
    print()


if __name__ == '__main__':
    main()
