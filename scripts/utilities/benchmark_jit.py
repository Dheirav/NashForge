#!/usr/bin/env python3
"""
Benchmark script to measure Numba JIT speedup across all optimizations.

Tests:
1. Forward pass (single)
2. Forward pass (batch)
3. Feature extraction
4. Hand evaluation
5. Genome mutation

Run with: python scripts/benchmark_jit.py
"""
import time
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from training import PolicyNetwork, NetworkConfig, GenomeFactory, EvolutionConfig, Genome
from engine import Card, get_state_vector
from engine.hand_eval_fast import find_straight_jit, count_ranks_jit
from training.policy_network import forward_pass_jit, forward_batch_jit, HAS_NUMBA

print(f"Numba available: {HAS_NUMBA}")
if not HAS_NUMBA:
    print("WARNING: Numba not installed. Install with: pip install numba")
    print("Benchmarks will show fallback performance only.\n")


def benchmark_forward_pass(n_iterations=10000):
    """Benchmark single forward pass."""
    print("=" * 60)
    print("1. Forward Pass (Single)")
    print("=" * 60)
    
    # Setup
    config = NetworkConfig(input_size=17, hidden_sizes=[64, 32], output_size=6)
    network = PolicyNetwork(config)
    
    # Random weights
    for i in range(len(network.weights)):
        network.weights[i] = np.random.randn(*network.weights[i].shape).astype(np.float32) * 0.1
        network.biases[i] = np.random.randn(*network.biases[i].shape).astype(np.float32) * 0.1
    
    # Test input
    features = np.random.randn(17).astype(np.float32)
    
    # Warmup (trigger JIT compilation)
    for _ in range(10):
        _ = network.forward(features)
    
    # Benchmark
    start = time.time()
    for _ in range(n_iterations):
        _ = network.forward(features)
    elapsed = time.time() - start
    
    print(f"Iterations: {n_iterations}")
    print(f"Total time: {elapsed:.4f}s")
    print(f"Time per forward: {elapsed/n_iterations*1e6:.2f} μs")
    print(f"Throughput: {n_iterations/elapsed:.0f} forward/sec")
    print()


def benchmark_forward_batch(n_iterations=1000):
    """Benchmark batched forward pass."""
    print("=" * 60)
    print("2. Forward Pass (Batch of 100)")
    print("=" * 60)
    
    # Setup
    config = NetworkConfig(input_size=17, hidden_sizes=[64, 32], output_size=6)
    network = PolicyNetwork(config)
    
    # Random weights
    for i in range(len(network.weights)):
        network.weights[i] = np.random.randn(*network.weights[i].shape).astype(np.float32) * 0.1
        network.biases[i] = np.random.randn(*network.biases[i].shape).astype(np.float32) * 0.1
    
    # Test input (batch of 100)
    batch_size = 100
    features_batch = np.random.randn(batch_size, 17).astype(np.float32)
    
    # Warmup
    for _ in range(10):
        _ = network.forward_batch(features_batch)
    
    # Benchmark
    start = time.time()
    for _ in range(n_iterations):
        _ = network.forward_batch(features_batch)
    elapsed = time.time() - start
    
    total_forwards = n_iterations * batch_size
    print(f"Iterations: {n_iterations} batches")
    print(f"Batch size: {batch_size}")
    print(f"Total forwards: {total_forwards}")
    print(f"Total time: {elapsed:.4f}s")
    print(f"Time per batch: {elapsed/n_iterations*1e3:.2f} ms")
    print(f"Time per forward: {elapsed/total_forwards*1e6:.2f} μs")
    print(f"Throughput: {total_forwards/elapsed:.0f} forward/sec")
    print()


def benchmark_feature_extraction(n_iterations=10000):
    """Benchmark feature extraction."""
    print("=" * 60)
    print("3. Feature Extraction")
    print("=" * 60)
    
    # Create mock game state with minimal attributes
    class MockPot:
        total = 150
    
    class MockState:
        pot = MockPot()
        button = 0
        betting_round = 'flop'
        big_blind = 10
    
    class MockPlayer:
        def __init__(self):
            self.hole_cards = [Card('A', 'h'), Card('K', 'h')]  # hearts
            self.stack = 1000
            self.bet = 0
            self.total_contributed = 50
            self.has_folded = False
            self.is_all_in = False
    
    class MockGame:
        def __init__(self):
            self.players = [MockPlayer() for _ in range(6)]
            self.state = MockState()
            self.current_bet = 50
    
    game = MockGame()
    player_id = 2
    
    # Warmup
    for _ in range(10):
        _ = get_state_vector(game, player_id)
    
    # Benchmark
    start = time.time()
    for _ in range(n_iterations):
        _ = get_state_vector(game, player_id)
    elapsed = time.time() - start
    
    print(f"Iterations: {n_iterations}")
    print(f"Total time: {elapsed:.4f}s")
    print(f"Time per extraction: {elapsed/n_iterations*1e6:.2f} μs")
    print(f"Throughput: {n_iterations/elapsed:.0f} extractions/sec")
    print()


def benchmark_hand_eval_helpers(n_iterations=10000):
    """Benchmark hand evaluation JIT helpers."""
    print("=" * 60)
    print("4. Hand Evaluation Helpers")
    print("=" * 60)
    
    if not HAS_NUMBA:
        print("Skipped (Numba not available)\n")
        return
    
    # Test data
    rank_values = np.array([12, 11, 10, 9, 8, 7, 6], dtype=np.int32)
    
    # Warmup
    for _ in range(10):
        _ = find_straight_jit(rank_values)
        _ = count_ranks_jit(rank_values)
    
    # Benchmark find_straight
    start = time.time()
    for _ in range(n_iterations):
        _ = find_straight_jit(rank_values)
    elapsed_straight = time.time() - start
    
    # Benchmark count_ranks
    start = time.time()
    for _ in range(n_iterations):
        _ = count_ranks_jit(rank_values)
    elapsed_count = time.time() - start
    
    print(f"Iterations: {n_iterations}")
    print(f"\nfind_straight_jit:")
    print(f"  Total time: {elapsed_straight:.4f}s")
    print(f"  Time per call: {elapsed_straight/n_iterations*1e6:.2f} μs")
    print(f"  Throughput: {n_iterations/elapsed_straight:.0f} calls/sec")
    
    print(f"\ncount_ranks_jit:")
    print(f"  Total time: {elapsed_count:.4f}s")
    print(f"  Time per call: {elapsed_count/n_iterations*1e6:.2f} μs")
    print(f"  Throughput: {n_iterations/elapsed_count:.0f} calls/sec")
    print()


def benchmark_genome_mutation(n_iterations=1000):
    """Benchmark genome mutation."""
    print("=" * 60)
    print("5. Genome Mutation")
    print("=" * 60)
    
    # Setup
    network_config = NetworkConfig(input_size=17, hidden_sizes=[64, 32], output_size=6)
    evolution_config = EvolutionConfig(population_size=20, mutation_sigma=0.1)
    factory = GenomeFactory(network_config, evolution_config, rng=np.random.default_rng(42))
    
    # Create parent genome
    parent = factory.create_random(generation=0)
    
    # Warmup
    for _ in range(10):
        _ = factory.mutate(parent, generation=1)
    
    # Benchmark
    start = time.time()
    for _ in range(n_iterations):
        _ = factory.mutate(parent, generation=1)
    elapsed = time.time() - start
    
    print(f"Genome size: {factory.genome_size} parameters")
    print(f"Iterations: {n_iterations}")
    print(f"Total time: {elapsed:.4f}s")
    print(f"Time per mutation: {elapsed/n_iterations*1e3:.2f} ms")
    print(f"Throughput: {n_iterations/elapsed:.0f} mutations/sec")
    print()


def main():
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print(" NUMBA JIT PERFORMANCE BENCHMARKS")
    print("=" * 60)
    print()
    
    if HAS_NUMBA:
        try:
            import numba
            print(f"Numba version: {numba.__version__}")
            print(f"NumPy version: {np.__version__}")
        except Exception:
            pass
    print()
    
    # Run benchmarks
    benchmark_forward_pass(n_iterations=10000)
    benchmark_forward_batch(n_iterations=1000)
    benchmark_feature_extraction(n_iterations=10000)
    benchmark_hand_eval_helpers(n_iterations=10000)
    benchmark_genome_mutation(n_iterations=1000)
    
    print("=" * 60)
    print(" BENCHMARK COMPLETE")
    print("=" * 60)
    print()
    print("Expected speedups with Numba JIT:")
    print("  Forward pass:       2-3× faster")
    print("  Forward batch:      2-3× faster")
    print("  Feature extraction: 2-3× faster")
    print("  Hand evaluation:    1.5-2× faster")
    print("  Genome mutation:    1.5-2× faster")
    print()
    print("Overall training speedup: 2-3× (13 sec/gen → 4-6 sec/gen)")
    print()


if __name__ == "__main__":
    main()
