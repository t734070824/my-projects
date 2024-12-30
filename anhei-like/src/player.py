import pygame

class Player:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.image = None
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.attack_range = 50
        self.attack_cooldown = 0
        self.attack_cooldown_max = 10
        
    def update(self):
        # Get keyboard state
        keys = pygame.key.get_pressed()
        
        # Reset direction
        self.direction = pygame.math.Vector2(0, 0)
        
        # WASD movement
        if keys[pygame.K_w]:
            self.direction.y = -1
        if keys[pygame.K_s]:
            self.direction.y = 1
        if keys[pygame.K_a]:
            self.direction.x = -1
        if keys[pygame.K_d]:
            self.direction.x = 1
            
        # Normalize diagonal movement
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()
        
        # Update position based on direction
        self.position += self.direction * self.speed
        
        # Update rect position
        self.rect.center = self.position
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
    def can_attack(self):
        return self.attack_cooldown == 0
        
    def attack(self, enemies):
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
                enemy.health -= 20  # Deal damage
                
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
