#!/usr/bin/env python3
"""
Run Batch 5 tournament: All completed Batch 5 configurations.
Saves results to tournament_reports/Batch5/

Batch 5 includes:
  MT track  — σ fine-sweep {0.04, 0.045, 0.05, 0.06} × seeded + cold-start
  HU track  — h={250, 375} × σ={0.05, 0.06, 0.07} × seeded
  Survivors — B3 calibration configs (σ=0.09, σ=0.08)
  All runs: g50 only

Usage:
  python run_batch5_tournament.py                    # 10 rounds, both modes
  python run_batch5_tournament.py --mode multi-table # MT only
  python run_batch5_tournament.py --rounds 5         # 5 rounds each
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime


def get_valid_checkpoints():
    """Return checkpoint directory names that have actual trained weights."""
    checkpoints = Path("checkpoints")

    # All B5 config families (mirrors run_batch5_configs.py)
    configs = [
        # MT seeded
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,   'seeded': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.045,  'seeded': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,   'seeded': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06,   'seeded': True},
        # MT cold-start
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,   'seeded': False},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,   'seeded': False},
        # HU seeded (heads_up_fraction=1.0 → _hu100_ suffix)
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.05,   'seeded': True,  'hu': True},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,   'seeded': True,  'hu': True},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.07,   'seeded': True,  'hu': True},
        {'pop': 12, 'matchups': 7, 'hands': 250, 'sigma': 0.06,   'seeded': True,  'hu': True},
        {'pop': 12, 'matchups': 7, 'hands': 250, 'sigma': 0.05,   'seeded': True,  'hu': True},
        # Cross-batch survivors (cold, no HU)
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.09,   'seeded': False},
        {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.08,   'seeded': False},
    ]

    valid = []
    seen = set()

    for cfg in configs:
        seed_sfx = "_seeded" if cfg['seeded'] else ""
        hu_sfx   = "_hu100"  if cfg.get('hu') else ""
        name = (
            f"deep_p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}"
            f"_s{cfg['sigma']}{hu_sfx}{seed_sfx}_hof3_g50"
        )
        if name in seen:
            continue
        seen.add(name)

        runs_dir = checkpoints / name / "runs"
        if runs_dir.exists() and any(runs_dir.rglob("best_genome.npy")):
            valid.append(name)
        else:
            print(f"  ⚠️  Skipping (no weights): {name}")

    return valid


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Batch 5 tournament with all completed configs'
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
    args = parser.parse_args()

    print("=" * 80)
    print("BATCH 5 TOURNAMENT — B5 σ Fine-Sweep + HU h-Sweep")
    print("=" * 80)

    checkpoint_dirs = get_valid_checkpoints()

    if not checkpoint_dirs:
        print("\n❌ No valid checkpoints found.")
        print("   Run  python run_batch5_configs.py  first.")
        sys.exit(1)

    print(f"\nValid checkpoints: {len(checkpoint_dirs)}")
    for d in checkpoint_dirs:
        print(f"  ✅  {d}")

    print(f"\nRounds per mode : {args.rounds}")
    print(f"Mode            : {args.mode}")
    print(f"Hands/matchup   : {args.hands}")
    if args.mode in ['multi-table', 'both']:
        print(f"Table size      : {args.table_size}")
        print(f"Min encounters  : {args.min_encounters}")
    print("=" * 80)

    batch5_dir = Path("tournament_reports/Batch5")
    batch5_dir.mkdir(parents=True, exist_ok=True)

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

        mode_dir = batch5_dir / mode_name
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
    print("BATCH 5 TOURNAMENT COMPLETE!")
    print(f"{'='*80}")

    if args.mode == 'both':
        print(f"Completed {args.rounds} HeadsUp + {args.rounds} MultiTable rounds")
    else:
        print(f"Completed {args.rounds} {args.mode} rounds")

    print(f"\nResults saved to: {batch5_dir}")
    print()
    for mode_subdir in sorted(batch5_dir.iterdir()):
        if mode_subdir.is_dir() and mode_subdir.name in ['HeadsUp', 'MultiTable']:
            rounds = sorted(mode_subdir.glob("round_*"))
            print(f"{mode_subdir.name} Results ({len(rounds)} rounds):")
            for r in rounds:
                print(f"  - {r.name}")
    print()

    summary = {
        'batch': 'Batch5',
        'description': (
            'σ fine-sweep {0.04, 0.045, 0.05, 0.06} MT + '
            'h={250,375}×σ={0.05,0.06,0.07} HU + B3 survivor calibration'
        ),
        'date': datetime.now().isoformat(),
        'num_configs': len(checkpoint_dirs),
        'num_rounds_per_mode': args.rounds,
        'mode': args.mode,
        'hands_per_matchup': args.hands,
        'headsup_rounds': args.rounds if args.mode in ['heads-up', 'both'] else 0,
        'multitable_rounds': args.rounds if args.mode in ['multi-table', 'both'] else 0,
        'multitable_settings': {
            'table_size': args.table_size,
            'min_encounters': args.min_encounters,
        } if args.mode in ['multi-table', 'both'] else None,
        'checkpoint_dirs': checkpoint_dirs,
        'key_questions': [
            'Does σ=0.04 beat σ=0.05 for MT, or is 0.05 the true floor?',
            'Does seeded warm-start produce measurably better agents vs cold-start at same σ?',
            'Does h=250 improve or hurt HeadsUp vs h=375?',
            'Are B3 survivors (σ=0.08, σ=0.09) still regressing vs B4 configs?',
        ],
    }

    summary_file = batch5_dir / 'batch5_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {summary_file}")
    print("\nNext step: python scripts/analysis/analyze_tournament_history.py \\")
    print("    --folder tournament_reports/Batch5/ \\")
    print("    --top-n 20 \\")
    print("    --output-dir tournament_reports/overall_reports/Batch5_Overall_Report")
    print("\n✅ All done!")


if __name__ == '__main__':
    main()
