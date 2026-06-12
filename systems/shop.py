"""systems/shop.py — v5.1 — Menus déroulants, filtre par rareté"""
import pygame, math
from core.constants import (
    W, H, BG_COLORS, BACKGROUNDS,
    CYAN, MAGENTA, YELLOW, GREEN, ORANGE, RED, PURPLE, PINK, WHITE, GREY, GOLD, TEAL,
    POWERUP_DUR, RARITIES, ATTACK_TYPES, XP_UPGRADES,
)
from systems.hud import draw_bg, draw_bar, glow, cx
import core.sound_manager as snd

COIN_ITEMS = [
    ("life",      "+1 VIE",      "Récupère une vie",          80,  MAGENTA, "commun"),
    ("life2",     "+2 VIES",     "Deux vies d'un coup",       145, MAGENTA, "peu commun"),
    ("slow",      "SLOWMO",      "Ralentit obstacles (5s)",   55,  YELLOW,  "commun"),
    ("shield",    "BOUCLIER",    "Invincible (4s)",            95,  CYAN,    "peu commun"),
    ("bomb",      "BOMBE",       "Efface tous les obstacles", 110, ORANGE,  "peu commun"),
    ("magnet",    "AIMANT",      "Attire les items (5s)",      65,  GREEN,   "commun"),
    ("teleport",  "TÉL. ×3",    "3 charges de téléport",     85,  WHITE,   "peu commun"),
    ("score2x",   "SCORE ×2",    "Double le score (10s)",     140, YELLOW,  "rare"),
    ("xp2x",      "XP ×2",       "Double l'XP (manche)",     120, PURPLE,  "rare"),
    ("shrink",    "SHRINK",      "Réduit la hitbox (8s)",      75,  PINK,    "commun"),
    ("ghost",     "GHOST",       "Traverse phantoms (6s)",     90,  PURPLE,  "peu commun"),
    ("repair",    "RÉPARATION",  "Soigne 0.5 vie",             60,  GREEN,   "commun"),
    ("attack+",   "ATK BONUS",   "Rayon d'attaque +50%",      100, CYAN,    "rare"),
    ("forbid",    "INTERDIT",    "Bloque 1 type de proj.",    130, ORANGE,  "rare"),
    ("invincible","INVINCIBLE",  "30s d'invincibilité !",     400, GOLD,    "légendaire"),
    ("lifesteal", "VOL DE VIE",  "Collecte = +0.2 vie",       350, RED,     "épique"),
    ("chain_atk", "CHAIN ATK",   "L'attaque rebondit ×3",     300, TEAL,    "épique"),
]

RARITY_ORDER = ["commun","peu commun","rare","épique","légendaire"]
RARITY_COLORS_MAP = {
    "commun":GREY,"peu commun":GREEN,"rare":CYAN,"épique":PURPLE,"légendaire":GOLD
}

def _apply_shop_item(iid, coins, lives, inv, xp_sys):
    if iid=="life":    lives=min(lives+1,12)
    elif iid=="life2": lives=min(lives+2,12)
    elif iid=="repair":lives=min(lives+0.5,12)
    elif iid in ("slow","shield","bomb","magnet","shrink","ghost","score2x","xp2x",
                 "attack+","forbid","invincible","lifesteal","chain_atk"):
        inv[iid]=inv.get(iid,0)+1
    elif iid=="teleport": inv["teleport"]=inv.get("teleport",0)+3
    return coins,lives,inv

def _ai_shop(coins,lives,inv,xp_sys,hardcore,atk_sys=None):
    mult=1.3 if hardcore else 1.0
    prios=[]
    if lives<=2:   prios+=[("life2",2),("life",3)]
    elif lives<=4: prios+=[("life",1)]
    prios+=[("bomb",1),("shield",2),("slow",2),("magnet",2),("teleport",1),
            ("xp2x",1),("score2x",1),("shrink",2),("ghost",1),("attack+",1),("forbid",1)]
    for iid,mq in prios:
        row=next((r for r in COIN_ITEMS if r[0]==iid),None)
        if not row: continue
        cost=int(row[3]*mult); qty=0
        while coins>=cost and qty<mq:
            coins-=cost; coins,lives,inv=_apply_shop_item(iid,coins,lives,inv,xp_sys); qty+=1
    if atk_sys:
        for upg_id,info in XP_UPGRADES.items():
            lvl=atk_sys.upgrades.get(upg_id,0)
            if lvl<info[4]:
                cost=int(info[2]*(info[3]**lvl))
                if xp_sys.spend_upgrade_xp(cost): atk_sys.upgrades[upg_id]=lvl+1
    return coins,lives,inv


def run_shop(coins,lives,inv,xp_sys,auto_mode,fonts,hardcore=False,
             stats=None,current_bg="space",atk_sys=None):
    if auto_mode:
        c,l,i=_ai_shop(coins,lives,inv,xp_sys,hardcore,atk_sys)
        return c,l,i,current_bg,atk_sys

    F_BIG=fonts["big"]; F_MED=fonts["med"]; F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    screen=pygame.display.get_surface(); clock=pygame.time.Clock()
    msg=""; msg_t=0
    tab="items"   # "items" | "upgrades" | "attacks"

    # Filtre rareté pour items
    rarity_filter = "toutes"   # "toutes" ou une rareté spécifique
    dropdown_open = False       # menu déroulant ouvert

    # Scroll pour la liste items
    scroll_offset = 0
    ITEM_H = 80   # hauteur d'une ligne item

    while True:
        tick=pygame.time.get_ticks()//16
        screen.fill(BG_COLORS[current_bg]); draw_bg(screen,tick,current_bg)

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
            if ev.type==pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_ESCAPE):
                    return coins,lives,inv,current_bg,atk_sys
                if ev.key==pygame.K_b:
                    current_bg=BACKGROUNDS[(BACKGROUNDS.index(current_bg)+1)%len(BACKGROUNDS)]
                if ev.key==pygame.K_TAB:
                    tabs=["items","upgrades","attacks"]
                    tab=tabs[(tabs.index(tab)+1)%len(tabs)]
                    dropdown_open=False; scroll_offset=0
                if ev.key in (pygame.K_UP,):    scroll_offset=max(0,scroll_offset-1)
                if ev.key in (pygame.K_DOWN,):  scroll_offset+=1
            if ev.type==pygame.MOUSEWHEEL:
                # Nombre de lignes selon l'onglet courant
                if tab=="items":
                    n_items=len(_get_filtered_items(rarity_filter)); ncols=3
                elif tab=="upgrades":
                    n_items=len(XP_UPGRADES); ncols=3
                else:
                    n_items=len(ATTACK_TYPES); ncols=3
                total_rows=max(1,(n_items+ncols-1)//ncols)
                max_scroll=max(0,total_rows-5)   # 5 lignes visibles
                scroll_offset=max(0,min(max_scroll,scroll_offset-ev.y))

            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                mx,my=pygame.mouse.get_pos()

                # Onglets
                for ti,(tlbl,ttab) in enumerate([("ITEMS ¢","items"),("AMÉL. XP","upgrades"),("ATTAQUES","attacks")]):
                    tr=pygame.Rect(30+ti*310,145,295,36)
                    if tr.collidepoint(mx,my): tab=ttab; dropdown_open=False; scroll_offset=0; break

                if tab=="items":
                    # Bouton dropdown rareté
                    dd_btn=pygame.Rect(30,188,220,32)
                    if dd_btn.collidepoint(mx,my):
                        dropdown_open=not dropdown_open
                    elif dropdown_open:
                        # Sélection dans dropdown
                        for ri,rar in enumerate(["toutes"]+RARITY_ORDER):
                            dr=pygame.Rect(30,220+ri*32,220,30)
                            if dr.collidepoint(mx,my):
                                rarity_filter=rar; dropdown_open=False; scroll_offset=0
                                break
                        else:
                            dropdown_open=False
                    else:
                        # Clic sur item
                        visible=_get_filtered_items(rarity_filter)
                        COLS=3; CONTENT_Y=230; ITEM_W=(W-60)//COLS
                        for vi,row in enumerate(visible):
                            row_i=(vi//COLS)-scroll_offset; col_i=vi%COLS
                            if row_i<0 or row_i>4: continue
                            bx=30+col_i*ITEM_W; by=CONTENT_Y+row_i*ITEM_H
                            rect=pygame.Rect(bx,by,ITEM_W-8,ITEM_H-8)
                            iid,_,_,base_cost,_,rar=row
                            mult=1.3 if hardcore else 1.0
                            rc_mult=RARITIES.get(rar,(WHITE,rar,1.0))[2]; cost=int(base_cost*mult*rc_mult)
                            if rect.collidepoint(mx,my):
                                if coins>=cost:
                                    coins-=cost; coins,lives,inv=_apply_shop_item(iid,coins,lives,inv,xp_sys)
                                    msg=f"✓ {row[1]} acheté !"; msg_t=100; snd.play("buy_item")
                                else: msg="Pas assez de ¢ !"; msg_t=80

                elif tab=="upgrades" and atk_sys:
                    for ui,(upg_id,upg_info) in enumerate(XP_UPGRADES.items()):
                        ci=ui%3; ri2=ui//3; bx=30+ci*305; by=195+ri2*155
                        rect=pygame.Rect(bx,by,288,138)
                        if rect.collidepoint(mx,my):
                            lvl=atk_sys.upgrades.get(upg_id,0)
                            if lvl>=upg_info[4]: msg="Niveau MAX !"; msg_t=80
                            else:
                                cost=int(upg_info[2]*(upg_info[3]**lvl))
                                if xp_sys.spend_upgrade_xp(cost):
                                    atk_sys.upgrades[upg_id]=lvl+1
                                    _apply_upgrade(atk_sys,upg_id,lvl+1)
                                    msg=f"✓ {upg_info[0]} amélioré !"; msg_t=100; snd.play("buy_item")
                                else: msg="Pas assez d'XP !"; msg_t=80

                elif tab=="attacks" and atk_sys:
                    for ai,(atk_id,info) in enumerate(ATTACK_TYPES.items()):
                        ci=ai%2; ri2=ai//2; bx=30+ci*455; by=195+ri2*155
                        rect=pygame.Rect(bx,by,438,140)
                        if rect.collidepoint(mx,my):
                            unlock_xp=info[5]
                            if atk_id in atk_sys.unlocked:
                                atk_sys.current=atk_id; msg=f"✓ {info[0]} sélectionné !"; msg_t=80
                            elif xp_sys.total_xp_ever>=unlock_xp:
                                atk_sys.unlocked.append(atk_id); atk_sys.current=atk_id
                                msg=f"✓ {info[0]} débloqué !"; msg_t=100; snd.play("buy_item")
                            else: msg=f"Besoin de {unlock_xp} XP total"; msg_t=80

        # ── Header ────────────────────────────────────────────────────────────
        glow(screen,"BOUTIQUE",F_BIG,CYAN,(cx("BOUTIQUE",F_BIG),10))
        glow(screen,f"¢ {int(coins)}",F_MED,GREEN,(W//2-200,88))
        glow(screen,f"XP dispo: {int(xp_sys.upgrade_xp)}",F_MED,PURPLE,(W//2+20,88))
        if hardcore: screen.blit(F_XSM.render("HARDCORE — prix ×1.3",True,RED),(cx("HARDCORE — prix ×1.3",F_XSM),118))
        draw_bar(screen,pygame.Rect(W//2-220,128,440,14),xp_sys.xp,xp_sys.xp_next,PURPLE,
                 text=f"LVL {xp_sys.level}  {xp_sys.xp}/{xp_sys.xp_next}")

        # Onglets
        for ti,(tlbl,ttab) in enumerate([("ITEMS ¢","items"),("AMÉL. XP","upgrades"),("ATTAQUES","attacks")]):
            tr=pygame.Rect(30+ti*310,145,295,36); act=(tab==ttab)
            pygame.draw.rect(screen,(25,25,55) if act else (12,12,30),tr,border_radius=8)
            pygame.draw.rect(screen,CYAN if act else GREY,tr,2,border_radius=8)
            ts=F_SM.render(tlbl,True,CYAN if act else GREY)
            screen.blit(ts,(tr.centerx-ts.get_width()//2,tr.centery-ts.get_height()//2))

        mx2,my2=pygame.mouse.get_pos()

        # ── Contenu ────────────────────────────────────────────────────────────
        if tab=="items":
            _draw_items_dropdown(screen,fonts,rarity_filter,dropdown_open,
                                 coins,lives,inv,hardcore,scroll_offset,mx2,my2)
        elif tab=="upgrades":
            _draw_upgrades_tab(screen,fonts,atk_sys,xp_sys,mx2,my2)
        elif tab=="attacks":
            _draw_attacks_tab(screen,fonts,atk_sys,xp_sys,mx2,my2)

        # Inventaire + message
        inv_p=[f"{k[:4].upper()}×{v}" for k,v in inv.items() if v>0]
        if inv_p:
            t2="Inv: "+"  ".join(inv_p)
            screen.blit(F_XSM.render(t2,True,CYAN),(cx(t2,F_XSM),H-50))
        if msg_t>0: glow(screen,msg,F_MED,GREEN if "✓" in msg else RED,(cx(msg,F_MED),H-86)); msg_t-=1

        hint="[TAB] Onglets   [↑↓/Molette] Défiler   [B] Fond   [ESPACE] Continuer"
        pulse=int(200+55*math.sin(tick*0.08))
        glow(screen,hint,F_XSM,(0,pulse,pulse//2),(cx(hint,F_XSM),H-15))
        pygame.display.flip(); clock.tick(60)


def _get_filtered_items(rarity_filter:str) -> list:
    if rarity_filter=="toutes": return COIN_ITEMS
    return [r for r in COIN_ITEMS if r[5]==rarity_filter]


def _draw_items_dropdown(screen,fonts,rarity_filter,dropdown_open,
                          coins,lives,inv,hardcore,scroll_offset,mx,my):
    F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    # Bouton dropdown
    rc=RARITY_COLORS_MAP.get(rarity_filter, WHITE) if rarity_filter!="toutes" else WHITE
    dd_btn=pygame.Rect(30,188,220,32)
    pygame.draw.rect(screen,(20,20,40),dd_btn,border_radius=6)
    pygame.draw.rect(screen,rc,dd_btn,2,border_radius=6)
    lbl_text=f"Rareté : {rarity_filter.upper()}  ▼"
    screen.blit(F_XSM.render(lbl_text,True,rc),(dd_btn.x+8,dd_btn.y+8))

    # Légendes raretés à droite
    x_leg=270
    for rar in RARITY_ORDER:
        rc2=RARITY_COLORS_MAP[rar]; n=sum(1 for r in COIN_ITEMS if r[5]==rar)
        s=F_XSM.render(f"● {rar.upper()} ({n})",True,rc2); screen.blit(s,(x_leg,194)); x_leg+=s.get_width()+18

    # Menu déroulant
    if dropdown_open:
        for ri,rar in enumerate(["toutes"]+RARITY_ORDER):
            dr=pygame.Rect(30,220+ri*32,220,30)
            rc3=RARITY_COLORS_MAP.get(rar,WHITE) if rar!="toutes" else WHITE
            hov=dr.collidepoint(mx,my); sel=(rar==rarity_filter)
            pygame.draw.rect(screen,(30,30,60) if (hov or sel) else (15,15,35),dr,border_radius=6)
            pygame.draw.rect(screen,rc3,dr,2 if sel else 1,border_radius=6)
            screen.blit(F_XSM.render(rar.upper(),True,rc3),(dr.x+10,dr.y+7))
        return  # Ne pas afficher les items pendant que le dropdown est ouvert

    # Items filtrés
    visible=_get_filtered_items(rarity_filter)
    COLS=3; CONTENT_Y=230; ITEM_W=(W-60)//COLS; ITEM_H=80
    MAX_ROWS=5  # nombre de lignes visibles
    # Clip
    clip=pygame.Rect(0,CONTENT_Y,W,MAX_ROWS*ITEM_H+4)
    old_clip=screen.get_clip(); screen.set_clip(clip)

    for vi,row in enumerate(visible):
        iid,lbl,desc,base_cost,col,rar=row
        row_i=(vi//COLS)-scroll_offset; col_i=vi%COLS
        if row_i<0 or row_i>=MAX_ROWS: continue
        bx=30+col_i*ITEM_W; by=CONTENT_Y+row_i*ITEM_H
        rect=pygame.Rect(bx,by,ITEM_W-8,ITEM_H-6)
        mult=1.3 if hardcore else 1.0
        rc_mult=RARITIES.get(rar,(WHITE,rar,1.0))[2]; cost=int(base_cost*mult*rc_mult)
        ok=coins>=cost; rc4=RARITY_COLORS_MAP.get(rar,WHITE); hov=rect.collidepoint(mx,my)
        bg=tuple(min(255,c//3+18) for c in col) if hov else (12,12,32)
        pygame.draw.rect(screen,bg,rect,border_radius=8)
        pygame.draw.rect(screen,col if ok else GREY,rect,2,border_radius=8)
        # Badge rareté (petit)
        rb=F_XSM.render(rar[:3].upper(),True,rc4)
        screen.blit(rb,(bx+rect.w-rb.get_width()-5,by+4))
        screen.blit(F_SM.render(lbl,True,col if ok else GREY),(bx+7,by+5))
        screen.blit(F_XSM.render(desc[:32],True,WHITE if ok else GREY),(bx+7,by+28))
        cs=F_SM.render(f"¢ {cost}",True,GREEN if ok else RED); screen.blit(cs,(bx+7,by+52))

    screen.set_clip(old_clip)
    # Scrollbar
    total_rows=math.ceil(len(visible)/COLS)
    if total_rows>MAX_ROWS:
        sb_h=int(MAX_ROWS/total_rows*(MAX_ROWS*ITEM_H))
        sb_y=CONTENT_Y+int(scroll_offset/total_rows*(MAX_ROWS*ITEM_H))
        pygame.draw.rect(screen,(30,30,50),pygame.Rect(W-12,CONTENT_Y,8,MAX_ROWS*ITEM_H),border_radius=4)
        pygame.draw.rect(screen,CYAN,pygame.Rect(W-12,sb_y,8,sb_h),border_radius=4)


def _draw_upgrades_tab(screen,fonts,atk_sys,xp_sys,mx,my):
    F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    if not atk_sys: return
    glow(screen,"Améliorations — coût en XP",F_SM,PURPLE,(cx("Améliorations — coût en XP",F_SM),185))
    for ui,(upg_id,info) in enumerate(XP_UPGRADES.items()):
        lbl,col,base_cost,mult_c,max_lvl,desc=info
        lvl=atk_sys.upgrades.get(upg_id,0)
        cost=int(base_cost*(mult_c**lvl)) if lvl<max_lvl else 0
        can=xp_sys.upgrade_xp>=cost and lvl<max_lvl
        ci=ui%3; ri2=ui//3; bx=30+ci*305; by=210+ri2*155
        rect=pygame.Rect(bx,by,288,138); hov=rect.collidepoint(mx,my)
        bg=tuple(min(255,c//3+18) for c in col) if hov else (12,12,32)
        pygame.draw.rect(screen,bg,rect,border_radius=10)
        pygame.draw.rect(screen,col if can else GREY,rect,2,border_radius=10)
        glow(screen,lbl,F_SM,col,(bx+10,by+8))
        screen.blit(F_XSM.render(desc,True,WHITE),(bx+10,by+36))
        draw_bar(screen,pygame.Rect(bx+10,by+62,268,14),lvl,max_lvl,col,text=f"NIV {lvl}/{max_lvl}")
        if lvl<max_lvl:
            cs=F_SM.render(f"XP: {cost}",True,GREEN if can else RED); screen.blit(cs,(bx+10,by+112))
        else:
            screen.blit(F_SM.render("MAX !",True,GOLD),(bx+10,by+112))


def _draw_attacks_tab(screen,fonts,atk_sys,xp_sys,mx,my):
    F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    if not atk_sys: return
    glow(screen,"Types d'attaques — XP total pour débloquer",F_SM,YELLOW,
         (cx("Types d'attaques — XP total pour débloquer",F_SM),185))
    for ai,(atk_id,info) in enumerate(ATTACK_TYPES.items()):
        lbl,col,radius,dmg,cd,unlock_xp,desc=info
        unlocked=(atk_id in atk_sys.unlocked); current=(atk_id==atk_sys.current)
        can_unlock=(xp_sys.total_xp_ever>=unlock_xp and not unlocked)
        ci=ai%2; ri2=ai//2; bx=30+ci*455; by=210+ri2*158
        rect=pygame.Rect(bx,by,438,145); hov=rect.collidepoint(mx,my)
        border=col if unlocked else (GREEN if can_unlock else GREY)
        bg=tuple(min(255,c//3+20) for c in col) if (hov or current) else (12,12,32)
        pygame.draw.rect(screen,bg,rect,border_radius=10)
        pygame.draw.rect(screen,border,rect,3 if current else 2,border_radius=10)
        if current: glow(screen,"▶ ACTIF",F_XSM,col,(bx+rect.w-72,by+8))
        glow(screen,lbl,F_SM,col,(bx+10,by+8))
        screen.blit(F_XSM.render(desc,True,WHITE),(bx+10,by+36))
        screen.blit(F_XSM.render(f"Rayon:{radius}px  Dmg:{dmg}  Cooldown:{cd}fr",True,GREY),(bx+10,by+58))
        if unlocked:
            screen.blit(F_SM.render("✓ DÉBLOQUÉ — cliquer pour activer",True,GREEN),(bx+10,by+110))
        elif can_unlock:
            screen.blit(F_SM.render(f"→ Cliquer pour débloquer ({unlock_xp} XP)",True,YELLOW),(bx+10,by+110))
        else:
            pct=min(100,int(xp_sys.total_xp_ever/max(1,unlock_xp)*100))
            screen.blit(F_SM.render(f"🔒 {xp_sys.total_xp_ever}/{unlock_xp} XP  ({pct}%)",True,GREY),(bx+10,by+110))


def _apply_upgrade(atk_sys, upg_id, new_lvl):
    if upg_id=="atk_dmg":    atk_sys.dmg_mult=1.0+new_lvl*0.15
    elif upg_id=="atk_spd":  atk_sys.cd_mult=max(0.3,1.0-new_lvl*0.08)
    elif upg_id=="atk_radius":atk_sys.radius_mult=1.0+new_lvl*0.12
    elif upg_id=="boss_dmg": atk_sys.boss_dmg_mult=1.0+new_lvl*0.20
