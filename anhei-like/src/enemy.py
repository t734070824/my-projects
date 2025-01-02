import pygame
import random

class Enemy:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.health = 50
        self.max_health = 50
        self.speed = 2
        self.detection_range = 200
        self.radius = 15  # Enemy radius for boundary checking
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self.attack_cooldown = 0
        # Screen boundaries (will be set from main.py)
        self.screen_width = 1024
        self.screen_height = 768
        # Experience value
        self.exp_value = 20  # Base exp value
        # Track previous health for damage display
        self.previous_health = self.health
        
    def set_boundaries(self, width, height):
        self.screen_width = width
        self.screen_height = height
        
    def set_level(self, wave_number):
        # Base stats
        base_health = 50
        base_exp = 20
        base_speed = 2
        
        # Calculate stat multipliers
        health_multiplier = 1.0 + (wave_number - 1) * 0.2  # +20% health per wave
        exp_multiplier = 1.0 + (wave_number - 1) * 0.15    # +15% exp per wave
        speed_multiplier = 1.0 + (wave_number - 1) * 0.1   # +10% speed per wave
        
        # Apply bonus every 5 waves
        bonus_multiplier = 1.0 + (wave_number // 5) * 0.2  # +20% bonus every 5 waves
        
        # Set enemy stats
        self.health = int(base_health * health_multiplier * bonus_multiplier)
        self.max_health = self.health
        self.exp_value = int(base_exp * exp_multiplier * bonus_multiplier)
        self.speed = base_speed * speed_multiplier
        
        # Cap speed to prevent enemies from being too fast
        self.speed = min(self.speed, 5.0)
        
    def update(self, player_pos):
        # Move towards player if within detection range
        distance = self.position.distance_to(player_pos)
        if distance < self.detection_range:
            direction = (player_pos - self.position).normalize()
            new_x = self.position.x + direction.x * self.speed
            new_y = self.position.y + direction.y * self.speed
            
            # Check boundaries before moving
            if self.radius <= new_x <= self.screen_width - self.radius:
                self.position.x = new_x
            if self.radius <= new_y <= self.screen_height - self.radius:
                self.position.y = new_y
            
        # Update rect position
        self.rect.center = self.position
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            
    def take_damage(self, amount, ui):
        # Apply damage
        self.previous_health = self.health
        self.health = max(self.health - amount, 0)
        # Add damage number to UI
        ui.add_damage_number(self.position.x, self.position.y - self.radius, amount)

    def draw(self, screen):
        # Draw the enemy as a red circle
        pygame.draw.circle(screen, (255, 0, 0), self.position, self.radius)
