"""
systems/animations.py
──────────────────────
Animations spectaculaires bloquantes :
  - boss_death_animation : écran noir, boss rouge vif qui implose, puis onde d'énergie
  - player_death_animation : le joueur explose, fracture de l'écran, fondu au rouge

Ces fonctions prennent la main sur la boucle le temps de l'animation
(elles gèrent leur propre clock.tick) puis rendent la main.
"""
import pygame, math, random
from core.constants import W, H, RED, WHITE, CYAN, MAGENTA, ORANGE, FPS


def _drain_events():
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); raise SystemExit


def boss_death_animation(screen, clock, bx, by, boss_color, boss_name, fonts,
                         recorder=None):
    """
    Tout l'écran devient noir sauf le boss en rouge vif qui implose,
    puis une onde d'énergie balaie l'écran.
    """
    F_BIG = fonts.get("big"); F_MED = fonts.get("med")
    cx, cy = int(bx), int(by)
    DUR_IMPLODE = 50   # frames d'implosion
    DUR_WAVE    = 35   # frames de l'onde

    # Phase 1 : implosion
    base_r = 90
    sparks = []
    for _ in range(40):
        a = random.uniform(0, math.tau); d = random.uniform(40, 160)
        sparks.append([cx + math.cos(a)*d, cy + math.sin(a)*d,
                       math.cos(a), math.sin(a), random.uniform(2, 5)])

    for f in range(DUR_IMPLODE):
        _drain_events()
        screen.fill((0, 0, 0))
        t = f / DUR_IMPLODE
        # Le boss rétrécit puis brille de plus en plus rouge
        r = max(2, int(base_r * (1 - t)))
        glow = int(120 + 135 * t)
        # halo
        for gr in range(r+30, r, -6):
            a = max(0, 60 - (gr - r)*2)
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(s, (glow, 0, 0, a), (cx, cy), gr)
            screen.blit(s, (0, 0))
        pygame.draw.circle(screen, (255, 40, 40), (cx, cy), r)
        pygame.draw.circle(screen, (255, 200, 200), (cx, cy), max(1, r//3))
        # étincelles aspirées vers le centre
        for sp in sparks:
            sp[0] -= (sp[0]-cx) * 0.08
            sp[1] -= (sp[1]-cy) * 0.08
            pygame.draw.circle(screen, (255, 90, 90),
                               (int(sp[0]), int(sp[1])), int(sp[4]*(1-t))+1)
        # tremblement
        if f > DUR_IMPLODE*0.6 and f % 2 == 0:
            screen.scroll(random.randint(-4,4), random.randint(-4,4))
        if recorder: recorder.capture(screen)
        pygame.display.flip(); clock.tick(FPS)

    # Flash blanc
    screen.fill((255, 255, 255))
    if recorder: recorder.capture(screen)
    pygame.display.flip(); clock.tick(FPS)

    # Phase 2 : onde d'énergie
    for f in range(DUR_WAVE):
        _drain_events()
        screen.fill((0, 0, 0))
        t = f / DUR_WAVE
        ring_r = int(t * max(W, H) * 0.9)
        thick = max(2, int(40 * (1-t)))
        for k in range(thick, 0, -3):
            a = max(0, int(220 * (1-t)))
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 60, 30, a), (cx, cy), ring_r - k, 3)
            screen.blit(s, (0, 0))
        if F_BIG:
            msg = "BOSS VAINCU"
            gs = F_BIG.render(msg, True, (255, 80, 80))
            screen.blit(gs, (W//2 - gs.get_width()//2, H//2 - gs.get_height()//2))
        if recorder: recorder.capture(screen)
        pygame.display.flip(); clock.tick(FPS)


def player_death_animation(screen, clock, px, py, fonts, recorder=None):
    """
    Le joueur explose en éclats cyan, l'écran se fracture puis vire au rouge sombre.
    """
    F_BIG = fonts.get("big")
    cx, cy = int(px), int(py)
    DUR = 55

    shards = []
    for _ in range(60):
        a = random.uniform(0, math.tau); spd = random.uniform(3, 11)
        shards.append([cx, cy, math.cos(a)*spd, math.sin(a)*spd,
                       random.uniform(3, 7), random.choice([CYAN, WHITE, MAGENTA])])

    # capture du dernier rendu pour le fondu
    snapshot = screen.copy()

    for f in range(DUR):
        _drain_events()
        t = f / DUR
        # fond : l'image figée qui s'assombrit et rougit
        screen.blit(snapshot, (0, 0))
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((40, 0, 0, int(200 * t)))
        screen.blit(dark, (0, 0))
        # éclats
        for sh in shards:
            sh[0] += sh[2]; sh[1] += sh[3]
            sh[3] += 0.25  # gravité
            sh[4] *= 0.97
            if sh[4] > 0.6:
                pygame.draw.circle(screen, sh[5],
                                   (int(sh[0]), int(sh[1])), int(sh[4]))
        # onde de choc initiale
        if f < 20:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, max(0, 160 - f*8)),
                               (cx, cy), 20 + f*14, 4)
            screen.blit(s, (0, 0))
        # tremblement
        if f % 2 == 0:
            screen.scroll(random.randint(-6, 6), random.randint(-6, 6))
        if t > 0.5 and F_BIG:
            msg = "ÉLIMINÉ"
            a = int(255 * min(1, (t-0.5)*2))
            gs = F_BIG.render(msg, True, (255, 60, 60))
            gs.set_alpha(a)
            screen.blit(gs, (W//2 - gs.get_width()//2, H//2 - gs.get_height()//2))
        if recorder: recorder.capture(screen)
        pygame.display.flip(); clock.tick(FPS)
