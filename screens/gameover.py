"""
screens/gameover.py
───────────────────
Écran de fin de partie :
  - Stats complètes (score, manches, niveau, attaques, items…)
  - Historique des boss vaincus
  - Option enregistrement vidéo → instructions TikTok
"""

import pygame, math, os
from core.constants import (
    W, H, BG, BG_COLORS,
    CYAN, MAGENTA, YELLOW, GREEN, ORANGE, RED, PURPLE, GREY, WHITE,
)
from systems.hud import glow, cx, draw_bg, draw_bar
from core.recorder import CV2_OK


# ═══════════════════════════════════════════════════════════════════
#  GAME OVER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════
def screen_gameover(screen, clock, fonts: dict, recorder,
                    score: int, hiscore: int, rounds: int,
                    xp_sys, stats: dict, hardcore: bool,
                    boss_defs: dict, save: dict,
                    current_bg: str = "space") -> None:
    F_BIG = fonts["big"]; F_MED = fonts["med"]
    F_SM  = fonts["sm"];  F_XSM = fonts["xsm"]

    choice = None
    bs = pygame.Rect(W // 2 - 220, 490, 200, 52)
    ns = pygame.Rect(W // 2 + 20,  490, 200, 52)

    while choice is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_s: choice = "save"
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r, pygame.K_n):
                    choice = "skip"
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if bs.collidepoint(mx, my): choice = "save"
                if ns.collidepoint(mx, my): choice = "skip"

        tick = pygame.time.get_ticks() // 16
        mx, my = pygame.mouse.get_pos()
        screen.fill(BG); draw_bg(screen, tick, current_bg)

        # Titre glitch
        to = int(math.sin(tick * 0.07) * 3)
        glow(screen, "GAME OVER", F_BIG, MAGENTA, (cx("GAME OVER", F_BIG) + 1, 70 + to))
        glow(screen, "GAME OVER", F_BIG, CYAN,    (cx("GAME OVER", F_BIG),     70))

        # Carte stats
        card = pygame.Rect(W // 2 - 300, 155, 600, 300)
        pygame.draw.rect(screen, (9, 9, 25), card, border_radius=14)
        pygame.draw.rect(screen, RED if hardcore else CYAN, card, 2, border_radius=14)

        rows = [
            ("Mode",      "HARDCORE" if hardcore else "RUSH",   RED if hardcore else GREEN),
            ("Manches",   str(rounds),                          WHITE),
            ("Score",     f"{score:07d}",                       CYAN),
            ("Record",    f"{hiscore:07d}",                     YELLOW),
            ("Niveau",    f"{xp_sys.level}",                    PURPLE),
            ("Attaques",  str(stats.get("attacks", 0)),         CYAN),
            ("Items",     str(stats.get("items_used", 0)),      GREEN),
            ("Collectés", str(stats.get("items_collected", 0)), MAGENTA),
        ]
        for ri, (lbl, val, col) in enumerate(rows):
            ci = ri % 2; ri2 = ri // 2
            x0 = card.x + 20 + ci * 295; y0 = card.y + 14 + ri2 * 58
            screen.blit(F_XSM.render(lbl, True, GREY), (x0, y0))
            vs = F_SM.render(val, True, col); screen.blit(vs, (x0, y0 + 16))

        # Boss vaincus — uniquement cette partie
        run_bosses = stats.get("bosses_defeated", [])
        if run_bosses:
            # compter les doublons (ex: "GRAVITON ×2")
            from collections import Counter
            counts = Counter(run_bosses)
            parts = [f"{n} ×{c}" if c > 1 else n for n, c in counts.items()]
            defeated = "  ".join(parts)
        else:
            defeated = "aucun"
        bh_line = f"Boss vaincus (cette partie) : {defeated}"
        screen.blit(F_XSM.render(bh_line, True, ORANGE), (cx(bh_line, F_XSM), card.bottom - 20))

        # XP bar
        draw_bar(screen, pygame.Rect(W // 2 - 250, card.bottom + 8, 500, 16),
                 xp_sys.xp, xp_sys.xp_next, PURPLE,
                 text=f"LVL {xp_sys.level}  {xp_sys.xp}/{xp_sys.xp_next} XP")

        screen.blit(F_XSM.render("── Enregistrer la partie ? ──", True, GREY),
                    (cx("── Enregistrer la partie ? ──", F_XSM), 472))

        for btn, lbl, col, hint in [
            (bs, "🎬 OUI, SAUVER", GREEN,   "[S]"),
            (ns, "✕ NON MERCI",   MAGENTA, "[ESPACE]"),
        ]:
            hov = btn.collidepoint(mx, my)
            bg  = tuple(min(255, c // 3 + 22) for c in col) if hov else (10, 10, 28)
            pygame.draw.rect(screen, bg, btn, border_radius=9)
            pygame.draw.rect(screen, col, btn, 2, border_radius=9)
            bs2 = F_SM.render(lbl, True, col)
            hs  = F_XSM.render(hint, True, GREY)
            screen.blit(bs2, (btn.centerx - bs2.get_width() // 2, btn.centery - bs2.get_height() // 2 - 3))
            screen.blit(hs,  (btn.centerx - hs.get_width() // 2,  btn.bottom + 3))

        if not CV2_OK:
            screen.blit(F_XSM.render("⚠ pip install opencv-python", True, ORANGE),
                        (cx("⚠ pip install opencv-python", F_XSM), 558))

        pygame.display.flip(); clock.tick(60)

    # ── Sauvegarde vidéo ────────────────────────────────────────────────────
    if choice == "save":
        screen.fill(BG)
        glow(screen, "Encodage…", F_MED, CYAN, (cx("Encodage…", F_MED), H // 2))
        pygame.display.flip(); pygame.event.pump()
        path = recorder.stop_and_save()
        if path and os.path.exists(path):
            _success_screen(screen, clock, fonts, path, score, rounds, xp_sys)
        elif not CV2_OK:
            _no_cv2_screen(screen, clock, fonts)
        else:
            screen.fill(BG)
            glow(screen, "Aucune frame capturée.", F_MED, RED,
                 (cx("Aucune frame capturée.", F_MED), H // 2))
            pygame.display.flip(); pygame.time.wait(2000)
    else:
        recorder.stop_and_save()

    # ── Attente rejouer ──────────────────────────────────────────────────────
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r): return
        tick = pygame.time.get_ticks() // 16
        screen.fill(BG); draw_bg(screen, tick, current_bg)
        pulse = int(200 + 55 * math.sin(tick * 0.09))
        glow(screen, "[ R / ESPACE ]  Rejouer", F_MED, (pulse, 0, pulse),
             (cx("[ R / ESPACE ]  Rejouer", F_MED), H // 2 + 20))
        pygame.display.flip(); clock.tick(60)


# ═══════════════════════════════════════════════════════════════════
#  SOUS-ÉCRANS
# ═══════════════════════════════════════════════════════════════════
def _no_cv2_screen(screen, clock, fonts):
    F_MED = fonts["med"]; F_SM = fonts["sm"]
    screen.fill(BG)
    for yi, (txt, col, font) in enumerate([
        ("opencv-python non installé", ORANGE, F_MED),
        ("pip install opencv-python",  CYAN,   F_MED),
        ("puis relance le jeu.",        GREY,   F_SM),
    ]):
        s = font.render(txt, True, col); screen.blit(s, (cx(txt, font), 200 + yi * 58))
    pygame.display.flip()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if e.type == pygame.KEYDOWN: return
        clock.tick(30)


def _success_screen(screen, clock, fonts, path: str,
                    score: int, rounds: int, xp_sys) -> None:
    F_BIG = fonts["big"]; F_MED = fonts["med"]; F_XSM = fonts["xsm"]
    waiting = True; t0 = pygame.time.get_ticks() // 16

    while waiting:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN): waiting = False

        tick = pygame.time.get_ticks() // 16; t = tick - t0
        screen.fill(BG); draw_bg(screen, tick, "space")

        card = pygame.Rect(50, 35, W - 100, H - 70)
        pygame.draw.rect(screen, (7, 7, 20), card, border_radius=16)
        hue = (t * 2) % 360
        bc  = (int(abs(math.sin(math.radians(hue))) * 255),
               int(abs(math.sin(math.radians(hue + 120))) * 255),
               int(abs(math.sin(math.radians(hue + 240))) * 255))
        pygame.draw.rect(screen, bc, card, 3, border_radius=16)

        glow(screen, "✓", F_BIG, GREEN, (cx("✓", F_BIG), 85 + int(math.sin(t * 0.06) * 5)))
        glow(screen, "Vidéo enregistrée !", F_MED, WHITE,
             (cx("Vidéo enregistrée !", F_MED), 180))

        fn = os.path.basename(path); fd = os.path.dirname(path) or "."
        for yi, (line, col) in enumerate([(fn, CYAN), (f"dans : {fd}", GREY)]):
            s = F_XSM.render(line, True, col); screen.blit(s, (cx(line, F_XSM), 230 + yi * 20))

        pygame.draw.line(screen, (28, 28, 55), (card.x + 40, 284), (card.right - 40, 284))

        steps = [
            ("1.", "Ouvre TikTok",           WHITE),
            ("2.", "Appuie sur + → Importer",WHITE),
            ("3.", "Sélectionne  " + fn,      CYAN),
            ("4.", "Ajoute musique / texte",  WHITE),
            ("5.", "Poste !",                 YELLOW),
        ]
        y0 = 300
        for num, txt, col in steps:
            screen.blit(F_XSM.render(num, True, MAGENTA), (card.x + 55, y0))
            screen.blit(F_XSM.render(txt, True, col),     (card.x + 80, y0))
            y0 += 26

        stat = f"Score {score:07d}  ·  {rounds} manches  ·  LVL {xp_sys.level}"
        screen.blit(F_XSM.render(stat, True, GREY), (cx(stat, F_XSM), y0 + 4))

        pulse = int(200 + 55 * math.sin(t * 0.09))
        glow(screen, "[ Appuie sur n'importe quelle touche ]", F_XSM, (0, pulse, pulse // 2),
             (cx("[ Appuie sur n'importe quelle touche ]", F_XSM), card.bottom - 30))

        pygame.display.flip(); clock.tick(60)
