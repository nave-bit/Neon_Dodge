"""
main.py — NEON DODGE v5.0
Q/Z/S/D + clic droit = attaque
Attaques multiples, boss mobiles, LAZERRRR, courbe de difficulté réelle,
XP = monnaie d'amélioration, mode BOSS, chrono, items persistants
"""
import pygame, math, random, sys, time

from core.constants import (
    W, H, FPS, HUD_H, TITLE, BG, BG_COLORS, BACKGROUNDS,
    CYAN, MAGENTA, YELLOW, GREEN, ORANGE, RED, PURPLE, PINK, WHITE, GREY, GOLD,
    POWERUP_DUR, POWERUP_COL, BOSS_INTERVAL, ROUND_FRAMES,
    DIFFICULTY_TIERS, ATTACK_TYPES, MOUSE_ATTACK, load_fonts,
    ENERGY_PICKUP_GAIN, ENERGY_COST, XP_UPGRADES,
)
import core.save_manager as sm
import core.sound_manager as snd
from core.recorder import Recorder, CV2_OK

from systems.xp_system import XPSystem
from systems.hud       import draw_hud, draw_bg, glow, cx, draw_bar, neon_circ
from systems.shop      import run_shop, _apply_upgrade
from systems.animations import boss_death_animation, player_death_animation

from entities.player    import Player, AttackSystem
from entities.obstacle  import (Obstacle, LaserBeam, AttackWave,
                                 get_allowed_types, new_difficulty_tier_message)
from entities.pickup    import PUItem
from entities.particles import Particle, FloatText
from entities.boss      import Boss, BOSS_DEFS, pick_boss, DIFF_MULT

from screens.title      import screen_title
from screens.transition import run_transition, boss_intro
from screens.gameover   import screen_gameover
from screens.boss_mode  import screen_boss_mode

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.init()
_fullscreen = False
screen      = pygame.display.set_mode((W, H))
pygame.display.set_caption(TITLE)
clock       = pygame.time.Clock()
FONTS       = load_fonts()
SAVE        = sm.load()
KEYS        = SAVE["keys"]
recorder    = Recorder()
snd.init()
snd.configure_jukebox(SAVE.get("music_settings", {}))
snd.play_music("normal")
current_bg  = "space"

def toggle_fullscreen():
    """Bascule plein écran (F11)."""
    global screen, _fullscreen
    _fullscreen = not _fullscreen
    if _fullscreen:
        screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((W, H))


# ── Combo ─────────────────────────────────────────────────────────────────────
class ComboSystem:
    THRESH=[5,10,20,40,80]
    def __init__(self): self.count=0; self.display_t=0
    def dodged(self): self.count+=1; self.display_t=50
    def hit(self):    self.count=0;  self.display_t=0
    def update(self):
        if self.display_t>0: self.display_t-=1
    @property
    def mult(self) -> float:
        if self.count>=80: return 4.0
        if self.count>=40: return 3.0
        if self.count>=20: return 2.0
        if self.count>=10: return 1.5
        if self.count>=5:  return 1.2
        return 1.0
    def draw(self, surf, fonts):
        if self.count<5: return
        F_MED=fonts["med"]
        col=YELLOW if self.count<20 else (ORANGE if self.count<40 else RED)
        a=min(255,self.display_t*6)
        col_a=tuple(int(c*a/255) for c in col)
        s=F_MED.render(f"×{self.mult:.1f}  COMBO {self.count}",True,col_a)
        # en bas à droite (au-dessus de la légende des contrôles)
        surf.blit(s,(W-s.get_width()-20, H-58))


# ── Pause ─────────────────────────────────────────────────────────────────────
def _draw_char_stats(surf, player, atk_sys, xp_sys, lives):
    """Panneau des statistiques du personnage (overlay)."""
    F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    card=pygame.Rect(W//2-300,150,600,420)
    pygame.draw.rect(surf,(9,9,28),card,border_radius=14)
    pygame.draw.rect(surf,CYAN,card,2,border_radius=14)
    glow(surf,"STATS DU PERSO",F_MED,CYAN,(cx("STATS DU PERSO",F_MED),120))

    rows=[
        ("Vies",            f"{lives:.1f}",                       MAGENTA),
        ("Niveau XP",       f"{xp_sys.level}",                    PURPLE),
        ("Énergie max",     f"{int(player.energy_max)}",          CYAN),
        ("Énergie actuelle",f"{int(player.energy)}",              CYAN),
        ("Mult. dégâts",    f"×{atk_sys.dmg_mult:.2f}",           ORANGE),
        ("Mult. dégâts boss",f"×{atk_sys.boss_dmg_mult:.2f}",     RED),
        ("Mult. cadence",   f"×{atk_sys.cd_mult:.2f}",            GREEN),
        ("Mult. rayon",     f"×{atk_sys.radius_mult:.2f}",        PURPLE),
        ("Vitesse bonus",   f"×{player.extra_speed:.2f}",         GREEN),
    ]
    for i,(lbl,val,col) in enumerate(rows):
        ci=i%2; ri=i//2
        x0=card.x+24+ci*290; y0=card.y+18+ri*46
        surf.blit(F_XSM.render(lbl,True,GREY),(x0,y0))
        surf.blit(F_SM.render(val,True,col),(x0,y0+16))

    # Attaques débloquées + niveaux d'amélioration
    y=card.y+18+5*46
    surf.blit(F_XSM.render("ARMES & NIVEAUX :",True,WHITE),(card.x+24,y))
    y+=22
    for aid in atk_sys.unlocked:
        lbl=ATTACK_TYPES[aid][0]; col=ATTACK_TYPES[aid][1]; lvl=atk_sys.upgrades.get(aid,0)
        cost=ENERGY_COST.get(aid,0); ct="gratuit" if cost==0 else f"{cost}⚡"
        t=f"{lbl}  niv.{lvl}  ({ct})"
        surf.blit(F_XSM.render(t,True,col),(card.x+40,y)); y+=22

    surf.blit(F_XSM.render("[S] Fermer les stats",True,GREY),
              (cx("[S] Fermer les stats",F_XSM),card.bottom-26))


def screen_pause(score:int, round_num:int, player=None, atk_sys=None,
                 xp_sys=None, lives:float=0.0) -> str:
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    sfx_v=0.6; music_v=0.35; show_stats=False
    can_stats = player is not None and atk_sys is not None and xp_sys is not None
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_s and can_stats:
                    show_stats=not show_stats; continue
                if show_stats:
                    # en mode stats, seul S (ou ESC) referme
                    if ev.key in (pygame.K_ESCAPE,): show_stats=False
                    continue
                if ev.key in (pygame.K_p,pygame.K_ESCAPE,pygame.K_RETURN): return "resume"
                if ev.key==pygame.K_q: return "quit"
                if ev.key==pygame.K_UP:    sfx_v=min(1.0,sfx_v+0.1);   snd.set_sfx_volume(sfx_v)
                if ev.key==pygame.K_DOWN:  sfx_v=max(0.0,sfx_v-0.1);   snd.set_sfx_volume(sfx_v)
                if ev.key==pygame.K_RIGHT: music_v=min(1.0,music_v+0.1);snd.set_music_volume(music_v)
                if ev.key==pygame.K_LEFT:  music_v=max(0.0,music_v-0.1);snd.set_music_volume(music_v)
                if ev.key==pygame.K_m: snd.toggle()
            if ev.type==pygame.MOUSEBUTTONDOWN and not show_stats:
                mx,my=pygame.mouse.get_pos()
                if pygame.Rect(W//2-90,445,180,46).collidepoint(mx,my): return "resume"
                if pygame.Rect(W//2-90,505,180,46).collidepoint(mx,my): return "quit"
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,150)); screen.blit(ov,(0,0))

        if show_stats:
            _draw_char_stats(screen,player,atk_sys,xp_sys,lives)
            pygame.display.flip(); clock.tick(30); continue

        glow(screen,"PAUSE",F_BIG,CYAN,(cx("PAUSE",F_BIG),90))
        for yi,(lbl,val,col) in enumerate([
            (f"Score",f"{score:07d}",CYAN),(f"Manche",str(round_num),WHITE)]):
            s=F_SM.render(f"{lbl} : {val}",True,col); screen.blit(s,(cx(f"{lbl} : {val}",F_SM),220+yi*36))
        for yi,(lbl,v,col) in enumerate([("SFX  ↑↓",sfx_v,CYAN),("MUSIC ←→",music_v,MAGENTA)]):
            draw_bar(screen,pygame.Rect(W//2-150,325+yi*48,300,18),v,1.0,col,text=f"{lbl}  {int(v*100)}%")
        mx2,my2=pygame.mouse.get_pos()
        for rect,lbl,col in [(pygame.Rect(W//2-90,445,180,46),"▶ REPRENDRE",GREEN),
                              (pygame.Rect(W//2-90,505,180,46),"✕ QUITTER",RED)]:
            hov=rect.collidepoint(mx2,my2)
            pygame.draw.rect(screen,tuple(min(255,c//3+30) for c in col) if hov else (15,15,35),rect,border_radius=9)
            pygame.draw.rect(screen,col,rect,2,border_radius=9)
            s=F_SM.render(lbl,True,col); screen.blit(s,(rect.centerx-s.get_width()//2,rect.centery-s.get_height()//2))
        hint="[P/ESC] Reprendre  [Q] Quitter  [M] Mute" + ("  [S] Stats perso" if can_stats else "")
        screen.blit(F_XSM.render(hint,True,GREY),(cx(hint,FONTS["xsm"]),H-24))
        pygame.display.flip(); clock.tick(30)


# ── Round ─────────────────────────────────────────────────────────────────────
def run_round(round_num:int, lives:float, coins:float, inv:dict,
              xp_sys:XPSystem, auto_mode:bool, hardcore:bool,
              stats:dict, atk_sys:AttackSystem,
              boss_mode_id:str=None, boss_difficulty:str="basic",
              play_time:list=None) -> tuple:
    global current_bg

    player    = Player(auto=auto_mode, xp_sys=xp_sys, keys=KEYS,
                       skin=SAVE.get("selected_skin","cyan"))
    player.atk_sys = atk_sys
    # Appliquer upgrades persistants
    for upg_id, lvl in atk_sys.upgrades.items():
        if lvl>0: _apply_upgrade(atk_sys, upg_id, lvl)
    player.sync_from_upgrades()

    obstacles: list = []; pu_items: list = []; particles: list = []
    floats:    list = []; waves:    list = []; lasers:    list = []
    combo     = ComboSystem()

    score=0; tick=0; spawn_cd=0; pu_cd=220
    active={k:0 for k in POWERUP_DUR}
    hitstop=0; flash_alpha=0

    score2x_t  = inv.pop("score2x",0)*600
    xp2x_t     = inv.pop("xp2x",0)*ROUND_FRAMES
    tel_charges = inv.pop("teleport",0)
    invincible_t= inv.pop("invincible",0)*1800
    lifesteal   = inv.pop("lifesteal",0)>0
    chain_atk   = inv.pop("chain_atk",0)>0

    forbidden_projs=[]
    if inv.get("forbid",0)>0:
        inv["forbid"]-=1
        forbidden_projs=[random.choice(["bomb","meteor"])]
        floats.append(FloatText(W//2,H//2+40,f"INTERDIT: {forbidden_projs[0].upper()}",ORANGE))
    if inv.get("shrink",0)>0:
        inv["shrink"]-=1; active["shrink"]=POWERUP_DUR["shrink"]; player.shrink_t=POWERUP_DUR["shrink"]
    if inv.get("ghost",0)>0:
        inv["ghost"]-=1; active["ghost"]=POWERUP_DUR["ghost"];  player.ghost_t=POWERUP_DUR["ghost"]
    if invincible_t>0: player.invincible=invincible_t

    # Boss
    boss_interval=BOSS_INTERVAL//(2 if hardcore else 1)
    is_boss_round=(boss_mode_id is not None) or (xp_sys.level%boss_interval==0 and xp_sys.level>1)
    boss=None
    if is_boss_round:
        bid=boss_mode_id or pick_boss(xp_sys.level,hardcore)
        boss=Boss(bid, xp_sys.level, difficulty=boss_difficulty if boss_mode_id else ("brutal" if hardcore else "basic"))
        bh=SAVE["boss_history"].setdefault(bid,{"seen":0,"defeated":0})
        bh["seen"]+=1; sm.write(SAVE)
        snd.play("boss_spawn2" if bid in ("lazerrrr1","lazerrrr2") else "boss_spawn")
        snd.play_music("boss")
        boss_intro(screen,clock,FONTS,boss,current_bg)
    else:
        snd.play_music("normal")

    prev_xp_level=xp_sys.level
    game_start_time=time.time()

    def boom_all():
        for o in obstacles[:]:
            for _ in range(10): particles.append(Particle(o.x,o.y,o.color))
        obstacles.clear()
        if boss: boss.bomb_stun(); floats.append(FloatText(W//2,H//2-40,"BOSS ÉTOURDI !",GOLD))
        snd.play("boom")

    def add_float(x,y,text,color): floats.append(FloatText(x,y,text,color))

    def gain_xp(amount):
        nonlocal prev_xp_level
        g=amount*(2 if xp2x_t>0 else 1); lv=xp_sys.add(g)
        if lv:
            add_float(W//2,H//3,f"LEVEL UP ! LVL {xp_sys.level}",PURPLE); snd.play("levelup")
            # Vérifier si palier de difficulté franchi
            msg=new_difficulty_tier_message(prev_xp_level, xp_sys.level)
            if msg: add_float(W//2,H//2,msg,YELLOW)
            prev_xp_level=xp_sys.level
            # Vérifier nouvelles attaques
            new_atk=atk_sys.check_unlock(xp_sys.total_xp_ever)
            if new_atk:
                add_float(W//2,H//2+50,f"ATTAQUE DÉBLOQUÉE : {ATTACK_TYPES[new_atk][0]} !",GOLD)

    # ── Boucle ────────────────────────────────────────────────────────────────
    while True:
        mouse_attack=False
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE:
                    inv["teleport"]=tel_charges
                    if play_time is not None: play_time[0]+=time.time()-game_start_time
                    return score,lives,coins,inv,xp_sys,False,stats,atk_sys
                if ev.key==pygame.K_F11: toggle_fullscreen()
                if ev.key==pygame.K_p:
                    r=screen_pause(score,round_num,player,atk_sys,xp_sys,lives)
                    if r=="quit":
                        inv["teleport"]=tel_charges
                        if play_time is not None: play_time[0]+=time.time()-game_start_time
                        return score,lives,coins,inv,xp_sys,False,stats,atk_sys
                if ev.key==pygame.K_m: snd.toggle()
                if not auto_mode:
                    k=ev.key
                    # SHIFT = activer le turbo (maintenu)
                    if k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        player.turbo=True
                    # A = téléportation
                    if k==pygame.K_a and tel_charges>0:
                        # téléporte dans la direction du dernier mouvement, sinon vers le haut
                        kp=pygame.key.get_pressed(); d = KEYS["up"]
                        if   kp[KEYS["left"]]:  d=KEYS["left"]
                        elif kp[KEYS["right"]]: d=KEYS["right"]
                        elif kp[KEYS["down"]]:  d=KEYS["down"]
                        player.teleport(d,particles); tel_charges-=1; snd.play("teleport")
                        add_float(player.x,player.y-35,f"TÉLÉPORT ({tel_charges})",MAGENTA)
                    elif k==pygame.K_a:
                        add_float(player.x,player.y-35,"Pas de charge TP !",GREY)
                    # E = slow
                    if k==pygame.K_e and inv.get("slow",0)>0:
                        inv["slow"]-=1; stats["items_used"]+=1
                        active["slow"]=POWERUP_DUR["slow"]; add_float(W//2,H//2,"SLOWMO !",YELLOW)
                    # ESPACE = shield
                    if k==pygame.K_SPACE and inv.get("shield",0)>0:
                        inv["shield"]-=1; stats["items_used"]+=1
                        active["shield"]=POWERUP_DUR["shield"]; player.invincible=POWERUP_DUR["shield"]; snd.play("shield")
                        add_float(W//2,H//2,"BOUCLIER !",CYAN)
                    # Autres items sur touches restantes (bomb=B, magnet=F, score2x=G)
                    if k==pygame.K_b and inv.get("bomb",0)>0:
                        inv["bomb"]-=1; stats["items_used"]+=1; boom_all(); add_float(W//2,H//2,"BOOM !",ORANGE)
                    if k==pygame.K_f and inv.get("magnet",0)>0:
                        inv["magnet"]-=1; stats["items_used"]+=1; active["magnet"]=POWERUP_DUR["magnet"]; add_float(W//2,H//2,"AIMANT !",GREEN)
                    if k==pygame.K_g and inv.get("score2x",0)>0:
                        inv["score2x"]-=1; stats["items_used"]+=1; score2x_t=600; add_float(W//2,H//2,"SCORE×2 !",YELLOW)

            if ev.type==pygame.KEYUP:
                if ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    player.turbo=False

            # ── SOURIS ─────────────────────────────────────────────────────────
            if ev.type==pygame.MOUSEBUTTONDOWN and not auto_mode:
                if ev.button==1:   # clic GAUCHE = attaque
                    mouse_attack=True
                elif ev.button==3: # clic DROIT = change d'attaque
                    atk_sys.switch()
                    add_float(player.x,player.y-40,
                        f"ATK: {ATTACK_TYPES[atk_sys.current][0]}",ATTACK_TYPES[atk_sys.current][1])

        keys_pressed=pygame.key.get_pressed()
        for k2 in active:
            if active[k2]>0: active[k2]-=1
        if score2x_t>0: score2x_t-=1
        if xp2x_t>0:    xp2x_t-=1
        if hitstop>0:    hitstop-=1
        if flash_alpha>0:flash_alpha=max(0,flash_alpha-16)
        slow_f=0.32 if active["slow"]>0 else 1.0
        combo.update()
        if boss and boss.alive and boss.spell_locked:
            for k2 in active: active[k2]=0

        if hitstop>0:
            _draw_frame(screen,current_bg,tick,active,player,obstacles,pu_items,waves,
                        particles,floats,lasers,boss,score,lives,coins,xp_sys,round_num,
                        score2x_t,xp2x_t,hardcore,tel_charges,forbidden_projs,auto_mode,
                        combo,flash_alpha,inv,atk_sys)
            recorder.capture(screen); pygame.display.flip(); clock.tick(FPS); tick+=1
            if play_time is not None: play_time[0]+=1/FPS
            continue

        # Spawn
        if not (boss and boss.alive):
            rate=max(12,50-round_num*2-(score//500))
            if spawn_cd<=0:
                obstacles.append(Obstacle(round_num,slow_f,forbidden_projs,xp_sys.level))
                spawn_cd=rate+random.randint(-4,4)
            spawn_cd-=1
            if tick%180==0 and xp_sys.level>=20:
                lasers.append(LaserBeam(random.choice([0,45,90,135]),hardcore))

        if boss and boss.alive:
            boss.update(player.x,player.y,particles)

        pu_cd-=1
        if pu_cd<=0: pu_items.append(PUItem()); pu_cd=random.randint(150,290)

        mpos=pygame.mouse.get_pos()
        action=player.update(keys_pressed,obstacles,pu_items,active,inv,tick,
                              boss if boss and boss.alive else None, mouse_attack)
        if action=="bomb": boom_all(); add_float(W//2,H//2,"BOOM ! (IA)",ORANGE)
        if action=="attack" and player.attack_cd==0:
            cur=atk_sys.current
            if player.can_attack(cur):
                player.spend_energy(cur)
                w=player.do_attack(mpos); waves.append(w); stats["attacks"]+=1
                # Son : laser pour le rayon, sinon attack
                snd.play("laser" if cur=="beam" else "attack")
                if auto_mode: mouse_attack=False
                # Flash visuel autour du joueur
                for _ in range(8): particles.append(Particle(player.x,player.y,ATTACK_TYPES[cur][1],1.2))
            else:
                # Pas assez d'énergie -> repli sur l'ONDE gratuite
                if cur!="wave":
                    add_float(player.x,player.y-40,"PLUS D'ÉNERGIE !",RED)
                    atk_sys.current="wave"

        if active["magnet"]>0:
            for pu in pu_items:
                dx=player.x-pu.x; dy=player.y-pu.y; d=max(1,math.hypot(dx,dy))
                pu.x+=dx/d*3.5; pu.y+=dy/d*3.5

        # ── Couloir boss (WINDING) — dégâts si hors zone verte ───────────────
        if boss and boss.alive and boss.id in ("winding","winding2"):
            in_safe, corridor_dmg=boss.check_corridor(player.x,player.y)
            if not in_safe and player.invincible==0:
                if corridor_dmg>=999:   # one-shot
                    lives=0; floats.append(FloatText(player.x,player.y-40,"ONE SHOT !",RED))
                    if play_time is not None: play_time[0]+=time.time()-game_start_time
                    player_death_animation(screen,clock,player.x,player.y,FONTS,recorder)
                    return score,0,coins,inv,xp_sys,False,stats,atk_sys
                else:
                    lives-=corridor_dmg
                    if tick%30==0:   # feedback toutes les 0.5s
                        add_float(player.x,player.y-35,"ZONE DANGER !",RED)
                    if lives<=0:
                        if play_time is not None: play_time[0]+=time.time()-game_start_time
                        player_death_animation(screen,clock,player.x,player.y,FONTS,recorder)
                        return score,0,coins,inv,xp_sys,False,stats,atk_sys

        # Attack waves
        for w in waves[:]:
            w.update()
            if not w.alive: waves.remove(w); continue
            for o in obstacles[:]:
                if w.hits(o.x,o.y):
                    o.hp-=1
                    for _ in range(8): particles.append(Particle(o.x,o.y,o.color))
                    if o.hp<=0:
                        obstacles.remove(o); gain_xp(o.xp_val)
                        score+=int(15*combo.mult*(2 if score2x_t>0 else 1)); coins+=1
                        if lifesteal: lives=min(lives+0.2,12)
                    # Chain attack rebondit sur obstacle suivant
                    if chain_atk and o.hp<=0 and obstacles:
                        near=min(obstacles,key=lambda ob:math.hypot(ob.x-o.x,ob.y-o.y),default=None)
                        if near: near.hp-=1
            # Dégâts boss
            if boss and boss.alive and w.hits_boss(boss.bx,boss.by):
                did_dmg=boss.take_damage(w.boss_dmg)
                if did_dmg:
                    for _ in range(10): particles.append(Particle(boss.bx,boss.by,boss.color))
                    add_float(boss.bx,boss.by-50,f"-{w.boss_dmg:.1f}",RED)
                    if not boss.alive: coins,score=_on_boss_defeated(boss,coins,score,floats,stats); snd.play_music("normal")

        # Obstacles vs player
        for o in obstacles[:]:
            o.update(slow_f)
            if o.off_screen:
                obstacles.remove(o); gain_xp(o.xp_val)
                score+=int(20*combo.mult*(2 if score2x_t>0 else 1)); coins+=2; combo.dodged(); continue
            ghost_ok=active.get("ghost",0)>0 and o.is_phantom
            if player.invincible==0 and not ghost_ok and o.collides(player.x,player.y,player.R):
                for _ in range(28): particles.append(Particle(player.x,player.y,CYAN))
                lives-=o.dmg; obstacles.remove(o); player.invincible=80
                combo.hit(); snd.play("hit"); hitstop=6; flash_alpha=170
                add_float(player.x,player.y-40,f"-{o.dmg:.1f} ({o.kind.upper()})",RED)
                if lives<=0:
                    inv["teleport"]=tel_charges
                    if play_time is not None: play_time[0]+=time.time()-game_start_time
                    player_death_animation(screen,clock,player.x,player.y,FONTS,recorder)
                    return score,0,coins,inv,xp_sys,False,stats,atk_sys

        # Boss vs player
        if boss and boss.alive:
            dmg,bullet=boss.collides_player(player.x,player.y,player.R)
            if dmg and player.invincible==0:
                lives-=dmg; player.invincible=80
                if bullet and bullet in boss.bullets: boss.bullets.remove(bullet)
                add_float(player.x,player.y-40,f"-{dmg:.1f} BOSS",RED)
                for _ in range(20): particles.append(Particle(player.x,player.y,RED))
                combo.hit(); snd.play("hit"); hitstop=8; flash_alpha=210
                if lives<=0:
                    inv["teleport"]=tel_charges
                    if play_time is not None: play_time[0]+=time.time()-game_start_time
                    player_death_animation(screen,clock,player.x,player.y,FONTS,recorder)
                    return score,0,coins,inv,xp_sys,False,stats,atk_sys
            if not boss.alive:
                coins,score=_on_boss_defeated(boss,coins,score,floats,stats); snd.play_music("normal")

        # Lasers standalone
        for l in lasers[:]:
            l.update()
            if l.off_screen: lasers.remove(l); continue
            if l.collides_player(player.x,player.y,player.R) and player.invincible==0:
                lives-=l.dmg; player.invincible=80; combo.hit(); snd.play("hit")
                add_float(player.x,player.y-40,f"-{l.dmg:.1f} LASER",RED)
                hitstop=5; flash_alpha=150
                if lives<=0:
                    inv["teleport"]=tel_charges
                    if play_time is not None: play_time[0]+=time.time()-game_start_time
                    player_death_animation(screen,clock,player.x,player.y,FONTS,recorder)
                    return score,0,coins,inv,xp_sys,False,stats,atk_sys

        # Collecte
        for pu in pu_items[:]:
            pu.update()
            if pu.off_screen: pu_items.remove(pu); continue
            if pu.collides(player.x,player.y,player.R):
                pu_items.remove(pu)
                for _ in range(12): particles.append(Particle(pu.x,pu.y,pu.color))
                lives,coins=_apply_pickup(pu,lives,coins,active,player,xp_sys,xp2x_t,floats,lifesteal,inv)
                coins+=3; stats["items_collected"]+=1; snd.play("collect")

        particles[:]=[p for p in particles if p.alive]; [p.update() for p in particles]
        floats[:]   =[f for f in floats    if f.alive]; [f.update() for f in floats]
        score+=int(1*combo.mult*(2 if score2x_t>0 else 1))

        # Fin de manche BOSS (mode boss OU manche-boss normale) : quand le boss meurt.
        # Pas de timer pendant un combat de boss.
        if boss is not None and not boss.alive:
            bonus=round_num*60; score+=bonus; coins+=round_num*18; gain_xp(round_num*80)
            inv["teleport"]=tel_charges
            if play_time is not None: play_time[0]+=time.time()-game_start_time
            return score,lives,coins,inv,xp_sys,True,stats,atk_sys

        # Fin de manche NORMALE (sans boss) : au temps écoulé.
        if boss is None and tick>=ROUND_FRAMES and not boss_mode_id:
            bonus=round_num*60; score+=bonus; coins+=round_num*18; gain_xp(round_num*80)
            inv["teleport"]=tel_charges
            if play_time is not None: play_time[0]+=time.time()-game_start_time
            return score,lives,coins,inv,xp_sys,True,stats,atk_sys

        _draw_frame(screen,current_bg,tick,active,player,obstacles,pu_items,waves,
                    particles,floats,lasers,boss,score,lives,coins,xp_sys,round_num,
                    score2x_t,xp2x_t,hardcore,tel_charges,forbidden_projs,auto_mode,
                    combo,flash_alpha,inv,atk_sys)
        recorder.capture(screen); pygame.display.flip(); clock.tick(FPS)
        if not (boss and boss.alive): snd.update_music()
        tick+=1
        if play_time is not None: play_time[0]+=1/FPS


# ── Draw frame ────────────────────────────────────────────────────────────────
def _draw_frame(screen,current_bg,tick,active,player,obstacles,pu_items,waves,
                particles,floats,lasers,boss,score,lives,coins,xp_sys,round_num,
                score2x_t,xp2x_t,hardcore,tel_charges,forbidden_projs,auto_mode,
                combo,flash_alpha,inv,atk_sys):
    screen.fill(BG_COLORS[current_bg]); draw_bg(screen,tick,current_bg)

    # Couloir boss WINDING (overlay AVANT les entités)
    if boss and boss.alive and boss.id in ("winding","winding2"):
        boss.draw_corridor_overlay(screen)

    if active["slow"]>0:
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((255,215,0,int(18+10*math.sin(tick*0.2)))); screen.blit(ov,(0,0))
    if active["shield"]>0:
        neon_circ(screen,CYAN,(int(player.x),int(player.y)),player.R+14+int(3*math.sin(tick*0.28)),2)
    for l  in lasers:    l.draw(screen)
    for o  in obstacles: o.draw(screen)
    for pu in pu_items:  pu.draw(screen,tick)
    for w  in waves:     w.draw(screen)
    for p  in particles: p.draw(screen)
    player.draw(screen,tick)
    for f  in floats:    f.draw(screen)
    if boss and boss.alive: boss.draw(screen,FONTS)
    if flash_alpha>0:
        fov=pygame.Surface((W,H),pygame.SRCALPHA); fov.fill((255,0,0,flash_alpha)); screen.blit(fov,(0,0))
    draw_hud(screen,FONTS,score,lives,coins,xp_sys,active,round_num,tick,
             score2x_t,xp2x_t,hardcore,player.attack_cd)

    # ── Barre d'ÉNERGIE (en haut à gauche, sous la barre XP) ─────────
    en_col = CYAN if player.energy > player.energy_max*0.25 else RED
    if player.turbo: en_col = YELLOW
    draw_bar(screen, pygame.Rect(10, 66, 220, 12),
             player.energy, player.energy_max, en_col,
             text=f"ENERGIE {int(player.energy)}/{int(player.energy_max)}")
    if player.turbo:
        screen.blit(FONTS["xsm"].render("TURBO",True,YELLOW),(236,66))

    # ── Barre de vie du BOSS (tout en haut, compacte) ────────────────
    if boss and boss.alive:
        boss.draw_hp_bar(screen, FONTS, y0=2)

    # Attaque active affichée (clic droit pour changer) — à gauche sous le HUD
    cur=atk_sys.current
    atk_lbl=ATTACK_TYPES[cur][0]; atk_col=ATTACK_TYPES[cur][1]
    cost=ENERGY_COST.get(cur,0)
    cost_txt = "gratuit" if cost==0 else f"{cost} energie"
    atk_s=FONTS["xsm"].render(f"ATK: {atk_lbl} ({cost_txt})  [clic droit] changer",True,atk_col)
    screen.blit(atk_s,(10, HUD_H+6))

    # Timer bar — MASQUÉE pendant un combat de boss (la manche finit à la victoire/mort)
    if not (boss and boss.alive):
        pygame.draw.rect(screen,(18,18,38),pygame.Rect(0,HUD_H,W,5))
        pygame.draw.rect(screen,CYAN,pygame.Rect(0,HUD_H,int(W*(1-tick/ROUND_FRAMES)),5))
    combo.draw(screen,FONTS)

    # Charges de téléport — à droite sous le HUD
    if not auto_mode and tel_charges>0:
        screen.blit(FONTS["xsm"].render("TEL",True,MAGENTA),(W-120,HUD_H+8))
        for i in range(tel_charges):
            pygame.draw.circle(screen,MAGENTA,(W-90+i*18,HUD_H+14),5)

    if auto_mode: glow(screen,"IA AUTO",FONTS["xsm"],GREEN,(W//2-28,HUD_H+8))
    if forbidden_projs:
        screen.blit(FONTS["xsm"].render(f"INTERDIT:{forbidden_projs[0].upper()}",True,ORANGE),(10,HUD_H+26))

    # ── Légende des contrôles + compteurs d'items (en bas) ───────────
    if not auto_mode:
        # compteurs d'items détenus
        def n(k): return inv.get(k,0)
        items_line = (f"ESPACE bouclier x{n('shield')}   E slow x{n('slow')}   "
                      f"B bombe x{n('bomb')}   F aimant x{n('magnet')}   "
                      f"G score2x x{n('score2x')}   A teleport x{tel_charges}")
        il=FONTS["xsm"].render(items_line,True,WHITE)
        screen.blit(il,(cx(items_line,FONTS["xsm"]),H-34))
        legend = "CLIC G attaque   CLIC D changer arme   SHIFT turbo   P pause"
        ls=FONTS["xsm"].render(legend,True,GREY)
        screen.blit(ls,(cx(legend,FONTS["xsm"]),H-18))


# ── Helpers ───────────────────────────────────────────────────────────────────
def _record_boss_win(boss_id, difficulty):
    """Mémorise la meilleure difficulté à laquelle un boss a été vaincu."""
    from entities.boss import DIFFICULTIES_ORDER
    bh = SAVE["boss_history"].setdefault(boss_id, {"seen":0,"defeated":0})
    prev = bh.get("best_diff")
    # Garde la difficulté la plus élevée
    order = DIFFICULTIES_ORDER
    if prev is None or order.index(difficulty) > order.index(prev):
        bh["best_diff"] = difficulty
    sm.write(SAVE)


def _on_boss_defeated(boss,coins,score,floats,stats=None):
    bh=SAVE["boss_history"].setdefault(boss.id,{"seen":0,"defeated":0})
    bh["defeated"]+=1; sm.write(SAVE)
    if stats is not None:
        stats.setdefault("bosses_defeated",[]).append(boss.name)
    # Animation spectaculaire (une seule fois)
    if not getattr(boss, "_death_played", False):
        boss._death_played = True
        snd.play("boss_killed")
        boss_death_animation(screen, clock, boss.bx, boss.by,
                             boss.color, boss.name, FONTS, recorder)
    floats.append(FloatText(W//2,H//3,"BOSS VAINCU ! +200¢  +500pts",GOLD))
    return coins+200, score+500

def _record_run(hardcore, total, rounds, level, stats):
    """Enregistre la partie dans l'historique (dernière + top 5) par mode."""
    import time as _t
    mode = "hardcore" if hardcore else "rush"
    hist = SAVE.setdefault("run_history", {})
    mh   = hist.setdefault(mode, {"last": None, "best": []})
    entry = {
        "score": int(total), "rounds": int(rounds), "level": int(level),
        "bosses": len(stats.get("bosses_defeated", [])),
        "date": _t.strftime("%d/%m %H:%M"),
    }
    mh["last"] = entry
    mh["best"] = sorted(mh["best"] + [entry], key=lambda e: e["score"], reverse=True)[:5]
    # Gagner des pièces pour les skins (≈ score/100 + 20 par boss vaincu)
    earned = int(total/100) + 20*len(stats.get("bosses_defeated", []))
    SAVE["skin_coins"] = SAVE.get("skin_coins", 0) + earned
    sm.write(SAVE)


def screen_music(save):
    """Interface de sélection/écoute des musiques de jeu + options de lecture."""
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    settings = save.setdefault("music_settings",
                               {"mode":"loop","shuffle":False,"selected":[],"resume":True,"allow_interrupt":True})
    settings.setdefault("allow_interrupt", True)
    tracks = snd.list_game_music()              # [(fichier, libellé)]
    if not settings.get("selected") and tracks:
        settings["selected"] = [tracks[0][0]]
    preview_fn = None                            # musique en cours d'écoute

    def save_and_apply():
        save["music_settings"] = settings; sm.write(save)
        snd.configure_jukebox(settings)

    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,pygame.K_RETURN):
                snd.stop_music(300); save_and_apply(); return
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                mx,my=pygame.mouse.get_pos()
                # Lignes des musiques
                for i,(fn,lbl) in enumerate(tracks):
                    row=pygame.Rect(80, 175+i*54, W-160, 46)
                    # case cocher (gauche)
                    chk=pygame.Rect(row.x+10, row.y+12, 22, 22)
                    # bouton écouter (droite)
                    play_btn=pygame.Rect(row.right-150, row.y+8, 130, 30)
                    if chk.collidepoint(mx,my):
                        if fn in settings["selected"]:
                            if len(settings["selected"])>1: settings["selected"].remove(fn)
                        else:
                            settings["selected"].append(fn)
                        save_and_apply()
                    elif play_btn.collidepoint(mx,my):
                        if preview_fn==fn:
                            snd.stop_music(200); preview_fn=None
                        else:
                            snd.preview_music(fn); preview_fn=fn
                # Boutons options (bas)
                if pygame.Rect(80,  H-150, 200, 40).collidepoint(mx,my):
                    settings["mode"]="playlist" if settings["mode"]=="loop" else "loop"; save_and_apply()
                if pygame.Rect(300, H-150, 200, 40).collidepoint(mx,my):
                    settings["shuffle"]=not settings["shuffle"]; save_and_apply()
                if pygame.Rect(520, H-150, 320, 40).collidepoint(mx,my):
                    settings["resume"]=not settings["resume"]; save_and_apply()
                if pygame.Rect(80, H-200, 760, 36).collidepoint(mx,my):
                    settings["allow_interrupt"]=not settings.get("allow_interrupt",True); save_and_apply()

        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        glow(screen,"MUSIQUE",F_BIG,CYAN,(cx("MUSIQUE",F_BIG),36))
        info="Coche les musiques de jeu · écoute-les · règle la lecture en bas"
        screen.blit(F_XSM.render(info,True,GREY),(cx(info,F_XSM),112))

        mx,my=pygame.mouse.get_pos()
        if not tracks:
            nm="Aucune musique trouvée. Dépose des fichiers music_*.ogg dans assets/sounds/"
            screen.blit(F_SM.render(nm,True,ORANGE),(cx(nm,F_SM),300))
        for i,(fn,lbl) in enumerate(tracks):
            row=pygame.Rect(80, 175+i*54, W-160, 46)
            checked = fn in settings["selected"]
            pygame.draw.rect(screen,(14,14,34),row,border_radius=8)
            pygame.draw.rect(screen,CYAN if checked else GREY,row,2,border_radius=8)
            # case à cocher
            chk=pygame.Rect(row.x+10, row.y+12, 22, 22)
            pygame.draw.rect(screen,CYAN if checked else (40,40,60),chk,border_radius=4)
            if checked:
                pygame.draw.lines(screen,BG,False,[(chk.x+4,chk.y+11),(chk.x+9,chk.y+17),(chk.x+18,chk.y+5)],3)
            screen.blit(F_SM.render(lbl,True,WHITE),(row.x+46,row.y+12))
            # bouton écouter
            play_btn=pygame.Rect(row.right-150, row.y+8, 130, 30)
            playing = (preview_fn==fn)
            pygame.draw.rect(screen,(30,60,30) if playing else (24,24,48),play_btn,border_radius=6)
            pygame.draw.rect(screen,GREEN if playing else CYAN,play_btn,2,border_radius=6)
            blbl="⏸ STOP" if playing else "▶ ÉCOUTER"
            screen.blit(F_XSM.render(blbl,True,GREEN if playing else CYAN),
                        (play_btn.centerx-F_XSM.size(blbl)[0]//2,play_btn.y+7))

        # Options de lecture
        def opt_btn(rect,label,active,col):
            hov=rect.collidepoint(mx,my)
            pygame.draw.rect(screen,(30,30,55) if (active or hov) else (14,14,32),rect,border_radius=8)
            pygame.draw.rect(screen,col,rect,2,border_radius=8)
            screen.blit(F_XSM.render(label,True,col if active else GREY),
                        (rect.centerx-F_XSM.size(label)[0]//2,rect.centery-6))
        ai = settings.get("allow_interrupt",True)
        opt_btn(pygame.Rect(80,H-200,760,36),
                f"Interrompre pour boss / boutique : {'OUI' if ai else 'NON (la musique de jeu continue)'}",
                ai, ORANGE)
        mode_lbl = "Mode : BOUCLE" if settings["mode"]=="loop" else "Mode : PLAYLIST"
        opt_btn(pygame.Rect(80,H-150,200,40), mode_lbl, True, CYAN)
        opt_btn(pygame.Rect(300,H-150,200,40), f"Aléatoire : {'OUI' if settings['shuffle'] else 'NON'}",
                settings["shuffle"], PURPLE)
        opt_btn(pygame.Rect(520,H-150,320,40),
                f"Après boss/boutique : {'REPRENDRE' if settings['resume'] else 'PISTE SUIVANTE'}",
                True, GOLD)
        hint="[ÉCHAP] Retour et sauvegarder   ·   En PLAYLIST, les musiques cochées s'enchaînent"
        screen.blit(F_XSM.render(hint,True,GREY),(cx(hint,F_XSM),H-90))
        screen.blit(F_XSM.render("[ÉCHAP] Retour",True,GREY),(cx("[ÉCHAP] Retour",F_XSM),H-40))
        pygame.display.flip(); clock.tick(30)


def screen_skins(save):
    """Écran de personnalisation : choisir / acheter un skin du joueur."""
    from core.constants import PLAYER_SKINS
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    msg=""; msg_t=0
    ids=list(PLAYER_SKINS.keys())
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,pygame.K_RETURN):
                return
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                mx,my=pygame.mouse.get_pos()
                for i,sid in enumerate(ids):
                    col_i=i%4; row_i=i//4
                    rect=pygame.Rect(80+col_i*210, 200+row_i*180, 190, 160)
                    if rect.collidepoint(mx,my):
                        name,scol,tcol,price,shape=PLAYER_SKINS[sid]
                        owned=save.get("owned_skins",["cyan"])
                        if sid in owned:
                            save["selected_skin"]=sid; sm.write(save)
                            msg=f"✓ {name} équipé !"; msg_t=90
                        else:
                            # achat avec les pièces du record (coins persistants ? sinon hiscore-based)
                            wallet=save.get("skin_coins",0)
                            if wallet>=price:
                                save["skin_coins"]=wallet-price
                                owned.append(sid); save["owned_skins"]=owned
                                save["selected_skin"]=sid; sm.write(save)
                                msg=f"✓ {name} acheté et équipé !"; msg_t=90; snd.play("buy_item")
                            else:
                                msg=f"Pas assez de ¢ (besoin {price})"; msg_t=90
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        glow(screen,"SKINS",F_BIG,GOLD,(cx("SKINS",F_BIG),40))
        wallet=save.get("skin_coins",0)
        wt=f"Porte-monnaie : {wallet} ¢   (gagné en fin de partie)"
        screen.blit(F_XSM.render(wt,True,YELLOW),(cx(wt,F_XSM),120))
        sel=save.get("selected_skin","cyan"); owned=save.get("owned_skins",["cyan"])
        mx,my=pygame.mouse.get_pos()
        for i,sid in enumerate(ids):
            name,scol,tcol,price,shape=PLAYER_SKINS[sid]
            col_i=i%4; row_i=i//4
            rect=pygame.Rect(80+col_i*210, 200+row_i*180, 190, 160)
            hov=rect.collidepoint(mx,my)
            pygame.draw.rect(screen,(14,14,34) if not hov else (24,24,50),rect,border_radius=10)
            border = GOLD if sid==sel else (scol if sid in owned else GREY)
            pygame.draw.rect(screen,border,rect,3 if sid==sel else 2,border_radius=10)
            # aperçu de la forme
            cxp,cyp=rect.centerx,rect.y+62; r=20
            if shape=="circle": neon_circ(screen,scol,(cxp,cyp),r,3)
            elif shape=="square": pygame.draw.rect(screen,scol,pygame.Rect(cxp-r,cyp-r,2*r,2*r),3,border_radius=3)
            elif shape=="triangle": pygame.draw.polygon(screen,scol,[(cxp,cyp-r),(cxp-r,cyp+r),(cxp+r,cyp+r)],3)
            elif shape=="diamond": pygame.draw.polygon(screen,scol,[(cxp,cyp-r),(cxp+r,cyp),(cxp,cyp+r),(cxp-r,cyp)],3)
            screen.blit(F_SM.render(name,True,scol),(rect.centerx-F_SM.size(name)[0]//2,rect.y+100))
            if sid==sel:
                screen.blit(F_XSM.render("ÉQUIPÉ",True,GOLD),(rect.centerx-F_XSM.size("ÉQUIPÉ")[0]//2,rect.y+128))
            elif sid in owned:
                screen.blit(F_XSM.render("possédé · clic",True,GREEN),(rect.centerx-F_XSM.size("possédé · clic")[0]//2,rect.y+128))
            else:
                screen.blit(F_XSM.render(f"{price} ¢",True,YELLOW),(rect.centerx-F_XSM.size(f"{price} ¢")[0]//2,rect.y+128))
        if msg_t>0:
            msg_t-=1; screen.blit(F_SM.render(msg,True,WHITE),(cx(msg,F_SM),H-60))
        screen.blit(F_XSM.render("[ÉCHAP] Retour",True,GREY),(cx("[ÉCHAP] Retour",F_XSM),H-28))
        pygame.display.flip(); clock.tick(30)


def _shop_preview():
    """Aperçu lecture seule de la boutique (items ¢ et améliorations XP) avant la partie."""
    from systems.shop import COIN_ITEMS
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    scroll=0
    rows = [("ITEMS (¢)", None)]
    for iid,lbl,desc,cost,col,rar in COIN_ITEMS:
        rows.append((f"{lbl}", (desc, cost, col, rar)))
    rows.append(("AMÉLIORATIONS (XP)", None))
    for uid,info in XP_UPGRADES.items():
        lbl,col,base,mult,maxl,desc=info
        rows.append((lbl, (desc, base, col, f"max niv.{maxl}")))
    VISIBLE=12
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE): return
            if ev.type==pygame.MOUSEWHEEL:
                scroll=max(0,min(max(0,len(rows)-VISIBLE),scroll-ev.y))
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button!=1: return
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        glow(screen,"BOUTIQUE",F_BIG,GOLD,(cx("BOUTIQUE",F_BIG),40))
        screen.blit(F_XSM.render("Aperçu des prix (achat pendant la partie)",True,GREY),
                    (cx("Aperçu des prix (achat pendant la partie)",F_XSM),120))
        y=160
        for lbl,data in rows[scroll:scroll+VISIBLE]:
            if data is None:
                screen.blit(F_MED.render(lbl,True,CYAN),(80,y)); y+=42
            else:
                desc,cost,col,rar=data
                screen.blit(F_SM.render(lbl,True,col),(110,y))
                screen.blit(F_XSM.render(desc,True,GREY),(330,y+4))
                screen.blit(F_SM.render(str(cost),True,YELLOW),(W-180,y))
                screen.blit(F_XSM.render(str(rar),True,GREY),(W-120,y+4))
                y+=34
        msg="[molette] défiler    [ÉCHAP] Retour"
        screen.blit(F_XSM.render(msg,True,GREY),(cx(msg,F_XSM),H-30))
        pygame.display.flip(); clock.tick(30)


def screen_history(save):
    """Écran d'historique : dernière partie + meilleures, pour chaque mode."""
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE):
                return
            if ev.type==pygame.MOUSEBUTTONDOWN:
                return
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        glow(screen,"HISTORIQUE",F_BIG,CYAN,(cx("HISTORIQUE",F_BIG),50))
        hist=save.get("run_history",{})
        for ci,(mode,label,col) in enumerate([("rush","RUSH",GREEN),("hardcore","HARDCORE",RED)]):
            x0=60+ci*(W//2-30)
            card=pygame.Rect(x0,150,W//2-90,440)
            pygame.draw.rect(screen,(9,9,26),card,border_radius=12)
            pygame.draw.rect(screen,col,card,2,border_radius=12)
            screen.blit(F_MED.render(label,True,col),(card.centerx-F_MED.size(label)[0]//2,card.y+12))
            mh=hist.get(mode,{})
            last=mh.get("last"); best=mh.get("best",[])
            y=card.y+64
            screen.blit(F_SM.render("Dernière partie :",True,WHITE),(card.x+20,y)); y+=30
            if last:
                t=f"  {last['score']:07d} pts · M{last['rounds']} · niv.{last['level']} · {last['bosses']} boss"
                screen.blit(F_XSM.render(t,True,CYAN),(card.x+20,y)); y+=22
                screen.blit(F_XSM.render(f"  {last.get('date','')}",True,GREY),(card.x+20,y)); y+=34
            else:
                screen.blit(F_XSM.render("  aucune",True,GREY),(card.x+20,y)); y+=34
            screen.blit(F_SM.render("Meilleures parties :",True,WHITE),(card.x+20,y)); y+=30
            if best:
                for i,e in enumerate(best):
                    t=f"  {i+1}. {e['score']:07d} pts · M{e['rounds']} · niv.{e['level']}"
                    screen.blit(F_XSM.render(t,True,YELLOW),(card.x+20,y)); y+=24
            else:
                screen.blit(F_XSM.render("  aucune",True,GREY),(card.x+20,y))
        msg="[ÉCHAP / clic] Retour"
        screen.blit(F_XSM.render(msg,True,GREY),(cx(msg,F_XSM),H-30))
        pygame.display.flip(); clock.tick(30)


def _apply_pickup(pu,lives,coins,active,player,xp_sys,xp2x_t,floats,lifesteal,inv):
    def ft(x,y,t,c): floats.append(FloatText(x,y,t,c))
    if   pu.kind=="life":    lives=min(lives+1,12);    ft(pu.x,pu.y,"+1 VIE !",MAGENTA)
    elif pu.kind=="slow":    active["slow"]=POWERUP_DUR["slow"];    ft(pu.x,pu.y,"SLOWMO !",YELLOW)
    elif pu.kind=="bomb":    inv["bomb"]=inv.get("bomb",0)+1; ft(pu.x,pu.y,"+1 BOMBE !",ORANGE)
    elif pu.kind=="magnet":  active["magnet"]=POWERUP_DUR["magnet"];ft(pu.x,pu.y,"AIMANT !",GREEN)
    elif pu.kind=="shield":
        active["shield"]=POWERUP_DUR["shield"]; player.invincible=POWERUP_DUR["shield"]
        ft(pu.x,pu.y,"SHIELD !",CYAN); snd.play("shield")
    elif pu.kind=="xp":
        g=50*(2 if xp2x_t>0 else 1); xp_sys.add(g); ft(pu.x,pu.y,f"+{g}XP",PURPLE)
    elif pu.kind=="coin5":  coins+=5;  ft(pu.x,pu.y,"+5¢",YELLOW)
    elif pu.kind=="coin15": coins+=15; ft(pu.x,pu.y,"+15¢",GREEN)
    elif pu.kind=="energy":
        player.add_energy(ENERGY_PICKUP_GAIN); ft(pu.x,pu.y,f"+{ENERGY_PICKUP_GAIN} ÉNERGIE",CYAN)
    if lifesteal: lives=min(lives+0.2,12)
    return lives,coins


# ── HUD draw_hud (override to add timer) ─────────────────────────────────────
def draw_hud(surf, fonts, score, lives, coins, xp_sys, active,
             round_num, tick, score2x_t, xp2x_t, hardcore, attack_cd,
             play_time_s:float=0):
    from systems.hud import draw_hud as _dh
    _dh(surf,fonts,score,lives,coins,xp_sys,active,round_num,tick,
        score2x_t,xp2x_t,hardcore,attack_cd)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    global current_bg
    play_time = [0.0]   # [secondes] mutable pour être modifié dans run_round

    while True:
        auto_mode, hardcore, current_bg, mode = screen_title_with_boss_mode(
            screen, clock, FONTS, SAVE, BOSS_DEFS, current_bg
        )

        if mode == "boss":
            bid, bdiff, current_bg = screen_boss_mode(screen, clock, FONTS, SAVE, current_bg)
            if bid is None: continue
            # Budget d'équipement dégressif selon la difficulté
            BUDGET = {
                "basic":      (1200, 4000),
                "brutal":     (900,  3000),
                "destructeur":(650,  2200),
                "divin":      (450,  1500),
                "cauchemar":  (250,  800),
            }
            bcoins, bxp = BUDGET.get(bdiff, (1200, 4000))

            # phase: "equip" = passe par la boutique, "fight" = combat direct (relance)
            phase = "equip"
            saved_loadout = None   # (atk_sys, inv, coins, lives) pour relancer à l'identique

            while True:
                if phase == "equip":
                    xp_sys = XPSystem(); atk_sys = AttackSystem()
                    coins = bcoins
                    xp_sys.upgrade_xp = bxp        # XP dépensable en boutique
                    xp_sys.total_xp_ever = bxp     # pour débloquer les armes
                    inv = {}; lives = 5.0
                    stats = {"attacks":0,"items_used":0,"items_collected":0,"rounds":0,"bosses_defeated":[]}
                    # Phase d'équipement (réutilise la boutique) avant le combat
                    snd.play_music("shop")
                    coins,lives,inv,current_bg,atk_sys = run_shop(
                        coins,lives,inv,xp_sys,False,FONTS,False,stats,current_bg,atk_sys
                    )
                    # mémorise les conditions exactes pour une éventuelle relance
                    import copy
                    saved_loadout = (copy.deepcopy(atk_sys), dict(inv), coins, lives)
                else:  # phase == "fight" (relance dans les mêmes conditions)
                    import copy
                    src_atk, src_inv, src_coins, src_lives = saved_loadout
                    xp_sys = XPSystem()
                    xp_sys.upgrade_xp = bxp; xp_sys.total_xp_ever = bxp
                    atk_sys = copy.deepcopy(src_atk)
                    inv = dict(src_inv); coins = src_coins; lives = src_lives
                    stats = {"attacks":0,"items_used":0,"items_collected":0,"rounds":0,"bosses_defeated":[]}

                snd.play_music("boss")
                rs,lives,_,inv,xp_sys,survived,stats,atk_sys = run_round(
                    1,lives,coins,inv,xp_sys,False,False,stats,atk_sys,
                    boss_mode_id=bid, boss_difficulty=bdiff, play_time=play_time
                )

                if survived:
                    _record_boss_win(bid, bdiff)
                    _boss_mode_result_screen(bid, bdiff, rs)
                    break

                # Défaite → propose relancer / équipement / fuir
                snd.stop_music()
                action = _boss_mode_defeat_screen(bid, bdiff, rs)
                if action == "retry":
                    phase = "fight"; continue
                elif action == "equip":
                    phase = "equip"; continue
                else:  # flee → retour menu avec message
                    _boss_mode_flee_screen()
                    break
            continue

        xp_sys   = XPSystem()
        atk_sys  = AttackSystem()
        total    = 0; lives=3.0 if hardcore else 5.0; coins=40 if hardcore else 60
        inv={}; rounds=0
        stats={"attacks":0,"items_used":0,"items_collected":0,"rounds":0,"bosses_defeated":[]}
        snd.play_music("normal"); recorder.start()

        for round_num in range(1,99):
            rs,lives,coins,inv,xp_sys,survived,stats,atk_sys = run_round(
                round_num,lives,coins,inv,xp_sys,auto_mode,hardcore,
                stats,atk_sys,play_time=play_time
            )
            total+=rs; stats["rounds"]=round_num
            if not survived: break
            rounds+=1
            run_transition(screen,clock,FONTS,round_num,total,round_num*18,xp_sys,current_bg)
            snd.play_music("shop")
            coins,lives,inv,current_bg,atk_sys = run_shop(
                coins,lives,inv,xp_sys,auto_mode,FONTS,hardcore,stats,current_bg,atk_sys
            )
            snd.play_music("normal")

        hk="hiscore_hardcore" if hardcore else "hiscore"
        SAVE[hk]=max(SAVE.get(hk,0),total); sm.write(SAVE)
        _record_run(hardcore, total, rounds, xp_sys.level, stats)
        snd.stop_music(); snd.play("game_end")
        screen_gameover(screen,clock,FONTS,recorder,total,SAVE[hk],rounds,
                        xp_sys,stats,hardcore,BOSS_DEFS,SAVE,current_bg)


def screen_title_with_boss_mode(screen, clock, fonts, save, boss_defs, current_bg):
    """Écran titre étendu avec bouton MODE BOSS."""
    F_BIG=fonts["big"]; F_MED=fonts["med"]; F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
    choice=None
    while choice is None:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_a:  choice=("auto","rush","game")
                if ev.key in (pygame.K_RETURN,pygame.K_SPACE): choice=("player","rush","game")
                if ev.key==pygame.K_h:  choice=("player","hardcore","game")
                if ev.key==pygame.K_o:  choice=("player","rush","boss")
                if ev.key==pygame.K_k:
                    from screens.title import screen_keybinds
                    screen_keybinds(screen,clock,fonts,save)
                if ev.key==pygame.K_y:
                    screen_history(save)
                if ev.key==pygame.K_i:
                    _shop_preview()
                if ev.key==pygame.K_u:
                    screen_skins(save)
                if ev.key==pygame.K_j:
                    screen_music(save); snd.play_music("normal")
                if ev.key==pygame.K_b:
                    current_bg=BACKGROUNDS[(BACKGROUNDS.index(current_bg)+1)%len(BACKGROUNDS)]
            if ev.type==pygame.MOUSEBUTTONDOWN:
                mx,my=pygame.mouse.get_pos()
                btns=[
                    (pygame.Rect(W//2-310,340,140,52),"auto",  "game"),
                    (pygame.Rect(W//2-150,340,140,52),"player","game"),
                    (pygame.Rect(W//2+10, 340,140,52),"player","hardcore"),
                    (pygame.Rect(W//2+170,340,140,52),"player","boss"),
                ]
                for rect,mode,mtype in btns:
                    if rect.collidepoint(mx,my): choice=(mode,"rush" if mtype!="hardcore" else "hardcore",mtype); break
                if pygame.Rect(W//2-200,410,120,38).collidepoint(mx,my):
                    from screens.title import screen_keybinds
                    screen_keybinds(screen,clock,fonts,save)
                if pygame.Rect(W//2-65,410,130,38).collidepoint(mx,my):
                    screen_history(save)
                if pygame.Rect(W//2+80,410,120,38).collidepoint(mx,my):
                    _shop_preview()
                if pygame.Rect(W//2-200,456,250,30).collidepoint(mx,my):
                    screen_skins(save)
                if pygame.Rect(W//2+50,456,150,30).collidepoint(mx,my):
                    screen_music(save); snd.play_music("normal")
                if pygame.Rect(W//2-60,498,120,30).collidepoint(mx,my):
                    current_bg=BACKGROUNDS[(BACKGROUNDS.index(current_bg)+1)%len(BACKGROUNDS)]

        tick=pygame.time.get_ticks()//16
        screen.fill(BG_COLORS[current_bg]); draw_bg(screen,tick,current_bg)
        t=math.sin(tick*0.05)*6
        glow(screen,"NEON DODGE",F_BIG,CYAN,   (cx("NEON DODGE",F_BIG),  85+int(t)))
        glow(screen,"NEON DODGE",F_BIG,MAGENTA,(cx("NEON DODGE",F_BIG)+2,87+int(t)))
        glow(screen,"v5.0",F_XSM,GREY,(cx("v5.0",F_XSM),168))

        mx2,my2=pygame.mouse.get_pos()
        btn_data=[
            (pygame.Rect(W//2-310,340,140,52),"🤖 IA AUTO", GREEN,  "game"),
            (pygame.Rect(W//2-150,340,140,52),"🎮 JOUEUR",  CYAN,   "game"),
            (pygame.Rect(W//2+10, 340,140,52),"💀 HARDCORE",RED,    "game"),
            (pygame.Rect(W//2+170,340,140,52),"⚔ BOSS",    GOLD,   "boss"),
        ]
        for rect,lbl,col,_ in btn_data:
            hov=rect.collidepoint(mx2,my2)
            bg=tuple(min(255,c//3+25) for c in col) if hov else (12,12,32)
            pygame.draw.rect(screen,bg,rect,border_radius=9)
            pygame.draw.rect(screen,col,rect,2,border_radius=9)
            s=F_SM.render(lbl,True,col)
            screen.blit(s,(rect.centerx-s.get_width()//2,rect.centery-s.get_height()//2))

        for rect,lbl in [(pygame.Rect(W//2-200,410,120,38),"⚙ TOUCHES"),
                         (pygame.Rect(W//2-65,410,130,38),"📊 HISTORIQUE"),
                         (pygame.Rect(W//2+80,410,120,38),"🛒 BOUTIQUE"),
                         (pygame.Rect(W//2-200,456,250,30),"🎨 SKINS"),
                         (pygame.Rect(W//2+50,456,150,30),"🎵 MUSIQUE"),
                         (pygame.Rect(W//2-60,498,120,30),f"{current_bg.upper()}")]:
            hov2=rect.collidepoint(mx2,my2)
            pygame.draw.rect(screen,(20,20,20) if hov2 else (10,10,28),rect,border_radius=8)
            pygame.draw.rect(screen,GREY,rect,2,border_radius=8)
            s=F_XSM.render(lbl,True,WHITE); screen.blit(s,(rect.centerx-s.get_width()//2,rect.centery-6))

        defeated=[k for k,v in save["boss_history"].items() if v.get("defeated",0)>0]
        if defeated:
            dt="Boss vaincus: "+"  ".join(boss_defs[b][0][:8] for b in defeated)
            screen.blit(F_XSM.render(dt,True,GREY),(cx(dt,F_XSM),540))

        tips=["Q/Z/S/D bouger · CLIC GAUCHE attaque · CLIC DROIT change d'arme",
              "SHIFT turbo · ESPACE bouclier · A téléport · E slow · B bombe",
              "[Y] Historique  [I] Boutique  [U] Skins  [J] Musique  [K] Touches"]
        for i,tip in enumerate(tips):
            screen.blit(F_XSM.render(tip,True,GREY),(cx(tip,F_XSM),565+i*18))
        snd.update_music()
        pygame.display.flip(); clock.tick(60)

    mode,diff,mtype=choice
    return mode=="auto", diff=="hardcore", current_bg, mtype


def _boss_mode_flee_screen():
    """Écran affiché quand le joueur fuit le combat de boss."""
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_XSM=FONTS["xsm"]
    snd.play_music("normal")
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_ESCAPE):
                return
            if ev.type==pygame.MOUSEBUTTONDOWN:
                return
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,current_bg)
        to=int(math.sin(tick*0.08)*4)
        glow(screen,"LOSER",F_BIG,RED,(cx("LOSER",F_BIG)+1,H//2-80+to))
        glow(screen,"LOSER",F_BIG,MAGENTA,(cx("LOSER",F_BIG),H//2-80))
        msg="reviens quand tu seras plus fort"
        screen.blit(F_MED.render(msg,True,WHITE),(cx(msg,F_MED),H//2+10))
        pulse=int(200+55*math.sin(tick*0.09))
        glow(screen,"[ ESPACE / clic ]  Retour au menu",F_XSM,(pulse,0,pulse),
             (cx("[ ESPACE / clic ]  Retour au menu",F_XSM),H//2+90))
        pygame.display.flip(); clock.tick(60)


def _boss_mode_defeat_screen(boss_id:str, difficulty:str, score:int):
    """Écran de défaite en MODE BOSS. Retourne 'retry', 'equip' ou 'flee'."""
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_SM=FONTS["sm"]; F_XSM=FONTS["xsm"]
    from entities.boss import BOSS_DEFS, DIFF_LABELS, DIFF_COLORS
    info=BOSS_DEFS[boss_id]; dcol=DIFF_COLORS.get(difficulty,WHITE)

    retry_btn = pygame.Rect(W//2-330,430,200,56)
    equip_btn = pygame.Rect(W//2-100,430,200,56)
    flee_btn  = pygame.Rect(W//2+130,430,200,56)

    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_r: return "retry"
                if ev.key==pygame.K_e: return "equip"
                if ev.key in (pygame.K_f,pygame.K_ESCAPE): return "flee"
            if ev.type==pygame.MOUSEBUTTONDOWN:
                mx,my=pygame.mouse.get_pos()
                if retry_btn.collidepoint(mx,my): return "retry"
                if equip_btn.collidepoint(mx,my): return "equip"
                if flee_btn.collidepoint(mx,my):  return "flee"

        tick=pygame.time.get_ticks()//16
        mx,my=pygame.mouse.get_pos()
        screen.fill(BG); draw_bg(screen,tick,current_bg)

        to=int(math.sin(tick*0.07)*3)
        glow(screen,"VAINCU",F_BIG,RED,(cx("VAINCU",F_BIG)+1,80+to))
        glow(screen,"VAINCU",F_BIG,MAGENTA,(cx("VAINCU",F_BIG),80))

        sub=f"{info[0]}  [{DIFF_LABELS.get(difficulty,difficulty)}]"
        screen.blit(F_MED.render(sub,True,dcol),(cx(sub,F_MED),190))
        sc=f"Score : {score:07d}"
        screen.blit(F_SM.render(sc,True,CYAN),(cx(sc,F_SM),240))

        prompt="Que veux-tu faire ?"
        screen.blit(F_SM.render(prompt,True,WHITE),(cx(prompt,F_SM),340))

        for btn,lbl,col,hint,sub2 in [
            (retry_btn,"⟳ RELANCER",CYAN,"[R]","mêmes conditions"),
            (equip_btn,"⚙ ÉQUIPEMENT",GOLD,"[E]","ré-acheter avant"),
            (flee_btn, "🏃 FUIR",MAGENTA,"[F]","retour au menu"),
        ]:
            hov=btn.collidepoint(mx,my)
            bg=tuple(min(255,c//3+22) for c in col) if hov else (10,10,28)
            pygame.draw.rect(screen,bg,btn,border_radius=10)
            pygame.draw.rect(screen,col,btn,2,border_radius=10)
            ls=F_SM.render(lbl,True,col)
            screen.blit(ls,(btn.centerx-ls.get_width()//2,btn.y+8))
            hs=F_XSM.render(hint,True,GREY)
            screen.blit(hs,(btn.centerx-hs.get_width()//2,btn.y+30))
            ss=F_XSM.render(sub2,True,GREY)
            screen.blit(ss,(btn.centerx-ss.get_width()//2,btn.bottom+4))

        pygame.display.flip(); clock.tick(60)


def _boss_mode_result_screen(boss_id:str, difficulty:str, score:int):
    F_BIG=FONTS["big"]; F_MED=FONTS["med"]; F_XSM=FONTS["xsm"]
    from entities.boss import BOSS_DEFS, DIFF_LABELS, DIFF_COLORS
    info=BOSS_DEFS[boss_id]; dcol=DIFF_COLORS.get(difficulty,WHITE)
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_ESCAPE): return
        tick=pygame.time.get_ticks()//16
        screen.fill(BG); draw_bg(screen,tick,"space")
        glow(screen,"BOSS VAINCU !",F_BIG,GOLD,(cx("BOSS VAINCU !",F_BIG),120))
        glow(screen,info[0],F_MED,info[2],(cx(info[0],F_MED),218))
        screen.blit(F_MED.render(f"[{DIFF_LABELS.get(difficulty,difficulty)}]",True,dcol),
                    (cx(f"[{DIFF_LABELS.get(difficulty,difficulty)}]",F_MED),260))
        screen.blit(F_MED.render(f"Score : {score:07d}",True,CYAN),(cx(f"Score : {score:07d}",F_MED),310))
        pulse=int(200+55*math.sin(tick*0.09))
        glow(screen,"[ ESPACE ]  Retour",F_MED,(0,pulse,pulse//2),(cx("[ ESPACE ]  Retour",F_MED),400))
        pygame.display.flip(); clock.tick(60)


if __name__=="__main__":
    main()
