"""entities/boss.py — v5.1
Boss avec couloir WINDING redesigné : zone rouge = dégâts, verte = safe.
WINDING 1 : couloir de HAUT EN BAS
WINDING 2 : couloir de GAUCHE À DROITE + projectiles
One-shot si hors couloir en hardcore/boss_hard+
"""
import pygame, math, random
from core.constants import (
    W, H, HUD_H,
    CYAN, MAGENTA, YELLOW, GREEN, ORANGE, RED, WHITE, PURPLE, GREY, GOLD, TEAL,
)
from systems.hud import draw_bar, neon_circ, glow
from entities.obstacle import Obstacle, LaserBeam

BOSS_DEFS = {
    "winding":   ("CHEMIN BISCORNU",   "COMMUN",    CYAN,   16,  "Traverse le couloir vert — le rouge tue !"),
    "winding2":  ("BISCORNU INFERNAL", "RARE",      MAGENTA,26, "Couloir latéral + projectiles — précision requise"),
    "graviton":  ("GRAVITON",          "RARE",      PURPLE, 22, "Projectiles de toutes directions"),
    "antispell": ("ANTI-SPELL",        "LÉGENDAIRE",RED,    34, "Annule tous tes power-ups !"),
    "voidlord":  ("SEIGNEUR DU VIDE",  "LÉGENDAIRE",WHITE,  46, "Lasers + gravité + anti-spell"),
    "lazerrrr1": ("LAZERRRR  I",       "RARE",      ORANGE, 40, "Salves de lasers synchronisés — zone sûre !"),
    "lazerrrr2": ("LAZERRRR  II",      "LÉGENDAIRE",RED,    62, "Lasers diagonaux permanents"),
}
RARITY_COLORS = {"COMMUN":GREEN,"RARE":CYAN,"LÉGENDAIRE":GOLD}
# Échelle de difficulté repensée : "basic" est désormais un vrai défi
# (équivaut à l'ancien HARD), et deux crans encore plus durs sont ajoutés.
# Ordre : basic < brutal < destructeur < divin < cauchemar
DIFF_MULT   = {"basic":1.4,"brutal":1.9,"destructeur":2.6,"divin":3.5,"cauchemar":4.5}
# Multiplicateur de PV séparé (n'affecte PAS les dégâts du boss).
HP_MULT     = {"basic":2.2,"brutal":4.0,"destructeur":7.0,"divin":11.0,"cauchemar":16.0}
DIFF_LABELS = {"basic":"BASIC","brutal":"BRUTAL","destructeur":"DESTRUCTEUR","divin":"DIVIN","cauchemar":"CAUCHEMAR"}
DIFF_COLORS = {"basic":YELLOW,"brutal":ORANGE,"destructeur":RED,"divin":PURPLE,"cauchemar":(255,40,90)}
DIFFICULTIES_ORDER = ["basic","brutal","destructeur","divin","cauchemar"]

# Largeur du couloir selon la difficulté
CORRIDOR_W = {"basic":58,"brutal":46,"destructeur":38,"divin":28,"cauchemar":22}
# Dégâts hors couloir par frame (30 fps = /2)
CORRIDOR_DMG = {"basic":0.06,"brutal":0.12,"destructeur":0.5,"divin":999,"cauchemar":999}

def pick_boss(xp_level:int, hardcore:bool) -> str:
    if xp_level < 20:    pool=["winding","winding","graviton","lazerrrr1"]
    elif xp_level < 40:  pool=["winding","winding2","graviton","antispell","lazerrrr1"]
    else:                pool=["winding2","graviton","antispell","voidlord","lazerrrr1","lazerrrr2"]
    if hardcore: pool+=["antispell","voidlord","lazerrrr2"]
    return random.choice(pool)


def _point_in_corridor(px:float, py:float, path:list, width:float) -> bool:
    """Retourne True si (px,py) est dans le couloir (distance au segment < width/2)."""
    half = width / 2
    for i in range(len(path)-1):
        x1,y1 = path[i]; x2,y2 = path[i+1]
        lx=x2-x1; ly=y2-y1; ln=max(1, math.hypot(lx,ly))
        t = max(0, min(1, ((px-x1)*lx + (py-y1)*ly) / (ln*ln)))
        dist = math.hypot(px-(x1+t*lx), py-(y1+t*ly))
        if dist < half:
            return True
    return False


def _build_corridor_surface(path:list, width:float, orientation:str="vertical") -> pygame.Surface:
    """
    Construit une Surface semi-transparente :
    - Rouge (danger) sur tout l'écran
    - Vert (safe) sur le couloir
    """
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    # Fond rouge
    surf.fill((220, 0, 0, 110))
    # Couloir vert
    if len(path) > 1:
        pts_int = [(int(p[0]), int(p[1])) for p in path]
        pygame.draw.lines(surf, (0, 210, 60, 200), False, pts_int, int(width))
        # Bordures blanches pour la lisibilité
        pygame.draw.lines(surf, (255,255,255,120), False, pts_int, 3)
    return surf


class Boss:
    def __init__(self, boss_id:str, xp_level:int, difficulty:str="basic"):
        self.id    = boss_id
        info       = BOSS_DEFS[boss_id]
        self.name, self.rarity, self.color, hp_base, self.desc = info
        mult       = DIFF_MULT.get(difficulty, 1.0)
        hp_mult    = HP_MULT.get(difficulty, 1.0)
        self.hp    = int((hp_base + xp_level//3) * hp_mult)
        self.maxhp = self.hp
        self.diff  = difficulty
        self.tick  = 0
        self.alive = True
        self.stun_t   = 0
        self.stun_max = 90
        # Phases de repos : le boss alterne attaque / repos (ne peut pas attaquer en continu)
        self.resting    = False
        self._rest_timer= 0
        self._attack_window = random.randint(240, 360)  # frames d'attaque avant un repos

        # Position boss
        self.bx = float(W//2); self.by = float(HUD_H + 80)
        self._vx = random.choice([-1.2,1.2]) * mult
        self._target_x = float(W//2); self._target_y = float(HUD_H+80)
        self._move_cd  = 0

        self.bullets : list = []
        self.lasers  : list = []
        self.spell_locked = False
        self.shield_on    = False        # ANTI-SPELL : phase invulnérable
        self._last_px = float(W//2); self._last_py = float(H-110)
        # Pré-signalement d'attaque (télégraphie) : liste de (type,x,y,t_restant,t_total,angle)
        self._telegraphs : list = []

        # Couloir (winding)
        self._corridor_path  : list  = []
        self._corridor_surf  = None   # Surface pré-rendue
        self._corridor_w     : float = CORRIDOR_W.get(difficulty, 72)
        self._corridor_active: bool  = False
        self._corridor_warn  : int   = 0    # frames d'avertissement avant activation
        self._gen_phase      : int   = 0    # numéro de génération de chemin

        if boss_id in ("winding","winding2"):
            self._next_corridor()

        # LAZERRRR
        self._laz_phase  = "idle"
        self._laz_timer  = 0
        self._safe_cols  : list = []
        self._laz_lines  : list = []
        self._laz_beams  : list = []

    # ── Mouvement boss ────────────────────────────────────────────────────────
    def _update_movement(self):
        speed = 1.5 * DIFF_MULT[self.diff]
        if self.stun_t > 0: speed = 0.0
        if self.resting: speed *= 0.6   # se déplace doucement en repos
        self._move_cd -= 1

        px, py = self._last_px, self._last_py
        if self._move_cd <= 0:
            beh = self._move_behavior()
            if beh == "chase":
                # vise une position proche du joueur (mais reste en haut)
                self._target_x = max(80, min(W-80, px + random.uniform(-60,60)))
                self._target_y = random.uniform(HUD_H+50, H*0.34)
            elif beh == "strafe":
                # se décale latéralement par rapport au joueur
                side = random.choice([-1,1])
                self._target_x = max(80, min(W-80, px + side*random.uniform(180,320)))
                self._target_y = random.uniform(HUD_H+50, H*0.30)
            elif beh == "flee":
                # garde ses distances : va à l'opposé horizontal du joueur
                self._target_x = 80 if px > W/2 else W-80
                self._target_y = random.uniform(HUD_H+50, H*0.26)
            else:  # wander
                self._target_x = random.uniform(80, W-80)
                self._target_y = random.uniform(HUD_H+50, H*0.36)
            self._move_cd = random.randint(45,110)

        # déplacement fluide vers la cible
        dx=self._target_x-self.bx; dy=self._target_y-self.by; d=max(1,math.hypot(dx,dy))
        if d>4: self.bx+=dx/d*speed; self.by+=dy/d*speed
        self.bx=max(50,min(W-50,self.bx)); self.by=max(HUD_H+40,min(H*0.42,self.by))

    def _move_behavior(self) -> str:
        """Style de déplacement selon le boss."""
        return {
            "winding":  "wander", "winding2": "wander",
            "graviton": "strafe", "antispell":"chase",
            "voidlord": "strafe", "lazerrrr1":"flee", "lazerrrr2":"flee",
        }.get(self.id, "wander")

    # ── Génération couloir ────────────────────────────────────────────────────
    def _next_corridor(self):
        """Génère un nouveau couloir et prépare l'avertissement."""
        if self.id == "winding":
            self._corridor_path = self._gen_vertical_path()
        else:
            self._corridor_path = self._gen_horizontal_path()
        self._corridor_surf   = _build_corridor_surface(
            self._corridor_path, self._corridor_w)
        self._corridor_active = False
        self._corridor_warn   = 120   # 2s d'avertissement avant activation
        self._gen_phase      += 1

    def _gen_vertical_path(self) -> list:
        """Couloir HAUT → BAS avec virages naturels."""
        path=[]; x=random.randint(W//4, 3*W//4); y=HUD_H+20
        path.append((x,y))
        while y < H-20:
            x = max(80, min(W-80, x + random.randint(-160,160)))
            y += random.randint(55,100)
            path.append((x,y))
        return path

    def _gen_horizontal_path(self) -> list:
        """Couloir GAUCHE → DROITE (winding2), plus tortueux."""
        path=[]; x=20; y=random.randint(HUD_H+80, H-120)
        path.append((x,y))
        while x < W-20:
            x += random.randint(70,140)
            y = max(HUD_H+60, min(H-60, y+random.randint(-130,130)))
            path.append((x,y))
        return path

    def check_corridor(self, px:float, py:float) -> tuple:
        """
        Retourne (in_safe_zone: bool, dmg_per_frame: float).
        dmg=0 si dans le couloir ou couloir inactif.
        """
        if not self._corridor_active or not self._corridor_path:
            return True, 0.0
        in_zone = _point_in_corridor(px, py, self._corridor_path, self._corridor_w)
        if in_zone:
            return True, 0.0
        dmg = CORRIDOR_DMG.get(self.diff, 0.025)
        return False, dmg

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, px:float, py:float, particles:list, diff_mult:float=1.0):
        self.tick+=1
        self._last_px=px; self._last_py=py
        if self.stun_t>0: self.stun_t-=1
        self._update_movement()
        m=DIFF_MULT[self.diff]

        # ── Phases de repos : empêche l'attaque en continu ──────────────────────
        # Cycle : on attaque pendant _attack_window frames, puis on se repose ~90 frames.
        if self.resting:
            self._rest_timer-=1
            if self._rest_timer<=0:
                self.resting=False
                self._attack_window=random.randint(240,360)
        else:
            self._attack_window-=1
            if self._attack_window<=0:
                self.resting=True
                self._rest_timer=random.randint(70,110)
        # Pendant le repos, le boss bouge mais ne lance pas de nouvelles attaques.
        if self.resting:
            # on laisse vivre les projectiles/lasers existants mais on ne spawn rien
            self._update_existing()
            return

        if self.id=="winding":
            if self._corridor_warn>0:
                self._corridor_warn-=1
                if self._corridor_warn==0: self._corridor_active=True
            # Nouveau couloir toutes les ~5 secondes
            if self.tick % 300 == 0: self._next_corridor()

        elif self.id=="winding2":
            if self._corridor_warn>0:
                self._corridor_warn-=1
                if self._corridor_warn==0: self._corridor_active=True
            if self.tick%250==0: self._next_corridor()
            # + projectiles
            if self.tick%30==0:
                o=Obstacle(1); o.x=float(random.randint(40,W-40)); o.y=-20.0
                self.bullets.append(o)

        elif self.id=="graviton":
            interval=max(28,int(60/m))
            # Pré-signalement 25 frames avant la salve
            if self.tick%interval==interval-25:
                self._add_telegraph("burst", self.bx, self.by, 25)
            if self.tick%interval==0:
                for angle in range(0,360,30):
                    o=Obstacle(1); o.x=self.bx; o.y=self.by
                    rad=math.radians(angle); spd=2.6*m
                    o.vx=math.cos(rad)*spd; o.vy=math.sin(rad)*spd
                    self.bullets.append(o)

        elif self.id=="antispell":
            self.spell_locked=True
            # Cycle de bouclier : invulnérable par intermittence (il faut attendre l'ouverture)
            cyc = self.tick % 300
            self.shield_on = (cyc < 150)   # 150 frames blindé, 150 frames vulnérable
            # Salve en éventail vers le joueur quand le bouclier est actif
            if self.shield_on and self.tick%24==18:
                self._add_telegraph("aim", self.bx, self.by, 12,
                                    math.atan2(self._last_py-self.by, self._last_px-self.bx))
            if self.shield_on and self.tick%24==0:
                base_ang=math.atan2(self._last_py-self.by, self._last_px-self.bx)
                for off in (-0.35,0,0.35):
                    o=Obstacle(3); o.x=self.bx; o.y=self.by
                    spd=3.6*m; o.vx=math.cos(base_ang+off)*spd; o.vy=math.sin(base_ang+off)*spd
                    self.bullets.append(o)
            # Quand vulnérable, pluie de projectiles tombants (pression continue)
            if not self.shield_on and self.tick%18==0:
                o=Obstacle(2); o.x=float(random.randint(40,W-40)); o.y=-20.0
                o.vy=2.5*m; self.bullets.append(o)

        elif self.id=="voidlord":
            self.spell_locked=True
            if self.tick%40==15:
                self._add_telegraph("burst", self.bx, self.by, 25)
            if self.tick%40==0:
                for angle in range(0,360,45):
                    o=Obstacle(2); o.x=self.bx; o.y=self.by
                    rad=math.radians(angle); spd=3.2*m
                    o.vx=math.cos(rad)*spd; o.vy=math.sin(rad)*spd
                    self.bullets.append(o)
            if self.tick%100==0:
                self.lasers.append(LaserBeam(random.choice([0,45,90,135])))

        elif self.id=="lazerrrr1": self._update_lazerrrr1(m)
        elif self.id=="lazerrrr2": self._update_lazerrrr2(m)

        self._update_existing()

    def _update_existing(self):
        """Avance les projectiles et lasers déjà en vol (utilisé aussi en repos)."""
        for b in self.bullets[:]:
            b.y+=b.vy; b.x+=b.vx
            if b.x<-60 or b.x>W+60 or b.y>H+60 or b.y<-60: self.bullets.remove(b)
        for l in self.lasers[:]:
            l.update()
            if l.off_screen: self.lasers.remove(l)
        # Décrément des pré-signalements
        for t in self._telegraphs[:]:
            t[3]-=1
            if t[3]<=0: self._telegraphs.remove(t)

    def _add_telegraph(self, kind, x, y, dur, angle=0.0):
        """Enregistre un pré-signalement visuel (kind: 'burst' ou 'aim')."""
        self._telegraphs.append([kind, float(x), float(y), dur, dur, angle])

    # ── LAZERRRR ──────────────────────────────────────────────────────────────
    def _update_lazerrrr1(self, m):
        if self._laz_phase=="idle":
            if self.tick%max(80,int(180/m))==0:
                self._laz_phase="warn"; self._laz_timer=90
                n_cols=random.randint(8,11)
                xs=sorted(random.sample(range(60,W-60,60),min(n_cols,(W-120)//60)))
                self._safe_cols=random.sample(xs,1)
                self._laz_lines=[(x,ORANGE) for x in xs]
        elif self._laz_phase=="warn":
            self._laz_timer-=1
            if self._laz_timer<=0:
                self._laz_phase="fire"; self._laz_timer=22
                for (x,_) in self._laz_lines:
                    if x not in self._safe_cols:
                        lb=LaserBeam(90); lb.ox=float(x); lb.oy=float(HUD_H)
                        lb.warn=0; lb.active=True; lb.life=22; lb.dmg=2.5*m
                        self._laz_beams.append(lb)
        elif self._laz_phase=="fire":
            self._laz_timer-=1
            for lb in self._laz_beams[:]:
                lb.life-=1
                if lb.life<=0: self._laz_beams.remove(lb)
            if self._laz_timer<=0:
                self._laz_beams.clear(); self._laz_lines.clear(); self._safe_cols.clear()
                self._laz_phase="stun_anim"; self._laz_timer=self.stun_max; self.stun_t=self.stun_max
        elif self._laz_phase=="stun_anim":
            self._laz_timer-=1
            if self._laz_timer<=0: self._laz_phase="idle"

    def _update_lazerrrr2(self, m):
        """LAZERRRR II : lasers muraux, rythme soutenu mais lisible (warns plus longs)."""
        if self.stun_t > 0: return
        if self.resting: return
        freq       = max(14, int(40 / m))
        burst_freq = max(80, int(160 / m))
        n_burst    = max(2, int(3 * (m/2)))
        if self.tick % freq == 0:
            self.lasers.append(self._wall_laser(m))
        if self.tick % burst_freq == 0:
            for _ in range(n_burst):
                self.lasers.append(self._wall_laser(m))
            # Anneau radial seulement aux très hautes difficultés
            if m >= DIFF_MULT["divin"]:
                cx2=random.randint(100,W-100); cy2=random.randint(HUD_H+50,H-100)
                self._add_telegraph("burst", cx2, cy2, 30)
                for angle in range(0,360,60):
                    rad=math.radians(angle)
                    lb=LaserBeam.at(cx2-math.cos(rad)*50, cy2-math.sin(rad)*50, angle,
                                    warn=max(18,int(30/m)), life=max(8,int(16/m)), dmg=2.0)
                    self.lasers.append(lb)

    def _wall_laser(self, m):
        wall=random.choice(["top","bottom","left","right"])
        warn=max(22,int(45/m)); life=max(10,int(20/m)); dmg=1.8
        if wall=="top":
            return LaserBeam.at(random.randint(20,W-20), HUD_H,
                                random.uniform(55,125), warn=warn, life=life, dmg=dmg)
        elif wall=="bottom":
            return LaserBeam.at(random.randint(20,W-20), H,
                                random.uniform(235,305), warn=warn, life=life, dmg=dmg)
        elif wall=="left":
            return LaserBeam.at(0, random.uniform(HUD_H+20,H-20),
                                random.uniform(-40,40), warn=warn, life=life, dmg=dmg)
        else:
            return LaserBeam.at(W, random.uniform(HUD_H+20,H-20),
                                random.uniform(140,220), warn=warn, life=life, dmg=dmg)

    # ── Dégâts boss ───────────────────────────────────────────────────────────
    def take_damage(self, dmg:float) -> bool:
        # ANTI-SPELL : invulnérable tant que son bouclier est actif
        if self.id=="antispell" and self.shield_on and self.stun_t<=0:
            return False
        # Les LAZERRRR sont blindés : ils encaissent moins de dégâts hors étourdissement.
        if self.id in ("lazerrrr1","lazerrrr2") and self.stun_t<=0:
            dmg *= 0.4
        self.hp = max(0, self.hp - dmg)
        if self.hp<=0: self.alive=False
        return True

    def bomb_stun(self):
        self.stun_t=self.stun_max*2
        if self.id=="lazerrrr1":
            self._laz_phase="stun_anim"; self._laz_timer=self.stun_max*2; self._laz_beams.clear()
        elif self.id in ("winding","winding2"):
            self._corridor_active=False; self._corridor_warn=60

    # ── HP BAR (compacte, en haut de l'écran) ─────────────────────────────────
    def draw_hp_bar(self, surf, fonts:dict, y0:int=2):
        """Barre de vie compacte du boss, sur une seule ligne en haut."""
        F_SM=fonts["sm"]; F_XSM=fonts["xsm"]
        rc=RARITY_COLORS.get(self.rarity,WHITE)

        # Barre fine centrée
        bw=420; bh=18
        bar=pygame.Rect(W//2-bw//2, y0+18, bw, bh)
        pygame.draw.rect(surf,(0,0,0),bar.inflate(8,8),border_radius=7)
        pct=self.hp/max(1,self.maxhp)
        col2=GREEN if pct>0.5 else (YELLOW if pct>0.25 else RED)
        if self.stun_t>0: col2=GOLD
        pygame.draw.rect(surf,(18,18,30),bar,border_radius=6)
        w2=max(0,int(bar.w*pct))
        pygame.draw.rect(surf,tuple(c//2 for c in col2),pygame.Rect(bar.x,bar.y,w2,bar.h),border_radius=6)
        pygame.draw.rect(surf,col2,pygame.Rect(bar.x,bar.y,w2,bar.h//2),border_radius=6)
        pygame.draw.rect(surf,col2,bar,2,border_radius=6)

        # Nom + PV au-dessus de la barre, en petit
        name_s=F_XSM.render(self.name,True,self.color)
        surf.blit(name_s,(bar.x, y0))
        hp_s=F_XSM.render(f"{int(self.hp)}/{int(self.maxhp)} HP",True,WHITE)
        surf.blit(hp_s,(bar.right-hp_s.get_width(), y0))
        # rareté/difficulté à droite de la barre
        meta=F_XSM.render(f"[{self.rarity[:3]}·{DIFF_LABELS.get(self.diff,'')[:4]}]",True,rc)
        surf.blit(meta,(bar.right+8, bar.y))

        if self.stun_t>0:
            st=F_XSM.render(f"★ ÉTOURDI — ATTAQUE ! ★",True,GOLD)
            surf.blit(st,(W//2-st.get_width()//2,bar.bottom+2))

    # ── Draw overlay couloir ─────────────────────────────────────────────────
    def draw_corridor_overlay(self, surf):
        """À appeler AVANT draw() pour afficher le couloir derrière le joueur."""
        if self.id not in ("winding","winding2") or not self._corridor_path:
            return
        if self._corridor_surf:
            # Avertissement : clignotement avant activation
            if self._corridor_warn>0:
                if (self._corridor_warn//8)%2==0:
                    surf.blit(self._corridor_surf,(0,0))
                # Label countdown
                F_SM=pygame.font.SysFont("consolas",22,True)
                s=F_SM.render(f"⚠ PRÉPARE-TOI  {self._corridor_warn//60+1}s",True,(255,200,0))
                surf.blit(s,(W//2-s.get_width()//2, H//2-30))
            elif self._corridor_active:
                surf.blit(self._corridor_surf,(0,0))
                # Label largeur
                F_XSM=pygame.font.SysFont("consolas",13)
                w_lbl=F_XSM.render(f"COULOIR {int(self._corridor_w)}px",True,GREEN)
                surf.blit(w_lbl,(10,H-36))

    # ── Draw principal ────────────────────────────────────────────────────────
    def draw(self, surf, fonts:dict):
        F_XSM=fonts["xsm"]; F_SM=fonts["sm"]
        bxi,byi=int(self.bx),int(self.by)

        # ── Pré-signalements d'attaque (télégraphie) ──────────────────
        for kind,tx,ty,tleft,ttot,ang in self._telegraphs:
            prog=1-tleft/max(1,ttot)
            if kind=="burst":
                # cercle d'avertissement qui se remplit avant l'explosion radiale
                rr=int(20+prog*70)
                s=pygame.Surface((W,H),pygame.SRCALPHA)
                a=max(0,min(255,int(120*(0.4+0.6*abs(math.sin(self.tick*0.5))))))
                pygame.draw.circle(s,(255,80,80,a),(int(tx),int(ty)),rr,3)
                surf.blit(s,(0,0))
            elif kind=="aim":
                # ligne de visée qui s'épaissit vers le joueur
                ex=int(tx+math.cos(ang)*700); ey=int(ty+math.sin(ang)*700)
                s=pygame.Surface((W,H),pygame.SRCALPHA)
                aa=max(0,min(255,int(160*prog)))
                pygame.draw.line(s,(255,120,120,aa),(int(tx),int(ty)),(ex,ey),2+int(prog*3))
                surf.blit(s,(0,0))

        # Corps boss
        if self.id in ("lazerrrr1","lazerrrr2"):
            self._draw_lazerrrr_body(surf,bxi,byi)
        elif self.id=="graviton":
            neon_circ(surf,self.color,(bxi,byi),38+int(5*math.sin(self.tick*0.1)),3)
            pygame.draw.circle(surf,tuple(c//3 for c in self.color),(bxi,byi),20)
        elif self.id=="voidlord":
            neon_circ(surf,WHITE,(bxi,byi),42+int(4*math.sin(self.tick*0.08)),3)
            neon_circ(surf,PURPLE,(bxi,byi),28,2)
        elif self.id=="antispell":
            pts=[(bxi+int(36*math.cos(math.radians(60*i-30))),
                  byi+int(36*math.sin(math.radians(60*i-30)))) for i in range(6)]
            pygame.draw.polygon(surf,tuple(c//4 for c in RED),pts)
            pygame.draw.polygon(surf,RED,pts,3)
            # Bouclier actif : anneau cyan pulsant + mention INVULNÉRABLE
            if self.shield_on and self.stun_t<=0:
                rr=50+int(6*math.sin(self.tick*0.3))
                neon_circ(surf,CYAN,(bxi,byi),rr,3)
                neon_circ(surf,(120,220,255),(bxi,byi),rr-6,1)
        elif self.id in ("winding","winding2"):
            # Boss visible : orbe qui se déplace
            col2=CYAN if self.id=="winding" else MAGENTA
            neon_circ(surf,col2,(bxi,byi),32+int(4*math.sin(self.tick*0.12)),2)
            pygame.draw.circle(surf,col2,(bxi,byi),12)
            # Flèches indiquant la direction du couloir
            arrow_col=(0,255,100)
            if self.id=="winding":  # flèche vers le bas
                pygame.draw.polygon(surf,arrow_col,
                    [(bxi,byi+22),(bxi-10,byi+10),(bxi+10,byi+10)])
            else:  # flèche vers la droite
                pygame.draw.polygon(surf,arrow_col,
                    [(bxi+22,byi),(bxi+10,byi-10),(bxi+10,byi+10)])

        # Indicateur de repos (fenêtre où le boss n'attaque pas)
        if self.resting and self.stun_t<=0:
            rs=F_SM.render("— REPOS —",True,(120,200,255))
            surf.blit(rs,(bxi-rs.get_width()//2,byi-60))

        # Stun
        if self.stun_t>0:
            for i in range(5):
                a=self.tick*0.15+i*math.tau/5
                sx=bxi+int(55*math.cos(a)); sy=byi+int(55*math.sin(a))
                pygame.draw.circle(surf,GOLD,(sx,sy),5)
            s=F_SM.render("★ ÉTOURDI ★",True,GOLD)
            surf.blit(s,(bxi-s.get_width()//2,byi-58))

        if self.id=="lazerrrr1": self._draw_lazerrrr1_lines(surf)
        for lb in self._laz_beams: lb.draw(surf)
        for lb in self.lasers:     lb.draw(surf)
        for b  in self.bullets:    b.draw(surf)
        if self.spell_locked:
            ls=F_SM.render("🔒 ANTI-SPELL",True,RED)
            surf.blit(ls,(W//2-ls.get_width()//2,58))
        # HP bar est dessinée séparément via draw_hp_bar() après le HUD

    def _draw_lazerrrr_body(self, surf, bxi, byi):
        col=ORANGE if self.id=="lazerrrr1" else RED
        for r2 in [55,45,35]:
            a2=40 if r2==55 else (80 if r2==45 else 180)
            s2=pygame.Surface((r2*2+4,r2*2+4),pygame.SRCALPHA)
            pygame.draw.circle(s2,(*col,a2),(r2+2,r2+2),r2); surf.blit(s2,(bxi-r2-2,byi-r2-2))
        pygame.draw.circle(surf,col,(bxi,byi),35,3)
        for i in range(3):
            a=self.tick*0.08+i*math.tau/3; rx=int(28*math.cos(a)); ry=int(14*math.sin(a))
            pygame.draw.circle(surf,WHITE,(bxi+rx,byi+ry),5)
        if self.stun_t==0:
            for ex in [-12,12]:
                pygame.draw.circle(surf,RED,(bxi+ex,byi-5),7)
                pygame.draw.circle(surf,(255,200,0),(bxi+ex,byi-5),3)

    def _draw_lazerrrr1_lines(self, surf):
        if not self._laz_lines: return
        for (x,_) in self._laz_lines:
            is_safe=x in self._safe_cols
            if is_safe:
                a2=int(60+60*math.sin(self.tick*0.2))
                s2=pygame.Surface((40,H-HUD_H),pygame.SRCALPHA)
                s2.fill((0,255,110,a2)); surf.blit(s2,(x-20,HUD_H))
                lbl=pygame.font.SysFont("consolas",13).render("✓ SÛR",True,GREEN)
                surf.blit(lbl,(x-lbl.get_width()//2,H//2))
            else:
                a2=int(80+60*math.sin(self.tick*0.3))
                s2=pygame.Surface((8,H-HUD_H),pygame.SRCALPHA)
                s2.fill((220,80,0,a2)); surf.blit(s2,(x-4,HUD_H))

    def collides_player(self,px,py,pr):
        for b in self.bullets:
            if b.collides(px,py,pr): return b.dmg,b
        for lb in self.lasers:
            if lb.collides_player(px,py,pr): return lb.dmg,None
        for lb in self._laz_beams:
            if lb.collides_player(px,py,pr): return lb.dmg,None
        return None,None
