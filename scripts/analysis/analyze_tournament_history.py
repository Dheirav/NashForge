#!/usr/bin/env python3
"""
Tournament History Analyzer

Analyzes cumulative tournament results across multiple tournament runs to identify:
- Best performing agents consistently
- Hyperparameter patterns that correlate with success
- Development recommendations for future training
- Head-to-head matchup statistics between specific agents
- Visual analysis with charts and heatmaps

Usage:
    # Analyze all tournaments in tournament_reports directory
    python scripts/analysis/analyze_tournament_history.py
    
    # Analyze tournaments from a specific batch folder
    python scripts/analysis/analyze_tournament_history.py --folder tournament_reports/Batch1
    python scripts/analysis/analyze_tournament_history.py --folder tournament_reports/Batch1and2Purge

Options:
    --folder FOLDER        Analyze specific tournament folder/batch (default: all tournaments)
    --min-tournaments N    Only include agents that participated in N+ tournaments (default: 1)
    --top-n N             Show top N agents in rankings (default: 10)
"""

import json
import os
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import re
from datetime import datetime

# Additional imports for advanced visualization
import seaborn as sns
import networkx as nx
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Visualizations will be skipped.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class AgentStats:
    """Tracks cumulative statistics for a single agent across tournaments."""
    
    def __init__(self, name: str):
        self.name = name
        self.total_wins = 0
        self.total_losses = 0
        self.total_tournaments = 0
        self.total_chip_earnings = 0
        self.chip_counts = []  # Track per-tournament chip counts
        self.tournament_dates = []
        self.opponents = defaultdict(lambda: {'wins': 0, 'losses': 0})  # Head-to-head stats
        
        # New metrics for multi-table tournaments
        self.total_tables_played = 0
        self.win_rates = []  # Per-tournament win rates
        self.avg_chips_per_table = []  # Per-tournament avg chips
        self.consistency_scores = []  # Per-tournament consistency
        self.positive_table_pcts = []  # Per-tournament positive table %
        self.finish_distributions = defaultdict(int)  # Cumulative finish positions
        
        # New metrics for heads-up tournaments
        self.elo_ratings = []  # Per-tournament Elo ratings
        self.win_percentages = []  # Per-tournament win %
        self.avg_chip_margins = []  # Per-tournament chip margins
        self.h2h_win_rates = defaultdict(list)  # Per-opponent win rates over time
        
        # Track tournament modes
        self.tournament_modes = []  # 'multi-table' or 'heads-up'
        # Store all extra fields for holistic reporting
        self.extra_fields = defaultdict(list)  # field_name -> list of values
        
    @property
    def total_games(self) -> int:
        return self.total_wins + self.total_losses
    
    @property
    def win_rate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_wins / self.total_games
    
    @property
    def avg_chips_per_tournament(self) -> float:
        if self.total_tournaments == 0:
            return 0.0
        return self.total_chip_earnings / self.total_tournaments
    
    @property
    def avg_elo_rating(self) -> float:
        if not self.elo_ratings:
            return 0.0
        return sum(self.elo_ratings) / len(self.elo_ratings)
    
    @property
    def avg_consistency(self) -> float:
        if not self.consistency_scores:
            return 0.0
        return sum(self.consistency_scores) / len(self.consistency_scores)
    
    @property
    def chip_consistency(self) -> float:
        """Lower is better - measures variance in chip performance."""
        if len(self.chip_counts) < 2:
            return 0.0
        mean = sum(self.chip_counts) / len(self.chip_counts)
        variance = sum((x - mean) ** 2 for x in self.chip_counts) / len(self.chip_counts)
        return variance ** 0.5
    
    def add_tournament_result(self, wins: int, losses: int, final_chips: int, date: str, 
                            mode: str = 'heads-up', **kwargs):
        """Add results from a single tournament with mode-specific metrics."""
        self.total_wins += wins
        self.total_losses += losses
        self.total_tournaments += 1
        self.total_chip_earnings += final_chips
        self.chip_counts.append(final_chips)
        self.tournament_dates.append(date)
        self.tournament_modes.append(mode)
        
        # Store mode-specific metrics
        if mode == 'multi-table':
            self.total_tables_played += kwargs.get('tables_played', 0)
            if 'win_rate' in kwargs:
                self.win_rates.append(kwargs['win_rate'])
            if 'avg_chips_per_table' in kwargs:
                self.avg_chips_per_table.append(kwargs['avg_chips_per_table'])
            if 'consistency' in kwargs:
                self.consistency_scores.append(kwargs['consistency'])
            if 'positive_table_pct' in kwargs:
                self.positive_table_pcts.append(kwargs['positive_table_pct'])
            if 'finish_distribution' in kwargs:
                for pos, count in kwargs['finish_distribution'].items():
                    self.finish_distributions[int(pos)] += count
            if 'h2h_win_rates' in kwargs:
                for opp, rate in kwargs['h2h_win_rates'].items():
                    self.h2h_win_rates[opp].append(rate)
        else:  # heads-up
            if 'elo_rating' in kwargs:
                self.elo_ratings.append(kwargs['elo_rating'])
            if 'win_percentage' in kwargs:
                self.win_percentages.append(kwargs['win_percentage'])
            if 'avg_chip_margin' in kwargs:
                self.avg_chip_margins.append(kwargs['avg_chip_margin'])
            if 'consistency' in kwargs:
                self.consistency_scores.append(kwargs['consistency'])
        # Store all extra fields for holistic reporting
        for k, v in kwargs.items():
            if k not in {'win_rate','avg_chips_per_table','consistency','positive_table_pct','finish_distribution','h2h_win_rates','elo_rating','win_percentage','avg_chip_margin','win_loss_ratio','tables_played'}:
                self.extra_fields[k].append(v)
    
    def add_head_to_head(self, opponent: str, won: bool):
        """Record a head-to-head matchup result."""
        if won:
            self.opponents[opponent]['wins'] += 1
        else:
            self.opponents[opponent]['losses'] += 1


def parse_genome_spec(name: str) -> Dict[str, float]:
    """
    Parse genome specification from agent name.
    
    Expected format: p{pop}_m{matchups}_h{hands}_s{sigma}_g{gens}
    
    Returns:
        Dictionary with keys: population, matchups, hands, sigma, generations
    """
    pattern = r'p(\d+)_m(\d+)_h(\d+)_s([\d.]+)(?:_g(\d+))?'
    match = re.search(pattern, name)
    
    if not match:
        return {}
    
    return {
        'population': int(match.group(1)),
        'matchups': int(match.group(2)),
        'hands': int(match.group(3)),
        'sigma': float(match.group(4)),
        'generations': int(match.group(5)) if match.group(5) else None
    }


def find_tournament_reports(base_dir: str = 'tournament_reports') -> List[Tuple[str, Path]]:
    """
    Find all tournament JSON reports, including nested directories.

    Returns:
        List of (timestamp, path) tuples sorted by timestamp
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        return []

    reports = []
    for tournament_dir in base_path.rglob('*'):
        if not tournament_dir.is_dir():
            continue

        # Extract timestamp from directory name (tournament_YYYYMMDD_HHMMSS or run_N)
        match = re.search(r'(?:tournament_)?(\d{8}_\d{6})', tournament_dir.name)
        if match:
            timestamp = match.group(1)
        elif tournament_dir.name.startswith('run_'):
            # Use run number as timestamp for sorting
            timestamp = tournament_dir.name
        else:
            continue

        # Try both possible report filenames
        report_path = tournament_dir / 'report.json'
        if not report_path.exists():
            report_path = tournament_dir / 'round_robin_report.json'

        if report_path.exists():
            reports.append((timestamp, report_path))

    return sorted(reports)  # Sort by timestamp


def load_tournament_data(report_path: Path) -> Dict:
    """Load tournament data from JSON report."""
    with open(report_path, 'r') as f:
        return json.load(f)


def analyze_tournament_history(min_tournaments: int = 1, specific_folder: str = None) -> Tuple[Dict[str, AgentStats], List[Dict]]:
    """
    Analyze all tournament results and aggregate statistics.
    
    Args:
        min_tournaments: Minimum number of tournaments an agent must participate in
        specific_folder: Specific tournament or batch folder to analyze
                        Can be a single tournament (e.g., 'tournament_reports/tournament_20260128_120000')
                        or a batch folder containing multiple tournaments (e.g., 'tournament_reports/Batch2')
        
    Returns:
        Tuple of (agent_stats dictionary, list of match data dictionaries)
    """
    if specific_folder:
        folder_path = Path(specific_folder)
        if not folder_path.exists():
            print(f"Error: Folder '{specific_folder}' not found")
            return {}, []

        # Check if it's a single tournament folder or a batch folder
        report_path = folder_path / 'report.json'
        if not report_path.exists():
            report_path = folder_path / 'round_robin_report.json'

        if report_path.exists():
            # Single tournament folder
            reports = [('specific', report_path)]
            print(f"Analyzing specific tournament: {specific_folder}\n")
        else:
            # Batch folder containing multiple tournaments (recursive search)
            print(f"Scanning batch folder recursively: {specific_folder}")
            reports = []
            for report in folder_path.rglob('report.json'):
                # Use parent folder name as timestamp if possible
                parent = report.parent
                match = re.search(r'(?:tournament_)?(\d{8}_\d{6})', parent.name)
                if match:
                    timestamp = match.group(1)
                elif parent.name.startswith('run_'):
                    timestamp = parent.name
                else:
                    timestamp = parent.name
                reports.append((timestamp, report))
            for report in folder_path.rglob('round_robin_report.json'):
                parent = report.parent
                match = re.search(r'(?:tournament_)?(\d{8}_\d{6})', parent.name)
                if match:
                    timestamp = match.group(1)
                elif parent.name.startswith('run_'):
                    timestamp = parent.name
                else:
                    timestamp = parent.name
                reports.append((timestamp, report))
            if not reports:
                print(f"Error: No tournament reports found in '{specific_folder}'")
                return {}, []
            reports = sorted(reports)  # Sort by timestamp
            print(f"Found {len(reports)} tournament(s) in batch folder\n")
    else:
        # Analyze all tournaments
        reports = find_tournament_reports()
        
        if not reports:
            print("No tournament reports found in tournament_reports/")
            return {}, []
        
        print(f"Found {len(reports)} tournament(s) to analyze\n")
    
    agent_stats = {}
    all_matches = []  # Store all individual match results
    
    for timestamp, report_path in reports:
        print(f"Processing tournament from {timestamp}...")
        data = load_tournament_data(report_path)
        
        # Get tournament mode (multi-table or heads-up)
        tournament_mode = data.get('mode', 'heads-up')
        
        # Extract results for each agent (handle both list and dict formats)
        agents_data = data.get('agents', [])
        if isinstance(agents_data, dict):
            # Old format: dictionary with agent names as keys
            for agent_name, stats in agents_data.items():
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = AgentStats(agent_name)
                
                agent_stats[agent_name].add_tournament_result(
                    wins=stats.get('wins', 0),
                    losses=stats.get('losses', 0),
                    final_chips=stats.get('final_chips', stats.get('chips', 0)),
                    date=timestamp,
                    mode=tournament_mode
                )
        elif isinstance(agents_data, list):
            # New format: list of agent objects
            for agent in agents_data:
                agent_name = agent.get('name', 'Unknown')
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = AgentStats(agent_name)
                
                # Collect mode-specific metrics
                mode_specific_data = {}
                if tournament_mode == 'multi-table':
                    mode_specific_data = {
                        'win_rate': agent.get('win_rate', 0),
                        'avg_chips_per_table': agent.get('avg_chips_per_table', 0),
                        'consistency': agent.get('consistency', 0),
                        'positive_table_pct': agent.get('positive_table_pct', 0),
                        'tables_played': agent.get('tables_played', 0),
                        'finish_distribution': agent.get('finish_distribution', {}),
                        'h2h_win_rates': agent.get('h2h_win_rates', {})
                    }
                else:  # heads-up
                    mode_specific_data = {
                        'win_percentage': agent.get('win_percentage', 0),
                        'elo_rating': agent.get('elo_rating', 1500),
                        'avg_chip_margin': agent.get('avg_chip_margin', 0),
                        'win_loss_ratio': agent.get('win_loss_ratio', 0),
                        'consistency': agent.get('consistency', 0)
                    }
                
                agent_stats[agent_name].add_tournament_result(
                    wins=agent.get('wins', 0),
                    losses=agent.get('losses', 0),
                    final_chips=agent.get('chips', 0),
                    date=timestamp,
                    mode=tournament_mode,
                    **mode_specific_data
                )
                
                # Extract head-to-head from beat/lost_to lists
                for opponent in agent.get('beat', []):
                    if opponent in agent_stats or opponent != agent_name:
                        if opponent not in agent_stats:
                            agent_stats[opponent] = AgentStats(opponent)
                        agent_stats[agent_name].add_head_to_head(opponent, won=True)
                        
                        # Record in all_matches
                        all_matches.append({
                            'winner': agent_name,
                            'loser': opponent,
                            'tournament': timestamp
                        })
                
                for opponent in agent.get('lost_to', []):
                    if opponent in agent_stats or opponent != agent_name:
                        if opponent not in agent_stats:
                            agent_stats[opponent] = AgentStats(opponent)
                        agent_stats[agent_name].add_head_to_head(opponent, won=False)
        
        # Also handle explicit matches list if present (old format)
        if 'matches' in data:
            for match in data['matches']:
                winner = match['winner']
                loser = match['loser']
                
                # Track in all_matches for later analysis
                all_matches.append({
                    'winner': winner,
                    'loser': loser,
                    'tournament': timestamp
                })
                
                # Update head-to-head stats
                if winner in agent_stats:
                    agent_stats[winner].add_head_to_head(loser, won=True)
                if loser in agent_stats:
                    agent_stats[loser].add_head_to_head(winner, won=False)
    
    # Filter by minimum tournaments
    if min_tournaments > 1:
        agent_stats = {
            name: stats for name, stats in agent_stats.items()
            if stats.total_tournaments >= min_tournaments
        }
    
    return agent_stats, all_matches


def analyze_hyperparameter_correlations(agent_stats: Dict[str, AgentStats]) -> Dict:
    """
    Analyze which hyperparameters correlate with better performance.
    
    Returns:
        Dictionary with hyperparameter analysis results
    """
    # Group agents by each hyperparameter value
    by_population = defaultdict(list)
    by_matchups = defaultdict(list)
    by_hands = defaultdict(list)
    by_sigma = defaultdict(list)
    
    for name, stats in agent_stats.items():
        spec = parse_genome_spec(name)
        if not spec:
            continue
        
        by_population[spec['population']].append((name, stats))
        by_matchups[spec['matchups']].append((name, stats))
        by_hands[spec['hands']].append((name, stats))
        by_sigma[spec['sigma']].append((name, stats))
    
    def avg_win_rate(agents: List[Tuple[str, AgentStats]]) -> float:
        if not agents:
            return 0.0
        return sum(stats.win_rate for _, stats in agents) / len(agents)
    
    def avg_chips(agents: List[Tuple[str, AgentStats]]) -> float:
        if not agents:
            return 0.0
        return sum(stats.avg_chips_per_tournament for _, stats in agents) / len(agents)
    
    # Calculate average performance for each hyperparameter value
    correlations = {
        'population': {
            pop: {
                'avg_win_rate': avg_win_rate(agents),
                'avg_chips': avg_chips(agents),
                'count': len(agents)
            }
            for pop, agents in by_population.items()
        },
        'matchups': {
            m: {
                'avg_win_rate': avg_win_rate(agents),
                'avg_chips': avg_chips(agents),
                'count': len(agents)
            }
            for m, agents in by_matchups.items()
        },
        'hands': {
            h: {
                'avg_win_rate': avg_win_rate(agents),
                'avg_chips': avg_chips(agents),
                'count': len(agents)
            }
            for h, agents in by_hands.items()
        },
        'sigma': {
            s: {
                'avg_win_rate': avg_win_rate(agents),
                'avg_chips': avg_chips(agents),
                'count': len(agents)
            }
            for s, agents in by_sigma.items()
        }
    }
    
    return correlations


def generate_recommendations(agent_stats: Dict[str, AgentStats],
                            correlations: Dict) -> List[str]:
    """
    Generate development recommendations based on analysis.
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # 1. Identify top performers
    if agent_stats:
        sorted_agents = sorted(agent_stats.values(),
                             key=lambda s: (s.win_rate, s.avg_chips_per_tournament),
                             reverse=True)
        
        top_agent = sorted_agents[0]
        top_spec = parse_genome_spec(top_agent.name)
        
        if top_spec:
            recommendations.append(
                f"BEST PERFORMER: {top_agent.name} with {top_agent.win_rate:.1%} win rate\n"
                f"  → Configuration: pop={top_spec['population']}, matchups={top_spec['matchups']}, "
                f"hands={top_spec['hands']}, sigma={top_spec['sigma']}"
            )
    
    # 2. Analyze population size
    if 'population' in correlations and correlations['population']:
        pop_data = correlations['population']
        best_pop = max(pop_data.items(), key=lambda x: x[1]['avg_win_rate'])
        recommendations.append(
            f"POPULATION SIZE: Best performing = {best_pop[0]} "
            f"(avg win rate: {best_pop[1]['avg_win_rate']:.1%})"
        )
    
    # 3. Analyze matchups per agent
    if 'matchups' in correlations and correlations['matchups']:
        matchup_data = correlations['matchups']
        best_matchups = max(matchup_data.items(), key=lambda x: x[1]['avg_win_rate'])
        recommendations.append(
            f"MATCHUPS PER AGENT: Best performing = {best_matchups[0]} "
            f"(avg win rate: {best_matchups[1]['avg_win_rate']:.1%})"
        )
    
    # 4. Analyze hands per matchup
    if 'hands' in correlations and correlations['hands']:
        hands_data = correlations['hands']
        best_hands = max(hands_data.items(), key=lambda x: x[1]['avg_win_rate'])
        recommendations.append(
            f"HANDS PER MATCHUP: Best performing = {best_hands[0]} "
            f"(avg win rate: {best_hands[1]['avg_win_rate']:.1%})"
        )
    
    # 5. Analyze sigma (mutation strength)
    if 'sigma' in correlations and correlations['sigma']:
        sigma_data = correlations['sigma']
        best_sigma = max(sigma_data.items(), key=lambda x: x[1]['avg_win_rate'])
        recommendations.append(
            f"SIGMA (MUTATION): Best performing = {best_sigma[0]} "
            f"(avg win rate: {best_sigma[1]['avg_win_rate']:.1%})"
        )
    
    # 6. Consistency analysis
    if agent_stats:
        sorted_by_consistency = sorted(
            [s for s in agent_stats.values() if s.total_tournaments >= 2],
            key=lambda s: s.chip_consistency
        )
        
        if sorted_by_consistency:
            most_consistent = sorted_by_consistency[0]
            recommendations.append(
                f"MOST CONSISTENT: {most_consistent.name} "
                f"(chip std dev: {most_consistent.chip_consistency:.0f})"
            )
    
    # 7. Development suggestions
    recommendations.append("\nDEVELOPMENT SUGGESTIONS:")
    
    if agent_stats:
        # Find agents with high win rate and high consistency
        good_candidates = [
            s for s in agent_stats.values()
            if s.win_rate > 0.5 and s.total_tournaments >= 2
        ]
        
        if good_candidates:
            good_candidates.sort(key=lambda s: (s.win_rate, -s.chip_consistency), reverse=True)
            recommendations.append(
                f"  → Continue training: {', '.join(s.name for s in good_candidates[:3])}"
            )
        
        # Find underperformers
        poor_performers = [
            s for s in agent_stats.values()
            if s.win_rate < 0.4 and s.total_tournaments >= 2
        ]
        
        if poor_performers:
            recommendations.append(
                f"  → Consider retiring: {', '.join(s.name for s in poor_performers[:3])}"
            )
        
        # Suggest hyperparameter exploration
        if 'population' in correlations and len(correlations['population']) > 1:
            pop_values = sorted(correlations['population'].keys())
            recommendations.append(
                f"  → Population sizes tested: {pop_values}"
            )
            
            # Suggest gaps to explore
            if max(pop_values) < 100:
                recommendations.append(
                    f"  → Try larger population sizes (60-100) for better diversity"
                )
    
    return recommendations


def print_report(agent_stats: Dict[str, AgentStats],
                correlations: Dict,
                recommendations: List[str],
                top_n: int = 10):
    """Print comprehensive analysis report to console."""
    
    print("\n" + "="*80)
    print(" TOURNAMENT HISTORY ANALYSIS ".center(80, "="))
    print("="*80 + "\n")
    
    # Overall statistics
    total_tournaments = max((s.total_tournaments for s in agent_stats.values()), default=0)
    total_agents = len(agent_stats)
    total_games = sum(s.total_games for s in agent_stats.values())
    
    # Determine tournament modes present
    all_modes = set()
    for stats in agent_stats.values():
        all_modes.update(stats.tournament_modes)
    
    print(f"Total Tournaments Analyzed: {total_tournaments}")
    print(f"Tournament Modes: {', '.join(all_modes) if all_modes else 'Unknown'}")
    print(f"Unique Agents: {total_agents}")
    print(f"Total Games Played: {total_games}")
    print()
    
    # Top performers with mode-specific metrics
    print("-" * 100)
    if 'multi-table' in all_modes:
        print(f" TOP {top_n} AGENTS (Multi-Table Metrics) ".center(100, "-"))
        print("-" * 100)
        print(f"{'Rank':<6} {'Agent Name':<35} {'WinRate':<10} {'AvgChips/T':<12} {'Consistency':<12} {'Tables':<8}")
        print("-" * 100)
        
        sorted_agents = sorted(agent_stats.values(),
                              key=lambda s: (s.win_rate, sum(s.avg_chips_per_table) / len(s.avg_chips_per_table) if s.avg_chips_per_table else 0),
                              reverse=True)
        
        for rank, stats in enumerate(sorted_agents[:top_n], 1):
            avg_chips_t = sum(stats.avg_chips_per_table) / len(stats.avg_chips_per_table) if stats.avg_chips_per_table else 0
            avg_cons = stats.avg_consistency
            tables = stats.total_tables_played
            print(f"{rank:<6} {stats.name:<35} {stats.win_rate:>7.1%}   {avg_chips_t:>10.1f}  {avg_cons:>10.1f}  {tables:>6}")
        
        # Show finish distribution for top agents
        print("\n" + "-" * 100)
        print(" FINISH POSITION DISTRIBUTION (Top 5) ".center(100, "-"))
        print("-" * 100)
        print(f"{'Agent':<35} {'1st':<8} {'2nd':<8} {'3rd':<8} {'4th':<8} {'5th':<8} {'6th':<8}")
        print("-" * 100)
        
        for stats in sorted_agents[:5]:
            if stats.finish_distributions:
                print(f"{stats.name:<35} ", end="")
                for pos in range(1, 7):
                    count = stats.finish_distributions.get(pos, 0)
                    print(f"{count:<8}", end="")
                print()
    
    elif 'heads-up' in all_modes:
        print(f" TOP {top_n} AGENTS (Heads-Up Metrics) ".center(100, "-"))
        print("-" * 100)
        print(f"{'Rank':<6} {'Agent Name':<35} {'WinRate':<10} {'Avg Elo':<10} {'ChipMargin':<12} {'W-L':<12}")
        print("-" * 100)
        
        sorted_agents = sorted(agent_stats.values(),
                              key=lambda s: (s.avg_elo_rating, s.win_rate),
                              reverse=True)
        
        for rank, stats in enumerate(sorted_agents[:top_n], 1):
            avg_elo = stats.avg_elo_rating
            avg_margin = sum(stats.avg_chip_margins) / len(stats.avg_chip_margins) if stats.avg_chip_margins else 0
            print(f"{rank:<6} {stats.name:<35} {stats.win_rate:>7.1%}   {avg_elo:>8.0f}  {avg_margin:>10.1f}  {stats.total_wins:>4}-{stats.total_losses:<5}")
    
    else:
        # Fallback for mixed or unknown modes
        print(f" TOP {top_n} AGENTS BY WIN RATE ".center(100, "-"))
        print("-" * 100)
        print(f"{'Rank':<6} {'Agent Name':<40} {'Win Rate':<12} {'W-L':<12} {'Avg Chips':<15}")
        print("-" * 100)
        
        sorted_agents = sorted(agent_stats.values(),
                              key=lambda s: (s.win_rate, s.avg_chips_per_tournament),
                              reverse=True)
        
        for rank, stats in enumerate(sorted_agents[:top_n], 1):
            print(f"{rank:<6} {stats.name:<40} {stats.win_rate:>6.1%}     "
                  f"{stats.total_wins:>4}-{stats.total_losses:<5} {stats.avg_chips_per_tournament:>12,.0f}")
    
    print()
    
    # Hyperparameter analysis
    print("-" * 100)
    print(" HYPERPARAMETER CORRELATION ANALYSIS ".center(100, "-"))
    print("-" * 100)
    
    for param_name, param_data in correlations.items():
        if not param_data:
            continue
        
        print(f"\n{param_name.upper()}:")
        sorted_values = sorted(param_data.items(),
                             key=lambda x: x[1]['avg_win_rate'],
                             reverse=True)
        
        for value, metrics in sorted_values:
            print(f"  {value:>8}: Win Rate = {metrics['avg_win_rate']:>6.1%}, "
                  f"Avg Chips = {metrics['avg_chips']:>10,.0f}, "
                  f"Agents = {metrics['count']}")
    
    print()
    
    # Recommendations
    print("-" * 100)
    print(" RECOMMENDATIONS ".center(100, "-"))
    print("-" * 100)
    
    for rec in recommendations:
        print(rec)
    
    print("\n" + "="*100 + "\n")


def create_head_to_head_matrix(agent_stats: Dict[str, AgentStats]) -> Tuple[List[str], any]:
    """
    Create a head-to-head win rate matrix for visualization.
    
    Returns:
        Tuple of (agent names list, win rate matrix)
    """
    if not NUMPY_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return [], []
    
    agent_names = sorted(agent_stats.keys())
    n = len(agent_names)
    matrix = np.zeros((n, n))
    
    for i, agent1 in enumerate(agent_names):
        for j, agent2 in enumerate(agent_names):
            if i == j:
                matrix[i, j] = 0.5  # Neutral for self
            else:
                stats = agent_stats[agent1].opponents.get(agent2, {'wins': 0, 'losses': 0})
                total = stats['wins'] + stats['losses']
                if total > 0:
                    matrix[i, j] = stats['wins'] / total
                else:
                    matrix[i, j] = 0.5  # No data = neutral
    
    return agent_names, matrix


def create_visualizations(agent_stats: Dict[str, AgentStats],
                         correlations: Dict,
                         output_dir: Path):
    """Create and save visualization charts."""
    

    if not MATPLOTLIB_AVAILABLE:
        print("Skipping visualizations (matplotlib not available)")
        return

    print("Generating visualizations...")

    # Create a subfolder for advanced visuals
    viz_dir = output_dir / 'visualizations'
    viz_dir.mkdir(exist_ok=True)

    # 1. Win Rate Comparison Bar Chart (existing)
    # ...existing code...

    # 2. Average Chips per Tournament (existing)
    # ...existing code...

    # 3. Head-to-Head Matchup Matrix (existing)
    # ...existing code...

    # 4. Hyperparameter Correlation Charts (existing)
    # ...existing code...

    # 5. Consistency Analysis (existing)
    # ...existing code...

    # 6. Advanced Visuals
    # a) Head-to-Head Heatmap (seaborn)
    agent_names, matrix = create_head_to_head_matrix(agent_stats)
    if len(agent_names) > 0:
        plt.figure(figsize=(max(10, len(agent_names)//2), max(8, len(agent_names)//2)))
        sns.heatmap(matrix, annot=True, fmt=".2f", cmap="RdYlGn", xticklabels=agent_names, yticklabels=agent_names, cbar_kws={'label': 'Win Rate'})
        plt.title('Head-to-Head Win Rate Heatmap')
        plt.xlabel('Opponent')
        plt.ylabel('Agent')
        plt.tight_layout()
        plt.savefig(viz_dir / 'head_to_head_heatmap.png', dpi=200)
        plt.close()

    # Chip distribution plot removed
    # Clustering methods: t-SNE, PCA, UMAP (if available), with k-means coloring
    from sklearn.cluster import KMeans
    try:
        import umap
        UMAP_AVAILABLE = True
    except ImportError:
        UMAP_AVAILABLE = False

    def clustering_plot(features, agent_labels, method, color_by_cluster=True, suffix=''):
        from scipy.spatial import ConvexHull
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        n_clusters = min(5, len(features_scaled))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(features_scaled) if color_by_cluster else None
        if method == 'pca':
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=2)
            reduced = reducer.fit_transform(features_scaled)
        elif method == 'umap' and UMAP_AVAILABLE:
            reducer = umap.UMAP(n_components=2, random_state=42)
            reduced = reducer.fit_transform(features_scaled)
        else:
            return
        plt.figure(figsize=(10, 8))
        if color_by_cluster:
            palette = sns.color_palette('Set1', n_clusters)  # More distinct colors
            for i in range(n_clusters):
                idxs = np.where(cluster_labels == i)[0]
                plt.scatter(reduced[idxs, 0], reduced[idxs, 1], c=[palette[i]]*len(idxs), label=f'Cluster {i+1}', alpha=0.95, edgecolors='black', linewidths=1)
                # Draw convex hull outline for cluster (only if at least 3 non-collinear points)
                if len(idxs) > 2:
                    points = reduced[idxs]
                    try:
                        hull = ConvexHull(points)
                        hull_pts = points[hull.vertices]
                        from matplotlib.patches import Polygon
                        poly = Polygon(hull_pts, closed=True, edgecolor=palette[i], facecolor=palette[i], alpha=0.35, linewidth=2)
                        plt.gca().add_patch(poly)
                    except Exception:
                        # Skip hull if points are collinear or QhullError occurs
                        pass
                # Add cluster label at centroid if cluster has >1 point
                if len(idxs) > 1:
                    centroid = np.mean(reduced[idxs], axis=0)
                    plt.text(centroid[0], centroid[1], f'C{i+1}', fontsize=14, color=palette[i], weight='bold', alpha=0.95, bbox=dict(facecolor='white', alpha=0.5, edgecolor=palette[i]))
        else:
            plt.scatter(reduced[:, 0], reduced[:, 1], c='blue', alpha=0.7)
        for i, label in enumerate(agent_labels):
            plt.text(reduced[i, 0], reduced[i, 1], label, fontsize=8, alpha=0.7)
        plt.title(f'Agent Clustering ({method.upper()}) {suffix}')
        plt.xlabel(f'{method.upper()} Dimension 1')
        plt.ylabel(f'{method.upper()} Dimension 2')
        if color_by_cluster:
            plt.legend()
        plt.tight_layout()
        plt.savefig(viz_dir / f'agent_clustering_{suffix}_{method}.png', dpi=200)
        plt.close()

    # Performance-based clustering
    features_perf = []
    agent_labels_perf = []
    for s in agent_stats.values():
        features_perf.append([
            s.win_rate,
            s.avg_chips_per_tournament,
            s.total_wins - s.total_losses
        ])
        agent_labels_perf.append(s.name)
    features_perf = np.array(features_perf)
    if len(features_perf) > 2:
        clustering_plot(features_perf, agent_labels_perf, 'pca', True, 'performance')
        if UMAP_AVAILABLE:
            clustering_plot(features_perf, agent_labels_perf, 'umap', True, 'performance')

    # Hyperparameter-based clustering
    features_hyper = []
    agent_labels_hyper = []
    for name, s in agent_stats.items():
        spec = parse_genome_spec(name)
        if spec:
            features_hyper.append([
                spec.get('population', 0),
                spec.get('matchups', 0),
                spec.get('hands', 0),
                spec.get('sigma', 0)
            ])
            agent_labels_hyper.append(name)
    features_hyper = np.array(features_hyper)
    if len(features_hyper) > 2:
        clustering_plot(features_hyper, agent_labels_hyper, 'pca', True, 'hyperparams')
        if UMAP_AVAILABLE:
            clustering_plot(features_hyper, agent_labels_hyper, 'umap', True, 'hyperparams')

    # Only keep the head-to-head win rate heatmap

    # d) Dominance Network (with node/edge stats)
    try:
        G = nx.DiGraph()
        for agent in agent_names:
            G.add_node(agent)
        for i, a1 in enumerate(agent_names):
            for j, a2 in enumerate(agent_names):
                if i != j and matrix[i, j] > 0.5:
                    G.add_edge(a1, a2, weight=matrix[i, j])
        plt.figure(figsize=(max(10, len(agent_names)//2), max(8, len(agent_names)//2)))
        pos = nx.spring_layout(G, seed=42)
        edges = G.edges()
        weights = [G[u][v]['weight'] for u,v in edges]
        nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color=weights, edge_cmap=plt.cm.RdYlGn, width=2, arrowsize=20)
        # Annotate top nodes by out-degree (most dominant)
        out_degrees = dict(G.out_degree())
        top_nodes = sorted(out_degrees, key=out_degrees.get, reverse=True)[:5]
        for node in top_nodes:
            x, y = pos[node]
            plt.text(x, y+0.05, f"Top Dominant: {node}", color='red', fontsize=10, ha='center')
        plt.title('Dominance Network (Edges: Win Rate > 0.5)\nTop nodes are most dominant agents')
        plt.tight_layout()
        plt.savefig(viz_dir / 'dominance_network.png', dpi=200)
        plt.close()
    except Exception as e:
        print(f"Could not generate dominance network: {e}")

    # e) Parameter Interaction Heatmaps (if possible)
    try:
        pop_matchup = defaultdict(lambda: defaultdict(list))
        for name, stats in agent_stats.items():
            spec = parse_genome_spec(name)
            if spec and 'population' in spec and 'matchups' in spec:
                pop_matchup[spec['population']][spec['matchups']].append(stats.win_rate)
        if pop_matchup:
            pop_vals = sorted(pop_matchup.keys())
            matchup_vals = sorted({m for d in pop_matchup.values() for m in d.keys()})
            heatmap_data = []
            for p in pop_vals:
                row = []
                for m in matchup_vals:
                    vals = pop_matchup[p][m]
                    row.append(np.mean(vals) if vals else np.nan)
                heatmap_data.append(row)
            plt.figure(figsize=(10, 8))
            sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="YlGnBu", xticklabels=matchup_vals, yticklabels=pop_vals, cbar_kws={'label': 'Avg Win Rate'})
            plt.title('Population vs Matchups: Avg Win Rate\nShows how win rate varies with population and matchups')
            plt.xlabel('Matchups')
            plt.ylabel('Population')
            plt.tight_layout()
            plt.savefig(viz_dir / 'population_vs_matchups_heatmap.png', dpi=200)
            plt.close()
    except Exception as e:
        print(f"Could not generate parameter interaction heatmap: {e}")

    # Restore and enhance top 15 visuals
    # Win Rate Comparison Bar Chart (top 15)
    sorted_agents = sorted(agent_stats.values(), key=lambda s: s.win_rate, reverse=True)[:15]
    names = [s.name for s in sorted_agents]
    win_rates = [s.win_rate * 100 for s in sorted_agents]
    plt.figure(figsize=(12, 8))
    bars = plt.barh(range(len(names)), win_rates, color=plt.cm.viridis(np.linspace(0, 1, len(names))))
    plt.xlabel('Win Rate (%)', fontsize=12)
    plt.title('Top 15 Agents by Win Rate\nSorted by win rate, color-coded')
    plt.yticks(range(len(names)), names, fontsize=9)
    plt.grid(axis='x', alpha=0.3)
    for i, (bar, rate) in enumerate(zip(bars, win_rates)):
        plt.text(rate + 0.5, i, f'{rate:.1f}%', va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(viz_dir / 'win_rate_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Average Chips per Tournament (top 15)
    sorted_by_chips = sorted(agent_stats.values(), key=lambda s: s.avg_chips_per_tournament, reverse=True)[:15]
    names_chips = [s.name for s in sorted_by_chips]
    avg_chips = [s.avg_chips_per_tournament for s in sorted_by_chips]
    plt.figure(figsize=(12, 8))
    bars = plt.barh(range(len(names_chips)), avg_chips, color='green', alpha=0.7)
    plt.xlabel('Average Chips per Tournament', fontsize=12)
    plt.title('Top 15 Agents by Average Chips\nSorted by average chips, green bars')
    plt.yticks(range(len(names_chips)), names_chips, fontsize=9)
    plt.grid(axis='x', alpha=0.3)
    for i, (bar, chips) in enumerate(zip(bars, avg_chips)):
        plt.text(chips + max(avg_chips)*0.01, i, f'{chips:,.0f}', va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(viz_dir / 'avg_chips_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Consistency Analysis (top 15)
    agents_with_multiple = [s for s in agent_stats.values() if s.total_tournaments >= 2]
    sorted_consistency = sorted(agents_with_multiple, key=lambda s: s.chip_consistency)[:15]
    names_cons = [s.name for s in sorted_consistency]
    consistency = [s.chip_consistency for s in sorted_consistency]
    plt.figure(figsize=(12, 8))
    bars = plt.barh(range(len(names_cons)), consistency, color='purple', alpha=0.6)
    plt.xlabel('Chip Standard Deviation (Lower = More Consistent)', fontsize=12)
    plt.title('Top 15 Most Consistent Agents\nSorted by chip std dev, purple bars')
    plt.yticks(range(len(names_cons)), names_cons, fontsize=9)
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(viz_dir / 'consistency_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Hyperparameter Impact (bar charts)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Hyperparameter Impact on Performance', fontsize=16, fontweight='bold')
    param_names = ['population', 'matchups', 'hands', 'sigma']
    titles = ['Population Size', 'Matchups per Agent', 'Hands per Matchup', 'Sigma (Mutation Strength)']
    for idx, (param, title) in enumerate(zip(param_names, titles)):
        ax = axes[idx // 2, idx % 2]
        if param in correlations and correlations[param]:
            data = correlations[param]
            values = sorted(data.keys())
            win_rates = [data[v]['avg_win_rate'] * 100 for v in values]
            counts = [data[v]['count'] for v in values]
            bars = ax.bar(range(len(values)), win_rates, color='coral', alpha=0.7)
            ax.set_xticks(range(len(values)))
            ax.set_xticklabels([str(v) for v in values])
            ax.set_xlabel(title, fontsize=11)
            ax.set_ylabel('Avg Win Rate (%)', fontsize=11)
            ax.set_title(f'{title} vs Performance\nBar height = avg win rate, label = sample size')
            ax.grid(axis='y', alpha=0.3)
            for i, (bar, count) in enumerate(zip(bars, counts)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5, f'n={count}', ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    plt.savefig(viz_dir / 'hyperparameter_impact.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 8. Correlation Matrix
    try:
        df = pd.DataFrame({
            'win_rate': [s.win_rate for s in agent_stats.values()],
            'avg_chips': [s.avg_chips_per_tournament for s in agent_stats.values()],
            'chip_consistency': [s.chip_consistency for s in agent_stats.values()],
            'avg_elo': [s.avg_elo_rating for s in agent_stats.values()],
            'avg_consistency': [s.avg_consistency for s in agent_stats.values()],
        }, index=[s.name for s in agent_stats.values()])
        corr = df.corr()
        plt.figure(figsize=(8, 6))
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
        plt.title('Correlation Matrix of Agent Metrics')
        plt.tight_layout()
        plt.savefig(viz_dir / 'correlation_matrix.png', dpi=200)
        plt.close()
    except Exception as e:
        print(f"Could not generate correlation matrix: {e}")

    # 8b. Correlation Matrix (Hyperparameters)
    try:
        hyper_df = pd.DataFrame([
            parse_genome_spec(name) for name in agent_stats.keys() if parse_genome_spec(name)
        ], index=[name for name in agent_stats.keys() if parse_genome_spec(name)])
        if not hyper_df.empty:
            corr_hyper = hyper_df.corr()
            plt.figure(figsize=(8, 6))
            sns.heatmap(corr_hyper, annot=True, cmap='viridis', fmt='.2f')
            plt.title('Correlation Matrix of Hyperparameters')
            plt.tight_layout()
            plt.savefig(viz_dir / 'correlation_matrix_hyperparameters.png', dpi=200)
            plt.close()
    except Exception as e:
        print(f"Could not generate correlation matrix (hyperparameters): {e}")

    # 9. Parameter Sensitivity Plots (encode all other hyperparameters visually)
    try:
        param_names = ['population', 'matchups', 'hands', 'sigma']
        for param in param_names:
            param_vals = []
            win_rates = []
            other_params = {p: [] for p in param_names if p != param}
            for name, stats in agent_stats.items():
                spec = parse_genome_spec(name)
                if spec and param in spec:
                    param_vals.append(spec[param])
                    win_rates.append(stats.win_rate)
                    for p in other_params:
                        other_params[p].append(spec.get(p, 0))
            if param_vals:
                plt.figure(figsize=(8, 6))
                # Use seaborn.scatterplot to encode up to 3 other params: hue, style, size
                plot_kwargs = dict(x=param_vals, y=win_rates)
                keys = list(other_params.keys())
                legend_labels = []
                if len(keys) > 0:
                    plot_kwargs['hue'] = other_params[keys[0]]
                    legend_labels.append(f"Color: {keys[0].capitalize()}")
                if len(keys) > 1:
                    plot_kwargs['style'] = other_params[keys[1]]
                    legend_labels.append(f"Marker: {keys[1].capitalize()}")
                if len(keys) > 2:
                    plot_kwargs['size'] = other_params[keys[2]]
                    legend_labels.append(f"Size: {keys[2].capitalize()}")
                # Use a more distinct palette for hue
                palette = 'tab10' if 'hue' in plot_kwargs else None
                ax = sns.scatterplot(**plot_kwargs, palette=palette, edgecolor='black', alpha=0.8, legend='full')
                # Add colorbar if hue is present
                if 'hue' in plot_kwargs:
                    # For categorical/discrete hues, create a custom legend
                    unique_vals = sorted(set(plot_kwargs['hue']))
                    handles = [plt.Line2D([0], [0], marker='o', color='w', label=str(val),
                                          markerfacecolor=sns.color_palette('tab10')[i % 10], markersize=10)
                               for i, val in enumerate(unique_vals)]
                    ax.legend(handles=handles, title=f"{keys[0].capitalize()} (Color)", loc='best')
                plt.title(f'Parameter Sensitivity: {param} vs Win Rate')
                plt.xlabel(param.capitalize())
                plt.ylabel('Win Rate')
                # Add a custom legend for what each visual encoding means
                if legend_labels:
                    plt.legend(title="Visual Encoding", labels=legend_labels, loc='best')
                plt.tight_layout()
                plt.savefig(viz_dir / f'parameter_sensitivity_{param}.png', dpi=200)
                plt.close()
    except Exception as e:
        print(f"Could not generate parameter sensitivity plots: {e}")

    # 10. Streak Analysis (winning/losing streaks)
    try:
        win_streaks = {}
        lose_streaks = {}
        for s in agent_stats.values():
            win_streak = 0
            lose_streak = 0
            max_win_streak = 0
            max_lose_streak = 0
            last_result = None
            for chips in s.chip_counts:
                result = chips > 0
                if result:
                    if last_result is True:
                        win_streak += 1
                    else:
                        win_streak = 1
                    max_win_streak = max(max_win_streak, win_streak)
                    lose_streak = 0
                else:
                    if last_result is False:
                        lose_streak += 1
                    else:
                        lose_streak = 1
                    max_lose_streak = max(max_lose_streak, lose_streak)
                    win_streak = 0
                last_result = result
            win_streaks[s.name] = max_win_streak
            lose_streaks[s.name] = max_lose_streak
        plt.figure(figsize=(12, 7))
        agents = list(agent_stats.keys())
        win_vals = [win_streaks.get(a, 0) for a in agents]
        lose_vals = [lose_streaks.get(a, 0) for a in agents]
        bar1 = plt.bar(np.arange(len(agents)), win_vals, color='green', label='Longest Win Streak')
        bar2 = plt.bar(np.arange(len(agents)), [-v for v in lose_vals], color='red', label='Longest Lose Streak')
        plt.axhline(0, color='black', linewidth=0.8)
        plt.xticks(np.arange(len(agents)), agents, rotation=45, ha='right')
        plt.ylabel('Streak Length')
        plt.title('Longest Win (Green) and Lose (Red) Streak per Agent')
        plt.legend()
        plt.tight_layout()
        plt.savefig(viz_dir / 'streak_analysis.png', dpi=200)
        plt.close()
    except Exception as e:
        print(f"Could not generate streak analysis: {e}")

    # 11. Upset Maps (lower-ranked agent beats higher-ranked)
    try:
        # Use all_matches if available
        if 'all_matches' in locals():
            sorted_agents = sorted(agent_stats.values(), key=lambda s: s.win_rate, reverse=True)
            rank = {s.name: i for i, s in enumerate(sorted_agents)}
            upsets = []
            for match in all_matches:
                winner = match['winner']
                loser = match['loser']
                if rank[winner] > rank[loser]:
                    upsets.append((winner, loser))
            if upsets:
                upset_df = pd.DataFrame(upsets, columns=['Winner', 'Loser'])
                plt.figure(figsize=(8, 6))
                sns.countplot(data=upset_df, x='Winner', order=upset_df['Winner'].value_counts().index)
                plt.title('Upset Map: Lower-Ranked Agents Beating Higher-Ranked')
                plt.xlabel('Agent (Upset Winner)')
                plt.ylabel('Upset Count')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig(viz_dir / 'upset_map.png', dpi=200)
                plt.close()
    except Exception as e:
        print(f"Could not generate upset map: {e}")

    # 12. Survival Analysis (how long agents remain competitive)
    try:
        survival = {s.name: sum(1 for c in s.chip_counts if c > 0) for s in agent_stats.values()}
        plt.figure(figsize=(10, 6))
        sns.barplot(x=list(survival.keys()), y=list(survival.values()))
        plt.title('Agent Survival Analysis (Tournaments with Positive Chips)')
        plt.xlabel('Agent')
        plt.ylabel('Tournaments Survived')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(viz_dir / 'survival_analysis.png', dpi=200)
        plt.close()
    except Exception as e:
        print(f"Could not generate survival analysis: {e}")

def save_json_report(agent_stats: Dict[str, AgentStats],
                    correlations: Dict,
                    recommendations: List[str],
                    output_dir: Path):
    """Save analysis results as JSON."""
    
    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_agents': len(agent_stats),
            'total_tournaments': max((s.total_tournaments for s in agent_stats.values()), default=0),
            'total_games': sum(s.total_games for s in agent_stats.values())
        },
        'agents': {},
        'correlations': correlations,
        'recommendations': recommendations
    }
    
    # Add detailed agent stats
    for name, stats in agent_stats.items():
        spec = parse_genome_spec(name)
        report['agents'][name] = {
            'win_rate': stats.win_rate,
            'total_wins': stats.total_wins,
            'total_losses': stats.total_losses,
            'tournaments_participated': stats.total_tournaments,
            'avg_chips_per_tournament': stats.avg_chips_per_tournament,
            'chip_consistency': stats.chip_consistency,
            'configuration': spec,
            'tournament_dates': stats.tournament_dates,
            'head_to_head': dict(stats.opponents)
        }
        # Include aggregated extra fields for transparency
        if hasattr(stats, 'extra_fields') and stats.extra_fields:
            report['agents'][name]['extra_fields'] = {k: v for k, v in stats.extra_fields.items()}
    
    # Save JSON
    with open(output_dir / 'analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"JSON report saved to {output_dir / 'analysis_report.json'}")


def save_text_report(agent_stats: Dict[str, AgentStats],
                    correlations: Dict,
                    recommendations: List[str],
                    output_dir: Path):
    """Save detailed report to text file."""
    
    output_file = output_dir / 'analysis_report.txt'
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write(" TOURNAMENT HISTORY ANALYSIS ".center(80, "=") + "\n")
        f.write("="*80 + "\n\n")
        
        # Overall statistics
        total_tournaments = max((s.total_tournaments for s in agent_stats.values()), default=0)
        total_agents = len(agent_stats)
        total_games = sum(s.total_games for s in agent_stats.values())
        
        f.write(f"Total Tournaments Analyzed: {total_tournaments}\n")
        f.write(f"Unique Agents: {total_agents}\n")
        f.write(f"Total Games Played: {total_games}\n\n")
        
        # Detailed agent statistics
        f.write("-" * 80 + "\n")
        f.write(" DETAILED AGENT STATISTICS ".center(80, "-") + "\n")
        f.write("-" * 80 + "\n\n")
        
        sorted_agents = sorted(agent_stats.values(),
                              key=lambda s: (s.win_rate, s.avg_chips_per_tournament),
                              reverse=True)
        
        for rank, stats in enumerate(sorted_agents, 1):
            f.write(f"{rank}. {stats.name}\n")
            f.write(f"   Win Rate: {stats.win_rate:.1%} ({stats.total_wins}W - {stats.total_losses}L)\n")
            f.write(f"   Tournaments: {stats.total_tournaments}\n")
            f.write(f"   Avg Chips/Tournament: {stats.avg_chips_per_tournament:,.0f}\n")
            f.write(f"   Chip Consistency (std dev): {stats.chip_consistency:.0f}\n")
            
            spec = parse_genome_spec(stats.name)
            if spec:
                f.write(f"   Config: pop={spec['population']}, matchups={spec['matchups']}, "
                       f"hands={spec['hands']}, sigma={spec['sigma']}")
                if spec['generations']:
                    f.write(f", gens={spec['generations']}")
                f.write("\n")
            
            f.write(f"   Tournament Dates: {', '.join(stats.tournament_dates)}\n\n")
        
        # Hyperparameter analysis
        f.write("-" * 80 + "\n")
        f.write(" HYPERPARAMETER CORRELATION ANALYSIS ".center(80, "-") + "\n")
        f.write("-" * 80 + "\n\n")
        
        for param_name, param_data in correlations.items():
            if not param_data:
                continue
            
            f.write(f"{param_name.upper()}:\n")
            sorted_values = sorted(param_data.items(),
                                 key=lambda x: x[1]['avg_win_rate'],
                                 reverse=True)
            
            for value, metrics in sorted_values:
                f.write(f"  {value:>8}: Win Rate = {metrics['avg_win_rate']:>6.1%}, "
                       f"Avg Chips = {metrics['avg_chips']:>10,.0f}, "
                       f"Agents = {metrics['count']}\n")
            f.write("\n")
        
        # Recommendations
        f.write("-" * 80 + "\n")
        f.write(" RECOMMENDATIONS ".center(80, "-") + "\n")
        f.write("-" * 80 + "\n\n")
        
        for rec in recommendations:
            f.write(rec + "\n")
        
        f.write("\n" + "="*80 + "\n")

        # Appendix: include all extra fields captured per agent for full transparency
        f.write('\n' + '-'*80 + "\n")
        f.write(' APPENDIX: AGENT EXTRA FIELDS (Raw aggregated values) '.center(80, '-') + "\n")
        f.write('-'*80 + "\n\n")

        for stats in sorted_agents:
            f.write(f"Agent: {stats.name}\n")
            if hasattr(stats, 'extra_fields') and stats.extra_fields:
                for k, vals in stats.extra_fields.items():
                    # Present a concise summary: unique values and counts
                    try:
                        uniq = list(dict.fromkeys(vals))[:10]
                        f.write(f"   {k}: {uniq} (n={len(vals)})\n")
                    except Exception:
                        f.write(f"   {k}: {vals}\n")
            else:
                f.write("   (no extra fields)\n")
            f.write('\n')

        # Visualizations index reference
        f.write('-'*80 + "\n")
        f.write(' VISUALIZATIONS INDEX '.center(80, '-') + "\n")
        f.write('-'*80 + "\n\n")
        # Embedded visuals descriptions (fallback if visuals_index.txt is missing)
        visuals_desc = {
            'win_rate_comparison.png': 'Top 15 agents by overall win rate (bar chart).',
            'avg_chips_comparison.png': 'Top 15 agents by average chips per tournament (bar chart).',
            'head_to_head_matrix.png': 'Head-to-head win rate matrix (rows = agent, cols = opponent).',
            'hyperparameter_impact.png': 'Hyperparameter impact on performance (multiple bar charts).',
            'consistency_analysis.png': 'Top 15 most consistent agents by chip std dev (horizontal bar chart).'
        }
        for fname, desc in visuals_desc.items():
            f.write(f"{fname}: {desc}\n")
        f.write('\n' + '='*80 + '\n')
    
    print(f"Text report saved to: {output_file}")


def analyze_specific_matchups(agent_stats: Dict[str, AgentStats], output_dir: Path):
    """
    Analyze and report on specific agent-vs-agent matchups.
    Creates a detailed head-to-head comparison report.
    """
    
    output_file = output_dir / 'head_to_head_analysis.txt'
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write(" HEAD-TO-HEAD MATCHUP ANALYSIS ".center(80, "=") + "\n")
        f.write("="*80 + "\n\n")
        
        f.write("This report shows detailed head-to-head statistics between all agents\n")
        f.write("that have faced each other in tournaments.\n\n")
        
        # Get all agents sorted by win rate
        sorted_agents = sorted(agent_stats.values(),
                             key=lambda s: s.win_rate,
                             reverse=True)
        
        for agent in sorted_agents:
            if not agent.opponents:
                continue
            
            f.write("-" * 80 + "\n")
            f.write(f"{agent.name}\n")
            f.write(f"Overall: {agent.win_rate:.1%} ({agent.total_wins}W - {agent.total_losses}L)\n")
            f.write("-" * 80 + "\n\n")
            
            # Sort opponents by number of games played
            opponent_data = []
            for opp_name, stats in agent.opponents.items():
                total = stats['wins'] + stats['losses']
                win_rate = stats['wins'] / total if total > 0 else 0
                opponent_data.append((opp_name, stats['wins'], stats['losses'], win_rate))
            
            opponent_data.sort(key=lambda x: x[1] + x[2], reverse=True)
            
            f.write("  Matchups:\n")
            for opp_name, wins, losses, wr in opponent_data:
                total = wins + losses
                f.write(f"    vs {opp_name}: {wr:.1%} ({wins}W - {losses}L, {total} games)\n")
            
            f.write("\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write(" KEY RIVALRIES (Most Games Played) ".center(80, "=") + "\n")
        f.write("="*80 + "\n\n")
        
        # Find most common matchups
        matchup_counts = defaultdict(int)
        matchup_details = {}
        
        for agent in agent_stats.values():
            for opp_name, stats in agent.opponents.items():
                pair = tuple(sorted([agent.name, opp_name]))
                total = stats['wins'] + stats['losses']
                matchup_counts[pair] += total
                
                if pair not in matchup_details:
                    matchup_details[pair] = defaultdict(lambda: {'wins': 0, 'losses': 0})
                
                matchup_details[pair][agent.name]['wins'] += stats['wins']
                matchup_details[pair][agent.name]['losses'] += stats['losses']
        
        # Sort by total games
        top_matchups = sorted(matchup_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for (agent1, agent2), total_games in top_matchups:
            details = matchup_details[(agent1, agent2)]
            
            a1_wins = details[agent1]['wins']
            a1_losses = details[agent1]['losses']
            a2_wins = details[agent2]['wins']
            a2_losses = details[agent2]['losses']
            
            # Note: a1_losses should equal a2_wins and vice versa
            a1_record = f"{a1_wins}W - {a1_losses}L"
            a2_record = f"{a2_wins}W - {a2_losses}L"
            
            f.write(f"{agent1}  vs  {agent2}\n")
            f.write(f"  {agent1}: {a1_record}\n")
            f.write(f"  {agent2}: {a2_record}\n")
            f.write(f"  Total games: {total_games}\n\n")
    
    print(f"Head-to-head analysis saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze tournament history to identify best performing agents and development paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all tournaments
  python scripts/analysis/analyze_tournament_history.py
  
  # Analyze tournaments from a specific folder
  python scripts/analysis/analyze_tournament_history.py --folder tournament_reports/tournament_20260128_120000
  
  # Only analyze agents that participated in 2+ tournaments
  python scripts/analysis/analyze_tournament_history.py --min-tournaments 2
  
  # Show top 5 agents and save to custom file
  python scripts/analysis/analyze_tournament_history.py --top-n 5 --output my_analysis.txt
        """
    )
    
    parser.add_argument('--folder', type=str, default=None,
                       help='Specific tournament folder or batch to analyze (e.g., tournament_reports/Batch1, tournament_reports/Batch1and2Purge). If not specified, analyzes all tournaments in tournament_reports/')
    parser.add_argument('--min-tournaments', type=int, default=1,
                       help='Minimum tournaments an agent must participate in (default: 1)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top agents to show (default: 10)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for results/visualizations (default: tournament_reports/overall_reports/analysis_<timestamp>)')
    
    args = parser.parse_args()
    
    # Create output directory (user-specified or default with timestamp)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('tournament_reports') / 'overall_reports' / f'analysis_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")
    
    # Analyze tournament history
    agent_stats, all_matches = analyze_tournament_history(
        min_tournaments=args.min_tournaments,
        specific_folder=args.folder
    )
    
    if not agent_stats:
        print("No agent data found matching criteria.")
        return
    
    # Analyze hyperparameter correlations
    correlations = analyze_hyperparameter_correlations(agent_stats)
    
    # Generate recommendations
    recommendations = generate_recommendations(agent_stats, correlations)
    
    # Print report to console
    print_report(agent_stats, correlations, recommendations, top_n=args.top_n)
    
    # Save reports
    save_text_report(agent_stats, correlations, recommendations, output_dir)
    save_json_report(agent_stats, correlations, recommendations, output_dir)
    
    # Analyze specific matchups
    analyze_specific_matchups(agent_stats, output_dir)
    
    # Create visualizations
    create_visualizations(agent_stats, correlations, output_dir)
    
    print(f"\n{'='*80}")
    print(f"Analysis complete! All reports saved to:")
    print(f"  {output_dir}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
