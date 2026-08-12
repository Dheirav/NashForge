#!/usr/bin/env python3
"""
Check if Hall of Fame needs updating based on recent training runs and tournaments.

This script analyzes:
1. Recent checkpoint runs (new best genomes from training)
2. Tournament results (new champions)
3. Current Hall of Fame contents
4. Recommends which genomes should be added/updated

Usage:
    # Check for any updates needed
    python scripts/utilities/check_hof_updates.py
    
    # Only check checkpoints from last N days
    python scripts/utilities/check_hof_updates.py --days 7
    
    # Set custom fitness threshold for recommendations
    python scripts/utilities/check_hof_updates.py --min-fitness 60
    
    # Check specific checkpoint directories
    python scripts/utilities/check_hof_updates.py --checkpoint-dir checkpoints/deep_p12_m6_h750_s0.1_hof3_g200
    
    # Verbose output with detailed comparisons
    python scripts/utilities/check_hof_updates.py --verbose
"""

import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class GenomeCandidate:
    """Represents a candidate genome for Hall of Fame inclusion."""
    
    def __init__(self, name: str, path: Path, fitness: float, 
                 generation: int, date: datetime, source: str, 
                 config: Optional[Dict] = None, tournament_stats: Optional[Dict] = None):
        self.name = name
        self.path = path
        self.fitness = fitness
        self.generation = generation
        self.date = date
        self.source = source  # 'checkpoint', 'tournament', 'milestone'
        self.config = config or {}
        self.weights = None
        self.hyperparams = self._extract_hyperparams()
        self.tournament_stats = tournament_stats or {}  # win_rate, wins, losses, tournaments
        
    def _extract_hyperparams(self) -> Dict:
        """Extract hyperparameters from config name."""
        params = {}
        # Parse from name pattern: p12_m6_h750_s0.1_hof3_g200
        import re
        match = re.search(r'p(\d+)', self.name)
        if match:
            params['population'] = int(match.group(1))
        match = re.search(r'm(\d+)', self.name)
        if match:
            params['matchups'] = int(match.group(1))
        match = re.search(r'h(\d+)', self.name)
        if match:
            params['hands'] = int(match.group(1))
        match = re.search(r's([0-9.]+)', self.name)
        if match:
            params['sigma'] = float(match.group(1))
        match = re.search(r'hof(\d+)', self.name)
        if match:
            params['hof_training'] = True
            params['hof_count'] = int(match.group(1))
        return params
        
    def load_weights(self):
        """Load genome weights for comparison."""
        if self.weights is None and self.path.exists():
            try:
                loaded = np.load(self.path)
                if loaded.ndim == 2:
                    self.weights = loaded[0]  # Take first genome from population
                else:
                    self.weights = loaded
            except Exception as e:
                print(f"  Warning: Could not load {self.path}: {e}")
        return self.weights
    
    def __repr__(self):
        return f"<Candidate {self.name} fitness={self.fitness:.1f} gen={self.generation}>"


class HallOfFameChecker:
    """Checks if Hall of Fame needs updates based on recent results."""
    
    def __init__(self, workspace_root: Path, verbose: bool = False):
        self.workspace_root = workspace_root
        self.verbose = verbose
        self.hof_dir = workspace_root / "hall_of_fame"
        self.checkpoints_dir = workspace_root / "checkpoints"
        self.tournament_reports_dir = workspace_root / "tournament_reports"
        
        self.current_champions = []
        self.current_champion_fitness = {}  # name -> fitness
        self.current_champion_tournament = {}  # name -> tournament stats
        self.current_milestones = []
        self.candidates = []
        self.tournaments_scanned = 0  # Track how many tournaments processed
        
    def _try_get_fitness_for_champion(self, name: str) -> Optional[float]:
        """Try to extract fitness from champion's original checkpoint."""
        # Look for matching checkpoint
        import re
        base_name = name.replace('_champion', '').replace('_v2', '')
        
        # Try to find in checkpoints
        for checkpoint_dir in self.checkpoints_dir.iterdir():
            if not checkpoint_dir.is_dir() or checkpoint_dir.name == "archived_configs":
                continue
            if base_name in checkpoint_dir.name:
                # Found matching checkpoint, look for runs
                for runs_type in ['runs', 'evolution_run']:
                    runs_dir = checkpoint_dir / runs_type
                    if runs_dir.exists():
                        # Get most recent run
                        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
                        if run_dirs:
                            history_path = run_dirs[-1] / "history.json"
                            if history_path.exists():
                                try:
                                    with open(history_path, 'r') as f:
                                        history = json.load(f)
                                    if isinstance(history, list) and history:
                                        return history[-1].get('best_ever_fitness', 
                                                             history[-1].get('max_fitness', None))
                                except Exception:
                                    pass
        return None
    
    def load_current_hof(self):
        """Load current Hall of Fame entries."""
        print("\n" + "="*70)
        print("CURRENT HALL OF FAME")
        print("="*70)
        
        # Load champions
        champions_dir = self.hof_dir / "champions"
        if champions_dir.exists():
            champion_files = sorted(champions_dir.glob("*.npy"))
            print(f"\n📊 Champions ({len(champion_files)}):")
            for champ_file in champion_files:
                name = champ_file.stem
                # Try to find original checkpoint to get fitness
                fitness = self._try_get_fitness_for_champion(name)
                if fitness:
                    print(f"  • {name:60s} (Fitness: {fitness:7.1f})")
                    self.current_champion_fitness[name] = fitness
                else:
                    print(f"  • {name}")
                self.current_champions.append(name)
        else:
            print("\n⚠️  No champions directory found")
        
        print(f"\n💾 Note: Tournament performance for existing champions will be loaded during tournament scan")
        
        # Load milestones
        milestones_dir = self.hof_dir / "milestones"
        if milestones_dir.exists():
            milestone_files = sorted(milestones_dir.glob("*.npy"))
            print(f"\n📊 Milestones ({len(milestone_files)}):")
            for mile_file in milestone_files:
                name = mile_file.stem
                print(f"  • {name}")
                self.current_milestones.append(name)
        else:
            print("\n⚠️  No milestones directory found")
    
    def scan_checkpoints(self, checkpoint_dir: Optional[Path] = None, 
                        days_back: Optional[int] = None,
                        min_fitness: float = 50.0):
        """Scan checkpoint directories for new high-performing genomes."""
        print("\n" + "="*70)
        print("SCANNING CHECKPOINTS")
        print("="*70)
        
        if checkpoint_dir:
            checkpoint_dirs = [checkpoint_dir]
        else:
            checkpoint_dirs = [d for d in self.checkpoints_dir.iterdir() if d.is_dir()]
        
        cutoff_date = None
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            print(f"\n⏰ Only considering checkpoints from last {days_back} days")
        
        candidates_found = 0
        
        for checkpoint_dir in checkpoint_dirs:
            if checkpoint_dir.name == "archived_configs":
                continue  # Skip archived
            
            runs_dir = checkpoint_dir / "runs"
            if not runs_dir.exists():
                # Check for evolution_run (old structure)
                runs_dir = checkpoint_dir / "evolution_run"
                if not runs_dir.exists():
                    continue
            
            # Scan all runs in this checkpoint
            for run_dir in runs_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                
                # Check run date
                try:
                    # Extract date from run directory name (run_YYYYMMDD_HHMMSS)
                    date_str = run_dir.name.split('_', 1)[1] if '_' in run_dir.name else None
                    if date_str:
                        run_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                        if cutoff_date and run_date < cutoff_date:
                            continue
                    else:
                        # Use file modification time as fallback
                        run_date = datetime.fromtimestamp(run_dir.stat().st_mtime)
                        if cutoff_date and run_date < cutoff_date:
                            continue
                except Exception:
                    run_date = datetime.now()
                
                # Check for best_genome.npy
                best_genome_path = run_dir / "best_genome.npy"
                if not best_genome_path.exists():
                    continue
                
                # Load history to get final fitness
                history_path = run_dir / "history.json"
                config_path = run_dir / "config.json"
                
                if not history_path.exists():
                    continue
                
                try:
                    with open(history_path, 'r') as f:
                        history = json.load(f)
                    
                    config = {}
                    if config_path.exists():
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                    
                    # Get final best fitness
                    # History can be either a list of generation dicts or a dict with best_progress
                    if isinstance(history, list):
                        if not history:
                            continue
                        final_gen = history[-1]
                        final_fitness = final_gen.get('best_ever_fitness', final_gen.get('max_fitness', 0))
                        generation = len(history)
                    else:
                        best_progress = history.get('best_progress', [])
                        if not best_progress:
                            continue
                        final_fitness = best_progress[-1]
                        generation = len(best_progress)
                    
                    # Check if fitness meets threshold
                    if final_fitness < min_fitness:
                        continue
                    
                    # Create candidate
                    name = checkpoint_dir.name.replace('deep_', '')
                    candidate = GenomeCandidate(
                        name=f"{name}_g{generation}",
                        path=best_genome_path,
                        fitness=final_fitness,
                        generation=generation,
                        date=run_date,
                        source='checkpoint',
                        config=config
                    )
                    
                    self.candidates.append(candidate)
                    candidates_found += 1
                    
                    if self.verbose:
                        print(f"\n  ✓ {candidate.name}")
                        print(f"    Fitness: {final_fitness:.2f} BB/100")
                        print(f"    Generation: {generation}")
                        print(f"    Date: {run_date.strftime('%Y-%m-%d %H:%M')}")
                        print(f"    Path: {best_genome_path}")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️  Error processing {run_dir.name}: {e}")
                    continue
        
        print(f"\n✅ Found {candidates_found} candidate genomes with fitness ≥ {min_fitness}")
    
    def enhance_candidates_with_tournament_data(self, tournament_data: Dict):
        """Match candidates with tournament performance data."""
        if not tournament_data:
            return
        
        matched = 0
        for candidate in self.candidates:
            # Extract base config from candidate name
            # e.g., p12_m6_h375_s0.1_hof3_g200_g200 -> p12_m6_h375_s0.1
            import re
            
            # Try to extract config pattern: p{pop}_m{match}_h{hands}_s{sigma}
            match = re.search(r'(p\d+_m\d+_h\d+_s[0-9.]+)', candidate.name)
            if match:
                base_config = match.group(1)
                
                # Try to match against tournament names with various generation suffixes
                best_match = None
                best_match_score = 0
                
                for tournament_name, stats in tournament_data.items():
                    # Check if tournament name starts with base config
                    if tournament_name.startswith(base_config):
                        # Calculate match score based on how close the names are
                        score = len(base_config)
                        
                        # Bonus for exact match with generation
                        if f"_g{candidate.generation}" in tournament_name:
                            score += 100
                        
                        # Bonus for matching without hof tag
                        if '_hof' not in tournament_name:
                            score += 10
                        
                        if score > best_match_score:
                            best_match = tournament_name
                            best_match_score = score
                            candidate.tournament_stats = stats.copy()
                
                if best_match:
                    matched += 1
                    if self.verbose:
                        win_rate = candidate.tournament_stats.get('win_rate', 0) * 100
                        tournaments = candidate.tournament_stats.get('tournaments', 0)
                        print(f"  ✓ Matched {candidate.name} with {best_match}: "
                              f"{win_rate:.1f}% win rate in {tournaments} tournaments")
        
        if matched > 0:
            print(f"\n✅ Enhanced {matched}/{len(self.candidates)} candidates with tournament performance data")
        else:
            print(f"\n⚠️  No candidates matched with tournament data (name patterns may differ)")
    
    def scan_tournaments(self, min_win_rate: float = 0.60):
        """Scan tournament reports for new champions and enhance candidates with tournament data."""
        print("\n" + "="*70)
        print("SCANNING TOURNAMENT RESULTS")
        print("="*70)
        
        if not self.tournament_reports_dir.exists():
            print("\n⚠️  No tournament reports directory found")
            return {}
        
        tournament_winners = defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'tournaments': 0, 
            'total_chips': 0, 'win_rate': 0.0, 'avg_chips': 0.0
        })
        
        tournaments_scanned = 0
        
        # Scan all tournament batch directories
        for batch_dir in self.tournament_reports_dir.iterdir():
            if not batch_dir.is_dir() or batch_dir.name == 'overall_reports':
                continue
            
            # Look for tournament subdirectories (tournament_YYYYMMDD_HHMMSS)
            for tournament_dir in batch_dir.iterdir():
                if not tournament_dir.is_dir():
                    continue
                
                report_file = tournament_dir / "report.json"
                if not report_file.exists():
                    continue
                
                try:
                    with open(report_file, 'r') as f:
                        report = json.load(f)
                    
                    tournaments_scanned += 1
                    agents = report.get('agents', [])
                    
                    # Handle both list and dict formats
                    if isinstance(agents, list):
                        for agent in agents:
                            agent_name = agent.get('name', '')
                            if not agent_name:
                                continue
                            tournament_winners[agent_name]['wins'] += agent.get('wins', 0)
                            tournament_winners[agent_name]['losses'] += agent.get('losses', 0)
                            tournament_winners[agent_name]['tournaments'] += 1
                            tournament_winners[agent_name]['total_chips'] += agent.get('chips', 0)
                    elif isinstance(agents, dict):
                        for agent_name, stats in agents.items():
                            tournament_winners[agent_name]['wins'] += stats.get('wins', 0)
                            tournament_winners[agent_name]['losses'] += stats.get('losses', 0)
                            tournament_winners[agent_name]['tournaments'] += 1
                            tournament_winners[agent_name]['total_chips'] += stats.get('chips', stats.get('chip_delta', 0))
                
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️  Error reading {report_file}: {e}")
                    continue
        
        self.tournaments_scanned = tournaments_scanned
        
        if tournaments_scanned > 0:
            print(f"\n📁 Scanned {tournaments_scanned} tournament reports")
        else:
            print(f"\n⚠️  No tournament reports found")
        
        # Calculate win rates and identify top performers
        top_performers = []
        for agent_name, stats in tournament_winners.items():
            total_games = stats['wins'] + stats['losses']
            if total_games > 0:
                stats['win_rate'] = stats['wins'] / total_games
                stats['avg_chips'] = stats['total_chips'] / stats['tournaments'] if stats['tournaments'] > 0 else 0
                if stats['win_rate'] >= min_win_rate and stats['tournaments'] >= 2:
                    top_performers.append((agent_name, stats))
        
        # Sort by win rate
        top_performers.sort(key=lambda x: x[1]['win_rate'], reverse=True)
        
        # Match existing champions with tournament data
        existing_champs_matched = 0
        for champ_name in self.current_champions:
            # Extract base config from champion name
            import re
            base_champ = champ_name.replace('_champion', '').replace('_v2', '')
            match = re.search(r'(p\d+_m\d+_h\d+_s[0-9.]+)', base_champ)
            if match:
                base_config = match.group(1)
                # Find matching tournament data
                for tournament_name, stats in tournament_winners.items():
                    if tournament_name.startswith(base_config):
                        self.current_champion_tournament[champ_name] = stats.copy()
                        existing_champs_matched += 1
                        break
        
        if existing_champs_matched > 0:
            print(f"📊 Matched {existing_champs_matched}/{len(self.current_champions)} existing champions with tournament data")
        
        print(f"\n📊 Top Tournament Performers (≥{min_win_rate*100:.0f}% win rate):")
        if top_performers:
            for agent_name, stats in top_performers[:10]:
                print(f"  • {agent_name:40s} {stats['win_rate']*100:5.1f}% "
                      f"({stats['wins']}W-{stats['losses']}L) "
                      f"Chips: {stats['avg_chips']:+.0f}/tournament "
                      f"[{stats['tournaments']} tournaments]")
        else:
            print(f"  None found with ≥{min_win_rate*100:.0f}% win rate in 2+ tournaments")
        
        # Return all tournament data for matching with candidates
        return dict(tournament_winners)
    
    def compare_with_current_hof(self):
        """Compare candidates with current Hall of Fame to find updates."""
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        if not self.candidates:
            print("\n✅ No new candidates found. Hall of Fame is up to date.")
            self._check_for_dethronement()
            return
        
        # Sort candidates by fitness
        self.candidates.sort(key=lambda c: c.fitness, reverse=True)
        
        # Categorize recommendations with TOURNAMENT PRIORITY
        new_champions = []  # High fitness OR strong tournament performance
        new_milestones = []  # Good fitness at milestone generations
        improvements = []  # Better than existing HoF entries
        
        for candidate in self.candidates:
            # Check if already in champions
            is_champion = any(candidate.name in champ for champ in self.current_champions)
            
            # Check milestone generations (50, 100, 200, etc.)
            is_milestone = candidate.generation in [50, 100, 200, 300, 400, 500]
            
            # Calculate priority score (TOURNAMENT RESULTS WEIGHTED HIGHER)
            has_tournament_data = candidate.tournament_stats and candidate.tournament_stats.get('tournaments', 0) >= 2
            
            if has_tournament_data:
                # Tournament performance is PRIMARY criterion
                win_rate = candidate.tournament_stats.get('win_rate', 0)
                tournaments = candidate.tournament_stats.get('tournaments', 0)
                
                # Strong tournament performer = champion, regardless of fitness
                if win_rate >= 0.70 and tournaments >= 2 and not is_champion:
                    new_champions.append(candidate)
                    candidate.source = 'tournament_champion'  # Mark source
                elif win_rate >= 0.60 and tournaments >= 3 and not is_champion:
                    new_champions.append(candidate)
                    candidate.source = 'tournament_strong'
                elif is_milestone:
                    is_in_milestones = any(candidate.name in mile for mile in self.current_milestones)
                    if not is_in_milestones:
                        new_milestones.append(candidate)
                elif win_rate >= 0.55:
                    improvements.append(candidate)
            else:
                # No tournament data - fall back to fitness (LOWER PRIORITY)
                if candidate.fitness >= 70.0 and not is_champion:
                    new_champions.append(candidate)
                elif is_milestone:
                    is_in_milestones = any(candidate.name in mile for mile in self.current_milestones)
                    if not is_in_milestones or candidate.fitness >= 60.0:
                        new_milestones.append(candidate)
                elif candidate.fitness >= 60.0:
                    improvements.append(candidate)
        
        # Sort champions by tournament performance FIRST, then fitness
        new_champions.sort(key=lambda c: (
            c.tournament_stats.get('win_rate', 0) if c.tournament_stats else 0,
            c.fitness
        ), reverse=True)
        
        # Report new champions with detailed reasoning
        if new_champions:
            print(f"\n🏆 NEW CHAMPIONS (Tournament Winners + Elite Performers):")
            print("=" * 70)
            for i, candidate in enumerate(new_champions[:5], 1):
                print(f"\n{i}. {candidate.name}")
                
                # TOURNAMENT STATS FIRST (if available)
                if candidate.tournament_stats and candidate.tournament_stats.get('tournaments', 0) >= 2:
                    stats = candidate.tournament_stats
                    print(f"   🎯 TOURNAMENT PERFORMANCE: {stats['win_rate']*100:5.1f}% win rate")
                    print(f"      {stats['wins']}W-{stats['losses']}L across {stats['tournaments']} tournaments")
                    print(f"      Avg chips: {stats['avg_chips']:+.1f} per tournament")
                
                # Then fitness
                print(f"   📊 Training Fitness: {candidate.fitness:7.2f} BB/100 (Generation {candidate.generation})")
                print(f"   📅 Trained: {candidate.date.strftime('%Y-%m-%d %H:%M')}")
                
                # Show hyperparameters
                if candidate.hyperparams:
                    params = candidate.hyperparams
                    print(f"   Config: ", end="")
                    if 'population' in params:
                        print(f"pop={params['population']}", end="")
                    if 'matchups' in params:
                        print(f" matchups={params['matchups']}", end="")
                    if 'hands' in params:
                        print(f" hands={params['hands']}", end="")
                    if 'sigma' in params:
                        print(f" sigma={params['sigma']}", end="")
                    if params.get('hof_training'):
                        print(f" [HoF-trained]", end="")
                    print()
                
                # Comparison with existing champions
                if self.current_champion_fitness:
                    avg_fitness = sum(self.current_champion_fitness.values()) / len(self.current_champion_fitness)
                    max_fitness = max(self.current_champion_fitness.values())
                    improvement = ((candidate.fitness - avg_fitness) / avg_fitness) * 100 if avg_fitness > 0 else 0
                    
                    print(f"   vs Existing Champions:")
                    print(f"      • {improvement:+.1f}% vs average ({avg_fitness:.1f})")
                    if candidate.fitness > max_fitness:
                        print(f"      • 🌟 NEW RECORD! Beats previous best ({max_fitness:.1f})")
                    else:
                        print(f"      • Ranks among top performers (current best: {max_fitness:.1f})")
                
                # Why this should be added - TOURNAMENT REASONS FIRST
                print(f"   💡 Why Add to Hall of Fame:")
                
                # Tournament performance (HIGHEST PRIORITY)
                if candidate.tournament_stats and candidate.tournament_stats.get('tournaments', 0) >= 2:
                    stats = candidate.tournament_stats
                    if stats['win_rate'] >= 0.70:
                        print(f"      ⭐ ELITE TOURNAMENT CHAMPION (≥70% win rate in real competition)")
                    elif stats['win_rate'] >= 0.60:
                        print(f"      ✓ Strong tournament performer (≥60% win rate)")
                    
                    if stats['tournaments'] >= 5:
                        print(f"      ✓ Proven consistency across {stats['tournaments']} tournaments")
                    
                    if stats['avg_chips'] > 20000:
                        print(f"      ✓ Dominant chip leader (+{stats['avg_chips']:.0f} chips/tournament)")
                    elif stats['avg_chips'] > 0:
                        print(f"      ✓ Profitable in tournament play (+{stats['avg_chips']:.0f} chips/tournament)")
                
                # Fitness (SECONDARY)
                if candidate.fitness >= 1000:
                    print(f"      ✓ Elite training fitness (>1000 BB/100)")
                elif candidate.fitness >= 100:
                    print(f"      ✓ Strong training fitness (>100 BB/100)")
                
                if candidate.generation >= 200:
                    print(f"      ✓ Well-trained (200+ generations)")
                
                if candidate.hyperparams.get('hof_training'):
                    print(f"      ✓ Trained against Hall of Fame opponents (better generalization)")
                
                # Small population analysis
                if candidate.hyperparams.get('population', 0) <= 12:
                    print(f"      ✓ Efficient: Small population achieved high performance")
                
                # Note if no tournament data
                if not candidate.tournament_stats or candidate.tournament_stats.get('tournaments', 0) < 2:
                    print(f"      ℹ️  Note: No tournament data (fitness-based recommendation)")
                
                print(f"\n   📁 Source: {candidate.path}")
                print(f"   💾 Command: cp {candidate.path} \\")
                print(f"      hall_of_fame/champions/{candidate.name}_champion.npy")
                print()
        
        # Report milestone candidates with reasoning
        if new_milestones:
            print(f"\n📍 MILESTONE CANDIDATES (Gen 50/100/200/...):")
            print("=" * 70)
            for candidate in new_milestones[:10]:
                print(f"\n  • {candidate.name:45s} {candidate.fitness:6.2f} BB/100")
                print(f"    Generation: {candidate.generation} (milestone checkpoint)")
                
                # Explain why milestones matter
                if candidate.generation == 50:
                    print(f"    Value: Early-stage performance baseline")
                elif candidate.generation == 100:
                    print(f"    Value: Mid-training performance reference")
                elif candidate.generation == 200:
                    print(f"    Value: Well-converged performance benchmark")
                else:
                    print(f"    Value: Extended training milestone")
                    
                if self.verbose:
                    print(f"    📁 {candidate.path}")
        
        # Report general improvements
        if improvements:
            print(f"\n⚡ STRONG PERFORMERS (Fitness ≥ 60.0):")
            for candidate in improvements[:10]:
                print(f"  • {candidate.name:45s} {candidate.fitness:6.2f} BB/100 @ gen {candidate.generation}")
        
        # Summary with insights
        print("\n" + "="*70)
        print("SUMMARY & INSIGHTS")
        print("="*70)
        
        # Tournament coverage
        print(f"\n📊 Tournament Data Coverage:")
        total_tournament_dirs = sum(1 for batch_dir in self.tournament_reports_dir.iterdir() 
                                    if batch_dir.is_dir() and batch_dir.name != 'overall_reports'
                                    for tournament_dir in batch_dir.iterdir() if tournament_dir.is_dir())
        print(f"   Total tournaments available: {total_tournament_dirs}")
        # tournaments_scanned is not accessible here, need to track it
        print(f"   Unique agents in tournament data: {len(set(self.current_champion_tournament.keys()) | set(c.name for c in self.candidates if c.tournament_stats))}")
        print(f"\n📊 Current Hall of Fame:")
        print(f"   Champions:  {len(self.current_champions)}")
        if self.current_champion_tournament:
            champs_with_data = len(self.current_champion_tournament)
            avg_champ_wr = sum(s['win_rate'] for s in self.current_champion_tournament.values()) / champs_with_data
            print(f"   With tournament data: {champs_with_data}")
            print(f"   Avg tournament win rate: {avg_champ_wr*100:.1f}%")
            max_fitness = max(self.current_champion_fitness.values())
            print(f"   Avg Fitness: {avg_fitness:.1f} BB/100")
            print(f"   Best Fitness: {max_fitness:.1f} BB/100")
        print(f"   Milestones: {len(self.current_milestones)}")
        
        print(f"\n🔍 Analysis Results:")
        print(f"   Total candidates found:  {len(self.candidates)}")
        
        # Separate tournament vs fitness-based
        tournament_champions = [c for c in new_champions if c.tournament_stats and c.tournament_stats.get('tournaments', 0) >= 2]
        fitness_champions = [c for c in new_champions if not c.tournament_stats or c.tournament_stats.get('tournaments', 0) < 2]
        
        print(f"   New champion candidates: {len(new_champions)}")
        if tournament_champions:
            print(f"      → Tournament-proven: {len(tournament_champions)} ⭐")
        if fitness_champions:
            print(f"      → Fitness-based: {len(fitness_champions)}")
        print(f"   New milestone candidates: {len(new_milestones)}")
        print(f"   Strong performers:       {len(improvements)}")
        
        # Hyperparameter trends in new candidates
        if new_champions:
            print(f"\n📈 Trends in New Champions:")
            pops = [c.hyperparams.get('population', 0) for c in new_champions if c.hyperparams.get('population')]
            if pops:
                print(f"   Population range: {min(pops)}-{max(pops)} (avg: {sum(pops)/len(pops):.0f})")
            
            sigmas = [c.hyperparams.get('sigma', 0) for c in new_champions if c.hyperparams.get('sigma')]
            if sigmas:
                print(f"   Sigma range: {min(sigmas):.2f}-{max(sigmas):.2f} (avg: {sum(sigmas)/len(sigmas):.2f})")
            
            hof_trained = sum(1 for c in new_champions if c.hyperparams.get('hof_training'))
            if hof_trained > 0:
                print(f"   HoF-trained: {hof_trained}/{len(new_champions)} ({hof_trained*100/len(new_champions):.0f}%)")
            
            fitness_range = (min(c.fitness for c in new_champions), max(c.fitness for c in new_champions))
            print(f"   Fitness range: {fitness_range[0]:.1f} - {fitness_range[1]:.1f} BB/100")
        
        if new_champions:
            print(f"\n✅ RECOMMENDATION: Hall of Fame needs updating!")
            print(f"   Add {len(new_champions)} new champion(s) to hall_of_fame/champions/")
            print(f"\n   💡 Why update?")
            
            # Tournament reasons FIRST
            tournament_champions = [c for c in new_champions if c.tournament_stats and c.tournament_stats.get('tournaments', 0) >= 2]
            if tournament_champions:
                best_wr = max(c.tournament_stats['win_rate'] for c in tournament_champions)
                print(f"      ⭐ {len(tournament_champions)} TOURNAMENT-PROVEN champions (best: {best_wr*100:.1f}% win rate)")
                print(f"         → Real competitive performance, not just training fitness")
            
            # Then fitness
            if any(c.fitness >= 1000 for c in new_champions):
                print(f"      • Elite training fitness (>1000 BB/100) achieved")
            if any(c.hyperparams.get('hof_training') for c in new_champions):
                print(f"      • HoF-trained agents show better generalization")
            if self.current_champion_fitness:
                best_candidate = max(new_champions, key=lambda c: c.fitness)
                if best_candidate.fitness > max(self.current_champion_fitness.values()):
                    print(f"      • New all-time training record achieved")
            
            # Mention dethronement if applicable
            if self.current_champion_tournament:
                underperforming_champs = sum(1 for stats in self.current_champion_tournament.values() 
                                            if stats.get('win_rate', 1.0) < 0.50 and stats.get('tournaments', 0) >= 3)
                if underperforming_champs > 0:
                    print(f"      • {underperforming_champs} existing champion(s) underperforming - consider archiving")
            
            # Mention dethronement if applicable
            underperforming_champs = sum(1 for stats in self.current_champion_tournament.values() 
                                        if stats.get('win_rate', 1.0) < 0.50 and stats.get('tournaments', 0) >= 3)
            if underperforming_champs > 0:
                print(f"      • {underperforming_champs} existing champion(s) underperforming - consider archiving")
            
            print(f"\n   Quick commands (top 3):")
            for candidate in new_champions[:3]:
                print(f"   cp {candidate.path} hall_of_fame/champions/{candidate.name}_champion.npy")
        else:
            print(f"\n✅ Hall of Fame is current. No urgent updates needed.")
            if self.candidates:
                print(f"   Note: {len(self.candidates)} candidates found but below champion threshold")
        
        # Check for dethronement
        self._check_for_dethronement()
    
    def _check_for_dethronement(self):
        """Check if existing champions should be archived due to poor performance."""
        if not self.current_champion_tournament:
            print("\n💡 Note: No tournament data for existing champions - cannot assess dethronement")
            return
        
        print("\n" + "="*70)
        print("EXISTING CHAMPIONS PERFORMANCE REVIEW")
        print("="*70)
        
        # Analyze existing champions
        underperformers = []
        champions_to_review = []
        
        for champ_name in self.current_champions:
            if champ_name in self.current_champion_tournament:
                stats = self.current_champion_tournament[champ_name]
                win_rate = stats.get('win_rate', 0)
                tournaments = stats.get('tournaments', 0)
                
                # Flag underperformers
                if win_rate < 0.50 and tournaments >= 3:
                    underperformers.append((champ_name, stats, 'poor'))
                elif win_rate < 0.55 and tournaments >= 5:
                    champions_to_review.append((champ_name, stats, 'below_average'))
        
        # Compare with new candidates
        if self.candidates and self.current_champion_tournament:
            # Get tournament stats for candidates
            candidate_tournament_stats = [
                (c, c.tournament_stats) for c in self.candidates 
                if c.tournament_stats and c.tournament_stats.get('tournaments', 0) >= 2
            ]
            
            if candidate_tournament_stats:
                # Find best candidate win rate
                best_candidate_wr = max(s['win_rate'] for _, s in candidate_tournament_stats)
                
                # Check if any existing champions are significantly outperformed
                for champ_name, stats in self.current_champion_tournament.items():
                    win_rate = stats.get('win_rate', 0)
                    if win_rate < best_candidate_wr - 0.15:  # 15% gap
                        if (champ_name, stats, 'poor') not in underperformers:
                            underperformers.append((champ_name, stats, 'outperformed'))
        
        # Report findings
        if underperformers:
            print("\n⚠️  CHAMPIONS TO CONSIDER ARCHIVING:")
            print("   (These champions show poor tournament performance)\n")
            
            for champ_name, stats, reason in underperformers:
                print(f"  • {champ_name:50s}")
                print(f"    Tournament: {stats['win_rate']*100:5.1f}% win rate "
                      f"({stats['wins']}W-{stats['losses']}L) in {stats['tournaments']} tournaments")
                
                if reason == 'poor':
                    print(f"    ⚠️  Below 50% win rate - consistently losing")
                elif reason == 'below_average':
                    print(f"    ⚠️  Below 55% win rate across multiple tournaments")
                elif reason == 'outperformed':
                    print(f"    ⚠️  Significantly outperformed by new candidates (15%+ gap)")
                
                if champ_name in self.current_champion_fitness:
                    print(f"    Fitness: {self.current_champion_fitness[champ_name]:.1f} BB/100")
                print(f"    💡 Recommend: mv hall_of_fame/champions/{champ_name}.npy hall_of_fame/archived/")
                print()
        
        if champions_to_review:
            print("\n📋 CHAMPIONS TO MONITOR:")
            print("   (Below average but not critically poor)\n")
            
            for champ_name, stats, _ in champions_to_review:
                print(f"  • {champ_name:50s} {stats['win_rate']*100:5.1f}% win rate "
                      f"({stats['wins']}W-{stats['losses']}L) in {stats['tournaments']} tournaments")
        
        if not underperformers and not champions_to_review:
            print("\n✅ All existing champions performing well in tournaments!")
            
            # Show top performers
            if self.current_champion_tournament:
                champ_perf = [(name, stats) for name, stats in self.current_champion_tournament.items()]
                champ_perf.sort(key=lambda x: x[1]['win_rate'], reverse=True)
                
                print("\n🏆 Top Performing Champions:")
                for name, stats in champ_perf[:5]:
                    print(f"  • {name:50s} {stats['win_rate']*100:5.1f}% win rate "
                          f"in {stats['tournaments']} tournaments")
    
    def generate_update_script(self, output_path: Optional[Path] = None):
        """Generate a shell script to update the Hall of Fame."""
        if not self.candidates:
            return
        
        # Find top candidates
        champions = [c for c in self.candidates if c.fitness >= 70.0][:5]
        milestones = [c for c in self.candidates 
                     if c.generation in [50, 100, 200, 300, 400, 500]][:10]
        
        if not champions and not milestones:
            return
        
        script_path = output_path or (self.workspace_root / "update_hof.sh")
        
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# Auto-generated Hall of Fame update script\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if champions:
                f.write("# NEW CHAMPIONS\n")
                for candidate in champions:
                    dest = f"hall_of_fame/champions/{candidate.name}_champion.npy"
                    f.write(f'echo "Adding champion: {candidate.name} (Fitness: {candidate.fitness:.2f})"\n')
                    f.write(f"cp \"{candidate.path}\" \"{dest}\"\n\n")
            
            if milestones:
                f.write("# MILESTONE GENOMES\n")
                for candidate in milestones:
                    dest = f"hall_of_fame/milestones/{candidate.name}_milestone.npy"
                    f.write(f'echo "Adding milestone: {candidate.name} (Fitness: {candidate.fitness:.2f})"\n')
                    f.write(f"cp \"{candidate.path}\" \"{dest}\"\n\n")
            
            f.write('echo "Hall of Fame updated!"\n')
        
        # Make executable
        script_path.chmod(0o755)
        
        print(f"\n💾 Update script generated: {script_path}")
        print(f"   Run with: ./{script_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Check if Hall of Fame needs updating",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check for any updates
  python scripts/utilities/check_hof_updates.py
  
  # Check only recent checkpoints (last 7 days)
  python scripts/utilities/check_hof_updates.py --days 7
  
  # Set custom fitness threshold
  python scripts/utilities/check_hof_updates.py --min-fitness 65
  
  # Generate update script automatically
  python scripts/utilities/check_hof_updates.py --generate-script
  
  # Verbose output
  python scripts/utilities/check_hof_updates.py --verbose
        """
    )
    
    parser.add_argument('--days', type=int, default=None,
                       help='Only consider checkpoints from last N days')
    parser.add_argument('--min-fitness', type=float, default=50.0,
                       help='Minimum fitness threshold for candidates (default: 50.0)')
    parser.add_argument('--min-win-rate', type=float, default=0.60,
                       help='Minimum win rate for tournament champions (default: 0.60)')
    parser.add_argument('--checkpoint-dir', type=str, default=None,
                       help='Specific checkpoint directory to scan')
    parser.add_argument('--generate-script', action='store_true',
                       help='Generate shell script to update Hall of Fame')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output with detailed information')
    
    args = parser.parse_args()
    
    # Get workspace root
    workspace_root = Path(__file__).parent.parent.parent
    
    # Create checker
    checker = HallOfFameChecker(workspace_root, verbose=args.verbose)
    
    # Run analysis
    print("\n" + "="*70)
    print("HALL OF FAME UPDATE CHECKER")
    print("="*70)
    print(f"\nWorkspace: {workspace_root}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load current HoF
    checker.load_current_hof()
    
    # Scan checkpoints
    checkpoint_dir = Path(args.checkpoint_dir) if args.checkpoint_dir else None
    checker.scan_checkpoints(
        checkpoint_dir=checkpoint_dir,
        days_back=args.days,
        min_fitness=args.min_fitness
    )
    
    # Scan tournaments and get data
    tournament_data = checker.scan_tournaments(min_win_rate=args.min_win_rate)
    
    # Enhance candidates with tournament data
    checker.enhance_candidates_with_tournament_data(tournament_data)
    
    # Compare and recommend
    checker.compare_with_current_hof()
    
    # Generate update script if requested
    if args.generate_script:
        checker.generate_update_script()
    
    print("\n" + "="*70)
    print()


if __name__ == '__main__':
    main()
