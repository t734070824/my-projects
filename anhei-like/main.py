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
        self.last_spawn_time = time.time()
        
    def should_spawn_wave(self):
        if self.waiting_for_spawn:
            current_time = time.time()
            if current_time - self.spawn_timer >= self.spawn_delay:
                self.waiting_for_spawn = False
                self.last_spawn_time = current_time
                return True
        return False
    
    def start_spawn_timer(self):
        if not self.waiting_for_spawn:  # Only start timer if not already waiting
            print("Starting spawn timer")
            self.spawn_timer = time.time()
            self.waiting_for_spawn = True
        
    def generate_wave(self):
        enemies = []
        if self.current_wave == 1:
            num_enemies = 15  # Start with 15 enemies
        else:
            # Increase enemies by 3 each wave, plus bonus enemies every 5 waves
            base_increase = (self.current_wave - 1) * 3
            bonus_enemies = (self.current_wave // 5) * 2  # Every 5 waves add 2 extra enemies
            num_enemies = 15 + base_increase + bonus_enemies
        
        print(f"Generating wave {self.current_wave} with {num_enemies} enemies")
        
        spawn_margin = 50  # Margin from screen edges
        
        # Calculate spawn positions for enemies
        for i in range(num_enemies):
            # Randomly choose which edge to spawn from
            edge = random.choice(['top', 'bottom', 'left', 'right'])
            
            if edge == 'top':
                x = random.randint(spawn_margin, self.screen_width - spawn_margin)
                y = spawn_margin
            elif edge == 'bottom':
                x = random.randint(spawn_margin, self.screen_width - spawn_margin)
                y = self.screen_height - spawn_margin
            elif edge == 'left':
                x = spawn_margin
                y = random.randint(spawn_margin, self.screen_height - spawn_margin)
            else:  # right
                x = self.screen_width - spawn_margin
                y = random.randint(spawn_margin, self.screen_height - spawn_margin)
            
            enemy = Enemy(x, y)
            enemy.set_boundaries(self.screen_width, self.screen_height)
            # Scale enemy stats with wave number
            enemy.set_level(self.current_wave)
            enemies.append(enemy)
            print(f"Spawned enemy {i+1} at position ({x}, {y})")
            
        self.current_wave += 1
        return enemies

# Initialize game objects
world = World()
player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
player.set_boundaries(SCREEN_WIDTH, SCREEN_HEIGHT)
wave_system = WaveSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
enemies = []  # Start with no enemies
ui = UI()

# Force spawn first wave immediately
enemies = wave_system.generate_wave()

current_state = GameState.PLAYING
keys = {
    "up": False,
    "down": False,
    "left": False,
    "right": False,
}

# Game loop
running = True
last_enemy_check = time.time()

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
            elif event.key == pygame.K_c:
                # Show player attributes
                attributes_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                attributes_overlay.fill((0, 0, 0))
                attributes_overlay.set_alpha(180)
                screen.blit(attributes_overlay, (0, 0))

                attributes_text = [
                    f"Level: {player.level}",
                    f"Health: {player.health:.1f}/{player.max_health}",
                    f"Damage: {player.damage}",
                    f"Speed: {player.speed:.1f}",
                    f"Crit Chance: {player.critical_chance * 100:.1f}%",
                    f"EXP: {player.exp}/{player.exp_to_next_level}",
                    f"Attack: {player.attack_power}",
                    f"Defense: {player.defense}"
                ]

                for i, text in enumerate(attributes_text):
                    text_surface = ui.font.render(text, True, (255, 255, 255))
                    screen.blit(text_surface, (SCREEN_WIDTH//2 - text_surface.get_width()//2, SCREEN_HEIGHT//2 - 100 + i * 30))

                pygame.display.flip()

                # Wait for any key to close
                waiting_for_close = True
                while waiting_for_close:
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            waiting_for_close = False
                        elif event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                continue
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

        # Check if all enemies are defeated (only check every 0.5 seconds)
        current_time = time.time()
        if len(enemies) == 0 and current_time - last_enemy_check >= 0.5:
            last_enemy_check = current_time
            if not wave_system.waiting_for_spawn:
                wave_system.start_spawn_timer()
                print(f"No enemies left, starting spawn timer")
            
        # Spawn new wave if it's time
        if wave_system.should_spawn_wave():
            enemies = wave_system.generate_wave()
            print(f"Spawned new wave with {len(enemies)} enemies")

        # Update enemies
        for enemy in enemies[:]:  # Create a copy of the list to safely remove enemies
            enemy.update(player.position)
            # Remove dead enemies
            if enemy.health <= 0:
                # Give experience to player
                player.gain_exp(enemy.exp_value)
                enemies.remove(enemy)
                print(f"Enemy defeated, gained {enemy.exp_value} exp, {len(enemies)} enemies remaining")

        # Check for collisions
        for enemy in enemies:
            if (enemy.position - player.position).length() < 30:
                player.health -= 0.1  # Continuous damage when touching enemy

        # Game over condition
        if player.health <= 0:
            print("Game Over")
            # Display game over sub-window
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            screen.blit(overlay, (0, 0))

            game_over_text = ui.font.render("Game Over", True, (255, 0, 0))
            restart_text = ui.small_font.render("Press R to Restart", True, (255, 255, 255))

            screen.blit(game_over_text, (SCREEN_WIDTH//2 - game_over_text.get_width()//2, SCREEN_HEIGHT//2 - 50))
            screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 10))

            pygame.display.flip()

            # Wait for restart command
            waiting_for_restart = True
            while waiting_for_restart:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                        # Restart the game logic
                        player.health = player.max_health
                        enemies = wave_system.generate_wave()
                        waiting_for_restart = False
                    elif event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
            continue

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