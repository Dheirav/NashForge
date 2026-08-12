import pygame
from gui.game_controller import GameController
from gui.renderer import Renderer

WIDTH, HEIGHT = 1000, 700
FPS = 60

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Heads-Up Poker (Balatro Style)")
    clock = pygame.time.Clock()
    controller = GameController()
    renderer = Renderer(screen, controller)
    debug_overlay = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    debug_overlay = not debug_overlay
            controller.handle_event(event)
        controller.update()
        renderer.render(debug_overlay)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()
