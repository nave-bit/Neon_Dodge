"""
entities/pickup.py
──────────────────
Items collectables qui tombent sur le terrain pendant la partie.
Chaque item donne un bonus immédiat au joueur (ou à l'IA) quand collecté.
"""

import pygame, math, random
from core.constants import MAGENTA, YELLOW, CYAN, ORANGE, GREEN, PURPLE, WHITE

# ── Types d'items ─────────────────────────────────────────────────────────────
# id : (couleur, label affiché)
PU_TYPES = {
    "life":   (MAGENTA, "+VIE"),
    "slow":   (YELLOW,  "SLOW"),
    "shield": (CYAN,    "SHIELD"),
    "bomb":   (ORANGE,  "BOMB"),
    "magnet": (GREEN,   "MAGNET"),
    "xp":     (PURPLE,  "+XP"),
    "coin5":  (YELLOW,  "+5¢"),
    "coin15": (GREEN,   "+15¢"),
    "energy": (CYAN,    "+ÉNERGIE"),
}


class PUItem:
    """Item collectif tombant du haut de l'écran."""

    def __init__(self):
        self.kind          = random.choice(list(PU_TYPES.keys()))
        self.color, self.label = PU_TYPES[self.kind]
        self.r     = 16
        self.x     = float(random.randint(30, 930))   # W - 30
        self.y     = float(-30)
        self.vy    = 1.6
        self.pulse = random.uniform(0, math.tau)

    def update(self) -> None:
        self.y     += self.vy
        self.pulse += 0.11

    def draw(self, surf, tick: int) -> None:
        ix, iy = int(self.x), int(self.y)
        glow_r = self.r + 3 + int(3 * math.sin(self.pulse))
        pygame.draw.circle(surf, tuple(c // 5 for c in self.color), (ix, iy), glow_r)
        pygame.draw.circle(surf, self.color, (ix, iy), self.r, 2)
        font = pygame.font.SysFont("consolas", 14)
        s    = font.render(self.label, True, self.color)
        surf.blit(s, (ix - s.get_width() // 2, iy - 7))

    def collides(self, px: float, py: float, pr: int) -> bool:
        return math.hypot(px - self.x, py - self.y) < self.r + pr

    @property
    def off_screen(self) -> bool:
        return self.y > 740   # H + 40
