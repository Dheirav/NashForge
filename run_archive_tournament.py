#!/usr/bin/env python3
"""
Tournament: all 6 current champions vs all 7 archived agents (13 total).

Runs:
  - 10 rounds heads-up     (10,000 hands per matchup)
  - 10 rounds multi-table  (6-player tables, min 50 encounters per pair)

Results saved to tournament_reports/ArchiveVsChampions/
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ── Agent paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent

AGENTS = [
    # Current B3 champions
    ROOT / 'hall_of_fame/champions/p12_m7_h500_s0.08_g200_b3_champion.npy',
    ROOT / 'hall_of_fame/champions/p12_m8_h500_s0.08_g200_champion.npy',
    ROOT / 'hall_of_fame/champions/p12_m8_h500_s0.09_g200_b3_champion.npy',
    ROOT / 'hall_of_fame/champions/p12_m8_h750_s0.1_g200_b3_champion.npy',
    ROOT / 'hall_of_fame/champions/p40_m8_h375_s0.1_champion.npy',
    ROOT / 'hall_of_fame/champions/p40_m8_h750_s0.07_g200_b3_champion.npy',

    # Archived B1/B2 agents
    ROOT / 'hall_of_fame/archived/p12_m6_h375_s0.1_g50_v2_champion.npy',
    ROOT / 'hall_of_fame/archived/p12_m6_h500_s0.15_champion.npy',
    ROOT / 'hall_of_fame/archived/p12_m6_h750_s0.08_g50_champion.npy',
    ROOT / 'hall_of_fame/archived/p12_m6_h750_s0.1_g200_champion.npy',
    ROOT / 'hall_of_fame/archived/p12_m6_h750_s0.1_g50_champion.npy',
    ROOT / 'hall_of_fame/archived/p20_m6_h500_s0.15_champion.npy',
    ROOT / 'hall_of_fame/archived/p40_m6_h500_s0.15_champion.npy',
]

AGENT_PATHS = [str(p) for p in AGENTS]


def verify_agents():
    missing = [p for p in AGENTS if not p.exists()]
    if missing:
        print("ERROR: Missing agent files:")
        for p in missing:
            print(f"  {p}")
        sys.exit(1)
    print(f"Verified {len(AGENTS)} agent files")


def run_round(mode, round_num, total_rounds, output_dir, extra_args):
    label = f"{mode.upper()} Round {round_num}/{total_rounds}"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = Path(output_dir) / f"round_{round_num:02d}_{timestamp}"

    cmd = [
        'python3', 'scripts/evaluation/round_robin_agents_config.py',
        '--mode', mode,
        '--hands', '10000',
        '--output', str(out),
        '--agents',
    ] + AGENT_PATHS + extra_args

    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"Output: {out}")
    print('='*80)

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ {label} done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {label} failed (exit {e.returncode})")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted at {label}")
        sys.exit(1)


def main():
    print('='*80)
    print('ARCHIVE vs CHAMPIONS TOURNAMENT')
    print('='*80)
    print(f'Agents : {len(AGENTS)}  (6 current champions + 7 archived)')
    print('Heads-up rounds    : 10  (10,000 hands each matchup)')
    print('Multi-table rounds : 10  (10,000 hands/table, min 50 encounters/pair)')
    print('='*80)

    verify_agents()

    base_dir = ROOT / 'tournament_reports' / 'ArchiveVsChampions'
    hu_dir   = base_dir / 'HeadsUp'
    mt_dir   = base_dir / 'MultiTable'
    hu_dir.mkdir(parents=True, exist_ok=True)
    mt_dir.mkdir(parents=True, exist_ok=True)

    # ── Heads-up: 10 rounds ──────────────────────────────────────────────────
    print('\n\n' + '='*80)
    print('PHASE 1: HEADS-UP (10 rounds)')
    print('='*80)

    hu_ok = 0
    for r in range(1, 11):
        ok = run_round('heads-up', r, 10, hu_dir, [])
        if ok:
            hu_ok += 1

    # ── Multi-table: 10 rounds ───────────────────────────────────────────────
    print('\n\n' + '='*80)
    print('PHASE 2: MULTI-TABLE (10 rounds, 6-player tables, min 50 encounters)')
    print('='*80)

    mt_ok = 0
    for r in range(1, 11):
        ok = run_round(
            'multi-table', r, 10, mt_dir,
            ['--table-size', '6', '--min-encounters', '50'],
        )
        if ok:
            mt_ok += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print('\n\n' + '='*80)
    print('TOURNAMENT COMPLETE')
    print('='*80)
    print(f'Heads-up  : {hu_ok}/10 rounds completed  → {hu_dir}')
    print(f'Multi-table: {mt_ok}/10 rounds completed  → {mt_dir}')
    print()
    print('To analyse results:')
    print(f'  python3 scripts/analysis/analyze_tournament_history.py --folder {base_dir}')


if __name__ == '__main__':
    main()
