import pygame
from gui.ui_components import get_action_buttons
from gui.game_controller import ACTION_LABELS
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
        self._draw_policy_panel(layout)
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
        size = layout['card_size']
        for i, (x, y) in enumerate(layout['community']):
            if i < len(cards):
                self._draw_card(cards[i], x, y, size, focus=True)
            else:
                self._draw_card(None, x, y, size)

    def _draw_player_cards(self, layout):
        game = self.controller.game
        cards = game.players[self.controller.human_seat].hole_cards
        size = layout['card_size']
        for i, (x, y) in enumerate(layout['player']):
            self._draw_card(cards[i] if i < len(cards) else None, x, y, size,
                            player=True)

    def _draw_agent_cards(self, layout):
        game = self.controller.game
        cards = game.players[self.controller.agent_seat].hole_cards
        for i, (x, y) in enumerate(layout['agent']):
            # showdown_visible(), not is_hand_over(): the latter means the
            # betting stopped, which happens a street before the chips move.
            if self.controller.showdown_visible():
                self._draw_card(cards[i] if i < len(cards) else None, x, y,
                                layout['card_size'], agent=True)
            else:
                self._draw_card(None, x, y, layout['card_size'], hidden=True,
                                agent=True)

    def _draw_card(self, card, x, y, size, hidden=False, focus=False,
                   player=False, agent=False):
        # Size is passed in rather than recomputed here: it was derived from the
        # window independently of the slot positions, so the two could disagree.
        card_w, card_h = size
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
        # An undealt slot is an outline, not a filled card: drawn solid, the
        # empty turn and river read as two face-down cards the agent holds.
        if card is None and not hidden:
            pygame.draw.rect(self.screen, (46, 62, 52), rect, 2, border_radius=14)
            return
        # Card background
        pygame.draw.rect(self.screen, CARD_COLOR, rect, border_radius=14)
        pygame.draw.rect(self.screen, CARD_BORDER, rect, 2, border_radius=14)
        if hidden:
            pygame.draw.rect(self.screen, (120, 120, 120), rect.inflate(-8, -8), border_radius=10)
            font = pygame.font.Font(FONT_NAME, max(16, card_w // 3))
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
            font = pygame.font.Font(FONT_NAME, max(16, card_w // 3))
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
        # The session is reported in BB/100, the unit every result in this
        # project is quoted in, so what is on screen can be compared with what
        # is in the reports rather than only with itself.
        control = self.controller
        rate = control.bb_per_100
        info = [
            ("Pot", str(game.state.pot.total)),
            ("Your stack", str(game.players[control.human_seat].stack)),
            ("Agent stack", str(game.players[control.agent_seat].stack)),
            ("To call", str(control.to_call)),
            ("Hands", str(control.hands_played)),
            ("Chips", f"{control.total_chips:+d}"),
            ("BB/100", "--" if rate is None else f"{rate:+.1f}"),
        ]
        line_h = max(26, (panel_h - 40) // max(len(info), 1))
        for i, (key, value) in enumerate(info):
            top = panel_y + 20 + i * line_h
            key_surf = self.small_font.render(key, True, (170, 190, 178))
            self.screen.blit(key_surf, key_surf.get_rect(left=panel_x + 20, top=top))
            val_surf = self.small_font.render(value, True, TEXT_COLOR)
            self.screen.blit(val_surf,
                             val_surf.get_rect(right=panel_x + panel_w - 20, top=top))

    def _draw_policy_panel(self, layout):
        """
        What the agent's strategy said at the node it last acted on.

        This is the only part of the table a person cannot work out by looking,
        and for a solved strategy it is the interesting part: the mixes are
        what distinguish an equilibrium approximation from a bot with rules.
        The numbers come from the agent itself through the probe, so what is
        shown is what was sampled from and not a second calculation of it.
        """
        panel_x, panel_y, panel_w, panel_h = layout['policy_panel']
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_COLOR, (0, 0, panel_w, panel_h), border_radius=22)
        self.screen.blit(panel, (panel_x, panel_y))

        title = self.small_font.render("agent policy", True, (170, 190, 178))
        self.screen.blit(title, title.get_rect(left=panel_x + 20, top=panel_y + 16))

        policy = self.controller.agent_policy
        if policy is None:
            note = ("no entry for this node"
                    if self.controller.agent_last_action is not None
                    else "waiting for the agent")
            surf = self.small_font.render(note, True, (150, 150, 150))
            self.screen.blit(surf, surf.get_rect(left=panel_x + 20, top=panel_y + 52))
            return

        chosen = self.controller.agent_last_action
        row_h = (panel_h - 60) // len(ACTION_LABELS)
        bar_left = panel_x + 20
        bar_max = panel_w - 40
        for i, label in enumerate(ACTION_LABELS):
            top = panel_y + 48 + i * row_h
            weight = float(policy[i])
            # The sampled action is marked, because a 30% action being taken is
            # not the same event as a 90% one and the bar alone does not say
            # which was drawn.
            colour = (120, 230, 150) if i == chosen else (90, 120, 105)
            pygame.draw.rect(self.screen, (34, 44, 38),
                             (bar_left, top + 15, bar_max, 10), border_radius=5)
            if weight > 0:
                pygame.draw.rect(self.screen, colour,
                                 (bar_left, top + 15, max(2, int(bar_max * weight)), 10),
                                 border_radius=5)
            text = self.small_font.render(f"{label}  {weight:.2f}", True,
                                          TEXT_COLOR if i == chosen else (170, 180, 174))
            self.screen.blit(text, text.get_rect(left=bar_left, top=top - 2))

    def _draw_action_buttons(self, layout):
        if not self.controller.awaiting_human:
            return
        buttons = get_action_buttons(self.controller, layout)
        for btn in buttons:
            rect = btn['rect']
            x, y, w, h = rect
            color = btn['color']
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
        if pos == self.controller.human_seat:
            x, y, r = layout['player_glow']
            glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120,255,120,90), glow.get_rect())
            self.screen.blit(glow, (x-r, y-r))
        elif pos == self.controller.agent_seat:
            x, y, r = layout['agent_glow']
            glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120,120,255,90), glow.get_rect())
            self.screen.blit(glow, (x-r, y-r))

    def show_feedback(self, text):
        import time
        self.last_feedback = text
        self.last_feedback_time = time.time()

    def _draw_feedback(self, layout):
        # A finished hand holds its result on screen until the next one is
        # dealt, rather than timing out: the person is being asked to act on it
        # (deal again), so it is a prompt and not a notification.
        import time
        holding = self.controller.hand_over
        if self.last_feedback and (holding or time.time() - self.last_feedback_time < 2.0):
            x, y = layout['feedback']
            surf = self.large_font.render(self.last_feedback, True, (255,255,180))
            rect = surf.get_rect(center=(x, y))
            glow = pygame.Surface((rect.width+40, rect.height+30), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255,255,180,80), glow.get_rect())
            self.screen.blit(glow, glow.get_rect(center=(x, y)))
            self.screen.blit(surf, rect)
            if holding:
                hint = self.small_font.render("space or click to deal", True,
                                              (200, 210, 204))
                self.screen.blit(hint, hint.get_rect(center=(x, y + 42)))

    def _draw_debug(self):
        overlay = pygame.Surface((460, 230), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        control = self.controller
        lines = [
            f"to_call: {control.to_call}",
            f"mask: {control.mask}",
            f"current_player: {control.game.state.current_player}",
            # The solver keys off this string; when a lookup misses, this is
            # the first thing to read.
            f"history: {control.history!r}",
            f"opponent: {control.opponent_name}",
        ]
        for i, line in enumerate(lines):
            surf = self.small_font.render(line, True, (255, 255, 0))
            overlay.blit(surf, (20, 18 + i * 40))
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
