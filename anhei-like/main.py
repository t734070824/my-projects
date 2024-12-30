import pygame
import sys
import math
from src.player import Player
from src.enemy import Enemy
from src.world import World
from src.ui import UI

# Initialize Pygame
pygame.init()

# Set up the display with a larger window for better visibility
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Diablo-like Game")

# Initialize game clock
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
DARK_GREY = (40, 40, 40)
RED = (255, 0, 0)

# Game states
class GameState:
    MENU = 0
    PLAYING = 1
    INVENTORY = 2

# Initialize game objects
world = World()
player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
enemies = [Enemy(100, 100), Enemy(200, 200), Enemy(300, 300)]  # Multiple enemies
ui = UI()

current_state = GameState.PLAYING
target_position = None

def handle_click(pos):
    """Handle mouse click for player movement"""
    global target_position
    target_position = pygame.math.Vector2(pos)
    # Calculate direction for player
    direction = target_position - player.position
    if direction.length() > 0:
        direction = direction.normalize()
        player.direction = direction

# Game loop
running = True
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                handle_click(event.pos)
            elif event.button == 3:  # Right click
                # Basic attack
                for enemy in enemies:
                    if (pygame.math.Vector2(event.pos) - enemy.position).length() < 30:
                        enemy.health -= 10
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                # Toggle inventory
                current_state = GameState.INVENTORY if current_state == GameState.PLAYING else GameState.PLAYING
            elif event.key == pygame.K_ESCAPE:
                if current_state == GameState.INVENTORY:
                    current_state = GameState.PLAYING

    # Update game state
    if current_state == GameState.PLAYING:
        # Update player movement
        if target_position:
            direction = target_position - player.position
            if direction.length() > 5:  # Movement threshold
                direction = direction.normalize()
                player.position += direction * player.speed
            else:
                target_position = None

        # Update enemies
        for enemy in enemies[:]:  # Create a copy of the list to safely remove enemies
            enemy.update(player.position)
            # Remove dead enemies
            if enemy.health <= 0:
                enemies.remove(enemy)

        # Check for collisions
        for enemy in enemies:
            if (enemy.position - player.position).length() < 30:
                player.health -= 0.1  # Continuous damage when touching enemy

    # Draw everything
    screen.fill(DARK_GREY)  # Dark background for dungeon feel
    
    # Draw world (floor, walls, etc.)
    world.draw(screen)
    
    # Draw movement target indicator
    if target_position:
        pygame.draw.circle(screen, (255, 255, 255), target_position, 5, 1)

    # Draw player
    player.draw(screen)
    
    # Draw enemies
    for enemy in enemies:
        enemy.draw(screen)
        # Draw enemy health bars
        health_bar_length = 30
        health_ratio = max(enemy.health / 50, 0)
        pygame.draw.rect(screen, RED, 
                        (enemy.position.x - health_bar_length/2,
                         enemy.position.y - 20,
                         health_bar_length * health_ratio,
                         5))

    # Draw UI elements
    ui.draw(screen)
    
    # Draw player health bar
    health_bar_length = 200
    health_ratio = max(player.health / 100, 0)
    pygame.draw.rect(screen, RED, (10, 10, health_bar_length * health_ratio, 20))

    # Draw inventory if open
    if current_state == GameState.INVENTORY:
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        screen.blit(overlay, (0, 0))
        
        # Inventory grid
        inventory_rect = pygame.Rect(SCREEN_WIDTH//4, SCREEN_HEIGHT//4,
                                   SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        pygame.draw.rect(screen, (70, 70, 70), inventory_rect)
        pygame.draw.rect(screen, (100, 100, 100), inventory_rect, 2)

    # Update display
    pygame.display.flip()

    # Control game speed
    clock.tick(60)

# Quit game
pygame.quit()
sys.exit()