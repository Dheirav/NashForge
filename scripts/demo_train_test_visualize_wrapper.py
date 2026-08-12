
import os
import subprocess
import numpy as np
from training.policy_network import PolicyNetwork

# --- Configurations ---
GENERATIONS = 5
NUM_HANDS = 100

# Force heads-up mode only
FORMAT = 'heads-up'
CHAMPION_PATH = 'hall_of_fame/ppo_hu/p12_m7_h375_s0.06_g50_b4_champion.npy'
num_players = 2
arch = "17 64 32 6"

TRAINED_GENOME_PATH = 'trained_demo_agent.npy'
TOURNAMENT_REPORTS_DIR = 'tournament_reports/demo_wrapper_run'

# --- Step 1: Train agent (calls demo_train_and_test_vs_champion.py logic) ---
def train_and_save_genome():
    from scripts.demo_train_and_test_vs_champion import train_simple_agent
    best_genome, fitness_history = train_simple_agent(FORMAT, GENERATIONS)
    np.save(TRAINED_GENOME_PATH, best_genome)
    print(f"Saved trained agent genome to {TRAINED_GENOME_PATH}")
    return best_genome, fitness_history

# --- Step 2: Play matches and save tournament results ---
import json
import tempfile
def play_and_save_tournament():
    print("\nPlaying matches between trained agent and champion...")
    os.makedirs(TOURNAMENT_REPORTS_DIR, exist_ok=True)
    agent1_name = os.path.splitext(os.path.basename(TRAINED_GENOME_PATH))[0]
    agent2_name = os.path.splitext(os.path.basename(CHAMPION_PATH))[0]
    # Run match_agents.py and capture output
    cmd = [
        'python',
        'scripts/evaluation/match_agents.py',
        '--agent1', TRAINED_GENOME_PATH,
        '--arch1', arch,
        '--agent2', CHAMPION_PATH,
        '--arch2', arch,
        '--hands', str(NUM_HANDS),
        '--players', '2'
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    # Robust JSON parsing for final stacks
    import json
    stacks = None
    for line in result.stdout.splitlines():
        try:
            data = json.loads(line)
            if "final_stacks" in data:
                stacks = data["final_stacks"]
                break
        except Exception:
            continue
    if stacks is None:
        raise ValueError("Failed to parse final stacks from match output")
    # Compose minimal report.json compatible with analyze_tournament_history.py
    agent_names = ["trained_agent", "champion"]
    agents = []
    for i, stack in enumerate(stacks):
        wins = int(stack == max(stacks))
        losses = int(stack != max(stacks))
        agents.append({
            "name": agent_names[i],
            "chips": stack,
            "wins": wins,
            "losses": losses,
            "win_percentage": 100.0 * wins
        })
    if stacks[0] > stacks[1]:
        winner = agent_names[0]
        loser = agent_names[1]
    elif stacks[1] > stacks[0]:
        winner = agent_names[1]
        loser = agent_names[0]
    else:
        winner = "draw"
        loser = "draw"
    matches = [{
        "winner": winner,
        "loser": loser
    }]
    report = {
        "mode": FORMAT,
        "agents": agents,
        "matches": matches
    }
    with open(os.path.join(TOURNAMENT_REPORTS_DIR, 'report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Tournament results saved to {TOURNAMENT_REPORTS_DIR}/report.json")

# --- Step 3: Visualize agent behavior ---
def visualize_agent_behavior():
    print("\nVisualizing agent behavior with existing script...")
    cmd = [
        'python',
        'scripts/analysis/visualize_agent_behavior.py',
        '--genome', TRAINED_GENOME_PATH,
        '--arch', arch,
        '--hands', str(NUM_HANDS),
        '--players', str(num_players)
    ]
    subprocess.run(cmd)

# --- Step 4: Visualize tournament results ---
def visualize_tournament_results():
    print("\nVisualizing tournament results with analyze_tournament_history.py...")
    cmd = [
        'python',
        'scripts/analysis/analyze_tournament_history.py',
        '--folder', TOURNAMENT_REPORTS_DIR,
        '--top-n', '5'
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    best_genome, fitness_history = train_and_save_genome()
    play_and_save_tournament()
    visualize_agent_behavior()
    visualize_tournament_results()

    # --- Step 5: Feature extraction and logging demo ---
    print("\nExtracting and logging features for a short match...")
    from engine import PokerGame, get_state_features
    num_demo_hands = 2
    demo_game = PokerGame([1000] * num_players, small_blind=5, big_blind=10, seed=123)
    for hand in range(num_demo_hands):
        demo_game = PokerGame([1000] * num_players, small_blind=5, big_blind=10, seed=123 + hand)
        print(f"\n=== Demo Hand {hand+1} ===")
        while not demo_game.is_hand_over():
            player = demo_game.state.current_player
            if player is None or demo_game.state.players[player].has_folded or demo_game.state.players[player].is_all_in:
                break
            features = get_state_features(demo_game, player)
            print(f"Player {player} features:")
            for k, v in features.items():
                print(f"  {k}: {v:.3f}")
            # Take a random legal action for demonstration
            legal = demo_game.get_legal_actions(player)
            action_type = legal[0]['type'] if legal else 'fold'
            from engine.actions import Action
            demo_game.apply_action(player, Action(action_type))
        demo_game.resolve_showdown()
    print("\nFeature extraction demo complete.")
