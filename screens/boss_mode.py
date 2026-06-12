"""screens/boss_mode.py — MODE BOSS : s'entraîner contre n'importe quel boss"""
import pygame, math
from core.constants import (
    W, H, BG, BG_COLORS,
    CYAN, MAGENTA, YELLOW, GREEN, RED, WHITE, PURPLE, GREY, GOLD, ORANGE,
)
from systems.hud import glow, cx, draw_bg, draw_bar
from entities.boss import BOSS_DEFS, RARITY_COLORS, DIFF_LABELS, DIFF_COLORS, DIFF_MULT

DIFFICULTIES = ["basic","brutal","destructeur","divin","cauchemar"]

DIVIN_TIPS = {
    "lazerrrr1": "DIVIN : lasers ultra-rapides, zone sûre réduite à 30px. Bombe = seule issue.",
    "lazerrrr2": "DIVIN : lasers permanents depuis 8 angles. Vitesse triplée. Bombe inutile.",
    "graviton":  "DIVIN : 16 projectiles simultanés toutes les 6 frames. Esquive pure.",
    "antispell": "DIVIN : anti-spell + gravité inversée + vitesse ×3.5.",
    "voidlord":  "DIVIN : toutes mécaniques actives. Survie = victoire.",
    "winding":   "DIVIN : chemin change toutes les 2 secondes. Marge d'erreur = 0.",
    "winding2":  "DIVIN : chemin rapide + déluge de bombes simultané.",
}


def screen_boss_mode(screen, clock, fonts:dict, save:dict, current_bg:str) -> tuple:
    """
    Retourne (boss_id, difficulty, current_bg) ou (None, None, current_bg) si annulé.
    """
    F_BIG=fonts["big"]; F_MED=fonts["med"]; F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    boss_ids  = list(BOSS_DEFS.keys())
    sel_boss  = 0
    sel_diff  = 0
    scroll_y  = 0

    while True:
        tick=pygame.time.get_ticks()//16
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: return None,None,current_bg
                if ev.key==pygame.K_LEFT:   sel_boss=(sel_boss-1)%len(boss_ids)
                if ev.key==pygame.K_RIGHT:  sel_boss=(sel_boss+1)%len(boss_ids)
                if ev.key==pygame.K_UP:     sel_diff=(sel_diff-1)%len(DIFFICULTIES)
                if ev.key==pygame.K_DOWN:   sel_diff=(sel_diff+1)%len(DIFFICULTIES)
                if ev.key in (pygame.K_RETURN,pygame.K_SPACE):
                    return boss_ids[sel_boss], DIFFICULTIES[sel_diff], current_bg
                if ev.key==pygame.K_b:
                    current_bg=["space","city","lava","ice","void"][
                        (["space","city","lava","ice","void"].index(current_bg)+1)%5]

            if ev.type==pygame.MOUSEBUTTONDOWN:
                mx,my=pygame.mouse.get_pos()
                # Sélection boss (cartes)
                for bi,bid in enumerate(boss_ids):
                    ci=bi%4; ri2=bi//4
                    bx=40+ci*222; by=175+ri2*155
                    if pygame.Rect(bx,by,206,138).collidepoint(mx,my):
                        sel_boss=bi
                # Sélection difficulté
                for di,diff in enumerate(DIFFICULTIES):
                    dr=pygame.Rect(40+di*180,H-140,165,44)
                    if dr.collidepoint(mx,my): sel_diff=di
                # Bouton lancer
                if pygame.Rect(W//2-120,H-75,240,50).collidepoint(mx,my):
                    return boss_ids[sel_boss], DIFFICULTIES[sel_diff], current_bg

        screen.fill(BG_COLORS[current_bg]); draw_bg(screen,tick,current_bg)

        t=math.sin(tick*0.06)*4
        glow(screen,"MODE BOSS",F_BIG,MAGENTA,(cx("MODE BOSS",F_BIG),18+int(t)))
        glow(screen,"Entraîne-toi contre n'importe quel boss",F_XSM,GREY,
             (cx("Entraîne-toi contre n'importe quel boss",F_XSM),96))

        mx2,my2=pygame.mouse.get_pos()

        # ── Cartes boss ─────────────────────────────────────────────────────
        for bi,bid in enumerate(boss_ids):
            info=BOSS_DEFS[bid]
            name,rarity,col,hp,desc=info
            ci=bi%4; ri2=bi//4; bx=40+ci*222; by=175+ri2*155
            rect=pygame.Rect(bx,by,206,138)
            selected=(bi==sel_boss); hov=rect.collidepoint(mx2,my2)
            rc=RARITY_COLORS.get(rarity,WHITE)
            border=col if selected else (rc if hov else GREY)
            bg=tuple(min(255,c//3+22) for c in col) if (selected or hov) else (10,10,28)
            pygame.draw.rect(screen,bg,rect,border_radius=10)
            pygame.draw.rect(screen,border,rect,3 if selected else 2,border_radius=10)
            if selected:
                pulse=int(200+55*math.sin(tick*0.12))
                pygame.draw.rect(screen,(0,pulse,pulse),rect,1,border_radius=10)
            glow(screen,name[:18],F_XSM,col,(bx+8,by+8))
            rs=F_XSM.render(f"[{rarity}]",True,rc); screen.blit(rs,(bx+8,by+28))
            screen.blit(F_XSM.render(desc[:28]+"…" if len(desc)>28 else desc,True,GREY),(bx+8,by+50))
            # Historique
            bh=save["boss_history"].get(bid,{})
            seen=bh.get("seen",0); beaten=bh.get("defeated",0)
            screen.blit(F_XSM.render(f"Vu:{seen}  Battu:{beaten}",True,WHITE if beaten else GREY),(bx+8,by+72))
            best=bh.get("best_diff")
            if best:
                bcol=DIFF_COLORS.get(best,WHITE)
                screen.blit(F_XSM.render(f"★ {DIFF_LABELS.get(best,best)}",True,bcol),(bx+95,by+72))
            # HP preview
            diff=DIFFICULTIES[sel_diff]; mult=DIFF_MULT[diff]
            hp_prev=int((hp+1)*(mult))
            screen.blit(F_XSM.render(f"HP ~{hp_prev}",True,RED),(bx+8,by+94))
            if selected:
                ck=F_SM.render("▶",True,YELLOW)
                screen.blit(ck,(bx+rect.w-ck.get_width()-8,by+rect.h-ck.get_height()-6))

        # ── Sélection difficulté ─────────────────────────────────────────────
        sep_y=175+math.ceil(len(boss_ids)/4)*155+8
        pygame.draw.line(screen,GREY,(30,sep_y),(W-30,sep_y))
        screen.blit(F_SM.render("Difficulté :",True,WHITE),(40,sep_y+8))

        for di,diff in enumerate(DIFFICULTIES):
            dcol=DIFF_COLORS[diff]; dlbl=DIFF_LABELS[diff]
            dr=pygame.Rect(40+di*182,sep_y+38,170,44)
            sel=(di==sel_diff); hov2=dr.collidepoint(mx2,my2)
            bg2=tuple(min(255,c//3+25) for c in dcol) if (sel or hov2) else (12,12,30)
            pygame.draw.rect(screen,bg2,dr,border_radius=8)
            pygame.draw.rect(screen,dcol,dr,3 if sel else 2,border_radius=8)
            ds=F_XSM.render(dlbl,True,dcol)
            screen.blit(ds,(dr.centerx-ds.get_width()//2,dr.centery-ds.get_height()//2))

        # Tip DIVIN
        sel_bid=boss_ids[sel_boss]; sel_diff_str=DIFFICULTIES[sel_diff]
        if sel_diff_str=="divin":
            tip=DIVIN_TIPS.get(sel_bid,"Mode DIVIN : mécanique unique, difficulté extrême.")
            tip_s=F_XSM.render(tip,True,RED)
            screen.blit(tip_s,(cx(tip,F_XSM),sep_y+95))

        # ── Bouton lancer ────────────────────────────────────────────────────
        go_rect=pygame.Rect(W//2-120,H-70,240,50)
        hov3=go_rect.collidepoint(mx2,my2)
        dcol=DIFF_COLORS[DIFFICULTIES[sel_diff]]
        pygame.draw.rect(screen,tuple(min(255,c//2+30) for c in dcol) if hov3 else (15,15,38),go_rect,border_radius=10)
        pygame.draw.rect(screen,dcol,go_rect,2,border_radius=10)
        gs=F_MED.render("▶  LANCER",True,dcol)
        screen.blit(gs,(go_rect.centerx-gs.get_width()//2,go_rect.centery-gs.get_height()//2))

        hint="← → Boss   ↑ ↓ Difficulté   ENTRÉE Lancer   ESC Retour"
        screen.blit(F_XSM.render(hint,True,GREY),(cx(hint,F_XSM),H-16))
        pygame.display.flip(); clock.tick(60)
