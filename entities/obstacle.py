"""entities/obstacle.py — v5.0 — Lasers plus grands/rapides + AttackWave typée"""
import pygame, math, random
from core.constants import (
    W, H, HUD_H,
    GREY, CYAN, MAGENTA, YELLOW, ORANGE, RED, PURPLE, WHITE, GREEN,
    DIFFICULTY_TIERS,
)
from systems.hud import draw_bar

PROJ_TYPES = {
    "pebble":  (GREY,    "circle",   8,  14, 0.8, 0.9,  5),
    "bolt":    (CYAN,    "diamond", 10,  16, 1.4, 1.2, 10),
    "shard":   (MAGENTA, "triangle",12,  20, 2.0, 1.0, 15),
    "bomb":    (ORANGE,  "circle",  20,  32, 2.8, 0.6, 25),
    "phantom": (PURPLE,  "diamond", 14,  22, 1.4, 0.8, 20),
    "meteor":  (YELLOW,  "circle",  52,  80, 5.0, 0.45,40),  # gros mais lent
}

def get_allowed_types(xp_level:int) -> list:
    """Retourne les types autorisés selon le niveau XP (courbe de difficulté)."""
    allowed = ["pebble"]
    for (min_lvl, types, _, _) in DIFFICULTY_TIERS:
        if xp_level >= min_lvl and types is not None:
            allowed = types
    return allowed

def proj_weights_for_level(xp_level:int, round_num:int) -> dict:
    allowed = get_allowed_types(xp_level)
    base = {"pebble":38,"bolt":22,"shard":14,"bomb":10,"phantom":8,"meteor":8}
    return {k:v for k,v in base.items() if k in allowed}

def new_difficulty_tier_message(old_level:int, new_level:int) -> str | None:
    """Retourne le message si un palier de difficulté vient d'être franchi."""
    for (min_lvl,_,_,msg) in DIFFICULTY_TIERS:
        if old_level < min_lvl <= new_level:
            return msg
    return None


class Obstacle:
    def __init__(self, round_num:int, slow_f:float=1.0,
                 forbidden:list=None, xp_level:int=1):
        forbidden = forbidden or []
        weights   = {k:v for k,v in proj_weights_for_level(xp_level, round_num).items()
                     if k not in forbidden}
        if not weights: weights = {"pebble":1}
        keys=list(weights); vals=list(weights.values()); total=sum(vals)
        r2=random.randint(1,total); pick=keys[0]
        for k,v in zip(keys,vals):
            r2-=v
            if r2<=0: pick=k; break

        self.kind=pick
        col,shape,rmin,rmax,dmg,spd,xp = PROJ_TYPES[pick]
        self.color=col; self.shape=shape
        self.r=random.randint(rmin,rmax); self.dmg=dmg; self.xp_val=xp
        self.x=float(random.randint(self.r+10,W-self.r-10)); self.y=float(-self.r-10)
        # Jeu d'esquive : projectiles plus lents, montée en difficulté douce
        difficulty_scale = 1.0 + (xp_level-1)*0.03
        base_spd=(1.8+round_num*0.18)*spd*difficulty_scale
        self.vy=base_spd*slow_f+random.uniform(-0.3,1.0)
        # Plafond de vitesse : aucun projectile ne devient "réflexe"
        SPEED_CAP=5.5
        self.vy=min(self.vy,SPEED_CAP*slow_f)
        self.vx=random.uniform(-0.8,0.8)*(1+round_num*0.05)
        self.angle=0; self.phase=random.uniform(0,math.tau)
        self.is_phantom=(pick=="phantom")
        self.hp=2 if pick=="meteor" else 1

    def update(self, slow_f=1.0):
        self.y+=self.vy*slow_f; self.x+=self.vx*slow_f
        if self.is_phantom: self.x+=math.sin(self.phase)*1.5; self.phase+=0.07
        self.x=max(self.r,min(W-self.r,self.x)); self.angle+=2+self.vy*0.4

    def draw(self, surf):
        ix,iy=int(self.x),int(self.y); col=self.color; d=tuple(c//4 for c in col)
        rad=math.radians(self.angle); F_XSM=pygame.font.SysFont("consolas",14)
        if self.shape=="circle":
            pygame.draw.circle(surf,d,(ix,iy),self.r+4)
            pygame.draw.circle(surf,col,(ix,iy),self.r,3 if self.kind=="meteor" else 2)
            if self.dmg>=2: pygame.draw.circle(surf,(60,0,0),(ix,iy),self.r+8,1)
            if self.hp>1: draw_bar(surf,pygame.Rect(ix-22,iy-self.r-14,44,6),self.hp,2,RED)
        elif self.shape=="diamond":
            pts=[(ix,iy-self.r),(ix+self.r,iy),(ix,iy+self.r),(ix-self.r,iy)]
            pygame.draw.polygon(surf,d,pts,4); pygame.draw.polygon(surf,col,pts,2)
        elif self.shape=="rect":
            pts_l=[(-self.r,-self.r),(self.r,-self.r),(self.r,self.r),(-self.r,self.r)]
            pts=[(ix+p[0]*math.cos(rad)-p[1]*math.sin(rad),
                  iy+p[0]*math.sin(rad)+p[1]*math.cos(rad)) for p in pts_l]
            pygame.draw.polygon(surf,d,pts,4); pygame.draw.polygon(surf,col,pts,2)
        else:
            pts=[(ix+int(self.r*math.cos(rad+i*math.tau/3)),
                  iy+int(self.r*math.sin(rad+i*math.tau/3))) for i in range(3)]
            pygame.draw.polygon(surf,d,pts,4); pygame.draw.polygon(surf,col,pts,2)
        lbl=F_XSM.render(self.kind[:3].upper(),True,tuple(c//2+40 for c in col))
        surf.blit(lbl,(ix-lbl.get_width()//2,iy-self.r-14))

    def collides(self,px,py,pr): return math.hypot(px-self.x,py-self.y)<self.r+pr-6
    @property
    def off_screen(self): return self.y>H+self.r+20


class LaserBeam:
    """Laser avec avertissement — v5.1 : origine/angle quelconque, plus épais."""
    def __init__(self, angle_deg:int=90, hardcore:bool=False):
        self.angle_deg=angle_deg
        self.warn =80; self.life=40
        self.dmg  =3.5 if not hardcore else 5.0
        self.xp_val=30; self.active=False
        if angle_deg==90:
            self.ox=random.randint(50,W-50); self.oy=-10; self.dx=0; self.dy=1
        elif angle_deg==0:
            self.ox=-10; self.oy=random.randint(HUD_H+30,H-60); self.dx=1; self.dy=0
        elif angle_deg==45:
            self.ox=random.randint(0,W//2); self.oy=-10; self.dx=0.6; self.dy=1
        else:
            self.ox=random.randint(W//2,W); self.oy=-10; self.dx=-0.6; self.dy=1

    @classmethod
    def at(cls, ox:float, oy:float, angle_deg:float,
           warn:int=40, life:int=28, dmg:float=3.5) -> "LaserBeam":
        """Crée un laser depuis n'importe quelle position, dans n'importe quelle direction."""
        lb = cls.__new__(cls)
        lb.angle_deg = angle_deg
        lb.warn  = warn; lb.life = life; lb.dmg = dmg
        lb.xp_val= 30;   lb.active = False
        lb.ox    = float(ox); lb.oy = float(oy)
        rad      = math.radians(angle_deg)
        lb.dx    = math.cos(rad); lb.dy = math.sin(rad)
        return lb

    def update(self):
        if self.warn>0: self.warn-=1
        else: self.active=True; self.life-=1

    def draw(self, surf):
        t_max=2400
        ex=self.ox+self.dx*t_max; ey=self.oy+self.dy*t_max
        F_XSM=pygame.font.SysFont("consolas",14)
        if self.warn>0:
            a=int(80+80*math.sin(self.warn*0.3))
            pygame.draw.line(surf,(a,0,0),(int(self.ox),int(self.oy)),(int(ex),int(ey)),3)
            mid_x=int(self.ox+self.dx*400); mid_y=int(self.oy+self.dy*400)
            s=F_XSM.render("⚠ LASER",True,(200,0,0)); surf.blit(s,(mid_x-s.get_width()//2,mid_y-10))
        elif self.life>0:
            w=10+int(4*math.sin(self.life*0.5))
            pygame.draw.line(surf,(255,0,0),(int(self.ox),int(self.oy)),(int(ex),int(ey)),w+8)
            pygame.draw.line(surf,(255,100,0),(int(self.ox),int(self.oy)),(int(ex),int(ey)),w+3)
            pygame.draw.line(surf,(255,255,180),(int(self.ox),int(self.oy)),(int(ex),int(ey)),w)

    def collides_player(self,px,py,pr):
        if not self.active or self.life<=0: return False
        t_max=2400; ex=self.ox+self.dx*t_max; ey=self.oy+self.dy*t_max
        lx=ex-self.ox; ly=ey-self.oy; ln=max(1,math.hypot(lx,ly))
        dist=abs((py-self.oy)*lx/ln-(px-self.ox)*ly/ln)
        return dist<pr+8

    @property
    def off_screen(self): return self.warn<=0 and self.life<=0


class AttackWave:
    """Onde d'attaque typée (wave/beam/nova/pulse)."""
    def __init__(self, x:float, y:float, radius_bonus:int=0,
                 atk_type:str="wave", mouse_pos=None,
                 damage:float=1.0, boss_dmg:float=1.0):
        self.x=x; self.y=y
        self.r=0; self.max_r=90+radius_bonus
        self._life=20; self.atk_type=atk_type
        self.damage=damage; self.boss_dmg=boss_dmg
        self.mouse_pos=mouse_pos   # pour beam
        # Beam : direction vers la souris
        if atk_type=="beam" and mouse_pos:
            dx=mouse_pos[0]-x; dy=mouse_pos[1]-y
            d=max(1,math.hypot(dx,dy))
            self.beam_dx=dx/d; self.beam_dy=dy/d
            self.beam_len=0; self.beam_max=280
        else:
            self.beam_dx=0; self.beam_dy=-1
            self.beam_len=0; self.beam_max=240
        # Nova : explosif
        self.nova_r=0
        # Pulse : multiple vagues
        self.pulse_n=0

    def update(self):
        if self.atk_type=="wave":
            self.r+=7; self._life-=1
        elif self.atk_type=="beam":
            self.beam_len=min(self.beam_max,self.beam_len+30); self._life-=1
        elif self.atk_type=="nova":
            self.nova_r=min(200,self.nova_r+12); self.r=self.nova_r; self._life-=1
        elif self.atk_type=="pulse":
            self.r+=10; self._life-=1
            if self._life%5==0 and self._life>0: self.r=0   # reset pour effet pulse

    def draw(self, surf):
        from core.constants import ATTACK_TYPES
        col=ATTACK_TYPES[self.atk_type][1]
        a=self._life/20
        col_a=tuple(int(c*a) for c in col)
        if self.atk_type=="wave":
            if self.r>0: pygame.draw.circle(surf,col_a,(int(self.x),int(self.y)),int(self.r),2+int(a*4))
        elif self.atk_type=="beam":
            if self.beam_len>0:
                ex=self.x+self.beam_dx*self.beam_len; ey=self.y+self.beam_dy*self.beam_len
                w=max(2,int(8*a))
                pygame.draw.line(surf,tuple(c//2 for c in col),(int(self.x),int(self.y)),(int(ex),int(ey)),w+4)
                pygame.draw.line(surf,col,(int(self.x),int(self.y)),(int(ex),int(ey)),w)
        elif self.atk_type=="nova":
            if self.nova_r>0:
                pygame.draw.circle(surf,col_a,(int(self.x),int(self.y)),int(self.nova_r),4)
                pygame.draw.circle(surf,tuple(c//3 for c in col),(int(self.x),int(self.y)),int(self.nova_r))
        elif self.atk_type=="pulse":
            if self.r>0: pygame.draw.circle(surf,col_a,(int(self.x),int(self.y)),int(self.r),1+int(a*3))

    @property
    def alive(self): return self._life>0

    def hits(self, ox:float, oy:float) -> bool:
        if self.atk_type=="beam":
            # Collision avec le rayon
            t_max=self.beam_len
            bx=self.x+self.beam_dx*t_max; by=self.y+self.beam_dy*t_max
            lx=bx-self.x; ly=by-self.y; ln=max(1,math.hypot(lx,ly))
            dist=abs((oy-self.y)*lx/ln-(ox-self.x)*ly/ln)
            # aussi vérifier que le point est dans la longueur
            t=((ox-self.x)*lx/ln+(oy-self.y)*ly/ln)
            return dist<20 and 0<t<t_max
        elif self.atk_type=="nova":
            return math.hypot(ox-self.x,oy-self.y)<self.nova_r+15
        else:
            return math.hypot(ox-self.x,oy-self.y)<self.r+8

    def hits_boss(self, bx:float, by:float, boss_r:int=40) -> bool:
        """Vérifie si l'attaque touche le boss à sa position."""
        return self.hits(bx, by)
