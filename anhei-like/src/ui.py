import pygame
import time

class DamageNumber:
    def __init__(self, damage, x, y):
        self.damage = damage
        self.position = pygame.math.Vector2(x, y)
        self.creation_time = time.time()
        self.lifetime = 1.0  # Show for 1 second
        self.speed = -50  # Float upward

    def is_alive(self):
        return time.time() - self.creation_time < self.lifetime

    def draw(self, screen, font):
        # Calculate alpha based on remaining lifetime
        alpha = int(255 * (1 - (time.time() - self.creation_time) / self.lifetime))
        # Move upward
        self.position.y += self.speed * (1/60)  # Assuming 60 FPS
        # Render text
        text = font.render(str(int(self.damage)), True, (255, 200, 0))
        text.set_alpha(alpha)
        screen.blit(text, self.position)

class UI:
    def __init__(self):
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.damage_numbers = []
        self.total_damage = 0
        self.last_damage_time = time.time()
        self.dps = 0
        self.dps_update_interval = 1.0  # Update DPS every second
        self.last_dps_update = time.time()
        # Fixed bar widths
        self.PLAYER_BAR_WIDTH = 200
        self.ENEMY_BAR_WIDTH = 40

    def add_damage_number(self, damage, x, y):
        self.damage_numbers.append(DamageNumber(damage, x, y))
        self.total_damage += damage
        current_time = time.time()
        
        # Update DPS
        if current_time - self.last_dps_update >= self.dps_update_interval:
            self.dps = self.total_damage / self.dps_update_interval
            self.total_damage = 0
            self.last_dps_update = current_time

    def draw_health_bar(self, screen, x, y, height, current_health, max_health, show_text=True, show_labels=False):
        # Draw background (empty health bar)
        pygame.draw.rect(screen, (80, 0, 0), (x, y, self.PLAYER_BAR_WIDTH, height))
        
        # Calculate health ratio and width
        health_ratio = min(max(current_health / max_health, 0), 1.0)
        health_width = int(self.PLAYER_BAR_WIDTH * health_ratio)
        
        # Draw current health
        if health_ratio > 0.5:
            color = (0, 255, 0)  # Green when health > 50%
        elif health_ratio > 0.25:
            color = (255, 255, 0)  # Yellow when health between 25% and 50%
        else:
            color = (255, 0, 0)  # Red when health < 25%
            
        pygame.draw.rect(screen, color, (x, y, health_width, height))
        
        # Draw border
        pygame.draw.rect(screen, (255, 255, 255), (x, y, self.PLAYER_BAR_WIDTH, height), 1)
        
        # Show health text if requested
        if show_text:
            health_text = f"{int(current_health)}/{int(max_health)}"
            text_surface = self.small_font.render(health_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(x + self.PLAYER_BAR_WIDTH/2, y + height/2))
            screen.blit(text_surface, text_rect)
            
            if show_labels:
                # Draw health text to the right of the bar
                health_text = f"HP: {int(current_health)}/{int(max_health)}"
                health_surface = self.font.render(health_text, True, color)
                screen.blit(health_surface, (x + self.PLAYER_BAR_WIDTH + 10, y + height/2 - health_surface.get_height()/2))

    def draw_enemy_health_bar(self, screen, x, y, height, current_health, max_health):
        # Draw background (empty health bar)
        pygame.draw.rect(screen, (80, 0, 0), (x, y, self.ENEMY_BAR_WIDTH, height))
        
        # Calculate health ratio and width
        health_ratio = min(max(current_health / max_health, 0), 1.0)
        health_width = int(self.ENEMY_BAR_WIDTH * health_ratio)
        
        # Draw current health
        if health_ratio > 0.5:
            color = (0, 255, 0)
        elif health_ratio > 0.25:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)
            
        pygame.draw.rect(screen, color, (x, y, health_width, height))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, self.ENEMY_BAR_WIDTH, height), 1)

    def draw_exp_bar(self, screen, x, y, height, player):
        # Draw background
        pygame.draw.rect(screen, (40, 40, 40), (x, y, self.PLAYER_BAR_WIDTH, height))
        
        # Draw exp progress
        exp_width = int(self.PLAYER_BAR_WIDTH * player.get_exp_percentage())
        pygame.draw.rect(screen, (0, 200, 255), (x, y, exp_width, height))
        
        # Draw border
        pygame.draw.rect(screen, (255, 255, 255), (x, y, self.PLAYER_BAR_WIDTH, height), 1)
        
        # Draw level and exp text
        level_text = f"Level {player.level}"
        exp_text = f"EXP: {player.exp}/{player.exp_to_next_level}"
        
        # Render level text
        level_surface = self.font.render(level_text, True, (255, 255, 255))
        screen.blit(level_surface, (x, y - 25))
        
        # Render exp text
        exp_surface = self.small_font.render(exp_text, True, (0, 200, 255))
        screen.blit(exp_surface, (x + self.PLAYER_BAR_WIDTH - exp_surface.get_width(), y - 20))

    def draw(self, screen, player, enemies):
        # Draw FPS
        fps = int(pygame.time.Clock().get_fps())
        fps_text = self.font.render(f'FPS: {fps}', True, (255, 255, 255))
        screen.blit(fps_text, (10, 40))
        
        # Draw DPS
        dps_text = self.font.render(f'DPS: {int(self.dps)}', True, (255, 200, 0))
        screen.blit(dps_text, (10, 80))
        
        # Draw player health bar
        health_bar_height = 20
        self.draw_health_bar(screen, 10, 10, health_bar_height, player.health, player.max_health, True, True)
        
        # Draw experience bar below health bar
        self.draw_exp_bar(screen, 10, 35, 5, player)
        
        # Draw player stats on the right side
        stats_x = screen.get_width() - 200
        stats_y = 10
        stats_text = [
            f"Damage: {int(player.damage)}",
            f"Speed: {player.speed:.1f}",
            f"Crit: {int(player.critical_chance * 100)}%"
        ]
        
        for i, text in enumerate(stats_text):
            text_surface = self.small_font.render(text, True, (200, 200, 200))
            screen.blit(text_surface, (stats_x, stats_y + i * 20))
        
        # Draw enemy health bars
        for enemy in enemies:
            bar_height = 4
            bar_x = enemy.position.x - self.ENEMY_BAR_WIDTH/2
            bar_y = enemy.position.y - enemy.radius - 10
            
            self.draw_enemy_health_bar(screen, bar_x, bar_y, bar_height, enemy.health, enemy.max_health)
            
            # Draw enemy health text above health bar
            health_text = f"{int(enemy.health)}/{int(enemy.max_health)}"
            text_surface = self.small_font.render(health_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(enemy.position.x, bar_y - 5))
            screen.blit(text_surface, text_rect)
        
        # Update and draw damage numbers
        current_numbers = []
        for damage_number in self.damage_numbers:
            if damage_number.is_alive():
                damage_number.draw(screen, self.small_font)
                current_numbers.append(damage_number)
        self.damage_numbers = current_numbers
        
    def draw_inventory(self, screen):
        # This will be implemented later for inventory UI
        pass
