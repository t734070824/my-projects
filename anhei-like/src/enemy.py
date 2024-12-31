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
        
    def set_boundaries(self, width, height):
        self.screen_width = width
        self.screen_height = height
        
    def set_level(self, wave_number):
        # Scale enemy stats with wave number
        self.health = 50 + (wave_number - 1) * 10
        self.max_health = self.health
        self.exp_value = 20 + (wave_number - 1) * 5  # More exp for higher waves
        
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
            
    def draw(self, screen):
        # Draw the enemy as a red circle
        pygame.draw.circle(screen, (255, 0, 0), self.position, self.radius)
