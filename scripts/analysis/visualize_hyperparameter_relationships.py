#!/usr/bin/env python3
"""
Generate visualizations for proven hyperparameter relationships.

This script creates publication-quality plots showing the empirical relationships
between population size, matchups, hands, and mutation sigma based on tournament data.

Automatically extracts data from all tournament reports in tournament_reports/ directory.
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
import re
from collections import defaultdict

def extract_config_from_name(name: str):
    """
    Extract hyperparameters from agent name.
    Format: p{pop}_m{matchups}_h{hands}_s{sigma}_g{gens}
    """
    pattern = r'p(\d+)_m(\d+)_h(\d+)_s([\d.]+)(?:_g(\d+))?'
    match = re.search(pattern, name)
    if match:
        pop = int(match.group(1))
        matchups = int(match.group(2))
        hands = int(match.group(3))
        sigma = float(match.group(4))
        gens = int(match.group(5)) if match.group(5) else None
        return pop, matchups, hands, sigma, gens
    return None

def load_tournament_data(tournament_reports_dir: Path):
    """
    Load all tournament data from tournament_reports directory.
    Returns list of (name, win_rate) tuples.
    """
    print("Loading tournament data from all reports...")
    
    agent_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'tournaments': 0})
    
    # Search for all report.json files
    for report_file in tournament_reports_dir.rglob('report.json'):
        try:
            with open(report_file) as f:
                data = json.load(f)
            
            # Check if this is the right format
            if 'agents' in data:
                for agent in data['agents']:
                    name = agent.get('name', '')
                    wins = agent.get('wins', 0)
                    losses = agent.get('losses', 0)
                    
                    # Only include agents with proper naming convention
                    if extract_config_from_name(name):
                        agent_stats[name]['wins'] += wins
                        agent_stats[name]['losses'] += losses
                        agent_stats[name]['tournaments'] += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Skipping {report_file}: {e}")
            continue
    
    # Calculate win rates
    configs = []
    for name, stats in agent_stats.items():
        total_games = stats['wins'] + stats['losses']
        if total_games > 0:
            win_rate = (stats['wins'] / total_games) * 100
            configs.append((name, win_rate))
            print(f"  Loaded: {name[:40]:40s} {stats['wins']:3d}W {stats['losses']:3d}L ({win_rate:.1f}%)")
    
    print(f"\nTotal configs loaded: {len(configs)}")
    return configs

# Load tournament data dynamically
tournament_reports_dir = Path(__file__).parent.parent.parent / 'tournament_reports'
if not tournament_reports_dir.exists():
    print(f"Error: Tournament reports directory not found: {tournament_reports_dir}")
    print("Using fallback hardcoded data...")
    # Fallback to hardcoded data if directory doesn't exist
    configs = [
        ('p40_m8_h375_s0.1_g50', 78.7),
        ('p40_m6_h500_s0.15_g200', 73.1),
        ('p40_m8_h375_s0.1_g200', 72.2),
        ('p20_m6_h500_s0.15_g200', 71.3),
        ('p12_m6_h500_s0.15_g200', 68.5),
        ('p12_m8_h500_s0.08_g200', 81.2),
        ('p12_m6_h750_s0.08_g50', 67.4),
        ('p12_m6_h375_s0.1_g50', 63.9),
        ('p12_m6_h750_s0.1_g50', 62.5),
        ('p12_m6_h750_s0.1_g200', 61.1),
    ]
else:
    configs = load_tournament_data(tournament_reports_dir)

# Parse configs

# Parse and sort configs
parsed = []
for name, wr in configs:
    result = extract_config_from_name(name)
    if result:
        pop, matchups, hands, sigma, gens = result
        # Filter out configs with extremely low win rates (likely failed runs)
        if wr > 10.0:  # Only include configs with >10% win rate
            parsed.append((pop, matchups, hands, sigma, wr, name))
        else:
            print(f"  Skipping low win rate: {name} ({wr:.1f}%)")
    else:
        print(f"Warning: Could not parse config name: {name}")

if not parsed:
    print("Error: No valid configurations found!")
    exit(1)

# Sort by pop, matchups, hands, sigma
parsed.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

print(f"\nParsed {len(parsed)} valid configurations for visualization (ordered by pop, matchups, hands, sigma)")
print("=" * 80)

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
colors = {'p12': '#e74c3c', 'p20': '#f39c12', 'p40': '#27ae60'}

# Create output directory
output_dir = Path('tournament_reports/hyperparameter_analysis')
output_dir.mkdir(parents=True, exist_ok=True)

print("Generating hyperparameter relationship visualizations...")
print("=" * 80)

# ============================================================================
# Figure 1: Population vs Matchups
# ============================================================================
print("\n1. Creating Population vs Matchups plot...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle('Relationship 1: Population Size ↔ Matchups per Agent', 
             fontsize=16, fontweight='bold', y=1.02)

# Left plot: Absolute values
for pop_size in [12, 20, 40]:
    data = [(p, m, wr) for p, m, h, s, wr, n in parsed if p == pop_size]
    if data:
        pops, matchups, wrs = zip(*data)
        color = f'p{pop_size}'
        ax1.scatter(matchups, wrs, s=200, alpha=0.7, 
                   color=colors.get(color, '#3498db'), 
                   label=f'pop={pop_size}', edgecolors='black', linewidth=1.5)

ax1.set_xlabel('Matchups per Agent', fontsize=12, fontweight='bold')
ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax1.set_title('Win Rate vs Matchups (by Population)', fontsize=13)
ax1.legend(fontsize=11, loc='lower right')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(30, 100)

# Right plot: Ratio-based
for pop_size in [12, 20, 40]:
    data = [(p, m/p, wr) for p, m, h, s, wr, n in parsed if p == pop_size]
    if data:
        pops, ratios, wrs = zip(*data)
        color = f'p{pop_size}'
        ax2.scatter(ratios, wrs, s=200, alpha=0.7, 
                   color=colors.get(color, '#3498db'),
                   label=f'pop={pop_size}', edgecolors='black', linewidth=1.5)

# Add trend zones
ax2.axvspan(0.15, 0.25, alpha=0.2, color='green', label='Large Pop Zone (15-25%)')
ax2.axvspan(0.50, 0.67, alpha=0.2, color='orange', label='Small Pop Zone (50-67%)')

ax2.set_xlabel('Matchups / Population Ratio', fontsize=12, fontweight='bold')
ax2.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax2.set_title('Win Rate vs Matchup Ratio', fontsize=13)
ax2.legend(fontsize=10, loc='lower right')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(30, 100)

plt.tight_layout()
plt.savefig(output_dir / 'relationship_1_population_vs_matchups.png', 
            dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: {output_dir / 'relationship_1_population_vs_matchups.png'}")

# ============================================================================
# Figure 2: Matchups vs Hands
# ============================================================================
print("\n2. Creating Matchups vs Hands plot...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle('Relationship 2: Matchups ↔ Hands per Matchup', 
             fontsize=16, fontweight='bold', y=1.02)

# Left plot: Matchups vs Hands (bubble size = win rate)
matchups_data = {}
for p, m, h, s, wr, n in parsed:
    key = (m, h)
    if key not in matchups_data:
        matchups_data[key] = []
    matchups_data[key].append(wr)

for (m, h), wrs in matchups_data.items():
    avg_wr = np.mean(wrs)
    size = 100 + avg_wr * 10  # Scale bubble size by win rate
    color_val = avg_wr / 100  # Normalize for colormap
    ax1.scatter(m, h, s=size, alpha=0.6, c=[color_val], cmap='RdYlGn', 
               vmin=0.5, vmax=0.85, edgecolors='black', linewidth=1.5)
    ax1.text(m, h, f'{avg_wr:.0f}%', ha='center', va='center', 
            fontsize=9, fontweight='bold')

ax1.set_xlabel('Matchups per Agent', fontsize=12, fontweight='bold')
ax1.set_ylabel('Hands per Matchup', fontsize=12, fontweight='bold')
ax1.set_title('Performance Map (bubble size = win rate)', fontsize=13)
ax1.grid(True, alpha=0.3)
ax1.set_xticks([6, 8])
ax1.set_yticks([375, 500, 750])

# Right plot: Total evaluations vs Win rate
total_evals_data = []
for p, m, h, s, wr, n in parsed:
    total_evals = m * h
    total_evals_data.append((total_evals, wr, f'm{m}+h{h}'))

total_evals_data.sort(key=lambda x: x[0])
evals, wrs, labels = zip(*total_evals_data)

scatter = ax2.scatter(evals, wrs, s=150, alpha=0.7, c=wrs, cmap='RdYlGn', 
                     vmin=55, vmax=85, edgecolors='black', linewidth=1.5)

# Highlight best performers
best_configs = [(3000, 78.7, 'm8+h375'), (4000, 81.2, 'm8+h500')]
for ev, wr, lbl in best_configs:
    ax2.scatter(ev, wr, s=400, alpha=0.3, color='gold', edgecolors='gold', 
               linewidth=3, marker='*', zorder=10)

# Add optimal zone
ax2.axvspan(3000, 4500, alpha=0.15, color='green', label='Optimal Zone')

ax2.set_xlabel('Total Evaluations (matchups × hands)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax2.set_title('Win Rate vs Total Evaluations', fontsize=13)
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)
ax2.set_ylim(55, 85)

plt.colorbar(scatter, ax=ax2, label='Win Rate (%)')
plt.tight_layout()
plt.savefig(output_dir / 'relationship_2_matchups_vs_hands.png', 
            dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: {output_dir / 'relationship_2_matchups_vs_hands.png'}")

# ============================================================================
# Figure 3: Population vs Sigma
# ============================================================================
print("\n3. Creating Population vs Sigma plot...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle('Relationship 3: Population Size ↔ Mutation Sigma', 
             fontsize=16, fontweight='bold', y=1.02)

# Left plot: Scatter with colors by population
for pop_size in [12, 20, 40]:
    data = [(s, wr) for p, m, h, s, wr, n in parsed if p == pop_size]
    if data:
        sigmas, wrs = zip(*data)
        color = f'p{pop_size}'
        ax1.scatter(sigmas, wrs, s=200, alpha=0.7, 
                   color=colors.get(color, '#3498db'),
                   label=f'pop={pop_size}', edgecolors='black', linewidth=1.5)

# Add empirical formula line
pop_range = np.linspace(12, 60, 100)
sigma_formula = 0.5 / np.sqrt(pop_range)
ax1_twin = ax1.twiny()
ax1_twin.plot(sigma_formula, pop_range, 'k--', alpha=0.3, linewidth=2, 
             label='σ ≈ 0.5/√pop')
ax1_twin.set_xlabel('Theoretical Sigma (from formula)', fontsize=10, style='italic')
ax1_twin.set_xlim(0.04, 0.16)

ax1.set_xlabel('Mutation Sigma', fontsize=12, fontweight='bold')
ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax1.set_title('Win Rate vs Sigma (by Population)', fontsize=13)
ax1.legend(fontsize=11, loc='lower left')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(30, 100)
ax1.set_xlim(0.06, 0.16)

# Right plot: Heat map showing population vs sigma
pop_values = [12, 20, 40]
sigma_values = [0.08, 0.10, 0.12, 0.15]

# Create matrix
matrix = np.zeros((len(pop_values), len(sigma_values)))
for i, pop in enumerate(pop_values):
    for j, sig in enumerate(sigma_values):
        matches = [wr for p, m, h, s, wr, n in parsed if p == pop and abs(s - sig) < 0.01]
        matrix[i, j] = np.mean(matches) if matches else np.nan

im = ax2.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=60, vmax=82)
ax2.set_xticks(range(len(sigma_values)))
ax2.set_yticks(range(len(pop_values)))
ax2.set_xticklabels([f'{s:.2f}' for s in sigma_values])
ax2.set_yticklabels([f'{p}' for p in pop_values])
ax2.set_xlabel('Mutation Sigma', fontsize=12, fontweight='bold')
ax2.set_ylabel('Population Size', fontsize=12, fontweight='bold')
ax2.set_title('Performance Heat Map', fontsize=13)

# Add text annotations
for i in range(len(pop_values)):
    for j in range(len(sigma_values)):
        if not np.isnan(matrix[i, j]):
            text = ax2.text(j, i, f'{matrix[i, j]:.1f}%',
                          ha="center", va="center", color="black", 
                          fontsize=10, fontweight='bold')

# Add formula overlay
ax2.text(0.95, 0.05, 'Formula: σ ≈ 0.5/√pop', 
        transform=ax2.transAxes, fontsize=11, style='italic',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
        ha='right', va='bottom')

plt.colorbar(im, ax=ax2, label='Win Rate (%)')
plt.tight_layout()
plt.savefig(output_dir / 'relationship_3_population_vs_sigma.png', 
            dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: {output_dir / 'relationship_3_population_vs_sigma.png'}")

# ============================================================================
# Figure 4: Comprehensive Overview
# ============================================================================
print("\n4. Creating comprehensive overview plot...")

fig = plt.figure(figsize=(28, 20))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

fig.suptitle('Hyperparameter Relationships - Comprehensive Overview', 
             fontsize=18, fontweight='bold', y=0.98)

# Top left: Win rate distribution by population
ax1 = fig.add_subplot(gs[0, 0])
pop_groups = {}
for p, m, h, s, wr, n in parsed:
    if p not in pop_groups:
        pop_groups[p] = []
    pop_groups[p].append(wr)

positions = []
data_to_plot = []
labels = []
for pop in sorted(pop_groups.keys()):
    positions.append(pop)
    data_to_plot.append(pop_groups[pop])
    labels.append(f'p{pop}')

bp = ax1.boxplot(data_to_plot, positions=positions, widths=3, patch_artist=True,
                 showmeans=True, meanline=True)
for patch, pop in zip(bp['boxes'], sorted(pop_groups.keys())):
    color = colors.get(f'p{pop}', '#3498db')
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax1.set_xlabel('Population Size', fontsize=11, fontweight='bold')
ax1.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
ax1.set_title('Win Rate Distribution by Population', fontsize=12)
ax1.grid(True, alpha=0.3, axis='y')
ax1.set_ylim(30, 100)

# Top middle: Matchups distribution
ax2 = fig.add_subplot(gs[0, 1])
matchup_groups = {}
for p, m, h, s, wr, n in parsed:
    if m not in matchup_groups:
        matchup_groups[m] = []
    matchup_groups[m].append(wr)

positions = list(sorted(matchup_groups.keys()))
data_to_plot = [matchup_groups[m] for m in positions]

bp = ax2.boxplot(data_to_plot, positions=positions, widths=0.5, patch_artist=True,
                 showmeans=True, meanline=True)
for patch in bp['boxes']:
    patch.set_facecolor('#3498db')
    patch.set_alpha(0.7)

ax2.set_xlabel('Matchups per Agent', fontsize=11, fontweight='bold')
ax2.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
ax2.set_title('Win Rate Distribution by Matchups', fontsize=12)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(30, 100)

# Top right: Sigma distribution

import random
ax3 = fig.add_subplot(gs[0, 2])
sigma_groups = {}
for p, m, h, s, wr, n in parsed:
    if s not in sigma_groups:
        sigma_groups[s] = []
    sigma_groups[s].append(wr)

raw_positions = list(sorted(sigma_groups.keys()))
# Scale the x positions to increase spacing
scale_factor = 25.0
positions = [x * scale_factor for x in raw_positions]
data_to_plot = [sigma_groups[s] for s in raw_positions]

# Increase width and add jitter to spread out points
box_width = 0.03 * scale_factor/np.sqrt(scale_factor)  # Adjust width based on scale
bp = ax3.boxplot(data_to_plot, positions=positions, widths=box_width, patch_artist=True,
                 showmeans=True, meanline=True)
for patch in bp['boxes']:
    patch.set_facecolor('#9b59b6')
    patch.set_alpha(0.7)

# Set custom x-ticks to show actual sigma values
ax3.set_xticks(positions)
ax3.set_xticklabels([f"{s:.2f}" for s in raw_positions])

ax3.set_xlabel('Mutation Sigma', fontsize=11, fontweight='bold')
ax3.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
ax3.set_title('Win Rate Distribution by Sigma', fontsize=12)
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim(30, 100)

# Middle row: 3D-style visualization (population, matchups, win rate)
ax4 = fig.add_subplot(gs[1, :])
for p, m, h, s, wr, n in parsed:
    color = colors.get(f'p{p}', '#3498db')
    size = max(50, (wr - 10) * 10)  # Ensure minimum size, scale from 10% baseline
    ax4.scatter(p, m, s=size, alpha=0.6, color=color, edgecolors='black', linewidth=1)
    
# Add champion marker
champion = [(p, m, wr) for p, m, h, s, wr, n in parsed if wr > max(wr2 for _, _, _, _, wr2, _ in parsed) - 5]
if champion:
    for p, m, wr in champion[:3]:  # Mark top 3
        ax4.scatter(p, m, s=500, alpha=0.3, color='gold', 
                   edgecolors='gold', linewidth=3, marker='*', zorder=10)

ax4.set_xlabel('Population Size', fontsize=12, fontweight='bold')
ax4.set_ylabel('Matchups per Agent', fontsize=12, fontweight='bold')
ax4.set_title('Population vs Matchups (bubble size = win rate)', fontsize=13)
ax4.legend(fontsize=11, loc='upper left')
ax4.grid(True, alpha=0.3)

# Bottom left: Best configs ranking
ax5 = fig.add_subplot(gs[2, :])
top_configs = sorted(parsed, key=lambda x: x[4], reverse=True)[:min(8, len(parsed))]
names = [f"Pop: {p}\nMatchups: {m}\nHands: {h}" for p, m, h, s, wr, n in top_configs]
wrs = [wr for p, m, h, s, wr, n in top_configs]
colors_list = [colors.get(f'p{p}', '#3498db') for p, m, h, s, wr, n in top_configs]

bars = ax5.barh(range(len(names)), wrs, color=colors_list, alpha=0.7, edgecolor='black', linewidth=1.5)
ax5.set_yticks(range(len(names)))
ax5.set_yticklabels(names, fontsize=9)
ax5.set_xlabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax5.set_title(f'Top {len(top_configs)} Configurations', fontsize=13)
ax5.grid(True, alpha=0.3, axis='x')
ax5.set_xlim(0, max(100, max(wrs) + 5))

# Add value labels
for i, (bar, wr) in enumerate(zip(bars, wrs)):
    ax5.text(wr + 1, i, f'{wr:.1f}%', va='center', fontsize=9, fontweight='bold')

# Update color legend to explain meaning of colors
color_legend = {'#e74c3c': 'Population 12', '#f39c12': 'Population 20', '#27ae60': 'Population 40'}

# Add color legend to the plot
legend_patches = [plt.Line2D([0], [0], color=color, lw=4, label=label) for color, label in color_legend.items()]
ax5.legend(handles=legend_patches, fontsize=10, loc='lower right', title='Population Colors')

plt.tight_layout()
plt.savefig(output_dir / 'comprehensive_overview.png', 
            dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: {output_dir / 'comprehensive_overview.png'}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("✓ All visualizations generated successfully!")
print(f"\nOutput location: {output_dir.absolute()}")
print("\nGenerated files:")
print("  1. relationship_1_population_vs_matchups.png")
print("  2. relationship_2_matchups_vs_hands.png")
print("  3. relationship_3_population_vs_sigma.png")
print("  4. comprehensive_overview.png")
print("\nThese visualizations have been added to your tournament reports.")
print("=" * 80)
