from engine.game import PokerGame
from engine.features import get_state_vector, get_abstract_action_mask
from training.policy_network import PolicyNetwork
import numpy as np
import os

class GameController:
    def __init__(self):
        self.STARTING_STACK = 1000
        self.SMALL_BLIND = 5
        self.BIG_BLIND = 10
        self.ARCH = [17, 64, 32, 6]
        self.AGENT_GENOME_PATH = 'hall_of_fame/ppo_hu/p12_m7_h375_s0.06_g50_b4_champion.npy'
        self.agent_net = self._load_agent()
        self.reset_game()
        self.selected_action = None
        self.awaiting_human = False
        self.last_action_mask = None
        self.last_to_call = 0
        self.last_current_player = 0

    def _load_agent(self):
        agent_genome = np.load(self.AGENT_GENOME_PATH)
        from training.config import NetworkConfig
        net = PolicyNetwork(NetworkConfig(input_size=self.ARCH[0], hidden_sizes=self.ARCH[1:-1], output_size=self.ARCH[-1]))
        net.set_weights_from_genome(agent_genome)
        return net

    def reset_game(self):
        self.game = PokerGame(player_stacks=[self.STARTING_STACK, self.STARTING_STACK],
                              small_blind=self.SMALL_BLIND, big_blind=self.BIG_BLIND, ante=0, seed=None)
        self.human_pos = 0
        self.agent_pos = 1
        self.hand = 1
        self.awaiting_human = False
        self.selected_action = None
        self.last_action_mask = None
        self.last_to_call = 0
        self.last_current_player = 0

    def update(self):
        game = self.game
        if all(p.stack > 0 for p in game.players):
            if game.is_hand_over():
                self.hand += 1
                game.reset_hand()
            pos = game.state.current_player
            self.last_current_player = pos
            if pos is None or game.state.players[pos].has_folded or game.state.players[pos].is_all_in:
                return
            features = np.array(get_state_vector(game, pos), dtype=np.float32)
            mask = get_abstract_action_mask(game, pos)
            self.last_action_mask = mask
            to_call = game.current_bet - game.players[pos].bet
            self.last_to_call = to_call
            has_legal_action = np.any(mask)
            if pos == self.human_pos:
                if has_legal_action:
                    self.awaiting_human = True
                else:
                    # No legal actions for human, auto-advance (fold by default)
                    self.awaiting_human = False
                    self.apply_action(0)  # 0 = fold (safe fallback)
            else:
                if has_legal_action:
                    action_idx = self.agent_net.select_action(features, mask, np.random.default_rng())
                    self.apply_action(action_idx)
                else:
                    # No legal actions for agent, auto-advance (fold by default)
                    self.apply_action(0)

    def handle_event(self, event):
        import pygame
        if self.awaiting_human and event.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(event, 'pos'):
                from gui.ui_components import get_action_buttons
                buttons = get_action_buttons(self)
                for idx, btn in enumerate(buttons):
                    if btn['rect'].collidepoint(event.pos) and btn['enabled']:
                        self.apply_action(idx)
                        break

    def apply_action(self, action_idx):
        game = self.game
        pos = game.state.current_player
        mask = self.last_action_mask
        ACTION_NAMES = ['fold', 'check/call', 'raise 0.5x', 'raise 1x', 'raise 2x', 'all-in']
        legal_actions = game.get_legal_actions(pos)
        def is_action_match(act, action_type):
            if action_type == 'check/call':
                return act['type'] in ('check', 'call')
            elif action_type in ('raise 0.5x', 'raise 1x', 'raise 2x'):
                return act['type'] == 'raise'
            elif action_type == 'all-in':
                return act['type'] == 'all-in'
            else:
                return act['type'] == action_type
        action_type = ACTION_NAMES[action_idx]
        chosen = None
        for act in legal_actions:
            if is_action_match(act, action_type):
                from engine.actions import Action
                pot = game.state.pot.total
                if action_type == 'raise 0.5x':
                    amount = max(game.state.big_blind, int(pot * 0.5))
                    chosen = Action('raise', amount)
                elif action_type == 'raise 1x':
                    amount = max(game.state.big_blind, pot)
                    chosen = Action('raise', amount)
                elif action_type == 'raise 2x':
                    amount = max(game.state.big_blind, pot * 2)
                    chosen = Action('raise', amount)
                elif action_type == 'all-in':
                    amount = act.get('amount', game.players[pos].stack)
                    chosen = Action('all-in', amount)
                else:
                    chosen = Action(act['type'])
                break
        if chosen is None:
            from engine.actions import Action
            chosen = Action('fold')
        game.apply_action(pos, chosen)
        self.awaiting_human = False
