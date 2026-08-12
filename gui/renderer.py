import pygame
from gui.ui_components import get_action_buttons
from gui.layout import get_layout
import os

BG_COLOR = (18, 44, 30)
PANEL_COLOR = (20, 28, 22, 220)
TEXT_COLOR = (240, 240, 240)
CARD_COLOR = (40, 90, 60)
CARD_BORDER = (220, 220, 220)
GLOW_COLOR = (120, 255, 120, 120)
SHADOW_COLOR = (0, 0, 0, 90)
BUTTON_COLORS = {
    'fold': (200, 60, 60),
    'call': (60, 120, 220),
    'check': (60, 120, 220),
    'raise': (220, 180, 60),
    'all-in': (120, 60, 180),
    'disabled': (80, 80, 80)
}

FONT_NAME = 'freesansbold.ttf'

class Renderer:
    def __init__(self, screen, controller):
        self.screen = screen
        self.controller = controller
        self.font = pygame.font.Font(FONT_NAME, 28)
        self.small_font = pygame.font.Font(FONT_NAME, 20)
        self.large_font = pygame.font.Font(FONT_NAME, 44)
        # Load card images once
        self.card_images = self._load_card_images()
        self.last_feedback = None
        self.last_feedback_time = 0

    def _load_card_images(self):
        card_images = {}
        suits = ['S', 'H', 'D', 'C']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        for suit in suits:
            for rank in ranks:
                fname = f"{suit}{rank}.png"
                path = os.path.join(os.path.dirname(__file__), 'assests', fname)
                if os.path.exists(path):
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (80, 110))
                    card_images[f"{suit}{rank}"] = img
        # Card back image (optional): fallback to gray
        card_images['BACK'] = None
        return card_images

    def render(self, debug_overlay=False):
        WIDTH, HEIGHT = self.screen.get_size()
        layout = get_layout(WIDTH, HEIGHT)
        self._draw_background(WIDTH, HEIGHT)
        self._draw_turn_indicator(layout)
        self._draw_community_cards(layout)
        self._draw_player_cards(layout)
        self._draw_agent_cards(layout)
        self._draw_info_panel(layout)
        self._draw_action_buttons(layout)
        self._draw_feedback(layout)
        if debug_overlay:
            self._draw_debug()

    def _draw_background(self, WIDTH, HEIGHT):
        # Radial gradient background
        bg = pygame.Surface((WIDTH, HEIGHT))
        for i in range(HEIGHT):
            color = [int(BG_COLOR[0] * (1 - i/HEIGHT) + 10 * (i/HEIGHT)),
                     int(BG_COLOR[1] * (1 - i/HEIGHT) + 20 * (i/HEIGHT)),
                     int(BG_COLOR[2] * (1 - i/HEIGHT) + 10 * (i/HEIGHT))]
            pygame.draw.line(bg, color, (0, i), (WIDTH, i))
        self.screen.blit(bg, (0, 0))

    def _draw_community_cards(self, layout):
        game = self.controller.game
        cards = game.state.community_cards
        for i, (x, y) in enumerate(layout['community']):
            if i < len(cards):
                self._draw_card(cards[i], x, y, focus=True)
            else:
                self._draw_card(None, x, y, focus=True)

    def _draw_player_cards(self, layout):
        game = self.controller.game
        cards = game.players[0].hole_cards
        for i, (x, y) in enumerate(layout['player']):
            self._draw_card(cards[i] if i < len(cards) else None, x, y, player=True)

    def _draw_agent_cards(self, layout):
        game = self.controller.game
        cards = game.players[1].hole_cards
        for i, (x, y) in enumerate(layout['agent']):
            if game.is_hand_over():
                self._draw_card(cards[i] if i < len(cards) else None, x, y, agent=True)
            else:
                self._draw_card(None, x, y, hidden=True, agent=True)

    def _draw_card(self, card, x, y, hidden=False, focus=False, player=False, agent=False):
        # Card size from layout
        card_w = int(self.screen.get_width() * 0.11)
        card_h = int(card_w * 1.375)
        rect = pygame.Rect(x, y, card_w, card_h)
        # Shadow
        shadow = pygame.Surface((card_w+12, card_h+12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, SHADOW_COLOR, shadow.get_rect())
        self.screen.blit(shadow, (x-6, y+8))
        # Glow for focus/turn
        if focus or player or agent:
            glow = pygame.Surface((card_w+24, card_h+24), pygame.SRCALPHA)
            glow_color = (180, 255, 180, 80) if player else (180, 180, 255, 60) if agent else (255,255,180,40)
            pygame.draw.ellipse(glow, glow_color, glow.get_rect())
            self.screen.blit(glow, (x-12, y-12))
        # Card background
        pygame.draw.rect(self.screen, CARD_COLOR, rect, border_radius=14)
        pygame.draw.rect(self.screen, CARD_BORDER, rect, 2, border_radius=14)
        if card is None and not hidden:
            return
        if hidden:
            pygame.draw.rect(self.screen, (120, 120, 120), rect.inflate(-8, -8), border_radius=10)
            font = pygame.font.Font(FONT_NAME, 36)
            text_surf = font.render('??', True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
            return
        key = self._card_to_key(card)
        img = self.card_images.get(key)
        if img:
            img = pygame.transform.smoothscale(img, (card_w, card_h))
            self.screen.blit(img, (x, y))
        else:
            font = pygame.font.Font(FONT_NAME, 36)
            text_surf = font.render(str(card), True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

    def _draw_info_panel(self, layout):
        game = self.controller.game
        panel_x, panel_y, panel_w, panel_h = layout['stats_panel']
        # Panel background
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_COLOR, (0, 0, panel_w, panel_h), border_radius=22)
        # Panel shadow
        shadow = pygame.Surface((panel_w+16, panel_h+16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, SHADOW_COLOR, shadow.get_rect())
        self.screen.blit(shadow, (panel_x-8, panel_y+8))
        self.screen.blit(panel, (panel_x, panel_y))
        # Stats text
        pot = game.state.pot.total
        player_stack = game.players[0].stack
        agent_stack = game.players[1].stack
        to_call = self.controller.last_to_call
        info = [
            f"Pot: {pot}",
            f"Your stack: {player_stack}",
            f"Agent stack: {agent_stack}",
            f"To call: {to_call}"
        ]
        for i, line in enumerate(info):
            surf = self.font.render(line, True, TEXT_COLOR)
            surf_rect = surf.get_rect(left=panel_x+24, top=panel_y+28 + i*58)
            self.screen.blit(surf, surf_rect)

    def _draw_action_buttons(self, layout):
        if not self.controller.awaiting_human:
            return
        buttons = get_action_buttons(self.controller)
        for i, btn in enumerate(buttons):
            x, y, w, h = layout['buttons'][i]
            rect = pygame.Rect(x, y, w, h)
            color = btn['color'] if btn['enabled'] else BUTTON_COLORS['disabled']
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            draw_color = tuple(min(255, c+30) for c in color) if is_hover and btn['enabled'] else color
            # Shadow
            shadow = pygame.Surface((w+8, h+8), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, SHADOW_COLOR, shadow.get_rect())
            self.screen.blit(shadow, (x-4, y+6))
            # Button
            pygame.draw.rect(self.screen, draw_color, rect, border_radius=16)
            pygame.draw.rect(self.screen, (255,255,255,60), rect, 2, border_radius=16)
            label_surf = self.font.render(btn['label'], True, TEXT_COLOR)
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

    def _draw_turn_indicator(self, layout):
        # Glow around player or agent area depending on turn
        game = self.controller.game
        pos = game.state.current_player
        if pos == 0:
            x, y, r = layout['player_glow']
            glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120,255,120,90), glow.get_rect())
            self.screen.blit(glow, (x-r, y-r))
        elif pos == 1:
            x, y, r = layout['agent_glow']
            glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120,120,255,90), glow.get_rect())
            self.screen.blit(glow, (x-r, y-r))

    def show_feedback(self, text):
        import time
        self.last_feedback = text
        self.last_feedback_time = time.time()

    def _draw_feedback(self, layout):
        import time
        if self.last_feedback and time.time() - self.last_feedback_time < 2.0:
            x, y = layout['feedback']
            surf = self.large_font.render(self.last_feedback, True, (255,255,180))
            rect = surf.get_rect(center=(x, y))
            glow = pygame.Surface((rect.width+40, rect.height+30), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255,255,180,80), glow.get_rect())
            self.screen.blit(glow, glow.get_rect(center=(x, y)))
            self.screen.blit(surf, rect)

    def _draw_debug(self):
        overlay = pygame.Surface((400, 180), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        lines = [
            f"to_call: {self.controller.last_to_call}",
            f"action_mask: {self.controller.last_action_mask}",
            f"current_player: {self.controller.last_current_player}"
        ]
        for i, line in enumerate(lines):
            surf = self.small_font.render(line, True, (255, 255, 0))
            overlay.blit(surf, (20, 20 + i * 40))
        self.screen.blit(overlay, (60, 480))

    def _card_to_key(self, card):
        # Accepts Card object or string like 'Ah', '10d', etc.
        if hasattr(card, 'rank') and hasattr(card, 'suit'):
            rank = str(card.rank)
            suit = str(card.suit)
        else:
            s = str(card)
            if len(s) == 3:  # '10h'
                rank, suit = s[:2], s[2]
            else:
                rank, suit = s[0], s[1]
        # Normalize rank and suit for filenames
        if rank == 'T':
            rank = '10'
        suit_map = {'h': 'H', 'd': 'D', 'c': 'C', 's': 'S',
                    'H': 'H', 'D': 'D', 'C': 'C', 'S': 'S'}
        suit = suit_map.get(suit, suit.upper())
        return f"{suit}{rank}"
