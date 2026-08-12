# layout.py
"""
Layout logic for Poker GUI. Computes all UI element positions and sizes based on screen size.
"""

def get_layout(WIDTH, HEIGHT):
    """
    Returns a dict with layout zones and coordinates for all UI elements.
    """
    layout = {}
    center_x = WIDTH // 2
    center_y = HEIGHT // 2
    margin = int(WIDTH * 0.06)
    card_w = int(WIDTH * 0.11)
    card_h = int(card_w * 1.375)
    card_spacing = int(card_w * 0.18)
    # Community cards (centered)
    comm_y = center_y - card_h // 2
    comm_total_w = 5 * card_w + 4 * card_spacing
    comm_x0 = center_x - comm_total_w // 2
    layout['community'] = [(comm_x0 + i * (card_w + card_spacing), comm_y) for i in range(5)]
    # Player cards (bottom center)
    player_y = HEIGHT - margin - card_h
    player_total_w = 2 * card_w + card_spacing
    player_x0 = center_x - player_total_w // 2
    layout['player'] = [(player_x0 + i * (card_w + card_spacing), player_y) for i in range(2)]
    # Agent cards (top center)
    agent_y = margin
    agent_total_w = 2 * card_w + card_spacing
    agent_x0 = center_x - agent_total_w // 2
    layout['agent'] = [(agent_x0 + i * (card_w + card_spacing), agent_y) for i in range(2)]
    # Stats panel (right side)
    panel_w = int(WIDTH * 0.22)
    panel_h = int(HEIGHT * 0.38)
    panel_x = WIDTH - panel_w - margin
    panel_y = center_y - panel_h // 2
    layout['stats_panel'] = (panel_x, panel_y, panel_w, panel_h)
    # Action buttons (bottom bar)
    btn_w = int(WIDTH * 0.13)
    btn_h = int(HEIGHT * 0.09)
    btn_spacing = int(WIDTH * 0.025)
    btn_y = HEIGHT - margin // 2 - btn_h
    btn_total_w = 6 * btn_w + 5 * btn_spacing
    btn_x0 = center_x - btn_total_w // 2
    layout['buttons'] = [(btn_x0 + i * (btn_w + btn_spacing), btn_y, btn_w, btn_h) for i in range(6)]
    # Turn indicator (glow radii)
    layout['player_glow'] = (center_x, player_y + card_h // 2, int(card_w * 1.1))
    layout['agent_glow'] = (center_x, agent_y + card_h // 2, int(card_w * 1.1))
    # Feedback text (centered above community)
    layout['feedback'] = (center_x, comm_y - int(card_h * 0.7))
    return layout
