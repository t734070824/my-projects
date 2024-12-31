import pygame
import math

class Player:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.health_multiplier = 1.0
        self.image = None
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.attack_range = 50
        self.attack_cooldown = 0
        self.attack_cooldown_max = 10
        self.damage = 20
        self.critical_chance = 0.2
        self.critical_multiplier = 2.0
        
        # Level system
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 100
        
        # Base stats
        self.base_damage = 20
        self.base_health = 100
        self.base_speed = 5
        self.base_crit_chance = 0.2
        
        # Screen boundaries (will be set from main.py)
        self.screen_width = 1024
        self.screen_height = 768
        self.radius = 15  # Player radius for boundary checking
        
    def set_boundaries(self, width, height):
        self.screen_width = width
        self.screen_height = height
        
    def gain_exp(self, amount):
        self.exp += amount
        while self.exp >= self.exp_to_next_level:
            self.level_up()
    
    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next_level
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        
        # Improve stats
        self.base_damage += 5
        self.health_multiplier += 0.2
        self.base_speed += 0.2
        self.base_crit_chance += 0.01
        
        # Update current stats
        self.damage = self.base_damage
        old_health_ratio = self.health / self.max_health
        self.max_health = int(self.base_health * self.health_multiplier)
        self.health = int(self.max_health * old_health_ratio)
        self.speed = self.base_speed
        self.critical_chance = min(0.5, self.base_crit_chance)
        
        # Heal 20% of max health on level up
        heal_amount = self.max_health * 0.2
        self.health = min(self.max_health, self.health + heal_amount)
        
    def get_exp_percentage(self):
        return self.exp / self.exp_to_next_level
        
    def update(self):
        # Get keyboard state for WASD movement
        keys = pygame.key.get_pressed()
        
        # Handle movement
        dx = 0
        dy = 0
        
        if keys[pygame.K_w]:
            dy = -self.speed
        if keys[pygame.K_s]:
            dy = self.speed
        if keys[pygame.K_a]:
            dx = -self.speed
        if keys[pygame.K_d]:
            dx = self.speed
            
        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.707  # 1/sqrt(2)
            dy *= 0.707
            
        # Calculate new position
        new_x = self.position.x + dx
        new_y = self.position.y + dy
        
        # Check boundaries
        if self.radius <= new_x <= self.screen_width - self.radius:
            self.position.x = new_x
        if self.radius <= new_y <= self.screen_height - self.radius:
            self.position.y = new_y
        
        # Update rect position
        self.rect.center = self.position
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
    def can_attack(self):
        return self.attack_cooldown == 0
        
    def calculate_damage(self):
        # Check for critical hit
        if pygame.time.get_ticks() % 100 < self.critical_chance * 100:
            return self.damage * self.critical_multiplier
        return self.damage
        
    def attack(self, enemies, ui):
        if not self.can_attack():
            return
            
        # Get mouse position for attack direction
        mouse_pos = pygame.mouse.get_pos()
        mouse_vector = pygame.math.Vector2(mouse_pos)
        
        # Check each enemy
        for enemy in enemies:
            # Calculate distance to enemy
            distance = (enemy.position - self.position).length()
            if distance <= self.attack_range:
                # Calculate damage
                damage = self.calculate_damage()
                enemy.health -= damage
                # Add damage number
                ui.add_damage_number(damage, enemy.position.x, enemy.position.y)
                
        # Set attack cooldown
        self.attack_cooldown = self.attack_cooldown_max
        
    def draw(self, screen):
        # Draw the player as a blue circle
        pygame.draw.circle(screen, (0, 0, 255), self.position, 15)
        
        # Draw attack range when attacking
        if self.attack_cooldown > 0:
            # Draw semi-transparent attack range
            attack_surface = pygame.Surface((self.attack_range * 2, self.attack_range * 2), pygame.SRCALPHA)
            pygame.draw.circle(attack_surface, (255, 255, 255, 50), (self.attack_range, self.attack_range), self.attack_range)
            screen.blit(attack_surface, (self.position.x - self.attack_range, self.position.y - self.attack_range))
