#!/usr/bin/env python3
"""
Hyperparameter sweep with fixed benchmark opponents for fair comparison.

This solves the problem where training fitness is non-comparable across runs
because each config trains against different opponents (self-play).

Key difference: All configs are evaluated against the SAME fixed opponents,
making fitness scores directly comparable.

Usage:
    # Use default grid
    python hyperparam_sweep_with_benchmark.py
    
    # Custom grid
    python hyperparam_sweep_with_benchmark.py --pop 30 40 50 --matchups 8 10 --hands 375 450 --sigma 0.1 0.12
"""
import sys
import json
import time
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from itertools import product

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from training.evolution import EvolutionTrainer
from training.config import TrainingConfig, NetworkConfig, EvolutionConfig, FitnessConfig


def load_benchmark_opponents(benchmark_paths: list) -> list:
    """Load fixed opponents for evaluation."""
    weights = []
    for path_str in benchmark_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Warning: Benchmark {path} not found")
            continue
        try:
            loaded = np.load(path)
            if loaded.ndim == 2:
                weights.append(loaded[0])
            else:
                weights.append(loaded)
            print(f"Loaded benchmark: {path.name}")
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return weights


def evaluate_against_benchmarks(trainer, benchmark_weights, num_hands=1000):
    """
    Evaluate best genome against fixed benchmark opponents.
    
    Returns BB/100 against the benchmark suite.
    """
    from training.fitness import evaluate_fixed_hands
    
    if not benchmark_weights or trainer.best_genome is None:
        return None
    
    # Generate fixed hand seeds for reproducibility
    eval_seeds = list(range(num_hands))
    
    total_delta = 0
    total_hands = 0
    
    for i, opponent_weights in enumerate(benchmark_weights):
        seed = 88888 + i * 1000
        delta, hands = evaluate_fixed_hands(
            trainer.best_genome.weights,
            opponent_weights,
            trainer.config.network,
            trainer.config.fitness,
            eval_seeds,
            seed
        )
        total_delta += delta
        total_hands += hands
    
    # total_delta is already in big blinds
    bb_per_100 = total_delta * (100 / max(1, total_hands))

    return bb_per_100


def run_sweep():
    """Run hyperparameter sweep with fixed benchmark evaluation."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Hyperparameter sweep with benchmark evaluation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default grid (recommended from tournament analysis)
  python hyperparam_sweep_with_benchmark.py
  
  # Focus on tournament winner region
  python hyperparam_sweep_with_benchmark.py --pop 30 40 50 --matchups 8 10 12 --hands 300 375 450 --sigma 0.08 0.1 0.12
  
  # Fast sweep
  python hyperparam_sweep_with_benchmark.py --pop 12 20 --matchups 6 8 --hands 375 500 --sigma 0.1
  
  # Single config test
  python hyperparam_sweep_with_benchmark.py --pop 40 --matchups 8 --hands 375 --sigma 0.1
        """
    )
    
    parser.add_argument('--pop', '--population', nargs='+', type=int,
                       default=[12, 20, 30, 50],
                       help='Population sizes to test (default: 12 20 30 50)')
    parser.add_argument('--matchups', nargs='+', type=int,
                       default=[4, 6, 8],
                       help='Matchups per agent to test (default: 4 6 8)')
    parser.add_argument('--hands', nargs='+', type=int,
                       default=[500, 750, 1000],
                       help='Hands per matchup to test (default: 500 750 1000)')
    parser.add_argument('--sigma', '--mutation', nargs='+', type=float,
                       default=[0.1, 0.15, 0.2],
                       help='Mutation sigma values to test (default: 0.1 0.15 0.2)')
    parser.add_argument('--gens', '--generations', type=int, default=30,
                       help='Generations per config (default: 30)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Base random seed (default: 42)')
    parser.add_argument('--benchmark-hands', type=int, default=500,
                       help='Hands per benchmark opponent (default: 500)')
    
    args = parser.parse_args()
    
    # Load benchmark opponents (use tournament winners)
    benchmark_paths = [
        'checkpoints/deep_p40_m6_h500_s0.15/runs/run_20260126_042643/best_genome.npy',
        'checkpoints/deep_p40_m8_h375_s0.1/runs/run_20260126_093215/best_genome.npy',
        'checkpoints/deep_p20_m6_h500_s0.15/runs/run_20260126_000023/best_genome.npy',
        'checkpoints/deep_p12_m6_h500_s0.15/runs/run_20260125_222103/best_genome.npy',
    ]
    
    print("="*70)
    print("LOADING BENCHMARK OPPONENTS")
    print("="*70)
    benchmark_weights = load_benchmark_opponents(benchmark_paths)
    print(f"\nLoaded {len(benchmark_weights)} benchmark opponents\n")
    
    if not benchmark_weights:
        print("ERROR: No benchmark opponents loaded. Exiting.")
        return
    
    # Hyperparameter grid from command-line args
    param_grid = {
        'population_size': args.pop,
        'matchups_per_agent': args.matchups,
        'hands_per_matchup': args.hands,
        'mutation_sigma': args.sigma,
    }
    
    # Generate all combinations
    configs = list(product(
        param_grid['population_size'],
        param_grid['matchups_per_agent'],
        param_grid['hands_per_matchup'],
        param_grid['mutation_sigma']
    ))
    
    total_configs = len(configs)
    print(f"Testing {total_configs} configurations")
    print(f"Each config: {args.gens} generations + benchmark evaluation")
    print(f"Parameter grid:")
    print(f"  Population: {param_grid['population_size']}")
    print(f"  Matchups: {param_grid['matchups_per_agent']}")
    print(f"  Hands: {param_grid['hands_per_matchup']}")
    print(f"  Sigma: {param_grid['mutation_sigma']}")
    print("="*70)
    
    # Output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sweep_dir = Path('hyperparam_results') / f'benchmark_sweep_{timestamp}'
    sweep_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # Prepare sweep input metadata
    sweep_input = {
        'pop': args.pop,
        'matchups': args.matchups,
        'hands': args.hands,
        'sigmas': args.sigma,
        'generations': args.gens,
        'timestamp': datetime.now().isoformat()
    }
    
    for idx, (pop, matchups, hands, sigma) in enumerate(configs, 1):
        config_name = f"p{pop}_m{matchups}_h{hands}_s{sigma}"
        print(f"\n[{idx}/{total_configs}] {config_name}")
        print("-" * 60)
        
        # Create config
        config = TrainingConfig(
            network=NetworkConfig(
                input_size=17,
                hidden_sizes=[128, 128],
                output_size=6,
            ),
            evolution=EvolutionConfig(
                population_size=pop,
                mutation_sigma=sigma,
                num_elites=max(2, pop // 10),
                num_immigrants=max(1, pop // 20),
            ),
            fitness=FitnessConfig(
                matchups_per_agent=matchups,
                hands_per_matchup=hands,
                num_players=2,
            ),
            num_generations=args.gens,
            seed=args.seed + idx,
            experiment_name=f'sweep_{config_name}',
            log_interval=5,
            checkpoint_interval=999,  # Don't checkpoint during sweep
        )
        
        # Train
        start_time = time.time()
        trainer = EvolutionTrainer(config)
        trainer.initialize()
        
        try:
            trainer.train(monitor_eval=False)  # Skip internal eval for speed
            train_time = time.time() - start_time
            
            # Evaluate against benchmarks
            print(f"\n  Evaluating against benchmark suite...")
            benchmark_fitness = evaluate_against_benchmarks(
                trainer, 
                benchmark_weights,
                num_hands=500  # 500 hands per benchmark opponent
            )
            
            # Collect results
            result = {
                'name': config_name,
                'config': {
                    'population_size': pop,
                    'matchups_per_agent': matchups,
                    'hands_per_matchup': hands,
                    'mutation_sigma': sigma,
                    'generations': 30,
                },
                'total_hands_per_gen': pop * matchups * hands,
                'avg_gen_time': train_time / 30,
                'total_train_time': train_time,
                'final_train_fitness': float(trainer.best_fitness),
                'benchmark_fitness': float(benchmark_fitness) if benchmark_fitness else None,
                'convergence': float(trainer.best_fitness - trainer.history[0]['max_fitness']) if trainer.history else 0,
                'final_generation': trainer.generation,
            }
            
            results.append(result)
            
            print(f"  Training fitness:  {result['final_train_fitness']:+8.2f} BB/100")
            print(f"  Benchmark fitness: {result['benchmark_fitness']:+8.2f} BB/100")
            print(f"  Time: {train_time:.1f}s ({train_time/60:.1f} min)")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'name': config_name,
                'config': asdict(config),
                'error': str(e)
            })
        
        # Save intermediate results
        output_data = {
            'sweep_input': sweep_input,
            'results': results
        }
        with open(sweep_dir / 'results.json', 'w') as f:
            json.dump(output_data, f, indent=2)
    
    # Generate report
    print("\n" + "="*70)
    print("SWEEP COMPLETE")
    print("="*70)
    
    # Sort by benchmark fitness (the fair comparison)
    valid_results = [r for r in results if 'benchmark_fitness' in r and r['benchmark_fitness'] is not None]
    valid_results.sort(key=lambda x: x['benchmark_fitness'], reverse=True)
    
    print("\n🏆 TOP 10 BY BENCHMARK FITNESS (vs Fixed Opponents)")
    print("-" * 70)
    for i, result in enumerate(valid_results[:10], 1):
        print(f"{i:2d}. {result['name']:25s} "
              f"Benchmark: {result['benchmark_fitness']:+7.2f} "
              f"Train: {result['final_train_fitness']:+7.2f} "
              f"Time: {result['avg_gen_time']:.1f}s/gen")
    
    # Save final report
    report_path = sweep_dir / 'report.txt'
    with open(report_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("HYPERPARAMETER SWEEP WITH BENCHMARK EVALUATION\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total configs: {total_configs}\n")
        f.write(f"Benchmark opponents: {len(benchmark_weights)}\n")
        f.write(f"Generations per config: 30\n\n")
        
        f.write("TOP 10 CONFIGURATIONS (by benchmark fitness)\n")
        f.write("-"*70 + "\n")
        for i, result in enumerate(valid_results[:10], 1):
            f.write(f"{i:2d}. {result['name']}\n")
            f.write(f"    Benchmark fitness: {result['benchmark_fitness']:+7.2f} BB/100\n")
            f.write(f"    Training fitness:  {result['final_train_fitness']:+7.2f} BB/100\n")
            f.write(f"    Config: pop={result['config']['population_size']}, "
                   f"matchups={result['config']['matchups_per_agent']}, "
                   f"hands={result['config']['hands_per_matchup']}, "
                   f"sigma={result['config']['mutation_sigma']}\n")
            f.write(f"    Time: {result['avg_gen_time']:.1f}s/gen\n\n")
        
        f.write("\n" + "="*70 + "\n")
        f.write("KEY INSIGHT:\n")
        f.write("Benchmark fitness = performance vs fixed opponents (fair comparison)\n")
        f.write("Training fitness = performance vs self-play opponents (not comparable)\n")
        f.write("="*70 + "\n")
    
    print(f"\n📊 Results saved to: {sweep_dir}")
    print(f"    - results.json (raw data)")
    print(f"    - report.txt (summary)\n")


if __name__ == '__main__':
    run_sweep()
