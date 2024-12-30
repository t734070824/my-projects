import pygame

class UI:
    def __init__(self):
        self.font = pygame.font.Font(None, 36)
        
    def draw(self, screen):
        # Draw UI elements
        # For now, just draw a simple frame counter
        fps = int(pygame.time.Clock().get_fps())
        fps_text = self.font.render(f'FPS: {fps}', True, (255, 255, 255))
        screen.blit(fps_text, (10, 40))
        
    def draw_inventory(self, screen):
        # This will be implemented later for inventory UI
        pass
