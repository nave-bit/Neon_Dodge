"""
screens/title.py
────────────────
Écran titre + menu keybinds.
"""

import pygame, math
from core.constants import (
    W, H, BG, BG_COLORS, BACKGROUNDS,
    CYAN, MAGENTA, YELLOW, GREEN, RED, GREY, WHITE,
)
from systems.hud import glow, cx, draw_bg


# ═══════════════════════════════════════════════════════════════════
#  ÉCRAN TITRE
# ═══════════════════════════════════════════════════════════════════
def screen_title(screen, clock, fonts: dict, save: dict,
                 boss_defs: dict, current_bg: str) -> tuple:
    """
    Retourne (auto_mode: bool, hardcore: bool, current_bg: str).
    """
    F_BIG = fonts["big"]; F_MED = fonts["med"]
    F_SM  = fonts["sm"];  F_XSM = fonts["xsm"]
    KEYS  = save["keys"]
    choice = None

    while choice is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_a:  choice = ("auto",   "rush")
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE): choice = ("player", "rush")
                if ev.key == pygame.K_h:  choice = ("player", "hardcore")
                if ev.key == pygame.K_k:
                    screen_keybinds(screen, clock, fonts, save)
                if ev.key == pygame.K_b:
                    current_bg = BACKGROUNDS[(BACKGROUNDS.index(current_bg) + 1) % len(BACKGROUNDS)]

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if pygame.Rect(W // 2 - 270, 340, 130, 50).collidepoint(mx, my): choice = ("auto",   "rush")
                if pygame.Rect(W // 2 - 120, 340, 130, 50).collidepoint(mx, my): choice = ("player", "rush")
                if pygame.Rect(W // 2 + 30,  340, 130, 50).collidepoint(mx, my): choice = ("player", "hardcore")
                if pygame.Rect(W // 2 - 60,  415, 120, 40).collidepoint(mx, my):
                    screen_keybinds(screen, clock, fonts, save)
                if pygame.Rect(W // 2 - 60,  465, 120, 30).collidepoint(mx, my):
                    current_bg = BACKGROUNDS[(BACKGROUNDS.index(current_bg) + 1) % len(BACKGROUNDS)]

        tick = pygame.time.get_ticks() // 16
        screen.fill(BG_COLORS[current_bg])
        draw_bg(screen, tick, current_bg)

        t = math.sin(tick * 0.05) * 6
        glow(screen, "NEON DODGE", F_BIG, CYAN,    (cx("NEON DODGE", F_BIG),     90 + int(t)))
        glow(screen, "NEON DODGE", F_BIG, MAGENTA, (cx("NEON DODGE", F_BIG) + 2, 92 + int(t)))
        glow(screen, "v4.0", F_XSM, GREY, (cx("v4.0", F_XSM), 172))

        mx, my = pygame.mouse.get_pos()
        for rect, lbl, col in [
            (pygame.Rect(W // 2 - 270, 340, 130, 50), "🤖 IA AUTO",  GREEN),
            (pygame.Rect(W // 2 - 120, 340, 130, 50), "🎮 JOUEUR",   CYAN),
            (pygame.Rect(W // 2 + 30,  340, 130, 50), "💀 HARDCORE", RED),
        ]:
            hov = rect.collidepoint(mx, my)
            bg  = tuple(min(255, c // 3 + 25) for c in col) if hov else (12, 12, 32)
            pygame.draw.rect(screen, bg, rect, border_radius=9)
            pygame.draw.rect(screen, col, rect, 2, border_radius=9)
            s = F_SM.render(lbl, True, col)
            screen.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - s.get_height() // 2))

        for rect, lbl in [
            (pygame.Rect(W // 2 - 60, 415, 120, 40), "⚙ TOUCHES"),
            (pygame.Rect(W // 2 - 60, 465, 120, 30), f"FOND: {current_bg.upper()}"),
        ]:
            hov2 = rect.collidepoint(mx, my)
            pygame.draw.rect(screen, (20, 20, 20) if hov2 else (10, 10, 28), rect, border_radius=8)
            pygame.draw.rect(screen, GREY, rect, 2, border_radius=8)
            s = F_XSM.render(lbl, True, WHITE)
            screen.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - 6))

        # Historique boss
        defeated = [k for k, v in save["boss_history"].items() if v.get("defeated", 0) > 0]
        if defeated:
            dt = "Boss vaincus: " + "  ".join(boss_defs[b][0] for b in defeated)
            screen.blit(F_XSM.render(dt, True, GREY), (cx(dt, F_XSM), 515))

        tips = [
            "BOSS tous les 10 LVL (5 en HARDCORE)  |  Double-tap = Téléport",
            f"ATK = {pygame.key.name(KEYS['attack']).upper()}   [K] Reconfigurer les touches   [B] Fond",
        ]
        for i, tip in enumerate(tips):
            screen.blit(F_XSM.render(tip, True, GREY), (cx(tip, F_XSM), 548 + i * 20))

        pygame.display.flip(); clock.tick(60)

    mode, diff = choice
    return mode == "auto", diff == "hardcore", current_bg


# ═══════════════════════════════════════════════════════════════════
#  ÉCRAN KEYBINDS
# ═══════════════════════════════════════════════════════════════════
def screen_keybinds(screen, clock, fonts: dict, save: dict) -> None:
    """Reconfiguration des touches. Modifie save['keys'] en place et sauvegarde."""
    import core.save_manager as sm
    F_BIG = fonts["big"]; F_SM = fonts["sm"]; F_XSM = fonts["xsm"]
    KEYS  = save["keys"]

    actions = ["left","right","up","down","attack","item1","item2","item3","item4","item5"]
    labels  = ["Gauche","Droite","Haut","Bas","Attaque","Item 1","Item 2","Item 3","Item 4","Item 5"]

    waiting_for = None; i_sel = 0

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if waiting_for is not None:
                    if ev.key == pygame.K_ESCAPE: waiting_for = None
                    else:
                        KEYS[waiting_for] = ev.key
                        waiting_for = None
                        save["keys"] = KEYS; sm.write(save)
                else:
                    if ev.key == pygame.K_ESCAPE: return
                    if ev.key == pygame.K_RETURN: waiting_for = actions[i_sel]
                    if ev.key == pygame.K_UP:   i_sel = (i_sel - 1) % len(actions)
                    if ev.key == pygame.K_DOWN: i_sel = (i_sel + 1) % len(actions)

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                for i in range(len(actions)):
                    if pygame.Rect(W // 2 - 200, 130 + i * 46, 400, 38).collidepoint(mx, my):
                        i_sel = i; waiting_for = actions[i]

        tick = pygame.time.get_ticks() // 16
        screen.fill(BG); draw_bg(screen, tick, "space")
        glow(screen, "TOUCHES", F_BIG, CYAN, (cx("TOUCHES", F_BIG), 30))

        for i, (act, lbl) in enumerate(zip(actions, labels)):
            rect = pygame.Rect(W // 2 - 200, 130 + i * 46, 400, 38)
            sel  = (i == i_sel); wt = (waiting_for == act)
            col2 = (255, 215, 0) if wt else (CYAN if sel else (255,255,255))
            pygame.draw.rect(screen, (30, 30, 60) if sel else (10, 10, 28), rect, border_radius=8)
            pygame.draw.rect(screen, col2, rect, 2, border_radius=8)
            kname = "??? APPUIE" if wt else pygame.key.name(KEYS[act]).upper()
            s = F_SM.render(f"{lbl:<12} {kname}", True, col2)
            screen.blit(s, (rect.x + 15, rect.y + 8))

        hint = "↑↓ Naviguer   ENTRÉE Changer   ESC Retour"
        screen.blit(F_XSM.render(hint, True, GREY), (cx(hint, F_XSM), H - 28))
        pygame.display.flip(); clock.tick(60)
