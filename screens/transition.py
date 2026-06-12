"""
screens/transition.py
─────────────────────
Écrans intermédiaires :
  - run_transition() : résumé de fin de manche
  - boss_intro()     : présentation du boss avant le combat
"""

import pygame, math
from core.constants import (
    W, H, BG_COLORS,
    CYAN, MAGENTA, YELLOW, GREEN, ORANGE, RED, WHITE, PURPLE, GREY,
)
from systems.hud import glow, cx, draw_bg, draw_bar
from entities.boss import RARITY_COLORS


def run_transition(screen, clock, fonts: dict, round_num: int,
                   total_score: int, coins_earned: int,
                   xp_sys, current_bg: str) -> None:
    """Résumé entre deux manches. Appuyer sur ESPACE pour continuer."""
    F_MED = fonts["med"]; F_SM = fonts["sm"]; F_XSM = fonts["xsm"]
    timer = 180

    while timer > 0:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN): return

        tick = pygame.time.get_ticks() // 16
        screen.fill(BG_COLORS[current_bg]); draw_bg(screen, tick, current_bg)

        t = math.sin(tick * 0.07) * 5
        glow(screen, f"MANCHE {round_num} TERMINÉE", F_MED, GREEN,
             (cx(f"MANCHE {round_num} TERMINÉE", F_MED), 150 + int(t)))
        glow(screen, f"Score total : {total_score:07d}", F_SM, CYAN,
             (cx(f"Score total : {total_score:07d}", F_SM), 230))
        glow(screen, f"+{coins_earned} ¢", F_SM, YELLOW,
             (cx(f"+{coins_earned} ¢", F_SM), 268))

        draw_bar(screen, pygame.Rect(W // 2 - 220, 312, 440, 24),
                 xp_sys.xp, xp_sys.xp_next, PURPLE,
                 text=f"LVL {xp_sys.level}  {xp_sys.xp}/{xp_sys.xp_next} XP")

        pulse = int(200 + 55 * math.sin(tick * 0.09))
        glow(screen, "BOUTIQUE  →", F_MED, (0, pulse, pulse // 2),
             (cx("BOUTIQUE  →", F_MED), 368))

        pygame.display.flip(); clock.tick(60); timer -= 1


def boss_intro(screen, clock, fonts: dict, boss, current_bg: str) -> None:
    """Écran d'intro avant un combat de boss."""
    F_BIG = fonts["big"]; F_MED = fonts["med"]; F_SM = fonts["sm"]; F_XSM = fonts["xsm"]
    rc    = RARITY_COLORS.get(boss.rarity, WHITE)
    timer = 180

    while timer > 0:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN): return

        tick = pygame.time.get_ticks() // 16
        screen.fill(BG_COLORS[current_bg]); draw_bg(screen, tick, current_bg)

        # Flash coloré
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((*boss.color, int(30 + 20 * math.sin(tick * 0.15))))
        screen.blit(ov, (0, 0))

        glow(screen, "⚠  BOSS  ⚠", F_BIG, RED, (cx("⚠  BOSS  ⚠", F_BIG), 125))
        glow(screen, boss.name, F_MED, boss.color, (cx(boss.name, F_MED), 218))

        rs = F_SM.render(f"[{boss.rarity}]", True, rc)
        screen.blit(rs, (cx(f"[{boss.rarity}]", F_SM), 260))

        ds = F_SM.render(boss.desc, True, WHITE)
        screen.blit(ds, (cx(boss.desc, F_SM), 305))

        draw_bar(screen, pygame.Rect(W // 2 - 200, 358, 400, 24),
                 boss.hp, boss.maxhp, boss.color,
                 text=f"HP  {boss.hp} / {boss.maxhp}")

        pulse = int(200 + 55 * math.sin(tick * 0.1))
        glow(screen, "[ ESPACE ]  Commencer", F_SM, (0, pulse, pulse // 2),
             (cx("[ ESPACE ]  Commencer", F_SM), 418))

        pygame.display.flip(); clock.tick(60); timer -= 1


def pre_boss_screen(screen, clock, fonts:dict, boss, inv:dict,
                    atk_sys, xp_sys, current_bg:str) -> dict:
    """
    Affiche les stats du joueur + restrictions avant le combat de boss.
    Retourne l'inv modifié (items restreints retirés temporairement).
    """
    from core.constants import BOSS_RESTRICTIONS, ATTACK_TYPES
    from systems.hud import glow, cx, draw_bg, draw_bar
    from entities.boss import RARITY_COLORS, DIFF_LABELS, DIFF_COLORS

    F_BIG=fonts["big"]; F_MED=fonts["med"]; F_SM=fonts["sm"]; F_XSM=fonts["xsm"]

    restrictions = BOSS_RESTRICTIONS.get(boss.id, {})
    blocked      = list(restrictions.keys())

    # Retirer temporairement les items bloqués
    removed = {}
    for item_id in blocked:
        if item_id in inv and inv[item_id]>0:
            removed[item_id]=inv.pop(item_id)

    timer = 300   # 5 secondes max, passage auto
    while timer > 0:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type==pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE): return inv

        tick=pygame.time.get_ticks()//16; timer-=1

        screen.fill(BG_COLORS.get(current_bg,(3,1,15)))
        draw_bg(screen, tick, current_bg)

        # Flash boss color
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((*boss.color,int(20+15*math.sin(tick*0.1)))); screen.blit(ov,(0,0))

        # Titre
        glow(screen,"BOSS — PRÉPARE-TOI",F_BIG,boss.color,(cx("BOSS — PRÉPARE-TOI",F_BIG),28))
        rc=RARITY_COLORS.get(boss.rarity,WHITE)
        screen.blit(F_SM.render(f"{boss.name}  [{boss.rarity}]",True,rc),
                    (cx(f"{boss.name}  [{boss.rarity}]",F_SM),108))
        screen.blit(F_XSM.render(boss.desc,True,WHITE),(cx(boss.desc,F_XSM),138))

        # Ligne séparatrice
        pygame.draw.line(screen,GREY,(40,162),(W-40,162))

        # ── Stats joueur ─────────────────────────────────────────────────────
        LEFT=55; RIGHT=W//2+20; y0=175
        screen.blit(F_SM.render("TES STATS",True,CYAN),(LEFT,y0))
        atk=atk_sys.current; info=ATTACK_TYPES[atk]
        lines_l=[
            (f"Niveau XP   : {xp_sys.level}",           WHITE),
            (f"Attaque     : {info[0]}",                 info[1]),
            (f"Dégâts      : {atk_sys.get_damage(atk):.1f} (boss: {atk_sys.get_boss_damage(atk):.1f})", YELLOW),
            (f"Cooldown    : {atk_sys.get_cooldown(atk)} frames",  GREY),
            (f"Rayon       : {atk_sys.get_radius(atk)} px",        GREY),
            (f"Vitesse     : ×{xp_sys.speed_bonus():.2f}",         GREEN),
        ]
        for i,(txt,col) in enumerate(lines_l):
            screen.blit(F_XSM.render(txt,True,col),(LEFT,y0+28+i*22))

        # ── Inventaire disponible ─────────────────────────────────────────────
        screen.blit(F_SM.render("ITEMS DISPONIBLES",True,GREEN),(RIGHT,y0))
        if inv:
            for i,(k,v) in enumerate([(k,v) for k,v in inv.items() if v>0]):
                col2=GREEN if k not in blocked else RED
                screen.blit(F_XSM.render(f"  {k.upper()} ×{v}",True,col2),(RIGHT,y0+28+i*22))
        else:
            screen.blit(F_XSM.render("  (aucun item)",True,GREY),(RIGHT,y0+28))

        # ── Restrictions ─────────────────────────────────────────────────────
        if restrictions:
            rx=W//2-200; ry=y0+165
            pygame.draw.rect(screen,(30,5,5),pygame.Rect(rx-10,ry-8,W//2+20,len(restrictions)*28+20),
                             border_radius=8)
            pygame.draw.rect(screen,RED,pygame.Rect(rx-10,ry-8,W//2+20,len(restrictions)*28+20),
                             1,border_radius=8)
            screen.blit(F_SM.render("⛔ RESTRICTIONS",True,RED),(rx,ry-4))
            for i,(item_id,msg) in enumerate(restrictions.items()):
                screen.blit(F_XSM.render(f"  • {msg}",True,ORANGE),(rx,ry+22+i*26))

        # ── HP preview ────────────────────────────────────────────────────────
        draw_bar(screen,pygame.Rect(W//2-200,y0+285,400,22),
                 boss.hp,boss.maxhp,boss.color,text=f"HP boss : {boss.hp}")

        # Countdown
        pulse=int(200+55*math.sin(tick*0.12))
        countdown=timer//60+1
        glow(screen,f"[ ESPACE ] Commencer  ({countdown}s)",F_SM,(0,pulse,pulse//2),
             (cx(f"[ ESPACE ] Commencer  ({countdown}s)",F_SM),H-36))
        pygame.display.flip(); clock.tick(60)

    return inv
