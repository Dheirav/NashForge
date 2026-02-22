"""
Enhanced round-robin tournament: sorts by wins, includes config insights, and prints per-agent configuration.
Uses descriptive names based on genome specifications instead of run names.

Supports two modes:
  - heads-up: Traditional 1v1 round-robin (all pairs play each other)
  - multi-table: 6-player tables with round-robin coverage (all agents play together at least once)

Usage:
    # Run all checkpoints in heads-up mode (default)
    python3 scripts/evaluation/round_robin_agents_config.py
    
    # Run multi-table tournament with 6 players per table
    python3 scripts/evaluation/round_robin_agents_config.py --mode multi-table --table-size 6
    
    # Run specific checkpoint directories
    python3 scripts/evaluation/round_robin_agents_config.py --checkpoints deep_p12_m6_h375_s0.1_hof3_g50 deep_p20_m6_h500_s0.15_hof3_g50
    
    # Run checkpoints matching a pattern
    python3 scripts/evaluation/round_robin_agents_config.py --pattern "*hof3*"
    
    # Run specific agent files
    python3 scripts/evaluation/round_robin_agents_config.py --agents checkpoints/deep_p12_m6_h375_s0.1_hof3_g50/runs/run_20260128_032747/best_genome.npy
    
    # Customize settings
    python3 scripts/evaluation/round_robin_agents_config.py --hands 5000 --checkpoints deep_p12_* deep_p20_*
"""
import os
import sys
import subprocess
import glob
import re
import json
import argparse
import collections
from collections import defaultdict
from datetime import datetime
from itertools import combinations
import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Visualizations will be skipped.")

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from training.policy_network import PolicyNetwork
from training.config import FitnessConfig
from training.self_play import play_match, AgentPlayer
from utils import genome_transform

ARCH = "17 64 32 6"
DEFAULT_HANDS = 10000
DEFAULT_PLAYERS = 2
MATCH_SCRIPT = "scripts/evaluation/match_agents.py"

# Generate descriptive name from config
def get_descriptive_name(config, original_name):
    """Generate a short descriptive name from genome config."""
    if config is None:
        return original_name
    
    try:
        pop = config['evolution']['population_size']
        sigma = config['evolution']['mutation_sigma']
        gens = config['num_generations']
        
        # Extract matchups and hands from the correct paths
        matchups = config['fitness']['matchups_per_agent']
        hands = config['fitness']['hands_per_matchup']
        
        # Format: p40_m8_h375_s0.1_g200
        name = f"p{pop}_m{matchups}_h{hands}_s{sigma}_g{gens}"
        return name
    except (KeyError, TypeError) as e:
        # Fallback to original name if config is malformed
        print(f"Warning: Could not parse config for {original_name}: {e}")
        return original_name

# Find all agents and configs
def get_agents_and_configs(checkpoint_dirs=None, checkpoint_pattern=None, agent_paths=None):
    """
    Find agents to include in tournament.
    
    Args:
        checkpoint_dirs: List of checkpoint directory names (e.g., ['deep_p12_m6_h375_s0.1_hof3_g50'])
        checkpoint_pattern: Glob pattern for checkpoint directories (e.g., '*hof3*')
        agent_paths: List of specific agent file paths
    """
    agent_files = []
    
    if agent_paths:
        # Use specific agent files provided
        agent_files = agent_paths
    elif checkpoint_dirs:
        # Use specific checkpoint directories
        for ckpt_dir in checkpoint_dirs:
            # Handle both with and without 'checkpoints/' prefix
            if not ckpt_dir.startswith('checkpoints/'):
                ckpt_dir = f'checkpoints/{ckpt_dir}'
            
            # Find all best_genome.npy files in this checkpoint
            pattern = f"{ckpt_dir}/runs/*/best_genome.npy"
            found = glob.glob(pattern)
            if not found:
                # Try without runs/ subdirectory
                pattern = f"{ckpt_dir}/best_genome.npy"
                found = glob.glob(pattern)
            
            if found:
                agent_files.extend(found)
                print(f"Found {len(found)} agent(s) in {ckpt_dir}")
            else:
                print(f"Warning: No agents found in {ckpt_dir}")
    elif checkpoint_pattern:
        # Use pattern matching for checkpoint directories
        pattern = f"checkpoints/{checkpoint_pattern}/runs/*/best_genome.npy"
        agent_files = glob.glob(pattern)
        if not agent_files:
            # Try without runs/ subdirectory
            pattern = f"checkpoints/{checkpoint_pattern}/best_genome.npy"
            agent_files = glob.glob(pattern)
        print(f"Found {len(agent_files)} agent(s) matching pattern '{checkpoint_pattern}'")
    else:
        # Default: find all agents
        agent_files = glob.glob("checkpoints/*/runs/*/best_genome.npy")
        print(f"Found {len(agent_files)} agent(s) in all checkpoints")
    
    if not agent_files:
        print("ERROR: No agents found!")
        sys.exit(1)
    
    agents = []
    seen_names = {}  # Track duplicate names
    
    for f in agent_files:
        original_name = re.sub(r"checkpoints/(.*)/runs/(.*)/best_genome.npy", r"\1/\2", f)
        # Handle case without runs/ subdirectory
        if 'runs/' not in f:
            original_name = re.sub(r"checkpoints/(.*)/best_genome.npy", r"\1", f)
        
        config_path = os.path.join(os.path.dirname(f), "config.json")
        
        if os.path.exists(config_path):
            with open(config_path) as cf:
                config = json.load(cf)
        else:
            config = None
        
        # Generate descriptive name
        desc_name = get_descriptive_name(config, original_name)
        
        # Handle duplicate names by adding a suffix
        if desc_name in seen_names:
            seen_names[desc_name] += 1
            desc_name = f"{desc_name}_v{seen_names[desc_name]}"
        else:
            seen_names[desc_name] = 1
        
        agents.append({
            'name': desc_name,
            'file': f,
            'config': config,
            'original_name': original_name
        })
    
    return agents

def run_tournament_headsup(agents, hands, players):
    """Run the heads-up round-robin tournament between all agents (1v1 matches)."""
    results = defaultdict(lambda: {
        'wins': 0, 
        'losses': 0, 
        'chips': 0, 
        'matchups': {},
        'matchup_results': []  # Track individual matchup results for consistency
    })
    
    total_matches = len(agents) * (len(agents) - 1)
    match_count = 0
    
    for i, agent1 in enumerate(agents):
        for j, agent2 in enumerate(agents):
            if i == j:
                continue
            
            match_count += 1
            name1 = agent1['name']
            name2 = agent2['name']
            print(f"\n[{match_count}/{total_matches}] === {name1} vs {name2} ===")
            
            cmd = [
                "python3", MATCH_SCRIPT,
                "--agent1", agent1['file'],
                "--arch1", ARCH,
                "--agent2", agent2['file'],
                "--arch2", ARCH,
                "--hands", str(hands),
                "--players", str(players)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            output = proc.stdout
            if proc.returncode != 0:
                print(f"Error running match: {name1} vs {name2}")
                print(proc.stderr)
            m = re.search(r"Final stacks: Agent 1: (\d+), Agent 2: (\d+)", output)
            if m:
                chips1 = int(m.group(1))
                chips2 = int(m.group(2))
                results[name1]['chips'] += chips1
                results[name2]['chips'] += chips2
                results[name1]['matchups'][name2] = chips1
                results[name2]['matchups'][name1] = chips2
                results[name1]['matchup_results'].append(chips1)
                results[name2]['matchup_results'].append(chips2)
                if chips1 > chips2:
                    results[name1]['wins'] += 1
                    results[name2]['losses'] += 1
                elif chips2 > chips1:
                    results[name2]['wins'] += 1
                    results[name1]['losses'] += 1
            else:
                print("Could not parse result for", name1, "vs", name2)
    
    return results

def run_tournament_multitable(agents, hands, table_size=6, min_encounters=1):
    """Run multi-table round-robin tournament where agents play at tables together.
    
    Generates table combinations to ensure all agents play together at least n times.
    
    Args:
        agents: List of agent dicts with 'name', 'file', 'config'
        hands: Number of hands to play per table
        table_size: Number of players per table (default: 6)
        min_encounters: Minimum times each pair of agents must meet (default: 1)
    
    Returns:
        Results dict with agent statistics
    """
    print(f"\nGenerating {table_size}-player table combinations (round-robin)...")
    print(f"Target: Each pair of agents meets at least {min_encounters} time(s)")

    import random as _random
    n = len(agents)
    total_pairs = n * (n - 1) // 2

    # Use a numpy matrix for fast pairwise encounter tracking
    encounter_matrix = np.zeros((n, n), dtype=np.int32)

    tables_to_play = []

    # Round-robin: each round, shuffle agents and partition into tables of table_size.
    # Pad with a dummy agent index if not divisible.
    # Repeat rounds until all pairs meet min_encounters.
    round_num = 0
    max_rounds = min_encounters * (n + table_size)  # Safety cap to prevent infinite loops

    while True:
        # Check if all pairs have met min_encounters
        # Only check the upper triangle (pairs)
        upper = encounter_matrix[np.triu_indices(n, k=1)]
        if np.all(upper >= min_encounters):
            break
        if round_num >= max_rounds:
            print(f"  Warning: Reached max rounds ({max_rounds}), some pairs may not meet target.")
            break

        # Shuffle agent indices for this round
        indices = list(range(n))
        _random.shuffle(indices)

        # Pad to be divisible by table_size
        remainder = len(indices) % table_size
        if remainder != 0:
            # Add dummy padding (will be filtered out when assigning tables)
            indices += [-1] * (table_size - remainder)

        # Partition into tables
        for i in range(0, len(indices), table_size):
            table = [idx for idx in indices[i:i + table_size] if idx != -1]
            if len(table) < 2:
                continue
            tables_to_play.append(tuple(table))
            # Update encounter matrix for all pairs in this table
            for a, b in combinations(table, 2):
                encounter_matrix[a, b] += 1
                encounter_matrix[b, a] += 1

        round_num += 1

    upper = encounter_matrix[np.triu_indices(n, k=1)]
    pairs_meeting_target = int(np.sum(upper >= min_encounters))
    print(f"Selected {len(tables_to_play)} tables over {round_num} rounds")
    print(f"Coverage: {pairs_meeting_target}/{total_pairs} pairs meet {min_encounters}+ times")

    min_count = int(np.min(upper)) if len(upper) > 0 else 0
    max_count = int(np.max(upper)) if len(upper) > 0 else 0
    avg_count = float(np.mean(upper)) if len(upper) > 0 else 0.0
    print(f"Encounter distribution: min={min_count}, max={max_count}, avg={avg_count:.1f}")
    
    # Load all agents into memory
    print("\nLoading agents...")
    loaded_agents = []
    for agent in agents:
        genome = np.load(agent['file'])
        arch = [int(x) for x in ARCH.split()]
        
        net = PolicyNetwork()
        net.layer_sizes = arch
        weights, biases = genome_transform.decode_genome(genome, arch)
        net.weights = weights
        net.biases = biases
        
        agent_player = AgentPlayer(net, temperature=1.0)
        loaded_agents.append(agent_player)
    
    print(f"Loaded {len(loaded_agents)} agents")
    
    # Results tracking
    results = defaultdict(lambda: {
        'wins': 0, 
        'losses': 0, 
        'chips': 0, 
        'tables_played': 0,
        'matchups': defaultdict(lambda: {'played': 0, 'chip_delta': 0}),
        'table_results': [],  # Track individual table chip changes for consistency
        'finish_positions': []  # Track finish position (1-6) at each table
    })
    
    # Play each table
    config = FitnessConfig()
    config.starting_stack = 1000
    config.small_blind = 5
    config.big_blind = 10
    
    for table_idx, table_indices in enumerate(tables_to_play, 1):
        table_agents = [loaded_agents[i] for i in table_indices]
        table_names = [agents[i]['name'] for i in table_indices]
        
        print(f"\n[{table_idx}/{len(tables_to_play)}] Table: {', '.join(table_names)}")
        
        # Play the match
        try:
            session_results = play_match(
                agents=table_agents,
                num_hands=hands,
                config=config,
                seed=None,
                verbose=False
            )
            
            # Extract results
            # First, determine finish positions based on chip changes
            table_chip_changes = [(i, session_results[i].total_chip_change) for i in range(len(table_indices))]
            table_chip_changes_sorted = sorted(table_chip_changes, key=lambda x: x[1], reverse=True)
            finish_positions = {idx: pos + 1 for pos, (idx, _) in enumerate(table_chip_changes_sorted)}
            
            for i, agent_idx in enumerate(table_indices):
                agent_name = agents[agent_idx]['name']
                stats = session_results[i]
                
                results[agent_name]['chips'] += stats.total_chip_change
                results[agent_name]['tables_played'] += 1
                results[agent_name]['table_results'].append(stats.total_chip_change)
                results[agent_name]['finish_positions'].append(finish_positions[i])
                
                # Count wins/losses based on chip change
                if stats.total_chip_change > 0:
                    results[agent_name]['wins'] += 1
                elif stats.total_chip_change < 0:
                    results[agent_name]['losses'] += 1
                
                # Track head-to-head (chip differentials against each opponent at this table)
                for j, opp_idx in enumerate(table_indices):
                    if i != j:
                        opp_name = agents[opp_idx]['name']
                        results[agent_name]['matchups'][opp_name]['played'] += 1
                        results[agent_name]['matchups'][opp_name]['chip_delta'] += stats.total_chip_change
            
            print(f"  Results: {[f'{table_names[i]}={session_results[i].total_chip_change:+d}' for i in range(len(table_indices))]}")
            
        except Exception as e:
            print(f"  Error playing table: {e}")
            import traceback
            traceback.print_exc()
    
    # Convert matchups dict to regular dict for JSON serialization
    for agent_name in results:
        results[agent_name]['matchups'] = dict(results[agent_name]['matchups'])
    
    return dict(results)

def calculate_elo_ratings(agents, results, k_factor=32, initial_rating=1500):
    """Calculate Elo ratings for all agents based on head-to-head results.
    
    Args:
        agents: List of agent dicts
        results: Tournament results dict
        k_factor: Elo K-factor (higher = more volatile ratings)
        initial_rating: Starting Elo rating
    
    Returns:
        Dict mapping agent names to final Elo ratings
    """
    # Initialize all agents with base rating
    elo = {agent['name']: initial_rating for agent in agents}
    
    # Process all matchups
    for agent1 in agents:
        name1 = agent1['name']
        for agent2 in agents:
            if agent1['name'] == agent2['name']:
                continue
            
            name2 = agent2['name']
            matchup_data = results[name1]['matchups'].get(name2)
            
            if matchup_data is not None:
                # Determine outcome
                if isinstance(matchup_data, dict):
                    chips1 = matchup_data.get('chip_delta', 0)
                    chips2 = results[name2]['matchups'].get(name1, {}).get('chip_delta', 0)
                else:
                    chips1 = matchup_data
                    chips2 = results[name2]['matchups'].get(name1, 0)
                
                # Calculate expected scores
                expected1 = 1 / (1 + 10 ** ((elo[name2] - elo[name1]) / 400))
                expected2 = 1 / (1 + 10 ** ((elo[name1] - elo[name2]) / 400))
                
                # Actual scores (1 for win, 0.5 for draw, 0 for loss)
                if chips1 > chips2:
                    actual1, actual2 = 1, 0
                elif chips2 > chips1:
                    actual1, actual2 = 0, 1
                else:
                    actual1, actual2 = 0.5, 0.5
                
                # Update Elo ratings
                elo[name1] += k_factor * (actual1 - expected1)
                elo[name2] += k_factor * (actual2 - expected2)
    
    return elo

def analyze_and_report(agents, results, output_dir=None, mode='heads-up'):
    # Create output directory with timestamp
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f"tournament_reports/tournament_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    report_path = os.path.join(output_dir, "report.json")
    
    mode_title = "Multi-Table" if mode == 'multi-table' else "Heads-Up Round Robin"
    
    # Calculate additional metrics
    if mode == 'multi-table':
        for agent in agents:
            name = agent['name']
            stats = results[name]
            tables = stats['tables_played']
            if tables > 0:
                stats['win_rate'] = stats['wins'] / tables
                stats['avg_chips_per_table'] = stats['chips'] / tables
                stats['positive_table_pct'] = sum(1 for x in stats['table_results'] if x > 0) / tables
                stats['consistency'] = np.std(stats['table_results']) if len(stats['table_results']) > 1 else 0
    else:  # heads-up
        for agent in agents:
            name = agent['name']
            stats = results[name]
            total_matches = stats['wins'] + stats['losses']
            if total_matches > 0:
                stats['win_percentage'] = (stats['wins'] / total_matches) * 100
                stats['win_loss_ratio'] = stats['wins'] / stats['losses'] if stats['losses'] > 0 else float('inf')
                stats['avg_chips_per_match'] = stats['chips'] / total_matches
                stats['consistency'] = np.std(stats['matchup_results']) if len(stats['matchup_results']) > 1 else 0
                
                # Calculate average chip margin (how much they win/lose by on average)
                chip_margins = []
                for opp in agents:
                    if opp['name'] != name:
                        my_chips = stats['matchups'].get(opp['name'], 0)
                        opp_chips = results[opp['name']]['matchups'].get(name, 0)
                        chip_margins.append(my_chips - opp_chips)
                stats['avg_chip_margin'] = np.mean(chip_margins) if chip_margins else 0
        
        # Calculate Elo ratings
        elo_ratings = calculate_elo_ratings(agents, results)
        for agent in agents:
            results[agent['name']]['elo_rating'] = elo_ratings[agent['name']]
    
    print(f"\n=== {mode_title} Results ===")
    if mode == 'multi-table':
        print(f"{'Agent':35}  WinRate  AvgChips  Consistency  +Tables%  Tables  Pop  Sigma  Gen")
        sorted_agents = sorted(agents, key=lambda a: results[a['name']].get('avg_chips_per_table', 0), reverse=True)
    else:
        print(f"{'Agent':35}  Win%  W/L   AvgChips  Margin  Elo    Consistency  Pop  Sigma  Gen")
        sorted_agents = sorted(agents, key=lambda a: results[a['name']].get('elo_rating', 1500), reverse=True)
    
    # For report
    report = {
        'mode': mode,
        'agents': [],
        'matchups': {},
        'insights': {}
    }
    
    # Per-agent summary
    for agent in sorted_agents:
        name = agent['name']
        stats = results[name]
        cfg = agent['config']
        pop = cfg['evolution']['population_size'] if cfg else '-'
        sigma = cfg['evolution']['mutation_sigma'] if cfg else '-'
        ngen = cfg['num_generations'] if cfg else '-'
        
        if mode == 'multi-table':
            win_rate = stats.get('win_rate', 0)
            avg_chips = stats.get('avg_chips_per_table', 0)
            consistency = stats.get('consistency', 0)
            pos_pct = stats.get('positive_table_pct', 0) * 100
            tables = stats['tables_played']
            print(f"{name:35}  {win_rate:6.1%}  {avg_chips:8.1f}  {consistency:11.1f}  {pos_pct:7.1f}%  {tables:6}  {pop:3}  {sigma:5}  {ngen:3}")
        else:
            win_pct = stats.get('win_percentage', 0)
            wl_ratio = stats.get('win_loss_ratio', 0)
            wl_str = f"{wl_ratio:.2f}" if wl_ratio != float('inf') else "∞"
            avg_chips = stats.get('avg_chips_per_match', 0)
            margin = stats.get('avg_chip_margin', 0)
            elo = stats.get('elo_rating', 1500)
            consistency = stats.get('consistency', 0)
            print(f"{name:35}  {win_pct:4.1f}  {wl_str:4}  {avg_chips:8.1f}  {margin:6.1f}  {elo:6.0f}  {consistency:11.1f}  {pop:3}  {sigma:5}  {ngen:3}")
        
        # Who did this agent beat/lose to?
        beat = []
        lost = []
        for opp in sorted_agents:
            if opp['name'] == name:
                continue
            my_score = results[name]['matchups'].get(opp['name'])
            opp_score = results[opp['name']]['matchups'].get(name)
            
            # Handle different matchup data structures
            if my_score is not None and opp_score is not None:
                if mode == 'multi-table':
                    # For multi-table, matchups store {'played': count, 'chip_delta': delta}
                    if isinstance(my_score, dict):
                        my_chips = my_score.get('chip_delta', 0)
                        opp_chips = opp_score.get('chip_delta', 0)
                    else:
                        my_chips = my_score
                        opp_chips = opp_score
                else:
                    # For heads-up, matchups store chip counts directly
                    my_chips = my_score
                    opp_chips = opp_score
                
                if my_chips > opp_chips:
                    beat.append(opp['name'])
                elif my_chips < opp_chips:
                    lost.append(opp['name'])
        
        agent_report = {
            'name': name,
            'original_path': agent['original_name'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'chips': stats['chips'],
            'population_size': pop,
            'mutation_sigma': sigma,
            'generations': ngen,
            'beat': beat,
            'lost_to': lost
        }
        
        # Add mode-specific metrics
        if mode == 'multi-table':
            agent_report['win_rate'] = stats.get('win_rate', 0)
            agent_report['avg_chips_per_table'] = stats.get('avg_chips_per_table', 0)
            agent_report['consistency'] = stats.get('consistency', 0)
            agent_report['positive_table_pct'] = stats.get('positive_table_pct', 0)
            agent_report['tables_played'] = stats['tables_played']
            agent_report['finish_distribution'] = {
                str(i): stats['finish_positions'].count(i) for i in range(1, 7)
            }
            
            # Calculate head-to-head win rates
            h2h_win_rates = {}
            for opp in sorted_agents:
                if opp['name'] != name:
                    matchup = stats['matchups'].get(opp['name'], {'played': 0, 'chip_delta': 0})
                    opp_matchup = results[opp['name']]['matchups'].get(name, {'played': 0, 'chip_delta': 0})
                    if matchup['played'] > 0:
                        # Count how many encounters this agent had more chips than opponent
                        wins = 1 if matchup['chip_delta'] > opp_matchup['chip_delta'] else 0
                        h2h_win_rates[opp['name']] = wins / matchup['played']
            agent_report['h2h_win_rates'] = h2h_win_rates
        else:  # heads-up
            agent_report['win_percentage'] = stats.get('win_percentage', 0)
            agent_report['win_loss_ratio'] = stats.get('win_loss_ratio', 0)
            agent_report['avg_chips_per_match'] = stats.get('avg_chips_per_match', 0)
            agent_report['avg_chip_margin'] = stats.get('avg_chip_margin', 0)
            agent_report['elo_rating'] = stats.get('elo_rating', 1500)
            agent_report['consistency'] = stats.get('consistency', 0)
        
        report['agents'].append(agent_report)
        report['matchups'][name] = stats['matchups']
    
    print("\nConfig columns: Pop=population size, Sigma=mutation sigma, Gen=generations trained")
    print("\nPer-matchup chip results:")
    for agent in sorted_agents:
        name = agent['name']
        print(f"{name:35}", end=': ')
        for opp in sorted_agents:
            if opp['name'] == name:
                continue
            matchup_data = results[name]['matchups'].get(opp['name'], '-')
            # Extract chip value based on mode
            if matchup_data != '-':
                if mode == 'multi-table' and isinstance(matchup_data, dict):
                    val = matchup_data.get('chip_delta', 0)
                else:
                    val = matchup_data
            else:
                val = '-'
            print(f"{val:6}", end=' ')
        print()
    
    # Parameter insights: which config values are most successful?
    pop_counter = collections.Counter()
    sigma_counter = collections.Counter()
    gen_counter = collections.Counter()
    for agent in report['agents']:
        if agent['population_size'] != '-':
            pop_counter[agent['population_size']] += agent['wins']
        if agent['mutation_sigma'] != '-':
            sigma_counter[agent['mutation_sigma']] += agent['wins']
        if agent['generations'] != '-':
            gen_counter[agent['generations']] += agent['wins']
    
    report['insights']['top_population_sizes'] = pop_counter.most_common()
    report['insights']['top_mutation_sigmas'] = sigma_counter.most_common()
    report['insights']['top_generations'] = gen_counter.most_common()
    
    print("\nParameter insights (by total wins):")
    print("Population size:", report['insights']['top_population_sizes'])
    print("Mutation sigma:", report['insights']['top_mutation_sigmas'])
    print("Generations:", report['insights']['top_generations'])
    
    # Write report
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written to {report_path}")
    
    # Print a summary of who each agent beat and lost to
    print("\nAgent win/loss breakdown:")
    for i, agent in enumerate(sorted_agents):
        agent_data = report['agents'][i]
        print(f"{agent['name']}: beat {len(agent_data['beat'])} agents, lost to {len(agent_data['lost_to'])} agents")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    create_visualizations(sorted_agents, results, report, output_dir)
    print(f"Visualizations saved to {output_dir}")

def create_visualizations(sorted_agents, results, report, output_dir):
    """Create visualization charts for tournament results."""
    
    if not MATPLOTLIB_AVAILABLE:
        print("Skipping visualizations (matplotlib not available)")
        return
    
    # Determine mode from report
    mode = report.get('mode', 'heads-up')
    
    # Import additional libraries for network graph
    try:
        import networkx as nx
        NETWORKX_AVAILABLE = True
    except ImportError:
        NETWORKX_AVAILABLE = False
    
    # 1. Win/Loss Bar Chart
    fig, ax = plt.subplots(figsize=(14, 8))
    agent_names = [a['name'].split('/')[-1] for a in sorted_agents]  # Short names
    wins = [results[a['name']]['wins'] for a in sorted_agents]
    losses = [results[a['name']]['losses'] for a in sorted_agents]
    
    x = np.arange(len(agent_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, wins, width, label='Wins', color='green', alpha=0.7)
    bars2 = ax.bar(x + width/2, losses, width, label='Losses', color='red', alpha=0.7)
    
    ax.set_xlabel('Agent', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Round Robin Tournament Results: Wins vs Losses', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(agent_names, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'wins_losses.png'), dpi=150)
    plt.close()
    
    # 2. Parameter Performance Analysis
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Population Size
    pop_data = report['insights']['top_population_sizes']
    if pop_data:
        pops, pop_wins = zip(*pop_data)
        axes[0].bar([str(p) for p in pops], pop_wins, color='blue', alpha=0.7)
        axes[0].set_xlabel('Population Size', fontsize=12)
        axes[0].set_ylabel('Total Wins', fontsize=12)
        axes[0].set_title('Wins by Population Size', fontsize=12, fontweight='bold')
        axes[0].grid(axis='y', alpha=0.3)
    
    # Mutation Sigma
    sigma_data = report['insights']['top_mutation_sigmas']
    if sigma_data:
        sigmas, sigma_wins = zip(*sigma_data)
        axes[1].bar([str(s) for s in sigmas], sigma_wins, color='orange', alpha=0.7)
        axes[1].set_xlabel('Mutation Sigma', fontsize=12)
        axes[1].set_ylabel('Total Wins', fontsize=12)
        axes[1].set_title('Wins by Mutation Sigma', fontsize=12, fontweight='bold')
        axes[1].grid(axis='y', alpha=0.3)
    
    # Generations
    gen_data = report['insights']['top_generations']
    if gen_data:
        gens, gen_wins = zip(*gen_data)
        axes[2].bar([str(g) for g in gens], gen_wins, color='purple', alpha=0.7)
        axes[2].set_xlabel('Generations Trained', fontsize=12)
        axes[2].set_ylabel('Total Wins', fontsize=12)
        axes[2].set_title('Wins by Training Generations', fontsize=12, fontweight='bold')
        axes[2].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'parameter_performance.png'), dpi=150)
    plt.close()
    
    # 3. Head-to-Head Heatmap
    fig, ax = plt.subplots(figsize=(14, 12))
    n_agents = len(sorted_agents)
    heatmap_data = np.zeros((n_agents, n_agents))
    
    for i, agent1 in enumerate(sorted_agents):
        for j, agent2 in enumerate(sorted_agents):
            if i != j:
                matchup_data = results[agent1['name']]['matchups'].get(agent2['name'], 0)
                # Extract chip value based on mode
                if matchup_data == 0:
                    chips = 0
                elif mode == 'multi-table' and isinstance(matchup_data, dict):
                    chips = matchup_data.get('chip_delta', 0)
                else:
                    chips = matchup_data
                heatmap_data[i, j] = chips
    
    im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto')
    
    # Set ticks and labels
    ax.set_xticks(np.arange(n_agents))
    ax.set_yticks(np.arange(n_agents))
    ax.set_xticklabels(agent_names, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(agent_names, fontsize=8)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Chips Won', rotation=270, labelpad=20)
    
    ax.set_title('Head-to-Head Results (Chips Won)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Opponent', fontsize=12)
    ax.set_ylabel('Agent', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'head_to_head_heatmap.png'), dpi=150)
    plt.close()
    
    # 4. Chip Distribution
    fig, ax = plt.subplots(figsize=(14, 8))
    chips = [results[a['name']]['chips'] for a in sorted_agents]
    
    bars = ax.bar(agent_names, chips, color='teal', alpha=0.7)
    ax.set_xlabel('Agent', fontsize=12)
    ax.set_ylabel('Total Chips', fontsize=12)
    ax.set_title('Total Chips Accumulated', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(agent_names)))
    ax.set_xticklabels(agent_names, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chip_distribution.png'), dpi=150)
    plt.close()
    
    # Multi-table specific visualizations
    if mode == 'multi-table':
        # 5. Win Rate % Chart
        fig, ax = plt.subplots(figsize=(14, 8))
        win_rates = [results[a['name']].get('win_rate', 0) * 100 for a in sorted_agents]
        
        bars = ax.bar(agent_names, win_rates, color='royalblue', alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Win Rate (%)', fontsize=12)
        ax.set_title('Win Rate % (Tables Won / Total Tables)', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% baseline')
        ax.legend()
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'win_rate_percentage.png'), dpi=150)
        plt.close()
        
        # 6. Average Chips per Table
        fig, ax = plt.subplots(figsize=(14, 8))
        avg_chips = [results[a['name']].get('avg_chips_per_table', 0) for a in sorted_agents]
        
        colors = ['green' if x > 0 else 'red' for x in avg_chips]
        bars = ax.bar(agent_names, avg_chips, color=colors, alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Average Chips per Table', fontsize=12)
        ax.set_title('Average Chips Won/Lost per Table', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'avg_chips_per_table.png'), dpi=150)
        plt.close()
        
        # 7. Consistency Plot (Box Plot)
        fig, ax = plt.subplots(figsize=(18, 10))
        table_results = [results[a['name']].get('table_results', [0]) for a in sorted_agents]
        
        # Create box plot with better spacing
        positions = np.arange(len(agent_names)) * 1.5  # Add spacing between boxes
        bp = ax.boxplot(table_results, positions=positions, labels=agent_names, 
                       patch_artist=True, widths=0.8)
        
        # Customize box plot colors and style
        for patch, median_line in zip(bp['boxes'], bp['medians']):
            patch.set_facecolor('lightblue')
            patch.set_alpha(0.7)
            patch.set_linewidth(1.5)
            median_line.set_color('red')
            median_line.set_linewidth(2)
        
        # Customize whiskers and caps
        for whisker in bp['whiskers']:
            whisker.set_linewidth(1.5)
            whisker.set_linestyle('--')
        for cap in bp['caps']:
            cap.set_linewidth(1.5)
        
        ax.set_xlabel('Agent', fontsize=14, fontweight='bold')
        ax.set_ylabel('Chips per Table', fontsize=14, fontweight='bold')
        ax.set_title('Consistency: Distribution of Chips Across Tables\n(Box = IQR, Red line = Median, Whiskers = Range)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(positions)
        ax.set_xticklabels(agent_names, rotation=60, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linewidth=1)
        ax.axhline(y=0, color='darkred', linestyle='--', alpha=0.7, linewidth=2, label='Break-even')
        ax.legend(fontsize=12)
        
        # Add more padding
        plt.subplots_adjust(bottom=0.25, top=0.92)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'consistency_boxplot.png'), dpi=200, bbox_inches='tight')
        plt.close()
        
        # 8. Finish Position Distribution (Stacked Bar)
        fig, ax = plt.subplots(figsize=(14, 8))
        
        positions = [1, 2, 3, 4, 5, 6]
        position_data = {pos: [] for pos in positions}
        
        for agent in sorted_agents:
            finish_positions = results[agent['name']].get('finish_positions', [])
            total_tables = len(finish_positions)
            for pos in positions:
                count = finish_positions.count(pos)
                pct = (count / total_tables * 100) if total_tables > 0 else 0
                position_data[pos].append(pct)
        
        # Create stacked bar chart
        bottom = np.zeros(len(agent_names))
        colors_pos = ['gold', 'silver', '#CD7F32', 'lightcoral', 'lightsalmon', 'lightgray']
        labels_pos = ['1st Place', '2nd Place', '3rd Place', '4th Place', '5th Place', '6th Place']
        
        for pos, color, label in zip(positions, colors_pos, labels_pos):
            ax.bar(agent_names, position_data[pos], bottom=bottom, label=label, color=color, alpha=0.8)
            bottom += position_data[pos]
        
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Percentage (%)', fontsize=12)
        ax.set_title('Finish Position Distribution', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'finish_position_distribution.png'), dpi=150)
        plt.close()
        
        # 9. Positive Table Percentage
        fig, ax = plt.subplots(figsize=(14, 8))
        pos_table_pct = [results[a['name']].get('positive_table_pct', 0) * 100 for a in sorted_agents]
        
        bars = ax.bar(agent_names, pos_table_pct, color='mediumseagreen', alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Percentage (%)', fontsize=12)
        ax.set_title('Percentage of Tables with Positive Chips', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% baseline')
        ax.legend()
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'positive_table_percentage.png'), dpi=150)
        plt.close()
        
        # 10. Encounter Coverage Heatmap
        fig, ax = plt.subplots(figsize=(14, 12))
        n_agents = len(sorted_agents)
        encounter_matrix = np.zeros((n_agents, n_agents))
        
        for i, agent1 in enumerate(sorted_agents):
            for j, agent2 in enumerate(sorted_agents):
                if i != j:
                    matchup = results[agent1['name']]['matchups'].get(agent2['name'], {'played': 0})
                    encounter_matrix[i, j] = matchup.get('played', matchup if isinstance(matchup, int) else 0)
        
        im = ax.imshow(encounter_matrix, cmap='YlOrRd', aspect='auto')
        
        ax.set_xticks(np.arange(n_agents))
        ax.set_yticks(np.arange(n_agents))
        ax.set_xticklabels(agent_names, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(agent_names, fontsize=8)
        
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Number of Encounters', rotation=270, labelpad=20)
        
        ax.set_title('Encounter Coverage: How Many Times Each Pair Played', fontsize=14, fontweight='bold')
        ax.set_xlabel('Opponent', fontsize=12)
        ax.set_ylabel('Agent', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'encounter_coverage_heatmap.png'), dpi=150)
        plt.close()
        
        # 11. Dominance Network Graph
        if NETWORKX_AVAILABLE:
            fig, ax = plt.subplots(figsize=(20, 20))
            G = nx.DiGraph()
            
            # Add nodes
            for agent in sorted_agents:
                G.add_node(agent['name'].split('/')[-1])
            
            # Add edges for significant dominance (based on chip differentials)
            for i, agent1 in enumerate(sorted_agents):
                for j, agent2 in enumerate(sorted_agents):
                    if i != j:
                        name1 = agent1['name']
                        name2 = agent2['name']
                        matchup1 = results[name1]['matchups'].get(name2, {'chip_delta': 0})
                        matchup2 = results[name2]['matchups'].get(name1, {'chip_delta': 0})
                        
                        delta1 = matchup1.get('chip_delta', matchup1 if isinstance(matchup1, int) else 0)
                        delta2 = matchup2.get('chip_delta', matchup2 if isinstance(matchup2, int) else 0)
                        
                        # If agent1 significantly outperformed agent2
                        if delta1 > delta2:
                            weight = abs(delta1 - delta2) / 1000  # Normalize
                            G.add_edge(agent1['name'].split('/')[-1], agent2['name'].split('/')[-1], weight=weight)
            
            # Use better layout algorithm with more spacing
            pos = nx.spring_layout(G, k=3.5, iterations=100, seed=42)
            
            # Draw nodes with larger size
            node_colors = [results[a['name']].get('avg_chips_per_table', 0) for a in sorted_agents]
            nodes = nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                          cmap='RdYlGn', node_size=2500, 
                                          vmin=min(node_colors), vmax=max(node_colors), 
                                          ax=ax, edgecolors='black', linewidths=2)
            
            # Draw edges with varying thickness
            edges = G.edges()
            weights = [G[u][v]['weight'] for u, v in edges]
            if weights:  # Only if there are edges
                max_weight = max(weights) if weights else 1
                normalized_weights = [3 * (w / max_weight) if max_weight > 0 else 1 for w in weights]
                nx.draw_networkx_edges(G, pos, width=normalized_weights, 
                                      alpha=0.5, edge_color='gray', 
                                      arrowsize=30, arrowstyle='->', 
                                      connectionstyle='arc3,rad=0.1', ax=ax)
            
            # Draw labels with larger font
            nx.draw_networkx_labels(G, pos, font_size=11, font_weight='bold', ax=ax)
            
            # Add colorbar
            sm = plt.cm.ScalarMappable(cmap='RdYlGn', 
                                      norm=plt.Normalize(vmin=min(node_colors), vmax=max(node_colors)))
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Avg Chips per Table', rotation=270, labelpad=25, fontsize=14, fontweight='bold')
            cbar.ax.tick_params(labelsize=12)
            
            ax.set_title('Dominance Network: Arrows Point from Winner to Loser\n(Node color = Avg chips/table, Edge thickness = Dominance strength)', 
                        fontsize=16, fontweight='bold', pad=20)
            ax.axis('off')
            ax.margins(0.15)  # Add margins around the graph
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'dominance_network.png'), dpi=200, bbox_inches='tight')
            plt.close()
        else:
            print("NetworkX not available, skipping dominance network graph")
    
    # Heads-up specific visualizations
    if mode == 'heads-up':
        # 5. Win Percentage Chart
        fig, ax = plt.subplots(figsize=(14, 8))
        win_percentages = [results[a['name']].get('win_percentage', 0) for a in sorted_agents]
        
        bars = ax.bar(agent_names, win_percentages, color='steelblue', alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Win Percentage (%)', fontsize=12)
        ax.set_title('Win Percentage (Wins / Total Matches)', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% baseline')
        ax.legend()
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'win_percentage.png'), dpi=150)
        plt.close()
        
        # 6. Elo Ratings
        fig, ax = plt.subplots(figsize=(14, 8))
        elo_ratings = [results[a['name']].get('elo_rating', 1500) for a in sorted_agents]
        
        colors = ['green' if x > 1500 else 'red' if x < 1500 else 'gray' for x in elo_ratings]
        bars = ax.bar(agent_names, elo_ratings, color=colors, alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Elo Rating', fontsize=12)
        ax.set_title('Elo Ratings (1500 = Average)', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=1500, color='black', linestyle='-', linewidth=0.8, label='1500 baseline')
        ax.legend()
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom' if height > 1500 else 'top', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'elo_ratings.png'), dpi=150)
        plt.close()
        
        # 7. Chip Margin Analysis
        fig, ax = plt.subplots(figsize=(14, 8))
        chip_margins = [results[a['name']].get('avg_chip_margin', 0) for a in sorted_agents]
        
        colors = ['green' if x > 0 else 'red' for x in chip_margins]
        bars = ax.bar(agent_names, chip_margins, color=colors, alpha=0.7)
        ax.set_xlabel('Agent', fontsize=12)
        ax.set_ylabel('Average Chip Margin', fontsize=12)
        ax.set_title('Average Chip Margin per Matchup (Dominance)', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(agent_names)))
        ax.set_xticklabels(agent_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'chip_margin.png'), dpi=150)
        plt.close()
        
        # 8. Consistency Scatter Plot (Performance vs Variability)
        fig, ax = plt.subplots(figsize=(14, 10))
        avg_chips = [results[a['name']].get('avg_chips_per_match', 0) for a in sorted_agents]
        consistencies = [results[a['name']].get('consistency', 0) for a in sorted_agents]
        
        scatter = ax.scatter(consistencies, avg_chips, s=200, alpha=0.6, c=elo_ratings, 
                            cmap='RdYlGn', edgecolors='black', linewidths=1)
        
        # Add labels for each point
        for i, name in enumerate(agent_names):
            ax.annotate(name, (consistencies[i], avg_chips[i]), 
                       fontsize=8, ha='right', va='bottom',
                       xytext=(-5, 5), textcoords='offset points')
        
        ax.set_xlabel('Consistency (Std Dev of Results)', fontsize=12)
        ax.set_ylabel('Average Chips per Match', fontsize=12)
        ax.set_title('Performance vs Consistency\\n(Lower consistency = more predictable)', 
                    fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Elo Rating', rotation=270, labelpad=20)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'consistency_scatter.png'), dpi=150)
        plt.close()
        
        # 9. Win/Loss Binary Heatmap
        fig, ax = plt.subplots(figsize=(14, 12))
        n_agents = len(sorted_agents)
        win_loss_matrix = np.zeros((n_agents, n_agents))
        
        for i, agent1 in enumerate(sorted_agents):
            for j, agent2 in enumerate(sorted_agents):
                if i != j:
                    chips1 = results[agent1['name']]['matchups'].get(agent2['name'], 0)
                    chips2 = results[agent2['name']]['matchups'].get(agent1['name'], 0)
                    # 1 for win, -1 for loss, 0 for tie
                    if chips1 > chips2:
                        win_loss_matrix[i, j] = 1
                    elif chips1 < chips2:
                        win_loss_matrix[i, j] = -1
        
        im = ax.imshow(win_loss_matrix, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
        
        ax.set_xticks(np.arange(n_agents))
        ax.set_yticks(np.arange(n_agents))
        ax.set_xticklabels(agent_names, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(agent_names, fontsize=8)
        
        cbar = plt.colorbar(im, ax=ax, ticks=[-1, 0, 1])
        cbar.set_ticklabels(['Loss', 'Tie', 'Win'])
        cbar.set_label('Match Outcome', rotation=270, labelpad=20)
        
        ax.set_title('Head-to-Head Win/Loss Matrix\\n(Green = Row agent beat Column agent)', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Opponent', fontsize=12)
        ax.set_ylabel('Agent', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'win_loss_matrix.png'), dpi=150)
        plt.close()
        
        # 10. Parameter Correlation Heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Extract parameter values
        param_data = []
        param_names = []
        for agent in sorted_agents:
            cfg = agent['config']
            if cfg:
                pop = cfg['evolution']['population_size']
                sigma = cfg['evolution']['mutation_sigma']
                gens = cfg['num_generations']
                matchups = cfg['fitness']['matchups_per_agent']
                hands = cfg['fitness']['hands_per_matchup']
                
                param_data.append([pop, sigma, gens, matchups, hands])
                param_names.append(agent['name'].split('/')[-1])
        
        if param_data:
            # Add performance metrics
            performance_data = []
            for agent in sorted_agents:
                if agent['config']:
                    elo = results[agent['name']].get('elo_rating', 1500)
                    win_pct = results[agent['name']].get('win_percentage', 0)
                    avg_margin = results[agent['name']].get('avg_chip_margin', 0)
                    performance_data.append([elo, win_pct, avg_margin])
            
            # Combine into full data matrix
            full_data = np.hstack([np.array(param_data), np.array(performance_data)])
            
            # Calculate correlation matrix
            corr_matrix = np.corrcoef(full_data.T)
            
            labels = ['Pop', 'Sigma', 'Gens', 'Matchups', 'Hands', 'Elo', 'Win%', 'Margin']
            
            im = ax.imshow(corr_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
            
            ax.set_xticks(np.arange(len(labels)))
            ax.set_yticks(np.arange(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.set_yticklabels(labels)
            
            # Add correlation values
            for i in range(len(labels)):
                for j in range(len(labels)):
                    text = ax.text(j, i, f'{corr_matrix[i, j]:.2f}',
                                 ha='center', va='center', color='black', fontsize=8)
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Correlation', rotation=270, labelpad=20)
            
            ax.set_title('Parameter Correlation Matrix', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'parameter_correlation.png'), dpi=150)
            plt.close()
        
        # 11. Dominance Network Graph (same as multi-table but for heads-up)
        if NETWORKX_AVAILABLE:
            fig, ax = plt.subplots(figsize=(20, 20))
            G = nx.DiGraph()
            
            # Add nodes
            for agent in sorted_agents:
                G.add_node(agent['name'].split('/')[-1])
            
            # Add edges for wins
            for i, agent1 in enumerate(sorted_agents):
                for j, agent2 in enumerate(sorted_agents):
                    if i != j:
                        name1 = agent1['name']
                        name2 = agent2['name']
                        chips1 = results[name1]['matchups'].get(name2, 0)
                        chips2 = results[name2]['matchups'].get(name1, 0)
                        
                        if chips1 > chips2:
                            margin = chips1 - chips2
                            weight = margin / 1000  # Normalize
                            G.add_edge(agent1['name'].split('/')[-1], 
                                     agent2['name'].split('/')[-1], weight=weight)
            
            # Use better layout with more spacing
            pos = nx.spring_layout(G, k=3.5, iterations=100, seed=42)
            
            # Draw nodes with larger size
            node_colors = elo_ratings
            nodes = nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                          cmap='RdYlGn', node_size=2500, 
                                          vmin=min(node_colors), vmax=max(node_colors), 
                                          ax=ax, edgecolors='black', linewidths=2)
            
            # Draw edges with better visibility
            edges = G.edges()
            weights = [G[u][v]['weight'] for u, v in edges]
            if weights:  # Only if there are edges
                max_weight = max(weights) if weights else 1
                normalized_weights = [3 * (w / max_weight) if max_weight > 0 else 1 for w in weights]
                nx.draw_networkx_edges(G, pos, width=normalized_weights, 
                                      alpha=0.5, edge_color='gray', 
                                      arrowsize=30, arrowstyle='->', 
                                      connectionstyle='arc3,rad=0.1', ax=ax)
            
            # Draw labels with larger font
            nx.draw_networkx_labels(G, pos, font_size=11, font_weight='bold', ax=ax)
            
            # Add colorbar
            sm = plt.cm.ScalarMappable(cmap='RdYlGn', 
                                      norm=plt.Normalize(vmin=min(node_colors), vmax=max(node_colors)))
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Elo Rating', rotation=270, labelpad=25, fontsize=14, fontweight='bold')
            cbar.ax.tick_params(labelsize=12)
            
            ax.set_title('Dominance Network: Arrows Point from Winner to Loser\n(Node color = Elo rating, Edge thickness = Win margin)', 
                        fontsize=16, fontweight='bold', pad=20)
            ax.axis('off')
            ax.margins(0.15)  # Add margins around the graph
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'dominance_network.png'), dpi=200, bbox_inches='tight')
            plt.close()

def main():
    parser = argparse.ArgumentParser(
        description='Run round-robin tournament between poker agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all checkpoints
  python3 scripts/evaluation/round_robin_agents_config.py
  
  # Run specific checkpoints
  python3 scripts/evaluation/round_robin_agents_config.py --checkpoints deep_p12_m6_h375_s0.1_hof3_g50 deep_p20_m6_h500_s0.15_hof3_g50
  
  # Run checkpoints matching pattern
  python3 scripts/evaluation/round_robin_agents_config.py --pattern "*hof3_g50"
  
  # Run specific agent files
  python3 scripts/evaluation/round_robin_agents_config.py --agents checkpoints/deep_p12_*/runs/*/best_genome.npy
  
  # Customize settings
  python3 scripts/evaluation/round_robin_agents_config.py --hands 5000 --checkpoints deep_p12_* deep_p20_*
        """
    )
    
    # Selection arguments
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--checkpoints', nargs='+', metavar='DIR',
                          help='Specific checkpoint directory names (e.g., deep_p12_m6_h375_s0.1_hof3_g50)')
    selection.add_argument('--pattern', type=str, metavar='PATTERN',
                          help='Glob pattern for checkpoint directories (e.g., "*hof3*")')
    selection.add_argument('--agents', nargs='+', metavar='PATH',
                          help='Specific agent file paths')
    
    # Tournament settings
    parser.add_argument('--mode', type=str, choices=['heads-up', 'multi-table'], default='heads-up',
                       help='Tournament mode: heads-up (1v1) or multi-table (6-player tables, default: heads-up)')
    parser.add_argument('--hands', type=int, default=DEFAULT_HANDS,
                       help=f'Hands per matchup (default: {DEFAULT_HANDS})')
    parser.add_argument('--table-size', type=int, default=6,
                       help='Players per table for multi-table mode (default: 6, only used with --mode multi-table)')
    parser.add_argument('--min-encounters', type=int, default=1,
                       help='Minimum times each pair must meet in multi-table mode (default: 1, only used with --mode multi-table)')
    parser.add_argument('--players', type=int, default=DEFAULT_PLAYERS,
                       help=f'Players per table for heads-up mode (default: {DEFAULT_PLAYERS}, only used with --mode heads-up)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output directory (default: tournament_reports/tournament_<timestamp>)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("POKER AI ROUND-ROBIN TOURNAMENT")
    print("=" * 80)
    print(f"Mode: {args.mode.upper()}")
    print(f"Hands per matchup: {args.hands}")
    if args.mode == 'multi-table':
        print(f"Players per table: {args.table_size}")
    else:
        print(f"Players per table: {args.players}")
    print()
    
    # Get agents based on selection criteria
    agents = get_agents_and_configs(
        checkpoint_dirs=args.checkpoints,
        checkpoint_pattern=args.pattern,
        agent_paths=args.agents
    )
    
    print(f"\nTournament participants: {len(agents)} agents")
    for i, agent in enumerate(agents, 1):
        print(f"  {i}. {agent['name']}")
    print()
    
    if len(agents) < 2:
        print("ERROR: Need at least 2 agents for a tournament!")
        sys.exit(1)
    
    # Validate table size for multi-table mode
    if args.mode == 'multi-table':
        if len(agents) < args.table_size:
            print(f"ERROR: Need at least {args.table_size} agents for multi-table tournament!")
            sys.exit(1)
    
    # Run tournament based on mode
    if args.mode == 'heads-up':
        results = run_tournament_headsup(agents, args.hands, args.players)
    else:  # multi-table
        results = run_tournament_multitable(agents, args.hands, args.table_size, args.min_encounters)
    
    # Analyze and report
    analyze_and_report(agents, results, output_dir=args.output, mode=args.mode)
    
    print("\n" + "=" * 80)
    print("Tournament complete!")
    print("=" * 80)

if __name__ == '__main__':
    main()

