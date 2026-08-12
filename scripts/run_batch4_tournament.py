#!/usr/bin/env python3
"""
Run Batch4 tournament: All completed Batch 4 configurations
Runs tournament rounds and saves results to tournament_reports/Batch4/

Batch 4 includes:
  - 3 survivor baselines (cold-start)
  - 9 seeded fine-tune runs (warm-start from B3 champion weights)
  - 5 cold-start sigma sweep runs (σ=0.06-0.07)
  - 2 mixed-format HU+MT runs (30% heads-up)
  - 1 MT specialist seeded run
  - 1 MT specialist seeded + HU exposure run
  Each config × g50 and g200 = 36 total
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime


def get_valid_checkpoints():
    """Return checkpoint directory names that have actual trained weights."""
    checkpoints = Path("checkpoints")

    configs = [
        # Survivor baselines
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.09},
        {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.08},
        {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.1},
        # Seeded fine-tune: p12_m8 champion
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05, 'seed_weights': True},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06, 'seed_weights': True},
        # Seeded fine-tune: p12_m7 champion
        {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.05, 'seed_weights': True},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06, 'seed_weights': True},
        # Seeded fine-tune: p40_m8 champion
        {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.05, 'seed_weights': True},
        {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.06, 'seed_weights': True},
        # Cold-start sigma sweep
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.07},
        {'pop': 12, 'matchups': 8, 'hands': 375, 'sigma': 0.07},
        {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.07},
        {'pop': 20, 'matchups': 8, 'hands': 500, 'sigma': 0.07},
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06},
        {'pop': 20, 'matchups': 7, 'hands': 500, 'sigma': 0.06},
        # Mixed-format HU+MT (30% heads-up)
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.08, 'hu_fraction': 0.3},
        {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.08, 'hu_fraction': 0.3},
        # MT specialist seeded (pure MT)
        {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
         'seed_weights': True, 'hu_fraction': 0.3},
    ]

    valid = []
    seen = set()
    for gen in [50, 200]:
        for cfg in configs:
            hu_suffix = f"_hu{int(cfg.get('hu_fraction', 0)*100)}" if cfg.get('hu_fraction') else ""
            seed_suffix = "_seeded" if cfg.get('seed_weights') else ""
            name = f"deep_p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}_s{cfg['sigma']}{hu_suffix}{seed_suffix}_hof3_g{gen}"
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
    parser = argparse.ArgumentParser(description='Run Batch4 tournament with all completed configs')
    parser.add_argument('--rounds', type=int, default=10,
                        help='Number of tournament rounds to run per mode (default: 10)')
    parser.add_argument('--mode', type=str, choices=['heads-up', 'multi-table', 'both'],
                        default='both',
                        help='Tournament mode: heads-up, multi-table, or both (default: both)')
    parser.add_argument('--hands', type=int, default=10000,
                        help='Hands per matchup (default: 10000)')
    parser.add_argument('--table-size', type=int, default=6,
                        help='Players per table for multi-table mode (default: 6)')
    parser.add_argument('--min-encounters', type=int, default=50,
                        help='Minimum encounters per pair in multi-table mode (default: 50)')

    args = parser.parse_args()

    print("=" * 80)
    print("BATCH4 TOURNAMENT - All Completed Batch 4 Configurations")
    print("=" * 80)

    checkpoint_dirs = get_valid_checkpoints()

    print(f"Valid checkpoints found: {len(checkpoint_dirs)}")
    print(f"Tournament rounds per mode: {args.rounds}")
    print(f"Mode: {args.mode}")
    print(f"Hands per matchup: {args.hands}")
    if args.mode in ['multi-table', 'both']:
        print(f"Players per table: {args.table_size}")
        print(f"Minimum encounters: {args.min_encounters}")
    print("=" * 80)
    print()

    if not checkpoint_dirs:
        print("❌ No valid checkpoints found. Aborting.")
        sys.exit(1)

    # Create base output directory
    batch4_dir = Path("tournament_reports/Batch4")
    batch4_dir.mkdir(parents=True, exist_ok=True)

    # Determine which modes to run
    if args.mode == 'both':
        modes_to_run = [('HeadsUp', 'heads-up'), ('MultiTable', 'multi-table')]
    elif args.mode == 'heads-up':
        modes_to_run = [('HeadsUp', 'heads-up')]
    else:
        modes_to_run = [('MultiTable', 'multi-table')]

    for mode_name, mode_type in modes_to_run:
        print(f"\n{'='*80}")
        print(f"STARTING {mode_name.upper()} TOURNAMENTS")
        print(f"{'='*80}\n")

        mode_dir = batch4_dir / mode_name
        mode_dir.mkdir(parents=True, exist_ok=True)

        for round_num in range(1, args.rounds + 1):
            print(f"\n{'='*80}")
            print(f"{mode_name.upper()} - ROUND {round_num}/{args.rounds}")
            print(f"{'='*80}\n")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = mode_dir / f"round_{round_num:02d}_{timestamp}"

            cmd = [
                'python3', 'scripts/evaluation/round_robin_agents_config.py',
                '--mode', mode_type,
                '--hands', str(args.hands),
                '--output', str(output_dir),
                '--checkpoints'
            ] + checkpoint_dirs

            if mode_type == 'multi-table':
                cmd.extend([
                    '--table-size', str(args.table_size),
                    '--min-encounters', str(args.min_encounters)
                ])

            print(f"Running {mode_name} round {round_num}...")
            print(f"Output: {output_dir}")
            print()

            try:
                result = subprocess.run(cmd, check=True)
                print(f"\n✅ {mode_name} Round {round_num} completed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"\n❌ {mode_name} Round {round_num} failed with exit code {e.returncode}")
                print("Continuing with remaining rounds...")
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Tournament interrupted by user at {mode_name} round {round_num}")
                print(f"Completed rounds: {round_num - 1}/{args.rounds}")
                sys.exit(1)

    print(f"\n{'='*80}")
    print("BATCH4 TOURNAMENT COMPLETE!")
    print(f"{'='*80}")
    if args.mode == 'both':
        print(f"Completed {args.rounds} HeadsUp rounds + {args.rounds} MultiTable rounds")
    else:
        print(f"Completed {args.rounds} tournament rounds ({args.mode})")
    print(f"Results saved to: {batch4_dir}")
    print()

    for mode_subdir in sorted(batch4_dir.iterdir()):
        if mode_subdir.is_dir() and mode_subdir.name in ['HeadsUp', 'MultiTable']:
            print(f"\n{mode_subdir.name} Results:")
            for round_dir in sorted(mode_subdir.glob("round_*")):
                print(f"  - {round_dir.name}")
    print()

    summary_file = batch4_dir / "batch4_summary.json"
    summary = {
        'batch': 'Batch4',
        'description': 'Tournament of all completed Batch 4 configurations (18 configs × 2 gen counts)',
        'date': datetime.now().isoformat(),
        'num_configs': len(checkpoint_dirs),
        'num_rounds_per_mode': args.rounds,
        'modes': args.mode,
        'hands_per_matchup': args.hands,
        'headsup_rounds': args.rounds if args.mode in ['heads-up', 'both'] else 0,
        'multitable_rounds': args.rounds if args.mode in ['multi-table', 'both'] else 0,
        'multitable_settings': {
            'table_size': args.table_size,
            'min_encounters': args.min_encounters,
        } if args.mode in ['multi-table', 'both'] else None,
        'checkpoint_dirs': checkpoint_dirs,
    }

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {summary_file}")
    print("\n✅ All done!")


if __name__ == '__main__':
    main()
