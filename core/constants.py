"""core/constants.py — NEON DODGE v5.0"""
import pygame

W, H   = 960, 700
FPS    = 60
HUD_H  = 78
TITLE  = "NEON DODGE  v5.0"

# ── Couleurs ──────────────────────────────────────────────────────────────────
BG      = (3,   1,  15)
CYAN    = (0,  220, 255)
MAGENTA = (255,  0, 200)
YELLOW  = (255, 215,  0)
GREEN   = (0,  255, 110)
ORANGE  = (255, 135,  0)
RED     = (255,  35,  35)
WHITE   = (255, 255, 255)
GREY    = (90,  90, 115)
PURPLE  = (160,  0, 255)
PINK    = (255, 100, 180)
GOLD    = (255, 200,  50)
TEAL    = (0,   200, 180)

# ── Fonds ─────────────────────────────────────────────────────────────────────
BACKGROUNDS = ["space","city","lava","ice","void"]
BG_COLORS   = {"space":(3,1,15),"city":(5,8,18),"lava":(18,3,1),"ice":(1,10,22),"void":(0,0,0)}
BG_GRID_COLORS = {
    "space":((0,25,40),(0,50,80)), "city":((10,20,5),(20,50,15)),
    "lava":((40,8,0),(80,20,0)),   "ice":((0,20,60),(0,50,120)),
    "void":((10,0,20),(25,0,50)),
}

# ── Gameplay ──────────────────────────────────────────────────────────────────
ROUND_FRAMES  = 1800
BOSS_INTERVAL = 10
XP_PER_LEVEL  = 300

# ── Courbe de difficulté RUSH ─────────────────────────────────────────────────
# (niveau_xp_min, types_autorisés, lasers_actifs, message_info)
DIFFICULTY_TIERS = [
    (1,  ["pebble"],                                              False, "Début en douceur..."),
    (3,  ["pebble","bolt"],                                       False, "★ NOUVEAU : Éclairs rapides !"),
    (5,  ["pebble","bolt","shard"],                               False, "★ NOUVEAU : Éclats triangulaires (×1.5 dmg)"),
    (7,  ["pebble","bolt","shard","bomb"],                        False, "★ NOUVEAU : Bombes lentes mais dévastatrices"),
    (10, ["pebble","bolt","shard","bomb","phantom"],              False, "★ NOUVEAU : Phantoms — trajectoire sinueuse !"),
    (15, ["pebble","bolt","shard","bomb","phantom","meteor"],     False, "⚠ ALERTE : MÉTÉORES — énormes, ×4 dégâts !"),
    (20, ["pebble","bolt","shard","bomb","phantom","meteor"],     True,  "⚠ ALERTE : LASERS multi-angles !"),
]

# ── Types d'attaque ───────────────────────────────────────────────────────────
# id: (label, couleur, rayon, dégâts_boss, cooldown, xp_unlock, description)
ATTACK_TYPES = {
    "wave":  ("ONDE",    CYAN,   90,  1.0, 25,    0,  "Onde circulaire — attaque de base"),
    "beam":  ("RAYON",   YELLOW, 240, 2.5, 45,  300,  "Rayon directionnel vers la souris"),
    "nova":  ("NOVA",    PURPLE, 160, 4.0, 80,  800,  "Explosion massive — gros dégâts boss"),
    "pulse": ("PULSE",   GREEN,  55,  0.7, 10, 1500,  "Rafale rapide, faibles dégâts unitaires"),
}

# ── Système d'énergie ─────────────────────────────────────────────────────────
# Coût en énergie de chaque attaque. L'ONDE est gratuite (toujours utilisable).
ENERGY_COST = {
    "wave":  0,
    "beam":  10,
    "nova":  25,
    "pulse": 4,
}
ENERGY_MAX_BASE   = 50      # jauge de départ
ENERGY_REGEN      = 0.15    # régénération auto par frame
ENERGY_PICKUP_GAIN= 20      # gain quand on ramasse un pickup énergie
TURBO_DRAIN       = 0.6     # énergie vidée par frame en mode turbo

# ── Skins du joueur ───────────────────────────────────────────────────────────
# id: (nom, couleur principale, couleur traînée, prix en ¢, forme)
# prix 0 = débloqué d'office. forme: "circle" | "triangle" | "diamond" | "square"
PLAYER_SKINS = {
    "cyan":    ("CYAN",      CYAN,    (0,155,255),   0,   "circle"),
    "magenta": ("MAGENTA",   MAGENTA, (255,0,180),   150, "circle"),
    "gold":    ("OR",        GOLD,    (255,200,40),  300, "diamond"),
    "green":   ("ÉMERAUDE",  GREEN,   (0,255,120),   250, "triangle"),
    "purple":  ("AMÉTHYSTE", PURPLE,  (180,80,255),  250, "diamond"),
    "red":     ("RUBIS",     RED,     (255,60,60),   400, "square"),
    "white":   ("DIAMANT",   WHITE,   (220,220,255), 600, "triangle"),
}

# ── Améliorations XP ─────────────────────────────────────────────────────────
# id: (label, couleur, coût_base, multiplicateur, max_niveau, description)
XP_UPGRADES = {
    "atk_dmg":   ("ATK DMG",   ORANGE, 150, 1.35, 10, "Augmente les dégâts d'attaque"),
    "atk_spd":   ("ATK SPD",   CYAN,   120, 1.40, 8,  "Réduit le cooldown d'attaque"),
    "move_spd":  ("VITESSE",   GREEN,  100, 1.35, 8,  "Augmente ta vitesse de déplacement"),
    "atk_radius":("RAYON ATK", PURPLE, 130, 1.35, 8,  "Agrandit le rayon d'attaque"),
    "boss_dmg":  ("BOSS DMG",  RED,    200, 1.40, 10, "Double les dégâts sur boss"),
    "energy_max":("ÉNERGIE+",  CYAN,   110, 1.35, 10, "+15 énergie max par niveau"),
}

# ── Raretés boutique ──────────────────────────────────────────────────────────
RARITIES = {
    "commun":    (GREY,   "COMMUN",    1.0),
    "peu commun":(GREEN,  "PEU COMM.", 1.5),
    "rare":      (CYAN,   "RARE",      2.5),
    "épique":    (PURPLE, "ÉPIQUE",    4.0),
    "légendaire":(GOLD,   "LÉGEND.",   8.0),
}

# ── Power-ups ─────────────────────────────────────────────────────────────────
POWERUP_DUR = {"slow":300,"shield":240,"magnet":300,"shrink":480,"ghost":360}
POWERUP_COL = {"slow":YELLOW,"shield":CYAN,"magnet":GREEN,"shrink":PINK,"ghost":PURPLE}

# ── Touches par défaut (Q/Z/S/D + clic droit) ────────────────────────────────
MOUSE_ATTACK = -1   # valeur spéciale = clic droit souris
DEFAULT_KEYS = {
    "left":   pygame.K_q,
    "right":  pygame.K_d,
    "up":     pygame.K_z,
    "down":   pygame.K_s,
    "attack": MOUSE_ATTACK,   # -1 = clic droit
    "item1":  pygame.K_e,
    "item2":  pygame.K_r,
    "item3":  pygame.K_t,
    "item4":  pygame.K_f,
    "item5":  pygame.K_g,
}

def load_fonts():
    def _f(n,s,b=False):
        try:    return pygame.font.SysFont(n,s,bold=b)
        except: return pygame.font.SysFont(None,s,bold=b)
    return {"big":_f("consolas",68,True),"med":_f("consolas",28,True),
            "sm":_f("consolas",18),"xsm":_f("consolas",14)}

# ── Restrictions par boss ─────────────────────────────────────────────────────
# item_id -> message d'info affiché avant le combat
BOSS_RESTRICTIONS = {
    "winding":   {"teleport": "Téléport interdit — tu dois traverser le couloir !"},
    "winding2":  {"teleport": "Téléport interdit", "slow": "Slowmo interdit"},
    "lazerrrr1": {"shield":   "Bouclier interdit — esquive pure !"},
    "lazerrrr2": {"shield":   "Bouclier interdit", "slow": "Slowmo interdit"},
    "graviton":  {"magnet":   "Aimant interdit"},
    "antispell": {},
    "voidlord":  {"shield":   "Bouclier interdit", "slow": "Slowmo interdit",
                  "teleport": "Téléport interdit"},
}
