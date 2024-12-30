import pygame
import random

class World:
    def __init__(self):
        self.tile_size = 32
        self.width = 32  # tiles
        self.height = 24  # tiles
        self.floor_tiles = []
        self.generate_floor()
        
    def generate_floor(self):
        # Generate random floor tiles for a dungeon-like appearance
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Random variation in floor darkness
                darkness = random.randint(30, 50)
                row.append(darkness)
            self.floor_tiles.append(row)
    
    def draw(self, screen):
        # Draw floor tiles
        for y in range(self.height):
            for x in range(self.width):
                darkness = self.floor_tiles[y][x]
                color = (darkness, darkness, darkness)
                rect = pygame.Rect(x * self.tile_size, y * self.tile_size,
                                 self.tile_size, self.tile_size)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)  # Grid lines
