#!/usr/bin/env python3
"""
Run Batch 4 configurations by calling train.py script.
Each configuration runs as an isolated subprocess for clean separation.

Batch 4 strategy:
- Survivors trimmed to 3 (one representative per proven cluster) for baseline
- NEW: seeded fine-tune runs — start from B3 champion weights, low σ (0.04-0.06)
  This is the highest-value thing we haven't tried: fix the feature bug + refine.
- NEW: σ=0.05-0.07 from random init (to confirm exploitation range works cold-start)
- NEW: mixed-format (30% HU) to train format-agnostic agents
- Retired: all m=9, dead-zone p40, and bulk of redundant survivor re-runs
"""
import sys
import subprocess
from pathlib import Path

# Path to the best B3 champion weights for seeded fine-tuning
_CHAMP_DIR = Path(__file__).parent / 'hall_of_fame' / 'champions'
_CHAMP = {
    'p12_m7': str(_CHAMP_DIR / 'p12_m7_h500_s0.08_g200_b3_champion.npy'),
    'p12_m8': str(_CHAMP_DIR / 'p12_m8_h500_s0.09_g200_b3_champion.npy'),
    'p40_m8': str(_CHAMP_DIR / 'p40_m8_h750_s0.07_g200_b3_champion.npy'),
    # MT specialist: 0% HU win rate but top-3 MT in every tournament group
    'mt_specialist': str(_CHAMP_DIR / 'p12_m8_h750_s0.1_g200_b3_champion.npy'),
}

# ── Batch 4 configurations ──────────────────────────────────────────────────
configs = [
    # ── 3 Survivor baselines (one per proven cluster, cold-start for comparison) ──
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.09},
    {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.08},
    {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.1},

    # ── Seeded fine-tune: start from B3 champion, low σ (highest value) ──
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
     'seed_weights': _CHAMP['p12_m8']},
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06,
     'seed_weights': _CHAMP['p12_m8']},
    {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.05,
     'seed_weights': _CHAMP['p12_m7']},
    {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,
     'seed_weights': _CHAMP['p12_m7']},
    {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.05,
     'seed_weights': _CHAMP['p40_m8']},
    {'pop': 40, 'matchups': 8, 'hands': 375, 'sigma': 0.06,
     'seed_weights': _CHAMP['p40_m8']},

    # ── σ=0.05-0.07 cold-start sweep (exploitation range from random init) ──
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.07},
    {'pop': 12, 'matchups': 8, 'hands': 375, 'sigma': 0.07},
    {'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.07},
    {'pop': 20, 'matchups': 8, 'hands': 500, 'sigma': 0.07},
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06},
    {'pop': 20, 'matchups': 7, 'hands': 500, 'sigma': 0.06},

    # ── Mixed-format HU+MT (30% heads-up matchups) ──
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.08,
     'hu_fraction': 0.3, 'hu_hands': 300},
    {'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.08,
     'hu_fraction': 0.3, 'hu_hands': 300},

    # ── MT specialist seeded fine-tune (confirmed 55-58% MT win rate across all groups) ──
    # Pure MT: no HU pressure, let it deepen its survival/stack-building strategy
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
     'seed_weights': _CHAMP['mt_specialist']},
    # Mixed MT: small HU exposure to avoid complete HU blindness while keeping MT strength
    {'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
     'seed_weights': _CHAMP['mt_specialist'],
     'hu_fraction': 0.3, 'hu_hands': 300},
]

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run specific 29 configs efficiently')
    parser.add_argument('--gens', '--generations', type=int, nargs='+', default=[50, 200],
                       help='Generations to run (default: 50 200)')
    parser.add_argument('--output', default='hyperparam_results',
                       help='Output directory')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed base')
    
    # Hall of Fame options
    hof_group = parser.add_mutually_exclusive_group()
    hof_group.add_argument('--hof-dir', type=str,
                          help='Directory containing best_genome.npy, hall_of_fame.npy, or population.npy')
    hof_group.add_argument('--hof-paths', nargs='+', type=str,
                          help='Specific .npy files to load as HoF opponents')
    hof_group.add_argument('--tournament-winners', action='store_true',
                          help='Automatically load top tournament winner checkpoints')
    parser.add_argument('--hof-count', type=int, default=3,
                       help='Maximum number of HoF opponents to load (default: 3)')
    # Removed --workers argument: workers are now auto-selected based on workload
    # (1 worker for <100k hands/gen, 4 workers for >100k hands/gen)
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip configs whose checkpoint directory already exists')
    
    args = parser.parse_args()
    
    # Build HoF arguments for train.py
    hof_args = []
    if args.tournament_winners:
        # Find and pass all champion paths directly (no cap — load every champion)
        champions_dir = Path(__file__).parent / 'hall_of_fame' / 'champions'
        if champions_dir.exists():
            champion_files = sorted(champions_dir.glob('*.npy'))
            if champion_files:
                hof_args = ['--hof-paths'] + [str(f) for f in champion_files]
                print(f"\n📂 Will load {len(champion_files)} Hall of Fame champions")
    elif args.hof_dir:
        hof_args = ['--hof-dir', args.hof_dir, '--hof-count', str(args.hof_count)]
        print(f"\n📂 Will load Hall of Fame from: {args.hof_dir}")
    elif args.hof_paths:
        hof_args = ['--hof-paths'] + args.hof_paths
        print(f"\n📂 Will load {len(args.hof_paths)} Hall of Fame opponents")
    
    print("="*70)
    print(f"RUNNING {len(configs)} SPECIFIC CONFIGS VIA TRAIN.PY")
    print("="*70)
    print(f"Configurations: {len(configs)}")
    print(f"Generations: {args.gens}")
    print(f"Total runs: {len(configs) * len(args.gens)}")
    if hof_args:
        print(f"HoF arguments: {' '.join(hof_args)}")
    print("="*70)
    print()
    
    from datetime import datetime
    import json
    import time
    
    # Create output directory for results tracking
    out_dir = Path(args.output) / f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    total = len(configs) * len(args.gens)
    current = 0
    
    for gen_count in args.gens:
        for i, cfg in enumerate(configs):
            current += 1
            # Include HOF count in name to match existing checkpoint naming convention
            hof_suffix = f"_hof{args.hof_count}" if hof_args else ""
            hu_suffix = f"_hu{int(cfg.get('hu_fraction', 0)*100)}" if cfg.get('hu_fraction') else ""
            seed_suffix = "_seeded" if cfg.get('seed_weights') else ""
            name = f"p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}_s{cfg['sigma']}{hu_suffix}{seed_suffix}{hof_suffix}_g{gen_count}"
            
            print(f"\n[{current}/{total}] {name}")
            print("="*70)
            
            # Build training config with deep_ prefix in output directory
            checkpoint_dir = Path("checkpoints") / f"deep_{name}"
            
            total_hands = cfg['pop'] * cfg['matchups'] * cfg['hands']
            
            # Determine optimal workers based on workload
            # Use 8 workers if workload > 50k hands (leaves headroom for gaming/multitasking on 16-core system)
            # Use 1 worker for smaller workloads to avoid multiprocessing overhead
            workers = 8 if total_hands > 50000 else 1
            
            # Skip if checkpoint already exists WITH actual trained weights
            # (a directory alone doesn't count — it may be an empty/aborted run)
            runs_dir = checkpoint_dir / "runs"
            has_weights = runs_dir.exists() and any(runs_dir.rglob("best_genome.npy"))
            if args.skip_existing and has_weights:
                print(f"  ⏭  Skipping (checkpoint exists): {checkpoint_dir.name}")
                current_skipped = getattr(args, '_skipped', 0) + 1
                args._skipped = current_skipped
                continue

            print(f"Config: pop={cfg['pop']}, m={cfg['matchups']}, h={cfg['hands']}, sig={cfg['sigma']}")
            print(f"Total hands/gen: {total_hands:,}")
            print(f"Workers: {workers} (auto-selected based on workload)")
            
            # Build train.py command
            cmd = [
                'python3', 'scripts/training/train.py',
                '--pop', str(cfg['pop']),
                '--matchups', str(cfg['matchups']),
                '--hands', str(cfg['hands']),
                '--sigma', str(cfg['sigma']),
                '--gens', str(gen_count),
                '--workers', str(workers),
                '--players', '6',  # 6-max poker (default)
                '--output', str(checkpoint_dir),
                '--name', 'evolution_run',
                '--seed', str(args.seed + current),
                '--checkpoint-interval', '999',  # Only save at end
            ] + hof_args

            # Mixed-format options (optional per-config)
            if cfg.get('hu_fraction'):
                cmd += ['--heads-up-fraction', str(cfg['hu_fraction'])]
            if cfg.get('hu_hands'):
                cmd += ['--hu-hands', str(cfg['hu_hands'])]
            # Seeded fine-tune: warm-start from an existing champion
            if cfg.get('seed_weights') and Path(cfg['seed_weights']).exists():
                cmd += ['--seed-weights', cfg['seed_weights']]
                print(f"Seeded from: {Path(cfg['seed_weights']).name}")
            
            print(f"Running: {' '.join(cmd)}")
            print()
            
            try:
                t0 = time.time()
                result = subprocess.run(cmd, check=True)
                elapsed = time.time() - t0
                
                print(f"\n✅ Completed in {elapsed:.1f}s")
                
                # Try to read final fitness from checkpoint
                state_file = checkpoint_dir / 'runs' / sorted((checkpoint_dir / 'runs').glob('run_*'))[-1] / 'state.json' if (checkpoint_dir / 'runs').exists() else None
                final_fitness = None
                if state_file and state_file.exists():
                    with open(state_file) as f:
                        state = json.load(f)
                        final_fitness = state.get('best_fitness', None)
                
                result_entry = {
                    'name': name,
                    'config': {
                        'population_size': cfg['pop'],
                        'matchups_per_agent': cfg['matchups'],
                        'hands_per_matchup': cfg['hands'],
                        'mutation_sigma': cfg['sigma'],
                        'generations': gen_count
                    },
                    'total_hands_per_gen': total_hands,
                    'total_time': elapsed,
                    'final_best_fitness': final_fitness,
                    'status': 'completed'
                }
                
                results.append(result_entry)
                
            except subprocess.CalledProcessError as e:
                print(f"\n❌ Failed with exit code {e.returncode}")
                result_entry = {
                    'name': name,
                    'config': cfg,
                    'status': 'failed',
                    'error': f'Exit code {e.returncode}'
                }
                results.append(result_entry)
                
            except KeyboardInterrupt:
                print("\n[Interrupted]")
                break
            
            # Save incrementally
            with open(out_dir / 'results.json', 'w') as f:
                json.dump(results, f, indent=2)
    
    if not results:
        print("\n❌ No results collected")
        return
    
    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    
    completed = [r for r in results if r.get('status') == 'completed' and r.get('final_best_fitness')]
    failed = [r for r in results if r.get('status') == 'failed']
    
    if completed:
        by_fitness = sorted(completed, key=lambda x: x.get('final_best_fitness', 0), reverse=True)
        
        print(f"\n✅ Completed: {len(completed)}/{len(results)}")
        if failed:
            print(f"❌ Failed: {len(failed)}/{len(results)}")
        
        print("\n🎯 Top 5 by Final Fitness:")
        for r in by_fitness[:5]:
            print(f"  {r['name']:40s} Fitness: {r['final_best_fitness']:+7.1f}  Time: {r.get('total_time', 0):.1f}s")
    else:
        print("\n⚠️  No completed runs with fitness data")
    
    print(f"\n📊 Results saved to: {out_dir}")
    print(f"   - results.json (detailed data)")
    print("\n✅ Done!")


if __name__ == '__main__':
    main()