"""
Feature extraction for AI training.
Provides normalized state vectors and hand strength calculations.
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from .cards import Card, RANKS, SUITS
from .hand_eval import evaluate_hand, RANK_ORDER

# Try to import Numba for JIT compilation
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Fallback decorator
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


@jit(nopython=True, cache=True, fastmath=True)
def compute_pot_odds_jit(to_call: float, pot_size: float) -> float:
    """JIT-compiled pot odds calculation."""
    if pot_size + to_call <= 0:
        return 0.0
    return to_call / (pot_size + to_call)


@jit(nopython=True, cache=True, fastmath=True)
def compute_stack_to_pot_jit(stack: float, pot_size: float) -> float:
    """JIT-compiled stack-to-pot ratio calculation."""
    if pot_size <= 0:
        return 10.0
    return min(stack / pot_size, 20.0) / 20.0  # Normalize to 0-1


@jit(nopython=True, cache=True, fastmath=True)
def build_feature_vector_jit(
    pot_odds: float,
    stack_to_pot: float,
    position_idx: int,
    street_idx: int,
    num_active: float,
    hand_strength: float,
    commitment: float
) -> np.ndarray:
    """
    JIT-compiled feature vector assembly.
    
    Returns 17-dimensional feature vector:
    [0] pot_odds
    [1] stack_to_pot ratio
    [2-7] position one-hot (6 positions)
    [8-11] street one-hot (4 streets)
    [12] num_active players (normalized)
    [13] hand_strength
    [14] hand_potential (placeholder, currently equals hand_strength)
    [15] aggression (placeholder, set to 0.5)
    [16] commitment level
    """
    features = np.zeros(17, dtype=np.float32)
    
    # Continuous features
    features[0] = pot_odds
    features[1] = stack_to_pot
    
    # Position one-hot (6 positions max)
    if 0 <= position_idx < 6:
        features[2 + position_idx] = 1.0
    
    # Street one-hot (4 streets: preflop, flop, turn, river)
    if 0 <= street_idx < 4:
        features[8 + street_idx] = 1.0
    
    # Other features
    features[12] = num_active
    features[13] = hand_strength
    features[14] = hand_strength  # hand_potential = hand_strength for now
    features[15] = 0.5  # aggression placeholder
    features[16] = commitment
    
    return features


# Precomputed lookup tables for common calculations
# Pot odds lookup: POT_ODDS_TABLE[to_call][pot] = to_call/(pot+to_call)
# Using 5-chip granularity for indices, covering 0-5000 chips
POT_ODDS_TABLE = np.zeros((1001, 1001), dtype=np.float32)
for tc_idx in range(1001):
    to_call = tc_idx * 5
    for pot_idx in range(1001):
        pot = pot_idx * 5
        if pot + to_call > 0:
            POT_ODDS_TABLE[tc_idx, pot_idx] = to_call / (pot + to_call)

# Precomputed hand strength for all 169 starting hands (13 ranks × 13 ranks × suited/offsuit)
PREFLOP_STRENGTH_CACHE = {}
def _init_preflop_cache():
    """Initialize precomputed hand strength for all starting hands."""
    for i, r1 in enumerate(RANKS):
        for j, r2 in enumerate(RANKS):
            # Suited
            key_suited = (r1, r2, True)
            PREFLOP_STRENGTH_CACHE[key_suited] = preflop_hand_strength([Card(r1, 'h'), Card(r2, 'h')])
            # Offsuit
            if r1 != r2:
                key_offsuit = (r1, r2, False)
                PREFLOP_STRENGTH_CACHE[key_offsuit] = preflop_hand_strength([Card(r1, 'h'), Card(r2, 'd')])

def get_preflop_strength_fast(hole_cards: List[Card]) -> float:
    """Fast lookup of precomputed preflop hand strength."""
    if len(hole_cards) != 2:
        return 0.5
    c1, c2 = hole_cards
    suited = (c1.suit == c2.suit)
    key = (c1.rank, c2.rank, suited)
    return PREFLOP_STRENGTH_CACHE.get(key, 0.5)

# Chen formula for preflop hand strength
def chen_formula(hole_cards: List[Card]) -> float:
    """
    Calculate Chen formula score for preflop hand strength.
    Returns a score from -1 to 20 (higher is better).
    """
    if len(hole_cards) != 2:
        return 0.0
    
    c1, c2 = hole_cards
    r1, r2 = RANK_ORDER[c1.rank], RANK_ORDER[c2.rank]
    
    # Ensure r1 >= r2 (high card first)
    if r2 > r1:
        r1, r2 = r2, r1
        c1, c2 = c2, c1
    
    # Base score from high card
    high_card_scores = {
        12: 10,  # A
        11: 8,   # K
        10: 7,   # Q
        9: 6,    # J
        8: 5, 7: 4.5, 6: 4, 5: 3.5, 4: 3, 3: 2.5, 2: 2, 1: 1.5, 0: 1
    }
    score = high_card_scores.get(r1, r1 / 2 + 1)
    
    # Pair bonus
    if r1 == r2:
        score = max(5, score * 2)
    
    # Suited bonus
    if c1.suit == c2.suit:
        score += 2
    
    # Gap penalty
    gap = r1 - r2 - 1
    if gap == 1:
        score -= 1
    elif gap == 2:
        score -= 2
    elif gap == 3:
        score -= 4
    elif gap >= 4:
        score -= 5
    
    # Straight potential bonus (both cards <= Q and gap <= 2)
    if r1 <= 10 and gap <= 2 and r1 != r2:
        score += 1
    
    return score


def preflop_hand_strength(hole_cards: List[Card]) -> float:
    """
    Returns normalized preflop hand strength from 0.0 to 1.0.
    Based on Chen formula, normalized.
    """
    chen = chen_formula(hole_cards)
    # Chen scores range roughly from -1 to 20
    # Normalize to 0-1
    return max(0.0, min(1.0, (chen + 1) / 21))

# Initialize lookup cache on module load
_init_preflop_cache()


def hand_strength_vs_random(hole_cards: List[Card], community_cards: List[Card], 
                            num_simulations: int = 500) -> float:
    """
    Monte Carlo simulation of hand strength against random opponent hands.
    Returns win probability from 0.0 to 1.0.
    """
    from .cards import Deck
    import random
    
    if len(hole_cards) != 2:
        return 0.5
    
    wins = 0
    ties = 0
    
    # Cards that are already used
    used = set((c.rank, c.suit) for c in hole_cards + community_cards)
    
    for _ in range(num_simulations):
        # Create remaining deck
        remaining = [Card(r, s) for r in RANKS for s in SUITS 
                     if (r, s) not in used]
        random.shuffle(remaining)
        
        # Deal opponent cards
        opp_cards = remaining[:2]
        remaining = remaining[2:]
        
        # Complete community cards if needed
        need_community = 5 - len(community_cards)
        full_community = community_cards + remaining[:need_community]
        
        # Evaluate hands
        my_hand = evaluate_hand(hole_cards + full_community)
        opp_hand = evaluate_hand(opp_cards + full_community)
        
        if my_hand > opp_hand:
            wins += 1
        elif my_hand == opp_hand:
            ties += 1
    
    return (wins + ties * 0.5) / num_simulations


def get_state_features(game, player_id: int) -> Dict[str, float]:
    """
    Extract normalized features for AI model input.
    Returns a dictionary of feature names to values (all normalized 0-1 or -1 to 1).
    """
    player = game.players[player_id]
    
    # Basic info
    num_players = len(game.players)
    active_players = [p for p in game.players if not p.has_folded]
    players_in_hand = len(active_players)
    
    # Stack and pot info
    total_chips = sum(p.stack + p.total_contributed for p in game.players)
    my_stack = player.stack
    pot_size = game.state.pot.total
    
    # Position (0 = button, normalized by num_players)
    position = (player_id - game.state.button) % num_players
    position_normalized = position / max(1, num_players - 1)
    
    # Betting round (one-hot style, but as separate features)
    rounds = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3, 'showdown': 4}
    round_idx = rounds.get(game.state.betting_round, 0)
    
    # Pot odds
    to_call = max(0, game.current_bet - player.bet)
    pot_odds = to_call / (pot_size + to_call) if (pot_size + to_call) > 0 else 0
    
    # Stack to pot ratio (SPR)
    spr = my_stack / pot_size if pot_size > 0 else 10.0
    spr_normalized = min(1.0, spr / 20.0)  # Normalize, cap at 20
    
    # Stack relative to starting (assuming 100 BB start)
    bb = game.state.big_blind
    stack_bbs = my_stack / bb if bb > 0 else 0
    stack_normalized = min(1.0, stack_bbs / 200)  # Normalize, cap at 200 BB
    
    # Number of players to act after me
    current_idx = game.state.current_player
    players_behind = 0
    if current_idx is not None:
        for i in range(1, num_players):
            idx = (current_idx + i) % num_players
            p = game.players[idx]
            if not p.has_folded and not p.is_all_in and idx != player_id:
                players_behind += 1
    
    # Hand strength (preflop or postflop)
    if game.state.betting_round == 'preflop':
        hand_strength = preflop_hand_strength(player.hole_cards)
    else:
        # Use preflop strength for speed during training (monte carlo is slow)
        # For more accurate evaluation, use hand_strength_vs_random with low sim count
        hand_strength = preflop_hand_strength(player.hole_cards)
    
    # Aggression indicators
    facing_bet = 1.0 if to_call > 0 else 0.0
    facing_raise = 1.0 if to_call > bb else 0.0
    
    # Is in position (acts last postflop among remaining)
    in_position = 0.0
    if game.state.betting_round != 'preflop':
        last_to_act = None
        for i in range(num_players - 1, -1, -1):
            idx = (game.state.button + 1 + i) % num_players
            p = game.players[idx]
            if not p.has_folded and not p.is_all_in:
                last_to_act = idx
                break
        in_position = 1.0 if last_to_act == player_id else 0.0
    
    # Am I all-in or committed?
    is_all_in = 1.0 if player.is_all_in else 0.0
    commitment = player.total_contributed / (my_stack + player.total_contributed) if (my_stack + player.total_contributed) > 0 else 0
    
    return {
        # Position features
        'position': position_normalized,
        'in_position': in_position,
        'players_behind': players_behind / max(1, num_players - 1),
        
        # Stack features
        'stack_normalized': stack_normalized,
        'spr': spr_normalized,
        'commitment': commitment,
        'is_all_in': is_all_in,
        
        # Pot features
        'pot_odds': pot_odds,
        'to_call_ratio': min(1.0, to_call / (my_stack + 1)),
        
        # Game state
        'round_preflop': 1.0 if round_idx == 0 else 0.0,
        'round_flop': 1.0 if round_idx == 1 else 0.0,
        'round_turn': 1.0 if round_idx == 2 else 0.0,
        'round_river': 1.0 if round_idx == 3 else 0.0,
        'players_in_hand': players_in_hand / 6.0,  # normalise by max table size
        
        # Action context
        'facing_bet': facing_bet,
        'facing_raise': facing_raise,
        
        # Hand strength
        'hand_strength': hand_strength,
    }


def get_state_vector(game, player_id: int, cache: Optional['FeatureCache'] = None) -> np.ndarray:
    """
    Returns state features as a flat vector for neural network input.
    Optimized with JIT-compiled feature extraction.
    
    Args:
        game: PokerGame instance
        player_id: Player index
        cache: Optional FeatureCache for performance (1.5-2× speedup)
        
    Returns:
        17-dimensional numpy array of normalized features
    """
    if cache is not None:
        # Use cached version (faster, reuses static features)
        return cache.get_features(game)
    
    # Fallback: compute features from scratch
    player = game.players[player_id]
    state = game.state
    
    # Extract raw values
    pot = state.pot.total
    to_call = max(0, game.current_bet - player.bet)
    my_stack = player.stack
    bb = state.big_blind
    num_players = len(game.players)
    
    # Position
    position = (player_id - state.button) % num_players
    position_idx = min(5, position)  # Cap at 5 for one-hot
    
    # Street
    rounds = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3, 'showdown': 3}
    street_idx = rounds.get(state.betting_round, 0)
    
    # Active players – normalise by max table size (6) so the network gets an
    # absolute count signal that distinguishes HU (≈0.33) from 6-max (≈1.0).
    active_players = sum(1 for p in game.players if not p.has_folded)
    num_active_norm = active_players / 6.0
    
    # Hand strength
    hand_strength = get_preflop_strength_fast(player.hole_cards)
    
    # Commitment
    total_invested = player.total_contributed
    starting_stack = my_stack + total_invested
    commitment = total_invested / starting_stack if starting_stack > 0 else 0.0
    
    if HAS_NUMBA:
        # Use JIT-compiled feature assembly (2-3× faster)
        pot_odds = compute_pot_odds_jit(float(to_call), float(pot))
        stack_to_pot = compute_stack_to_pot_jit(float(my_stack), float(pot))
        
        return build_feature_vector_jit(
            pot_odds,
            stack_to_pot,
            position_idx,
            street_idx,
            num_active_norm,
            hand_strength,
            commitment
        )
    else:
        # Fallback: numpy implementation
        features = np.zeros(17, dtype=np.float32)
        
        # Pot odds
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0.0
        features[0] = pot_odds
        
        # Stack to pot
        spr = my_stack / pot if pot > 0 else 10.0
        features[1] = min(1.0, spr / 20.0)
        
        # Position one-hot
        if 0 <= position_idx < 6:
            features[2 + position_idx] = 1.0
        
        # Street one-hot
        if 0 <= street_idx < 4:
            features[8 + street_idx] = 1.0
        
        # Other features
        features[12] = num_active_norm
        features[13] = hand_strength
        features[14] = hand_strength  # hand_potential
        features[15] = 0.5  # aggression
        features[16] = commitment
        
        return features


def get_feature_names() -> List[str]:
    """Returns the ordered list of feature names for documentation."""
    return [
        'position', 'in_position', 'players_behind',
        'stack_normalized', 'spr', 'commitment', 'is_all_in',
        'pot_odds', 'to_call_ratio',
        'round_preflop', 'round_flop', 'round_turn', 'round_river',
        'players_in_hand',
        'facing_bet', 'facing_raise',
        'hand_strength',
    ]


def get_action_mask(game, player_id: int) -> List[int]:
    """
    Returns a binary mask indicating which actions are legal.
    Useful for masking illegal actions in policy networks.
    
    Returns a list of 5 values: [fold, check, call, raise, all_in]
    1 = legal, 0 = illegal
    """
    legal_actions = game.get_legal_actions(player_id)
    
    action_types = {'fold': 0, 'check': 0, 'call': 0, 'raise': 0, 'all-in': 0}
    
    for action in legal_actions:
        action_types[action['type']] = 1
    
    return [
        action_types['fold'],
        action_types['check'],
        action_types['call'],
        action_types['raise'],
        action_types['all-in'],
    ]


def get_raise_sizing_info(game, player_id: int) -> Dict[str, float]:
    """
    Returns normalized raise sizing information for AI decision making.
    
    Returns:
        min_raise_ratio: Minimum raise as ratio of pot
        max_raise_ratio: Maximum raise as ratio of pot (all-in)
        can_raise: Whether raising is possible
    """
    player = game.players[player_id]
    legal_actions = game.get_legal_actions(player_id)
    
    pot = max(1, game.state.pot.total)
    
    raise_info = None
    for action in legal_actions:
        if action['type'] == 'raise':
            raise_info = action
            break
    
    if raise_info is None:
        return {
            'min_raise_ratio': 0.0,
            'max_raise_ratio': 0.0,
            'can_raise': 0.0,
        }
    
    min_raise = raise_info.get('min', game.state.big_blind)
    max_raise = raise_info.get('max', player.stack)
    
    return {
        'min_raise_ratio': min(2.0, min_raise / pot),  # Cap at 2x pot
        'max_raise_ratio': min(10.0, max_raise / pot),  # Cap at 10x pot
        'can_raise': 1.0,
    }


class FeatureCache:
    """
    Cache static features per hand to avoid recomputation.
    
    Optimization: Features that don't change during a hand are computed once,
    then only dynamic features are updated per action.
    
    Performance: ~1.5-2× speedup by reducing redundant calculations.
    """
    __slots__ = ['position_norm', 'hand_strength', 'starting_stack', 
                 'num_players', 'player_id', 'features', 'button']
    
    def __init__(self, game, player_id: int):
        """
        Compute static features once at hand start.
        
        Args:
            game: PokerGame instance (at hand start)
            player_id: Player to cache features for
        """
        player = game.players[player_id]
        self.num_players = len(game.players)
        self.player_id = player_id
        self.button = game.state.button
        
        # Static: Position (relative to button)
        position = (player_id - self.button) % self.num_players
        self.position_norm = position / max(1, self.num_players - 1)
        
        # Static: Hand strength (preflop) - use precomputed lookup
        self.hand_strength = get_preflop_strength_fast(player.hole_cards)
        
        # Static: Starting stack
        self.starting_stack = player.stack + player.total_contributed
        
        # Preallocate feature array
        self.features = np.zeros(17, dtype=np.float32)
    
    def get_features(self, game) -> np.ndarray:
        """
        Get current feature vector with cached static values.
        Only recomputes dynamic features that change per action.
        
        Args:
            game: Current game state
        
        Returns:
            Feature vector ready for neural network input
        """
        player = game.players[self.player_id]
        
        # Dynamic: Current game state
        pot = game.state.pot.total
        to_call = max(0, game.current_bet - player.bet)
        my_stack = player.stack
        bb = game.state.big_blind
        
        # Count active players
        players_in_hand = sum(1 for p in game.players if not p.has_folded)
        
        # Betting round
        rounds = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3, 'showdown': 4}
        round_idx = rounds.get(game.state.betting_round, 0)
        
        # Static features (index 0-2)
        self.features[0] = self.position_norm
        
        # In position (dynamic - changes as players fold)
        in_position = 0.0
        if game.state.betting_round != 'preflop':
            last_to_act = None
            for i in range(self.num_players - 1, -1, -1):
                idx = (self.button + 1 + i) % self.num_players
                p = game.players[idx]
                if not p.has_folded and not p.is_all_in:
                    last_to_act = idx
                    break
            in_position = 1.0 if last_to_act == self.player_id else 0.0
        self.features[1] = in_position
        
        # Players behind (dynamic)
        players_behind = 0
        if players_in_hand > 1:
            current_idx = self.player_id
            for i in range(1, self.num_players):
                idx = (current_idx + i) % self.num_players
                p = game.players[idx]
                if not p.has_folded and not p.is_all_in and idx != self.player_id:
                    players_behind += 1
        self.features[2] = players_behind / max(1, self.num_players - 1)
        
        # Stack features (index 3-6)
        self.features[3] = my_stack / self.starting_stack  # Stack normalized
        
        spr = my_stack / pot if pot > 0 else 10.0
        self.features[4] = min(1.0, spr / 20.0)  # SPR
        
        commitment = player.total_contributed / self.starting_stack if self.starting_stack > 0 else 0
        self.features[5] = commitment
        
        self.features[6] = 1.0 if player.is_all_in else 0.0
        
        # Pot features (index 7-8) - use precomputed pot odds table
        # Use lookup table with 5-chip granularity
        tc_idx = min(1000, to_call // 5)
        pot_idx = min(1000, pot // 5)
        pot_odds = POT_ODDS_TABLE[tc_idx, pot_idx]
        self.features[7] = pot_odds
        self.features[8] = min(1.0, to_call / (my_stack + 1))
        
        # Game state (index 9-13)
        self.features[9] = 1.0 if round_idx == 0 else 0.0   # preflop
        self.features[10] = 1.0 if round_idx == 1 else 0.0  # flop
        self.features[11] = 1.0 if round_idx == 2 else 0.0  # turn
        self.features[12] = 1.0 if round_idx == 3 else 0.0  # river
        # Normalise by max table size (6) so HU ≈ 0.33, 6-max ≈ 1.0.
        self.features[13] = players_in_hand / 6.0
        
        # Action context (index 14-15)
        self.features[14] = 1.0 if to_call > 0 else 0.0      # facing bet
        self.features[15] = 1.0 if to_call > bb else 0.0     # facing raise
        
        # Hand strength (index 16) - static
        self.features[16] = self.hand_strength
        
        return self.features
