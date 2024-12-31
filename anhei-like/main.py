import pygame
import sys
import math
import random
import time
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

# Wave system
class WaveSystem:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.current_wave = 1
        self.enemies_per_wave = 3
        self.spawn_timer = 0
        self.spawn_delay = 3  # 3 seconds delay between waves
        self.waiting_for_spawn = False
        
    def should_spawn_wave(self):
        if self.waiting_for_spawn:
            current_time = time.time()
            if current_time - self.spawn_timer >= self.spawn_delay:
                self.waiting_for_spawn = False
                return True
        return False
    
    def start_spawn_timer(self):
        self.spawn_timer = time.time()
        self.waiting_for_spawn = True
        
    def generate_wave(self):
        enemies = []
        num_enemies = self.enemies_per_wave + (self.current_wave - 1)
        
        for _ in range(num_enemies):
            # Randomly choose spawn side (top, bottom, left, right)
            side = random.choice(['top', 'bottom', 'left', 'right'])
            
            if side == 'top':
                x = random.randint(0, self.screen_width)
                y = -30
            elif side == 'bottom':
                x = random.randint(0, self.screen_width)
                y = self.screen_height + 30
            elif side == 'left':
                x = -30
                y = random.randint(0, self.screen_height)
            else:  # right
                x = self.screen_width + 30
                y = random.randint(0, self.screen_height)
                
            enemy = Enemy(x, y)
            # Increase enemy stats with each wave
            enemy.health = 50 + (self.current_wave - 1) * 10
            enemy.max_health = enemy.health
            enemies.append(enemy)
            
        self.current_wave += 1
        return enemies

# Initialize game objects
world = World()
player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
player.set_boundaries(SCREEN_WIDTH, SCREEN_HEIGHT)  # Set screen boundaries
wave_system = WaveSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
enemies = wave_system.generate_wave()  # Initial wave
ui = UI()

current_state = GameState.PLAYING
keys = {
    "up": False,
    "down": False,
    "left": False,
    "right": False,
}

# Game loop
running = True
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                player.attack(enemies, ui)  # Attack on left click
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                keys["up"] = True
            elif event.key == pygame.K_s:
                keys["down"] = True
            elif event.key == pygame.K_a:
                keys["left"] = True
            elif event.key == pygame.K_d:
                keys["right"] = True
            elif event.key == pygame.K_i:
                # Toggle inventory
                current_state = GameState.INVENTORY if current_state == GameState.PLAYING else GameState.PLAYING
            elif event.key == pygame.K_ESCAPE:
                if current_state == GameState.INVENTORY:
                    current_state = GameState.PLAYING
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                keys["up"] = False
            elif event.key == pygame.K_s:
                keys["down"] = False
            elif event.key == pygame.K_a:
                keys["left"] = False
            elif event.key == pygame.K_d:
                keys["right"] = False

    # Update game state
    if current_state == GameState.PLAYING:
        # Update player
        player.update()

        # Check if all enemies are defeated
        if len(enemies) == 0 and not wave_system.waiting_for_spawn:
            print("Starting spawn timer")  # Debug print
            wave_system.start_spawn_timer()
            
        # Spawn new wave if it's time
        if wave_system.should_spawn_wave():
            print(f"Spawning wave {wave_system.current_wave}")  # Debug print
            enemies = wave_system.generate_wave()
            print(f"Spawned {len(enemies)} enemies")  # Debug print

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
    ui.draw(screen, player, enemies)
    
    # Draw player health bar
    health_bar_length = 200
    health_ratio = max(player.health / 100, 0)
    pygame.draw.rect(screen, RED, (10, 10, health_bar_length * health_ratio, 20))

    # Draw wave information
    wave_text = ui.font.render(f'Wave: {wave_system.current_wave}', True, (255, 255, 255))
    screen.blit(wave_text, (SCREEN_WIDTH - 150, 10))
    
    # Draw "Next Wave" message when waiting
    if wave_system.waiting_for_spawn:
        time_left = max(0, wave_system.spawn_delay - (time.time() - wave_system.spawn_timer))
        next_wave_text = ui.font.render(f'Next Wave in: {int(time_left)}', True, (255, 200, 0))
        text_rect = next_wave_text.get_rect(center=(SCREEN_WIDTH/2, 50))
        screen.blit(next_wave_text, text_rect)

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