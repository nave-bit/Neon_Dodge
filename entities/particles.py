"""
entities/particles.py
─────────────────────
Effets visuels légers :
  - Particle   : éclat de particule physique
  - FloatText  : texte flottant qui monte et disparaît ("+1 VIE !", "BOOM !"…)
"""

import pygame, math, random


class Particle:
    """Particule physique émise lors d'une explosion ou d'une collecte."""

    def __init__(self, x: float, y: float, color: tuple, speed_mult: float = 1.0):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1, 5) * speed_mult
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life  = random.randint(18, 45)
        self.maxl  = self.life
        self.color = color
        self.r     = random.randint(2, 5)

    def update(self) -> None:
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.1      # gravité légère
        self.life -= 1

    def draw(self, surf) -> None:
        a   = self.life / self.maxl
        col = tuple(int(c * a) for c in self.color)
        r   = max(1, int(self.r * a))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)

    @property
    def alive(self) -> bool:
        return self.life > 0


class FloatText:
    """Texte flottant qui monte et s'estompe (feedback au joueur)."""

    def __init__(self, x: float, y: float, text: str, color: tuple):
        self.x     = float(x)
        self.y     = float(y)
        self.text  = text
        self.color = color
        self.life  = 70

    def update(self) -> None:
        self.y    -= 1.1
        self.life -= 1

    def draw(self, surf) -> None:
        font = pygame.font.SysFont("consolas", 18)
        a    = self.life / 70
        col  = tuple(int(c * a) for c in self.color)
        s    = font.render(self.text, True, col)
        surf.blit(s, (int(self.x) - s.get_width() // 2, int(self.y)))

    @property
    def alive(self) -> bool:
        return self.life > 0
