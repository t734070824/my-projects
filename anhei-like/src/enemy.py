import pygame
import random

class Enemy:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.health = 50
        self.max_health = 50
        self.speed = 2
        self.detection_range = 200
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.attack_cooldown = 0
        
    def update(self, player_pos):
        # Move towards player if within detection range
        distance = self.position.distance_to(player_pos)
        if distance < self.detection_range:
            direction = (player_pos - self.position).normalize()
            self.position += direction * self.speed
            
        # Update rect position
        self.rect.center = self.position
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            
    def draw(self, screen):
        # Draw the enemy as a red circle
        pygame.draw.circle(screen, (255, 0, 0), self.position, 15)
