"""
systems/hud.py
──────────────
Tout ce qui est dessiné en dehors du gameplay :
  - Bandeau HUD (score, vies, XP, buffs actifs)
  - Fonds de jeu animés (space, city, lava, ice, void)
  - Helpers visuels partagés (glow, neon_circ, draw_bar, cx)
"""

import pygame, math, random
from core.constants import (
    W, H, HUD_H, BG_COLORS, BG_GRID_COLORS, BACKGROUNDS,
    CYAN, MAGENTA, YELLOW, GREEN, PURPLE, PINK, WHITE, GREY, RED,
    POWERUP_DUR, POWERUP_COL,
)

# Étoiles (générées une seule fois)
STARS = [(random.randint(0, W), random.randint(0, H), random.randint(1, 3))
         for _ in range(150)]


# ═══════════════════════════════════════════════════════════════════
#  HELPERS VISUELS
# ═══════════════════════════════════════════════════════════════════

def cx(text: str, font) -> int:
    """Retourne le x pour centrer un texte horizontalement."""
    return W // 2 - font.size(text)[0] // 2


def glow(surf, text: str, font, color: tuple, pos: tuple, r: int = 3) -> None:
    """Dessine un texte avec halo néon."""
    gc = tuple(min(c, 90) for c in color)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx or dy:
                surf.blit(font.render(text, True, gc), (pos[0] + dx, pos[1] + dy))
    surf.blit(font.render(text, True, color), pos)


def neon_circ(surf, col: tuple, pos: tuple, r: int, w: int = 2) -> None:
    """Cercle avec halo sombre autour."""
    d = tuple(c // 4 for c in col)
    pygame.draw.circle(surf, d, pos, r + 4)
    pygame.draw.circle(surf, d, pos, r + 2)
    pygame.draw.circle(surf, col, pos, r, w)


def draw_bar(surf, rect: pygame.Rect, val: float, mx: float,
             fg: tuple, bg: tuple = (15, 15, 35), text: str = "") -> None:
    """Barre de progression néon avec reflet."""
    F_XSM = pygame.font.SysFont("consolas", 14)
    pygame.draw.rect(surf, bg, rect, border_radius=4)
    if mx > 0:
        w2 = max(0, int(rect.w * val / mx))
        pygame.draw.rect(surf, tuple(c // 2 for c in fg),
                         pygame.Rect(rect.x, rect.y, w2, rect.h), border_radius=4)
        pygame.draw.rect(surf, fg,
                         pygame.Rect(rect.x, rect.y, w2, rect.h // 2), border_radius=4)
    pygame.draw.rect(surf, tuple(c // 2 for c in fg), rect, 1, border_radius=4)
    if text:
        s = F_XSM.render(text, True, WHITE)
        surf.blit(s, (rect.centerx - s.get_width() // 2,
                      rect.centery - s.get_height() // 2))


# ═══════════════════════════════════════════════════════════════════
#  FONDS DE JEU
# ═══════════════════════════════════════════════════════════════════

def draw_bg(surf, tick: int, bg_name: str) -> None:
    """Dessine le fond animé correspondant au thème choisi."""
    col1, col2 = BG_GRID_COLORS[bg_name]
    vx, vy = W // 2, H // 2 - 20

    # Lignes de perspective
    for i in range(0, W + 90, 90):
        pygame.draw.line(surf, col1, (vx, vy), (i, H))
    for r in range(10):
        t  = ((r / 10) + (tick * 2 / 400)) % 1
        y  = int(vy + (H - vy) * t)
        x0 = int(vx + (0 - vx) * t)
        x1 = int(vx + (W - vx) * t)
        c  = tuple(int(col1[i] + (col2[i] - col1[i]) * t) for i in range(3))
        pygame.draw.line(surf, c, (x0, y), (x1, y))

    if bg_name == "space":
        for sx, sy, sr in STARS:
            b = 80 + int(65 * math.sin(tick * 0.033 + sx * 0.01))
            pygame.draw.circle(surf, (b, b, b), (sx, sy), sr)

    elif bg_name == "city":
        for i in range(0, W, 80):
            h2 = 30 + ((i * 7 + 13) % 170)
            pygame.draw.rect(surf, (8, 15, 5), (i, H - h2, 70, h2))
            for wy in range(H - h2 + 10, H, 25):
                for wx in range(i + 8, i + 65, 18):
                    col3 = (20, 40, 10) if (wx + wy) % 5 else (60, 120, 30)
                    pygame.draw.rect(surf, col3, (wx, wy, 10, 12))

    elif bg_name == "lava":
        for i, (sx, sy, sr) in enumerate(STARS):
            b = 40 + int(40 * math.sin(tick * 0.05 + i * 0.3))
            pygame.draw.circle(surf, (b, b // 3, 0), (sx, sy), sr)

    elif bg_name == "ice":
        for i, (sx, sy, sr) in enumerate(STARS):
            b = 60 + int(50 * math.sin(tick * 0.04 + i * 0.2))
            pygame.draw.circle(surf, (b // 2, b // 2, b), (sx, sy), sr)

    elif bg_name == "void":
        for i, (sx, sy, sr) in enumerate(STARS[:60]):
            b = 30 + int(20 * math.sin(tick * 0.06 + i * 0.5))
            pygame.draw.circle(surf, (b, 0, b), (sx, sy), sr)


# ═══════════════════════════════════════════════════════════════════
#  HUD PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

def draw_hud(surf, fonts: dict, score: int, lives: float, coins: float,
             xp_sys, active: dict, round_num: int, tick: int,
             score2x_t: int, xp2x_t: int, hardcore: bool, attack_cd: int) -> None:
    """Dessine le bandeau HUD en haut de l'écran."""
    F_MED = fonts["med"]; F_SM = fonts["sm"]; F_XSM = fonts["xsm"]

    pygame.draw.rect(surf, (5, 3, 18), pygame.Rect(0, 0, W, HUD_H))
    pygame.draw.line(surf, CYAN, (0, HUD_H), (W, HUD_H), 1)

    glow(surf, f"SCORE {score:07d}", F_MED, CYAN,   (10, 6))
    glow(surf, f"¢ {int(coins)}",    F_MED, GREEN,  (W // 2 - 50, 6))
    glow(surf, f"R{round_num}",       F_MED, YELLOW, (W - 85, 6))

    if hardcore:
        surf.blit(F_XSM.render("HARDCORE", True, RED), (W - 85, 36))

    # Vies (avec demi-vie)
    full = int(lives); half = (lives - full) >= 0.5
    for i in range(full):
        neon_circ(surf, MAGENTA, (W - 22 - i * 28, 50), 8, 2)
        pygame.draw.circle(surf, MAGENTA, (W - 22 - i * 28, 50), 4)
    if half:
        i = full
        pygame.draw.circle(surf, (80, 0, 60), (W - 22 - i * 28, 50), 8, 2)
        surf.blit(F_XSM.render("½", True, MAGENTA), (W - 22 - i * 28 - 6, 43))

    # Barre XP
    draw_bar(surf, pygame.Rect(10, 48, 220, 14),
             xp_sys.xp, xp_sys.xp_next, PURPLE,
             text=f"LVL {xp_sys.level}  {xp_sys.xp}/{xp_sys.xp_next}")

    # Buffs actifs
    x0 = 240
    for name, dur in active.items():
        if dur > 0 and name in POWERUP_DUR:
            col2 = POWERUP_COL[name]
            draw_bar(surf, pygame.Rect(x0, 38, 65, 12), dur, POWERUP_DUR[name], col2)
            surf.blit(F_XSM.render(name[:4].upper(), True, col2), (x0, 22))
            x0 += 72

    if score2x_t > 0: glow(surf, "×2",   F_MED, YELLOW, (W // 2 + 55, 6))
    if xp2x_t   > 0: surf.blit(F_XSM.render("XP×2", True, PURPLE), (W // 2 + 95, 38))

    # Cooldown attaque
    if attack_cd > 0:
        draw_bar(surf, pygame.Rect(W // 2 - 35, HUD_H + 4, 70, 8),
                 25 - attack_cd, 25, CYAN, text="ATK")
    else:
        surf.blit(F_XSM.render("ATK ✓", True, CYAN), (W // 2 - 22, HUD_H + 4))
