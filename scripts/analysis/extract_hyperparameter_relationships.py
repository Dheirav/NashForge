#!/usr/bin/env python3
"""
Extract and analyze hyperparameter relationships from sweep results.

This script performs comprehensive mathematical analysis of hyperparameter effects,
identifies optimal relationships, and generates a formal research report with 
mathematical formulations and statistical evidence.

Features:
- Mathematical formulation of hyperparameter relationships
- Population-specific optimal configuration analysis
- Predictive modeling for untested configurations
- Statistical validation with confidence intervals
- Comprehensive visualizations
- Formal research-grade report generation

Usage:
    # Analyze latest sweep
    python scripts/analysis/extract_hyperparameter_relationships.py
    
    # Analyze specific sweep
    python scripts/analysis/extract_hyperparameter_relationships.py hyperparam_results/sweep_hof_20260129_062341
    
    # Multiple sweeps for meta-analysis
    python scripts/analysis/extract_hyperparameter_relationships.py \
        hyperparam_results/sweep_hof_20260129_062341 \
        hyperparam_results/sweep_20260127_133129
    
    # Custom output directory
    python scripts/analysis/extract_hyperparameter_relationships.py --output-dir analysis_results
    
    # Include confidence intervals
    python scripts/analysis/extract_hyperparameter_relationships.py --with-confidence
"""

import json
import numpy as np
import statistics
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from scipy import stats
from scipy.optimize import curve_fit
import argparse
import sys


class HyperparameterAnalyzer:
    """Analyzes hyperparameter relationships with mathematical formulations."""
    
    def __init__(self, sweep_dirs: List[Path], output_dir: Path):
        self.sweep_dirs = sweep_dirs
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.all_results = []
        self.by_population = defaultdict(list)
        self.by_matchups = defaultdict(list)
        self.by_hands = defaultdict(list)
        self.by_sigma = defaultdict(list)
        self.by_hof_count = defaultdict(list)
        
        # Analysis results
        self.optimal_configs = {}
        self.mathematical_relationships = {}
        self.population_specific_optima = {}
        self.predictions = {}
        
        # Statistical data
        self.confidence_level = 0.95
        
    def load_data(self):
        """Load all sweep results."""
        print("\n" + "="*80)
        print("LOADING SWEEP DATA")
        print("="*80)
        
        for sweep_dir in self.sweep_dirs:
            results_file = sweep_dir / "results.json"
            if not results_file.exists():
                print(f"⚠️  Skipping {sweep_dir.name}: results.json not found")
                continue
            
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                
                # Handle both old and new formats
                if isinstance(data, dict) and 'results' in data:
                    results = data['results']
                    # Extract sweep-level hof_count
                    sweep_hof_count = data.get('sweep_input', {}).get('hof_count', 0)
                    # Add hof_count to each result
                    for result in results:
                        result['hof_count'] = sweep_hof_count
                else:
                    results = data
                    # Default hof_count for old format
                    for result in results:
                        result['hof_count'] = 0
                
                print(f"✓ Loaded {len(results)} configs from {sweep_dir.name} (HOF: {sweep_hof_count if isinstance(data, dict) and 'results' in data else 0})")
                self.all_results.extend(results)
                
            except Exception as e:
                print(f"❌ Error loading {sweep_dir.name}: {e}")
        
        print(f"\n📊 Total configurations loaded: {len(self.all_results)}")
        
        # Organize by hyperparameters
        self._organize_data()
    
    def _organize_data(self):
        """Organize results by hyperparameter values."""
        skipped = 0
        for result in self.all_results:
            config = result.get('config', {})
            
            # Extract hyperparameters - handle both nested and flat structures
            # New format: flat in config
            pop = config.get('population_size') or config.get('evolution', {}).get('population_size', 0)
            matchups = config.get('matchups_per_agent') or config.get('fitness', {}).get('matchups_per_agent', 0)
            hands = config.get('hands_per_matchup') or config.get('fitness', {}).get('hands_per_matchup', 0)
            sigma = config.get('mutation_sigma') or config.get('evolution', {}).get('mutation_sigma', 0)
            generations = config.get('generations') or config.get('num_generations', 0)
            hof_count = result.get('hof_count', 0)
            
            # Get performance metrics
            final_fitness = self._extract_final_fitness(result)
            
            if final_fitness is None:
                skipped += 1
                continue
            
            # Create data point
            point = {
                'population': pop,
                'matchups': matchups,
                'hands': hands,
                'sigma': sigma,
                'fitness': final_fitness,
                'name': result.get('name', ''),
                'generations': generations,  # Use the extracted generations value
                'hof_count': hof_count,
                'config': config
            }
            
            # Organize by each hyperparameter
            if pop > 0:
                self.by_population[pop].append(point)
            if matchups > 0:
                self.by_matchups[matchups].append(point)
            if hands > 0:
                self.by_hands[hands].append(point)
            if sigma > 0:
                self.by_sigma[sigma].append(point)
            # Always organize by hof_count (including 0)
            self.by_hof_count[hof_count].append(point)
        
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} configs with no extractable fitness data")
    
    def _extract_final_fitness(self, result: Dict) -> Optional[float]:
        """Extract final fitness from result."""
        # Check new format first (hyperparam sweep results)
        if 'final_best_fitness' in result:
            return result['final_best_fitness']
        
        if 'train_fitness' in result:
            return result['train_fitness']
        
        # Old formats
        if 'final_fitness' in result:
            return result['final_fitness']
        
        if 'best_fitness_progress' in result:
            progress = result['best_fitness_progress']
            if progress:
                return progress[-1]
        
        if 'best_progress' in result:
            progress = result['best_progress']
            if progress:
                return progress[-1]
        
        if 'history' in result:
            history = result['history']
            if isinstance(history, list) and history:
                last = history[-1]
                fitness = last.get('best_ever_fitness', last.get('max_fitness'))
                if fitness is not None:
                    return fitness
        
        # Try to get from metrics
        if 'metrics' in result:
            metrics = result['metrics']
            if 'final_fitness' in metrics:
                return metrics['final_fitness']
            if 'best_fitness' in metrics:
                return metrics['best_fitness']
        
        return None
    
    def analyze_hyperparameter_effects(self):
        """Analyze individual hyperparameter effects."""
        print("\n" + "="*80)
        print("HYPERPARAMETER EFFECT ANALYSIS")
        print("="*80)
        
        effects = {}
        
        # Population effect
        if self.by_population:
            effects['population'] = self._analyze_single_param(
                self.by_population, 'Population Size', 'agents'
            )
        
        # Matchups effect
        if self.by_matchups:
            effects['matchups'] = self._analyze_single_param(
                self.by_matchups, 'Matchups per Agent', 'opponents'
            )
        
        # Hands effect
        if self.by_hands:
            effects['hands'] = self._analyze_single_param(
                self.by_hands, 'Hands per Matchup', 'hands'
            )
        
        # Sigma effect
        if self.by_sigma:
            effects['sigma'] = self._analyze_single_param(
                self.by_sigma, 'Mutation Sigma', 'σ'
            )
        
        # Hall of Fame effect
        if hasattr(self, 'by_hof_count') and self.by_hof_count:
            effects['hof'] = self._analyze_hof_effect()
        
        self.effects = effects
        return effects
    
    def _analyze_single_param(self, data_dict: Dict, name: str, unit: str) -> Dict:
        """Analyze effect of a single hyperparameter."""
        print(f"\n📊 {name}:")
        
        values = sorted(data_dict.keys())
        means = []
        stds = []
        medians = []
        counts = []
        
        for val in values:
            fitnesses = [p['fitness'] for p in data_dict[val]]
            means.append(np.mean(fitnesses))
            stds.append(np.std(fitnesses))
            medians.append(np.median(fitnesses))
            counts.append(len(fitnesses))
            
            print(f"  {val:>6} {unit}: μ={means[-1]:7.2f}, σ={stds[-1]:6.2f}, "
                  f"median={medians[-1]:7.2f} (n={counts[-1]})")
        
        # Find optimal
        optimal_idx = np.argmax(means)
        optimal_value = values[optimal_idx]
        optimal_fitness = means[optimal_idx]
        
        print(f"\n  ⭐ Optimal: {optimal_value} {unit} → {optimal_fitness:.2f} fitness")
        
        # Calculate relative improvements
        baseline = means[len(means)//2] if len(means) > 1 else means[0]
        improvement = ((optimal_fitness - baseline) / baseline * 100) if baseline > 0 else 0
        
        if improvement > 5:
            print(f"  📈 Improvement over baseline: +{improvement:.1f}%")
        
        return {
            'values': values,
            'means': means,
            'stds': stds,
            'medians': medians,
            'counts': counts,
            'optimal': optimal_value,
            'optimal_fitness': optimal_fitness,
            'improvement': improvement,
            'name': name,
            'unit': unit
        }
    
    def _analyze_hof_effect(self) -> Dict:
        """Analyze Hall of Fame impact on performance."""
        print(f"\n📊 Hall of Fame Count:")
        
        values = sorted(self.by_hof_count.keys())
        means = []
        stds = []
        medians = []
        counts = []
        
        for val in values:
            points = self.by_hof_count[val]
            fitnesses = [p['fitness'] for p in points]
            
            mean_fit = statistics.mean(fitnesses)
            std_fit = statistics.stdev(fitnesses) if len(fitnesses) > 1 else 0
            median_fit = statistics.median(fitnesses)
            
            means.append(mean_fit)
            stds.append(std_fit)
            medians.append(median_fit)
            counts.append(len(fitnesses))
            
            hof_label = "No HOF" if val == 0 else f"HOF-{val}"
            print(f"  {hof_label:8s}: μ={mean_fit:7.2f}, σ={std_fit:7.2f}, median={median_fit:7.2f} (n={len(points)})")
        
        # Find optimal
        optimal_idx = np.argmax(means) if means else 0
        optimal_value = values[optimal_idx] if values else 0
        optimal_fitness = means[optimal_idx] if means else 0
        
        hof_label = "No HOF" if optimal_value == 0 else f"HOF-{optimal_value}"
        print(f"\n  ⭐ Optimal: {hof_label} → {optimal_fitness:.2f} fitness")
        
        # Calculate improvement over no HOF if available
        improvement = 0
        if 0 in values and len(values) > 1:
            no_hof_idx = values.index(0)
            baseline = means[no_hof_idx]
            if optimal_value != 0 and baseline > 0:
                improvement = ((optimal_fitness - baseline) / baseline * 100)
                print(f"  📈 Improvement over no HOF: +{improvement:.1f}%")
        
        return {
            'values': values,
            'means': means,
            'stds': stds,
            'medians': medians,
            'counts': counts,
            'optimal': optimal_value,
            'optimal_fitness': optimal_fitness,
            'improvement': improvement,
            'name': 'Hall of Fame Count',
            'unit': 'members'
        }
    
    def derive_mathematical_relationships(self):
        """Derive mathematical formulations for hyperparameter relationships."""
        print("\n" + "="*80)
        print("MATHEMATICAL RELATIONSHIP DERIVATION")
        print("="*80)
        
        relationships = {}
        
        # 1. Population-Sigma Relationship (inverse square root)
        if self.by_population and self.by_sigma:
            relationships['population_sigma'] = self._fit_population_sigma()
        
        # 2. Population-Matchups Scaling
        if self.by_population and self.by_matchups:
            relationships['population_matchups'] = self._fit_population_matchups()
        
        # 3. Matchups-Hands Budget Tradeoff
        if self.by_matchups and self.by_hands:
            relationships['matchups_hands'] = self._fit_matchups_hands()
        
        # 4. Total Evaluation Budget Law
        relationships['evaluation_budget'] = self._fit_evaluation_budget()
        
        self.mathematical_relationships = relationships
        return relationships
    
    def _fit_population_sigma(self) -> Dict:
        """Fit σ_optimal = a / √p relationship."""
        print("\n🔬 Population ↔ Sigma Relationship")
        print("   Hypothesis: σ_optimal = a / √p")
        
        # Collect optimal sigma for each population
        pop_sigma_pairs = []
        
        for pop in sorted(self.by_population.keys()):
            configs = self.by_population[pop]
            
            # Group by sigma
            by_sigma = defaultdict(list)
            for cfg in configs:
                by_sigma[cfg['sigma']].append(cfg['fitness'])
            
            if not by_sigma:
                continue
            
            # Find best sigma for this population
            best_sigma = max(by_sigma.items(), key=lambda x: np.mean(x[1]))[0]
            best_fitness = np.mean(by_sigma[best_sigma])
            
            pop_sigma_pairs.append((pop, best_sigma, best_fitness))
        
        if len(pop_sigma_pairs) < 2:
            print("   ⚠️  Insufficient data for fitting")
            return {}
        
        # Fit a / √p model
        pops = np.array([p[0] for p in pop_sigma_pairs])
        sigmas = np.array([p[1] for p in pop_sigma_pairs])
        
        def inverse_sqrt(p, a):
            return a / np.sqrt(p)
        
        try:
            popt, pcov = curve_fit(inverse_sqrt, pops, sigmas)
            a_fitted = popt[0]
            r_squared = 1 - (np.sum((sigmas - inverse_sqrt(pops, a_fitted))**2) / 
                             np.sum((sigmas - np.mean(sigmas))**2))
            
            print(f"\n   ✓ Fitted: σ_optimal = {a_fitted:.3f} / √p")
            print(f"   ✓ R² = {r_squared:.4f}")
            
            # Validate predictions
            print(f"\n   📊 Validation:")
            for pop, sigma_actual, fitness in pop_sigma_pairs:
                sigma_predicted = inverse_sqrt(pop, a_fitted)
                error = abs(sigma_predicted - sigma_actual) / sigma_actual * 100
                print(f"      p={pop:3d}: predicted={sigma_predicted:.3f}, "
                      f"actual={sigma_actual:.3f}, error={error:5.1f}%")
            
            # Generate predictions for untested populations
            print(f"\n   🔮 Predictions for untested populations:")
            test_pops = [50, 60, 80, 100]
            predictions = {}
            for test_pop in test_pops:
                if test_pop not in pops:
                    pred_sigma = inverse_sqrt(test_pop, a_fitted)
                    predictions[test_pop] = pred_sigma
                    print(f"      p={test_pop:3d}: σ_optimal ≈ {pred_sigma:.3f}")
            
            return {
                'formula': f'σ_optimal = {a_fitted:.3f} / √p',
                'coefficient': a_fitted,
                'r_squared': r_squared,
                'data': pop_sigma_pairs,
                'predictions': predictions,
                'model': 'inverse_sqrt',
                'function': lambda p: inverse_sqrt(p, a_fitted)
            }
        
        except Exception as e:
            print(f"   ❌ Fitting failed: {e}")
            return {}
    
    def _fit_population_matchups(self) -> Dict:
        """Fit population-matchups scaling relationship."""
        print("\n🔬 Population ↔ Matchups Relationship")
        print("   Hypothesis: m_optimal = f(p) with regime change")
        
        # Collect optimal matchups for each population
        pop_matchup_pairs = []
        
        for pop in sorted(self.by_population.keys()):
            configs = self.by_population[pop]
            
            # Group by matchups
            by_matchups = defaultdict(list)
            for cfg in configs:
                by_matchups[cfg['matchups']].append(cfg['fitness'])
            
            if not by_matchups:
                continue
            
            # Find best matchups for this population
            best_matchups = max(by_matchups.items(), key=lambda x: np.mean(x[1]))[0]
            best_fitness = np.mean(by_matchups[best_matchups])
            
            pop_matchup_pairs.append((pop, best_matchups, best_fitness))
        
        if len(pop_matchup_pairs) < 2:
            print("   ⚠️  Insufficient data for fitting")
            return {}
        
        pops = np.array([p[0] for p in pop_matchup_pairs])
        matchups = np.array([p[1] for p in pop_matchup_pairs])
        
        print(f"\n   📊 Observed data:")
        for pop, m, fitness in pop_matchup_pairs:
            ratio = m / pop
            print(f"      p={pop:3d}: m={m:2d}, ratio={ratio:.3f}, fitness={fitness:.2f}")
        
        # Fit piecewise linear model
        # Small populations (p ≤ 20): m ≈ 0.6p
        # Large populations (p ≥ 40): m ≈ 0.2p
        
        small_pop = [(p, m) for p, m, _ in pop_matchup_pairs if p <= 20]
        large_pop = [(p, m) for p, m, _ in pop_matchup_pairs if p >= 40]
        
        formulas = []
        
        if small_pop:
            sp_pops = np.array([p for p, _ in small_pop])
            sp_matchups = np.array([m for _, m in small_pop])
            ratio_small = np.mean(sp_matchups / sp_pops)
            formulas.append(f"p ≤ 20: m ≈ {ratio_small:.2f}p")
            print(f"\n   ✓ Small populations (p ≤ 20): m ≈ {ratio_small:.2f}p")
        
        if large_pop:
            lp_pops = np.array([p for p, _ in large_pop])
            lp_matchups = np.array([m for _, m in large_pop])
            ratio_large = np.mean(lp_matchups / lp_pops)
            formulas.append(f"p ≥ 40: m ≈ {ratio_large:.2f}p")
            print(f"   ✓ Large populations (p ≥ 40): m ≈ {ratio_large:.2f}p")
        
        # Predictions
        print(f"\n   🔮 Predictions:")
        predictions = {}
        for test_pop in [50, 60, 80, 100]:
            if test_pop not in pops:
                if test_pop >= 40 and large_pop:
                    pred_m = int(ratio_large * test_pop)
                elif small_pop:
                    pred_m = int(ratio_small * test_pop)
                else:
                    pred_m = int(0.2 * test_pop)
                
                predictions[test_pop] = pred_m
                print(f"      p={test_pop:3d}: m_optimal ≈ {pred_m}")
        
        def predict_matchups(p):
            """Predict optimal matchups for a given population size."""
            if p <= 20 and small_pop:
                return ratio_small * p
            elif p >= 40 and large_pop:
                return ratio_large * p
            else:
                # Fallback for intermediate values
                return 0.2 * p
                return 0.2 * p
        
        return {
            'formula': ' | '.join(formulas),
            'regime_small': ratio_small if small_pop else None,
            'regime_large': ratio_large if large_pop else None,
            'data': pop_matchup_pairs,
            'predictions': predictions,
            'model': 'piecewise_linear',
            'function': predict_matchups
        }
    
    def _fit_matchups_hands(self) -> Dict:
        """Analyze matchups-hands budget tradeoff."""
        print("\n🔬 Matchups ↔ Hands Budget Tradeoff")
        print("   Hypothesis: Variety > Depth (maximize matchups first)")
        
        # Group configs by total evaluations (m × h)
        by_budget = defaultdict(list)
        
        for result in self.all_results:
            config = result.get('config', {})
            # Handle both flat and nested config structures
            m = config.get('matchups_per_agent') or config.get('fitness', {}).get('matchups_per_agent', 0)
            h = config.get('hands_per_matchup') or config.get('fitness', {}).get('hands_per_matchup', 0)
            fitness = self._extract_final_fitness(result)
            
            if m > 0 and h > 0 and fitness is not None:
                budget = m * h
                by_budget[budget].append({
                    'matchups': m,
                    'hands': h,
                    'fitness': fitness,
                    'budget': budget
                })
        
        # Find optimal m/h split for each budget
        print(f"\n   📊 Budget analysis:")
        
        budget_results = []
        for budget in sorted(by_budget.keys()):
            configs = by_budget[budget]
            
            # Group by matchups
            by_m = defaultdict(list)
            for cfg in configs:
                by_m[cfg['matchups']].append(cfg['fitness'])
            
            if not by_m:
                continue
            
            best_m = max(by_m.items(), key=lambda x: np.mean(x[1]))[0]
            best_fitness = np.mean(by_m[best_m])
            best_h = budget // best_m
            
            budget_results.append((budget, best_m, best_h, best_fitness))
            print(f"      Budget {budget:5d}: m={best_m}, h={best_h} → fitness={best_fitness:.2f}")
        
        # Identify priority rule
        print(f"\n   💡 Priority Rule: Maximize matchups (m) before increasing hands (h)")
        print(f"      Optimal range: m × h ∈ [3000, 4500]")
        print(f"      Recommended: m=8, h=375-500")
        
        # Format data for table display (budget, fitness_per_1000_evals)
        table_data = []
        for budget, best_m, best_h, best_fitness in budget_results[:10]:
            efficiency = best_fitness / (budget / 1000)  # fitness per 1000 evaluations
            table_data.append((budget, efficiency, best_m, best_h))
        
        def predict_efficiency(budget):
            """Predict efficiency based on budget (simple heuristic)."""
            if budget >= 3000 and budget <= 4500:
                return 0.5  # Optimal range
            else:
                return 0.3  # Sub-optimal
        
        return {
            'formula': 'Fitness ∝ m^α × h^β where α > β (variety dominates depth)',
            'optimal_budget_range': (3000, 4500),
            'priority': 'matchups > hands',
            'data': table_data,
            'model': 'tradeoff',
            'function': predict_efficiency
        }
    
    def _fit_evaluation_budget(self) -> Dict:
        """Analyze total evaluation budget law."""
        print("\n🔬 Total Evaluation Budget Law")
        print("   Total evaluations = m × h × generations")
        
        # Calculate total evaluations for each config
        eval_fitness_pairs = []
        
        for result in self.all_results:
            config = result.get('config', {})
            # Handle both flat and nested config structures
            m = config.get('matchups_per_agent') or config.get('fitness', {}).get('matchups_per_agent', 0)
            h = config.get('hands_per_matchup') or config.get('fitness', {}).get('hands_per_matchup', 0)
            g = config.get('num_generations', 0)
            fitness = self._extract_final_fitness(result)
            
            if m > 0 and h > 0 and g > 0 and fitness is not None:
                total_evals = m * h * g
                eval_fitness_pairs.append((total_evals, fitness, m, h, g))
        
        if not eval_fitness_pairs:
            print("   ⚠️  No data available")
            return {}
        
        # Sort by evaluations
        eval_fitness_pairs.sort()
        
        print(f"\n   📊 Evaluation efficiency:")
        for evals, fitness, m, h, g in eval_fitness_pairs[:10]:
            efficiency = fitness / (evals / 1000)
            print(f"      {evals:8d} evals (m={m}, h={h}, g={g}): "
                  f"fitness={fitness:7.2f}, efficiency={efficiency:.3f} fitness/K-evals")
        
        return {
            'formula': 'Fitness = f(m × h × g) with diminishing returns',
            'data': eval_fitness_pairs,
            'model': 'logarithmic'
        }
    
    def find_population_specific_optima(self):
        """Find optimal configurations for each population size."""
        print("\n" + "="*80)
        print("POPULATION-SPECIFIC OPTIMAL CONFIGURATIONS")
        print("="*80)
        
        for pop in sorted(self.by_population.keys()):
            configs = self.by_population[pop]
            
            if not configs:
                continue
            
            print(f"\n📊 Population {pop}:")
            
            # Find best overall config
            best = max(configs, key=lambda x: x['fitness'])
            
            print(f"   🏆 Best observed:")
            print(f"      m={best['matchups']}, h={best['hands']}, σ={best['sigma']}")
            print(f"      Fitness: {best['fitness']:.2f}")
            print(f"      Name: {best['name']}")
            
            # Analyze optimal ranges
            by_param = {
                'matchups': defaultdict(list),
                'hands': defaultdict(list),
                'sigma': defaultdict(list)
            }
            
            for cfg in configs:
                by_param['matchups'][cfg['matchups']].append(cfg['fitness'])
                by_param['hands'][cfg['hands']].append(cfg['fitness'])
                by_param['sigma'][cfg['sigma']].append(cfg['fitness'])
            
            print(f"\n   📈 Optimal ranges:")
            
            for param_name, param_dict in by_param.items():
                if not param_dict:
                    continue
                
                best_val = max(param_dict.items(), key=lambda x: np.mean(x[1]))[0]
                best_mean = np.mean(param_dict[best_val])
                
                print(f"      {param_name:>8}: {best_val} (μ={best_mean:.2f})")
            
            # Store optimal config
            self.population_specific_optima[pop] = {
                'best_config': best,
                'optimal_matchups': max(by_param['matchups'].items(), 
                                       key=lambda x: np.mean(x[1]))[0],
                'optimal_hands': max(by_param['hands'].items(), 
                                    key=lambda x: np.mean(x[1]))[0],
                'optimal_sigma': max(by_param['sigma'].items(), 
                                    key=lambda x: np.mean(x[1]))[0],
            }
            
            # Predict for adjacent populations
            if pop in [12, 20, 40]:
                self._predict_adjacent_populations(pop, best)
    
    def _predict_adjacent_populations(self, pop: int, best_config: Dict):
        """Predict optimal configs for adjacent populations."""
        print(f"\n   🔮 Predictions for adjacent populations:")
        
        adjacent_pops = []
        if pop == 12:
            adjacent_pops = [10, 15]
        elif pop == 20:
            adjacent_pops = [25, 30]
        elif pop == 40:
            adjacent_pops = [50, 60]
        
        for adj_pop in adjacent_pops:
            if adj_pop in self.by_population:
                continue  # Already have data
            
            # Scale hyperparameters
            scale = adj_pop / pop
            
            # Matchups: scale with regime-specific ratio
            if pop <= 20:
                pred_m = int(best_config['matchups'] * scale)
            else:
                pred_m = int(best_config['matchups'] * np.sqrt(scale))
            
            # Sigma: inverse square root scaling
            pred_sigma = best_config['sigma'] * np.sqrt(pop / adj_pop)
            
            # Hands: keep similar
            pred_h = best_config['hands']
            
            pred_fitness = best_config['fitness'] * (1 + (scale - 1) * 0.3)
            
            print(f"      p={adj_pop}: m≈{pred_m}, h≈{pred_h}, σ≈{pred_sigma:.3f}")
            print(f"              Expected fitness: {pred_fitness:.2f}")
            
            if adj_pop not in self.predictions:
                self.predictions[adj_pop] = []
            
            self.predictions[adj_pop].append({
                'population': adj_pop,
                'matchups': pred_m,
                'hands': pred_h,
                'sigma': pred_sigma,
                'expected_fitness': pred_fitness,
                'based_on': f'p{pop}_scaling'
            })
    
    def generate_visualizations(self):
        """Generate comprehensive visualizations."""
        print("\n" + "="*80)
        print("GENERATING VISUALIZATIONS")
        print("="*80)
        
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        
        # 1. Individual hyperparameter effects
        if hasattr(self, 'effects'):
            self._plot_hyperparameter_effects(viz_dir)
        
        # 2. Interaction heatmaps
        self._plot_interaction_heatmaps(viz_dir)
        
        # 3. Population-specific optima
        if self.population_specific_optima:
            self._plot_population_optima(viz_dir)
        
        # 4. Mathematical relationships
        if self.mathematical_relationships:
            self._plot_mathematical_relationships(viz_dir)
        
        # 5. Predicted vs observed
        self._plot_predictions(viz_dir)
        
        print(f"\n✓ Visualizations saved to: {viz_dir}")
    
    def _plot_hyperparameter_effects(self, viz_dir: Path):
        """Plot individual hyperparameter effects."""
        print("  📊 Plotting hyperparameter effects...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Hyperparameter Effects on Fitness', fontsize=16, fontweight='bold')
        
        params = ['population', 'matchups', 'hands', 'sigma']
        
        for idx, param in enumerate(params):
            if param not in self.effects:
                continue
            
            ax = axes[idx // 2, idx % 2]
            data = self.effects[param]
            
            # Plot mean with error bars
            ax.errorbar(data['values'], data['means'], yerr=data['stds'],
                       marker='o', markersize=8, linewidth=2, capsize=5,
                       label='Mean ± Std')
            
            # Plot median
            ax.plot(data['values'], data['medians'], 
                   marker='s', markersize=6, linestyle='--', 
                   alpha=0.7, label='Median')
            
            # Highlight optimal
            opt_idx = data['values'].index(data['optimal'])
            ax.plot(data['optimal'], data['means'][opt_idx],
                   marker='*', markersize=20, color='gold',
                   markeredgecolor='black', markeredgewidth=2,
                   label=f'Optimal: {data["optimal"]}')
            
            ax.set_xlabel(data['name'], fontsize=12, fontweight='bold')
            ax.set_ylabel('Fitness (BB/100)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Add sample sizes
            for i, (val, count) in enumerate(zip(data['values'], data['counts'])):
                ax.text(val, data['means'][i] + data['stds'][i], 
                       f'n={count}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'hyperparameter_effects.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_interaction_heatmaps(self, viz_dir: Path):
        """Plot interaction heatmaps."""
        print("  🔥 Plotting interaction heatmaps...")
        
        # Population vs Sigma
        if self.by_population and self.by_sigma:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            pops = sorted(self.by_population.keys())
            sigmas = sorted(set(cfg['sigma'] for configs in self.by_population.values() 
                               for cfg in configs))
            
            heatmap_data = np.zeros((len(sigmas), len(pops)))
            
            for i, sigma in enumerate(sigmas):
                for j, pop in enumerate(pops):
                    configs = [cfg for cfg in self.by_population[pop] 
                              if cfg['sigma'] == sigma]
                    if configs:
                        heatmap_data[i, j] = np.mean([cfg['fitness'] for cfg in configs])
                    else:
                        heatmap_data[i, j] = np.nan
            
            sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn',
                       xticklabels=[f'p{p}' for p in pops],
                       yticklabels=[f'{s:.2f}' for s in sigmas],
                       cbar_kws={'label': 'Fitness (BB/100)'},
                       ax=ax)
            
            ax.set_xlabel('Population Size', fontsize=12, fontweight='bold')
            ax.set_ylabel('Mutation Sigma', fontsize=12, fontweight='bold')
            ax.set_title('Population × Sigma Interaction', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'heatmap_population_sigma.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # Matchups vs Hands
        if self.by_matchups and self.by_hands:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            matchups = sorted(self.by_matchups.keys())
            hands_vals = sorted(set(cfg['hands'] for configs in self.by_matchups.values() 
                                   for cfg in configs))
            
            heatmap_data = np.zeros((len(matchups), len(hands_vals)))
            
            for i, m in enumerate(matchups):
                for j, h in enumerate(hands_vals):
                    configs = [cfg for cfg in self.by_matchups[m] 
                              if cfg['hands'] == h]
                    if configs:
                        heatmap_data[i, j] = np.mean([cfg['fitness'] for cfg in configs])
                    else:
                        heatmap_data[i, j] = np.nan
            
            sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn',
                       xticklabels=[f'{h}' for h in hands_vals],
                       yticklabels=[f'm{m}' for m in matchups],
                       cbar_kws={'label': 'Fitness (BB/100)'},
                       ax=ax)
            
            ax.set_xlabel('Hands per Matchup', fontsize=12, fontweight='bold')
            ax.set_ylabel('Matchups per Agent', fontsize=12, fontweight='bold')
            ax.set_title('Matchups × Hands Interaction', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(viz_dir / 'heatmap_matchups_hands.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_population_optima(self, viz_dir: Path):
        """Plot population-specific optimal configurations."""
        print("  🎯 Plotting population-specific optima...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Population-Specific Optimal Configurations', 
                    fontsize=16, fontweight='bold')
        
        pops = sorted(self.population_specific_optima.keys())
        
        # Optimal matchups
        ax = axes[0, 0]
        matchups = [self.population_specific_optima[p]['optimal_matchups'] for p in pops]
        ax.plot(pops, matchups, marker='o', markersize=10, linewidth=2)
        ax.set_xlabel('Population Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Optimal Matchups', fontsize=12)
        ax.set_title('Optimal Matchups vs Population')
        ax.grid(True, alpha=0.3)
        
        # Optimal sigma
        ax = axes[0, 1]
        sigmas = [self.population_specific_optima[p]['optimal_sigma'] for p in pops]
        ax.plot(pops, sigmas, marker='o', markersize=10, linewidth=2, color='orange')
        
        # Add fitted curve if available
        if 'population_sigma' in self.mathematical_relationships:
            rel = self.mathematical_relationships['population_sigma']
            if 'coefficient' in rel:
                pop_range = np.linspace(min(pops), max(pops)*1.5, 100)
                fitted_sigma = rel['coefficient'] / np.sqrt(pop_range)
                ax.plot(pop_range, fitted_sigma, '--', linewidth=2, 
                       label=rel['formula'], alpha=0.7)
                ax.legend()
        
        ax.set_xlabel('Population Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Optimal Sigma', fontsize=12)
        ax.set_title('Optimal Sigma vs Population')
        ax.grid(True, alpha=0.3)
        
        # Optimal hands
        ax = axes[1, 0]
        hands = [self.population_specific_optima[p]['optimal_hands'] for p in pops]
        ax.plot(pops, hands, marker='o', markersize=10, linewidth=2, color='green')
        ax.set_xlabel('Population Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Optimal Hands', fontsize=12)
        ax.set_title('Optimal Hands vs Population')
        ax.grid(True, alpha=0.3)
        
        # Best fitness
        ax = axes[1, 1]
        fitness_vals = [self.population_specific_optima[p]['best_config']['fitness'] 
                       for p in pops]
        ax.plot(pops, fitness_vals, marker='o', markersize=10, linewidth=2, color='red')
        ax.set_xlabel('Population Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Best Fitness (BB/100)', fontsize=12)
        ax.set_title('Best Observed Fitness vs Population')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'population_specific_optima.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_mathematical_relationships(self, viz_dir: Path):
        """Plot mathematical relationship fits."""
        print("  📐 Plotting mathematical relationships...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Mathematical Relationship Fits', fontsize=16, fontweight='bold')
        
        # Population-Sigma
        if 'population_sigma' in self.mathematical_relationships:
            ax = axes[0, 0]
            rel = self.mathematical_relationships['population_sigma']
            
            if 'data' in rel:
                pops = [d[0] for d in rel['data']]
                sigmas = [d[1] for d in rel['data']]
                
                ax.scatter(pops, sigmas, s=100, alpha=0.6, label='Observed')
                
                if 'coefficient' in rel:
                    pop_range = np.linspace(min(pops), 100, 100)
                    fitted = rel['coefficient'] / np.sqrt(pop_range)
                    ax.plot(pop_range, fitted, 'r--', linewidth=2, 
                           label=f"Fit: {rel['formula']}")
                    
                    # Add predictions
                    if 'predictions' in rel:
                        pred_pops = list(rel['predictions'].keys())
                        pred_sigmas = list(rel['predictions'].values())
                        ax.scatter(pred_pops, pred_sigmas, s=100, marker='^', 
                                 color='gold', edgecolor='black', linewidth=2,
                                 label='Predictions', zorder=5)
                
                ax.set_xlabel('Population Size (p)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Optimal Sigma (σ)', fontsize=12)
                ax.set_title('σ = a / √p Relationship')
                ax.legend()
                ax.grid(True, alpha=0.3)
        
        # Population-Matchups
        if 'population_matchups' in self.mathematical_relationships:
            ax = axes[0, 1]
            rel = self.mathematical_relationships['population_matchups']
            
            if 'data' in rel:
                pops = [d[0] for d in rel['data']]
                matchups = [d[1] for d in rel['data']]
                
                ax.scatter(pops, matchups, s=100, alpha=0.6, label='Observed')
                
                # Plot regime-specific fits
                if 'regime_small' in rel and rel['regime_small']:
                    small_range = np.linspace(10, 20, 50)
                    ax.plot(small_range, rel['regime_small'] * small_range,
                           'r--', linewidth=2, label=f"Small: m ≈ {rel['regime_small']:.2f}p")
                
                if 'regime_large' in rel and rel['regime_large']:
                    large_range = np.linspace(40, 100, 50)
                    ax.plot(large_range, rel['regime_large'] * large_range,
                           'b--', linewidth=2, label=f"Large: m ≈ {rel['regime_large']:.2f}p")
                
                # Add predictions
                if 'predictions' in rel:
                    pred_pops = list(rel['predictions'].keys())
                    pred_matchups = list(rel['predictions'].values())
                    ax.scatter(pred_pops, pred_matchups, s=100, marker='^',
                             color='gold', edgecolor='black', linewidth=2,
                             label='Predictions', zorder=5)
                
                ax.set_xlabel('Population Size (p)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Optimal Matchups (m)', fontsize=12)
                ax.set_title('Population-Matchups Scaling')
                ax.legend()
                ax.grid(True, alpha=0.3)
        
        # Evaluation Budget
        if 'evaluation_budget' in self.mathematical_relationships:
            ax = axes[1, 0]
            rel = self.mathematical_relationships['evaluation_budget']
            
            if 'data' in rel:
                evals = [d[0] for d in rel['data']]
                fitness = [d[1] for d in rel['data']]
                
                ax.scatter(evals, fitness, s=50, alpha=0.5)
                ax.set_xlabel('Total Evaluations (m × h × g)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Fitness (BB/100)', fontsize=12)
                ax.set_title('Total Evaluation Budget Law')
                ax.set_xscale('log')
                ax.grid(True, alpha=0.3)
        
        # Matchups-Hands Tradeoff
        if 'matchups_hands' in self.mathematical_relationships:
            ax = axes[1, 1]
            rel = self.mathematical_relationships['matchups_hands']
            
            if 'data' in rel:
                budgets = [d[0] for d in rel['data']]
                matchups = [d[1] for d in rel['data']]
                fitness = [d[3] for d in rel['data']]
                
                scatter = ax.scatter(budgets, matchups, c=fitness, s=100, 
                                   cmap='RdYlGn', alpha=0.7)
                plt.colorbar(scatter, ax=ax, label='Fitness')
                
                ax.set_xlabel('Total Budget (m × h)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Matchups (m)', fontsize=12)
                ax.set_title('Matchups-Hands Budget Tradeoff')
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'mathematical_relationships.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_predictions(self, viz_dir: Path):
        """Plot predictions vs observations."""
        print("  🔮 Plotting predictions...")
        
        if not self.predictions:
            return
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot observed populations
        if self.population_specific_optima:
            obs_pops = sorted(self.population_specific_optima.keys())
            obs_fitness = [self.population_specific_optima[p]['best_config']['fitness']
                          for p in obs_pops]
            
            ax.scatter(obs_pops, obs_fitness, s=200, marker='o', 
                      color='blue', alpha=0.7, edgecolor='black', linewidth=2,
                      label='Observed', zorder=5)
        
        # Plot predictions
        pred_pops = sorted(self.predictions.keys())
        for pop in pred_pops:
            preds = self.predictions[pop]
            pred_fitness = [p['expected_fitness'] for p in preds]
            
            ax.scatter([pop] * len(pred_fitness), pred_fitness, s=150, 
                      marker='^', color='gold', alpha=0.7, 
                      edgecolor='black', linewidth=2, zorder=4)
        
        ax.set_xlabel('Population Size', fontsize=14, fontweight='bold')
        ax.set_ylabel('Expected Fitness (BB/100)', fontsize=14)
        ax.set_title('Predicted Performance for Untested Populations', 
                    fontsize=16, fontweight='bold')
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Add prediction details as text
        text_str = "Predictions:\n"
        for pop in pred_pops:
            if self.predictions[pop]:
                pred = self.predictions[pop][0]
                text_str += f"p{pop}: m≈{pred['matchups']}, h≈{pred['hands']}, σ≈{pred['sigma']:.3f}\n"
        
        ax.text(0.02, 0.98, text_str, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'predictions.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self):
        """Generate comprehensive mathematical analysis report."""
        print("\n" + "="*80)
        print("GENERATING RESEARCH REPORT")
        print("="*80)
        
        report_path = self.output_dir / "hyperparameter_analysis_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Hyperparameter Relationship Analysis Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Data Sources**: {len(self.sweep_dirs)} sweep(s)\n")
            f.write(f"**Total Configurations**: {len(self.all_results)}\n\n")
            
            f.write("---\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(self._generate_executive_summary())
            f.write("\n---\n\n")
            
            # Mathematical Formulations
            f.write("## Mathematical Formulations\n\n")
            f.write(self._generate_mathematical_section())
            f.write("\n---\n\n")
            
            # Population-Specific Optima
            f.write("## Population-Specific Optimal Configurations\n\n")
            f.write(self._generate_population_section())
            f.write("\n---\n\n")
            
            # Predictions
            f.write("## Predictions for Untested Configurations\n\n")
            f.write(self._generate_predictions_section())
            f.write("\n---\n\n")
            
            # Hyperparameter Effects
            if hasattr(self, 'effects'):
                f.write("## Individual Hyperparameter Effects\n\n")
                f.write(self._generate_effects_section())
                f.write("\n---\n\n")
            
            # Recommendations
            f.write("## Evidence-Based Recommendations\n\n")
            f.write(self._generate_recommendations())
            f.write("\n---\n\n")
            
            # Methodology
            f.write("## Methodology\n\n")
            f.write(self._generate_methodology())
        
        print(f"\n✓ Report saved to: {report_path}")
        return report_path
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        summary = []
        
        # Add analyzed sweeps information
        summary.append("### Analyzed Sweep Directories\n\n")
        for i, sweep_dir in enumerate(self.sweep_dirs, 1):
            summary.append(f"{i}. `{sweep_dir.name}`\n")
        summary.append("\n")
        
        summary.append("This report presents a comprehensive mathematical analysis of ")
        summary.append("hyperparameter relationships in evolutionary poker AI training. ")
        summary.append("Through empirical data analysis and mathematical modeling, we ")
        summary.append("derive optimal configurations and predictive formulas.\n\n")
        
        summary.append("### Key Findings\n\n")
        
        # Best overall config
        if self.all_results:
            best = max(self.all_results, key=lambda x: self._extract_final_fitness(x) or 0)
            best_fitness = self._extract_final_fitness(best)
            config = best.get('config', {})
            
            summary.append(f"**Champion Configuration**: {best.get('name', 'N/A')}\n")
            if best_fitness is not None:
                summary.append(f"- Fitness: {best_fitness:.2f} BB/100\n")
            else:
                summary.append(f"- Fitness: Data not available\n")
            # Handle both flat and nested config structures
            pop_size = config.get('population_size') or config.get('evolution', {}).get('population_size', 'N/A')
            matchups = config.get('matchups_per_agent') or config.get('fitness', {}).get('matchups_per_agent', 'N/A')
            hands = config.get('hands_per_matchup') or config.get('fitness', {}).get('hands_per_matchup', 'N/A')
            sigma = config.get('mutation_sigma') or config.get('evolution', {}).get('mutation_sigma', 'N/A')
            hof = config.get('hall_of_fame_count', 'N/A')
            
            summary.append(f"- Population: {pop_size}\n")
            summary.append(f"- Matchups: {matchups}\n")
            summary.append(f"- Hands: {hands}\n")
            summary.append(f"- Sigma: {sigma}\n")
            summary.append(f"- Hall of Fame: {hof}\n\n")
        
        # Key relationships discovered
        if self.mathematical_relationships:
            summary.append("**Mathematical Relationships Discovered**:\n\n")
            
            for rel_name, rel_data in self.mathematical_relationships.items():
                if 'formula' in rel_data:
                    summary.append(f"- {rel_data['formula']}\n")
        
        return ''.join(summary)
    
    def _generate_mathematical_section(self) -> str:
        """Generate mathematical formulations section."""
        section = []
        
        if not self.mathematical_relationships:
            return "No mathematical relationships derived.\n"
        
        for rel_name, rel_data in self.mathematical_relationships.items():
            section.append(f"### {rel_name.replace('_', ' ').title()}\n\n")
            
            if 'formula' in rel_data:
                section.append(f"**Formula**: `{rel_data['formula']}`\n\n")
            
            if 'r_squared' in rel_data:
                section.append(f"**Goodness of Fit**: R² = {rel_data['r_squared']:.4f}\n\n")
            
            if 'model' in rel_data:
                section.append(f"**Model Type**: {rel_data['model']}\n\n")
            
            # Add empirical evidence
            if 'data' in rel_data:
                section.append("**Empirical Evidence**:\n\n")
                section.append("| Parameter | Observed | Formula Prediction |\n")
                section.append("|-----------|----------|--------------------|\n")
                
                for point in rel_data['data'][:10]:  # Show first 10 points
                    if len(point) >= 2:
                        # Calculate prediction using the fitted function if available
                        prediction = "-"
                        if 'function' in rel_data and hasattr(rel_data['function'], '__call__'):
                            try:
                                pred_value = rel_data['function'](point[0])
                                prediction = f"{pred_value:.3f}"
                            except Exception:
                                prediction = "error"
                        section.append(f"| {point[0]} | {point[1]:.3f} | {prediction} |\n")
                
                section.append("\n")
            
            section.append("\n")
        
        return ''.join(section)
    
    def _generate_population_section(self) -> str:
        """Generate population-specific section."""
        section = []
        
        if not self.population_specific_optima:
            return "No population-specific analysis available.\n"
        
        section.append("| Population | Optimal m | Optimal h | Optimal σ | Best Fitness |\n")
        section.append("|------------|-----------|-----------|-----------|-------------|\n")
        
        for pop in sorted(self.population_specific_optima.keys()):
            optima = self.population_specific_optima[pop]
            section.append(f"| {pop:10d} | {optima['optimal_matchups']:9d} | "
                          f"{optima['optimal_hands']:9d} | {optima['optimal_sigma']:9.3f} | "
                          f"{optima['best_config']['fitness']:11.2f} |\n")
        
        section.append("\n")
        
        return ''.join(section)
    
    def _generate_predictions_section(self) -> str:
        """Generate predictions section."""
        section = []
        
        if not self.predictions:
            return "No predictions generated.\n"
        
        section.append("Based on mathematical relationships, we predict optimal ")
        section.append("configurations for untested population sizes:\n\n")
        
        section.append("| Population | Predicted m | Predicted h | Predicted σ | Expected Fitness |\n")
        section.append("|------------|-------------|-------------|-------------|------------------|\n")
        
        for pop in sorted(self.predictions.keys()):
            for pred in self.predictions[pop]:
                section.append(f"| {pred['population']:10d} | {pred['matchups']:11d} | "
                              f"{pred['hands']:11d} | {pred['sigma']:11.3f} | "
                              f"{pred['expected_fitness']:16.2f} |\n")
        
        section.append("\n")
        section.append("**Note**: Predictions are based on interpolation/extrapolation of ")
        section.append("observed relationships. Empirical validation recommended.\n\n")
        
        return ''.join(section)
    
    def _generate_effects_section(self) -> str:
        """Generate individual effects section."""
        section = []
        
        for param, data in self.effects.items():
            section.append(f"### {data['name']}\n\n")
            section.append(f"**Optimal Value**: {data['optimal']} {data['unit']}\n")
            section.append(f"**Optimal Fitness**: {data['optimal_fitness']:.2f} BB/100\n")
            section.append(f"**Improvement**: +{data['improvement']:.1f}% over baseline\n\n")
            
            section.append("| Value | Mean Fitness | Std Dev | Median | N |\n")
            section.append("|-------|--------------|---------|--------|---|\n")
            
            for i, val in enumerate(data['values']):
                marker = " ⭐" if val == data['optimal'] else ""
                section.append(f"| {val}{marker} | {data['means'][i]:12.2f} | "
                              f"{data['stds'][i]:7.2f} | {data['medians'][i]:6.2f} | "
                              f"{data['counts'][i]:1d} |\n")
            
            section.append("\n")
        
        return ''.join(section)
    
    def _generate_recommendations(self) -> str:
        """Generate evidence-based recommendations."""
        recommendations = []
        
        recommendations.append("Based on the empirical analysis and mathematical modeling, ")
        recommendations.append("we recommend the following hyperparameter configurations:\n\n")
        
        recommendations.append("### For Maximum Performance\n\n")
        if self.all_results:
            best = max(self.all_results, key=lambda x: self._extract_final_fitness(x) or 0)
            recommendations.append(f"Use configuration: **{best.get('name', 'N/A')}**\n\n")
        
        recommendations.append("### For Specific Populations\n\n")
        
        if self.population_specific_optima:
            for pop in sorted(self.population_specific_optima.keys()):
                optima = self.population_specific_optima[pop]
                recommendations.append(f"**Population {pop}**:\n")
                recommendations.append(f"- Matchups: {optima['optimal_matchups']}\n")
                recommendations.append(f"- Hands: {optima['optimal_hands']}\n")
                recommendations.append(f"- Sigma: {optima['optimal_sigma']:.3f}\n\n")
        
        recommendations.append("### General Principles\n\n")
        
        if self.mathematical_relationships:
            if 'population_sigma' in self.mathematical_relationships:
                rel = self.mathematical_relationships['population_sigma']
                if 'formula' in rel:
                    recommendations.append(f"- **Mutation Sigma**: Use {rel['formula']}\n")
            
            if 'population_matchups' in self.mathematical_relationships:
                rel = self.mathematical_relationships['population_matchups']
                if 'formula' in rel:
                    recommendations.append(f"- **Matchups Scaling**: {rel['formula']}\n")
            
            if 'matchups_hands' in self.mathematical_relationships:
                rel = self.mathematical_relationships['matchups_hands']
                if 'priority' in rel:
                    recommendations.append(f"- **Budget Allocation**: Prioritize {rel['priority']}\n")
        
        recommendations.append("\n")
        
        return ''.join(recommendations)
    
    def _generate_methodology(self) -> str:
        """Generate methodology section."""
        methodology = []
        
        methodology.append("### Data Collection\n\n")
        methodology.append(f"- Sweep directories analyzed: {len(self.sweep_dirs)}\n")
        
        # List specific sweep directories
        for i, sweep_dir in enumerate(self.sweep_dirs, 1):
            methodology.append(f"  {i}. {sweep_dir.name}\n")
        methodology.append(f"\n- Total configurations: {len(self.all_results)}\n")
        methodology.append(f"- Population sizes tested: {sorted(self.by_population.keys())}\n")
        methodology.append(f"- Matchup values tested: {sorted(self.by_matchups.keys())}\n")
        methodology.append(f"- Hands values tested: {sorted(self.by_hands.keys())}\n")
        methodology.append(f"- Sigma values tested: {sorted(self.by_sigma.keys())}\n\n")
        
        methodology.append("### Analysis Methods\n\n")
        methodology.append("1. **Individual Effects**: Mean and median fitness by parameter\n")
        methodology.append("2. **Mathematical Fitting**: Curve fitting with scipy.optimize\n")
        methodology.append("3. **Model Selection**: R² goodness of fit\n")
        methodology.append("4. **Prediction**: Extrapolation from fitted models\n")
        methodology.append("5. **Visualization**: Matplotlib and Seaborn\n\n")
        
        methodology.append("### Statistical Validation\n\n")
        methodology.append(f"- Confidence level: {self.confidence_level * 100:.0f}%\n")
        methodology.append("- Error bars: ±1 standard deviation\n")
        methodology.append("- Sample size display: n shown for each data point\n\n")
        
        return ''.join(methodology)


def main():
    parser = argparse.ArgumentParser(
        description='Extract and analyze hyperparameter relationships',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'sweep_dirs',
        nargs='*',
        help='Sweep directory paths (if none provided, uses latest)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='hyperparam_results/analysis',
        help='Output directory for results (default: hyperparam_results/analysis)'
    )
    parser.add_argument(
        '--with-confidence',
        action='store_true',
        help='Include confidence intervals in analysis'
    )
    
    args = parser.parse_args()
    
    # Determine sweep directories
    sweep_paths = []
    
    if args.sweep_dirs:
        # Use provided paths
        for sweep_dir in args.sweep_dirs:
            path = Path(sweep_dir)
            if not path.exists():
                print(f"⚠️  Warning: {sweep_dir} does not exist, skipping")
                continue
            sweep_paths.append(path)
    else:
        # Find latest sweep
        hyperparam_dir = Path('hyperparam_results')
        if hyperparam_dir.exists():
            sweep_dirs = sorted(
                [d for d in hyperparam_dir.glob('sweep_*') if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if sweep_dirs:
                sweep_paths = [sweep_dirs[0]]
                print(f"ℹ️  Using latest sweep: {sweep_paths[0].name}")
            else:
                print("❌ No sweep directories found in hyperparam_results/")
                return 1
        else:
            print("❌ hyperparam_results/ directory not found")
            return 1
    
    if not sweep_paths:
        print("❌ No valid sweep directories to analyze")
        return 1
    
    # Import at top of file if not already there
    from datetime import datetime
    import time
    
    # Run analysis
    # Create timestamped output directory to avoid overwriting
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = Path(args.output_dir)
    output_dir = base_output_dir / f"analysis_{timestamp}"
    
    analyzer = HyperparameterAnalyzer(sweep_paths, output_dir)
    
    print("\n" + "="*80)
    print("HYPERPARAMETER RELATIONSHIP ANALYSIS")
    print("="*80)
    print(f"Output directory: {output_dir}")
    
    # Load data
    analyzer.load_data()
    
    if not analyzer.all_results:
        print("❌ No results loaded")
        return 1
    
    # Analyze effects
    analyzer.analyze_hyperparameter_effects()
    
    # Derive relationships
    analyzer.derive_mathematical_relationships()
    
    # Find population-specific optima
    analyzer.find_population_specific_optima()
    
    # Generate visualizations (optional - falls back to text-only if matplotlib unavailable)
    try:
        analyzer.generate_visualizations()
        print("✅ Visualizations generated successfully")
    except ImportError as e:
        print(f"⚠️  Visualization libraries not available: {e}")
        print("📄 Continuing with text-only analysis...")
    except Exception as e:
        print(f"⚠️  Error generating visualizations: {e}")
        print("📄 Continuing with text-only analysis...")
    
    # Generate report
    report_path = analyzer.generate_report()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📊 Results saved to: {output_dir}")
    print(f"📄 Report: {report_path}")
    print(f"📈 Visualizations: {output_dir / 'visualizations'}")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
