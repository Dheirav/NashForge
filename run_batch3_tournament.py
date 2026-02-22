#!/usr/bin/env python3
"""
Run Batch3 tournament: All 58 completed configurations (29 configs × 2 gen counts)
Runs 10 tournament rounds and saves results to tournament_reports/Batch3/
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

# All 58 completed configurations
configs = [
    # p12 configs
    {'pop': 12, 'matchups': 9, 'hands': 750, 'sigma': 0.09},
    {'pop': 12, 'matchups': 8, 'hands': 375, 'sigma': 0.1},
    {'pop': 12, 'matchups': 9, 'hands': 375, 'sigma': 0.1},
    {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.09},
    {'pop': 12, 'matchups': 8, 'hands': 750, 'sigma': 0.1},
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.09},
    {'pop': 12, 'matchups': 8, 'hands': 750, 'sigma': 0.09},
    {'pop': 12, 'matchups': 7, 'hands': 750, 'sigma': 0.08},
    {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.08},
    {'pop': 12, 'matchups': 7, 'hands': 750, 'sigma': 0.09},
    {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.08},
    
    # p20 configs
    {'pop': 20, 'matchups': 8, 'hands': 500, 'sigma': 0.09},
    {'pop': 20, 'matchups': 8, 'hands': 375, 'sigma': 0.1},
    {'pop': 20, 'matchups': 9, 'hands': 750, 'sigma': 0.1},
    {'pop': 20, 'matchups': 7, 'hands': 750, 'sigma': 0.09},
    {'pop': 20, 'matchups': 9, 'hands': 500, 'sigma': 0.09},
    {'pop': 20, 'matchups': 9, 'hands': 750, 'sigma': 0.09},
    {'pop': 20, 'matchups': 9, 'hands': 500, 'sigma': 0.1},
    {'pop': 20, 'matchups': 7, 'hands': 375, 'sigma': 0.08},
    
    # p40 configs
    {'pop': 40, 'matchups': 9, 'hands': 750, 'sigma': 0.1},
    {'pop': 40, 'matchups': 7, 'hands': 375, 'sigma': 0.1},
    {'pop': 40, 'matchups': 9, 'hands': 375, 'sigma': 0.1},
    {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.1},
    {'pop': 40, 'matchups': 7, 'hands': 750, 'sigma': 0.08},
    {'pop': 40, 'matchups': 9, 'hands': 500, 'sigma': 0.08},
    {'pop': 40, 'matchups': 8, 'hands': 750, 'sigma': 0.08},
    {'pop': 40, 'matchups': 7, 'hands': 500, 'sigma': 0.1},
    {'pop': 40, 'matchups': 8, 'hands': 500, 'sigma': 0.1},
    {'pop': 40, 'matchups': 8, 'hands': 750, 'sigma': 0.07},
]

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run Batch3 tournament with all 58 configs')
    parser.add_argument('--rounds', type=int, default=10,
                       help='Number of tournament rounds to run per mode (default: 10)')
    parser.add_argument('--mode', type=str, choices=['heads-up', 'multi-table', 'both'], default='both',
                       help='Tournament mode: heads-up, multi-table, or both (default: both)')
    parser.add_argument('--hands', type=int, default=10000,
                       help='Hands per matchup (default: 10000)')
    parser.add_argument('--table-size', type=int, default=6,
                       help='Players per table for multi-table mode (default: 6)')
    parser.add_argument('--min-encounters', type=int, default=50,
                       help='Minimum encounters per pair in multi-table mode (default: 50)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("BATCH3 TOURNAMENT - All 58 Completed Configurations")
    print("=" * 80)
    print(f"Total configurations: {len(configs) * 2} (29 configs × 2 gen counts)")
    print(f"Tournament rounds per mode: {args.rounds}")
    print(f"Mode: {args.mode}")
    print(f"Hands per matchup: {args.hands}")
    if args.mode in ['multi-table', 'both']:
        print(f"Players per table: {args.table_size}")
        print(f"Minimum encounters: {args.min_encounters}")
    print("=" * 80)
    print()
    
    # Build list of checkpoint directories
    checkpoint_dirs = []
    gen_counts = [50, 200]
    
    for gen_count in gen_counts:
        for cfg in configs:
            name = f"deep_p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}_s{cfg['sigma']}_hof3_g{gen_count}"
            checkpoint_dirs.append(name)
    
    print(f"Collected {len(checkpoint_dirs)} checkpoint directories")
    print()
    
    # Create base output directory
    batch3_dir = Path("tournament_reports/Batch3")
    batch3_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine which modes to run
    modes_to_run = []
    if args.mode == 'both':
        modes_to_run = [('HeadsUp', 'heads-up'), ('MultiTable', 'multi-table')]
    elif args.mode == 'heads-up':
        modes_to_run = [('HeadsUp', 'heads-up')]
    else:
        modes_to_run = [('MultiTable', 'multi-table')]
    
    # Run tournaments for each mode
    for mode_name, mode_type in modes_to_run:
        print(f"\n{'='*80}")
        print(f"STARTING {mode_name.upper()} TOURNAMENTS")
        print(f"{'='*80}\n")
        
        # Create subdirectory for this mode
        mode_dir = batch3_dir / mode_name
        mode_dir.mkdir(parents=True, exist_ok=True)
        
        for round_num in range(1, args.rounds + 1):
            print(f"\n{'='*80}")
            print(f"{mode_name.upper()} - ROUND {round_num}/{args.rounds}")
            print(f"{'='*80}\n")
            
            # Create output directory for this round
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = mode_dir / f"round_{round_num:02d}_{timestamp}"
            
            # Build command
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
                print(f"Continuing with remaining rounds...")
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Tournament interrupted by user at {mode_name} round {round_num}")
                print(f"Completed rounds: {round_num - 1}/{args.rounds}")
                sys.exit(1)
    
    print(f"\n{'='*80}")
    print("BATCH3 TOURNAMENT COMPLETE!")
    print(f"{'='*80}")
    if args.mode == 'both':
        print(f"Completed {args.rounds} HeadsUp rounds + {args.rounds} MultiTable rounds")
    else:
        print(f"Completed {args.rounds} tournament rounds ({args.mode})")
    print(f"Results saved to: {batch3_dir}")
    print()
    
    # List completed modes
    for mode_subdir in sorted(batch3_dir.iterdir()):
        if mode_subdir.is_dir() and mode_subdir.name in ['HeadsUp', 'MultiTable']:
            print(f"\n{mode_subdir.name} Results:")
            for round_dir in sorted(mode_subdir.glob("round_*")):
                print(f"  - {round_dir.name}")
    print()
    
    # Create summary file
    summary_file = batch3_dir / "batch3_summary.json"
    summary = {
        'batch': 'Batch3',
        'description': 'Tournament of all 58 completed configurations (29 configs × 2 gen counts)',
        'date': datetime.now().isoformat(),
        'num_configs': len(configs) * 2,
        'num_rounds_per_mode': args.rounds,
        'modes': args.mode,
        'hands_per_matchup': args.hands,
        'headsup_rounds': args.rounds if args.mode in ['heads-up', 'both'] else 0,
        'multitable_rounds': args.rounds if args.mode in ['multi-table', 'both'] else 0,
        'multitable_settings': {
            'table_size': args.table_size,
            'min_encounters': args.min_encounters
        } if args.mode in ['multi-table', 'both'] else None
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_file}")
    print("\n✅ All done!")


if __name__ == '__main__':
    main()
