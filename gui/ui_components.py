import pygame

BUTTON_LAYOUT = [
    {'label': 'Fold', 'color': (200, 60, 60)},
    {'label': 'Check/Call', 'color': (60, 120, 220)},
    {'label': 'Raise 0.5x', 'color': (220, 180, 60)},
    {'label': 'Raise 1x', 'color': (220, 180, 60)},
    {'label': 'Raise 2x', 'color': (220, 180, 60)},
    {'label': 'All-in', 'color': (120, 60, 180)}
]

BUTTON_WIDTH = 120
BUTTON_HEIGHT = 50
BUTTON_SPACING = 20

# Returns a list of button dicts with rect, label, color, enabled
# controller: GameController

def get_action_buttons(controller):
    mask = controller.last_action_mask
    to_call = controller.last_to_call
    buttons = []
    x0 = 180
    y0 = 630
    for i, btn in enumerate(BUTTON_LAYOUT):
        rect = pygame.Rect(x0 + i * (BUTTON_WIDTH + BUTTON_SPACING), y0, BUTTON_WIDTH, BUTTON_HEIGHT)
        enabled = bool(mask[i]) if mask is not None else False
        label = btn['label']
        color = btn['color']
        # Dynamic label for check/call
        if i == 1:
            label = 'Check' if to_call == 0 else 'Call'
        buttons.append({'rect': rect, 'label': label, 'color': color, 'enabled': enabled})
    return buttons
