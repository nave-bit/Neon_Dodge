"""entities/player.py — v5.0 — Attaques multiples + clic droit"""
import pygame, math, random
from core.constants import (
    W, H, CYAN, MAGENTA, PURPLE, PINK, WHITE, YELLOW, GREEN, RED,
    POWERUP_DUR, ATTACK_TYPES, MOUSE_ATTACK,
    ENERGY_COST, ENERGY_MAX_BASE, ENERGY_REGEN, ENERGY_PICKUP_GAIN, TURBO_DRAIN,
    PLAYER_SKINS,
)
from systems.hud import neon_circ
from entities.particles import Particle
from entities.obstacle import AttackWave


class AttackSystem:
    """Gère les types d'attaques débloqués et leurs niveaux d'amélioration."""
    def __init__(self):
        self.unlocked    = ["wave"]   # attaques débloquées
        self.current     = "wave"
        self.upgrades    = {k: 0 for k in ATTACK_TYPES}  # niveau upgrade (0-5)
        # Bonus venant du shop
        self.dmg_mult    = 1.0
        self.cd_mult     = 1.0
        self.radius_mult = 1.0
        self.boss_dmg_mult=1.0

    def get_cooldown(self, atk_id:str) -> int:
        base_cd = ATTACK_TYPES[atk_id][4]
        spd_lvl = self.upgrades.get("wave",0)  # utilise le niveau général
        cd_bonus= 1.0 - spd_lvl * 0.12
        return max(6, int(base_cd * cd_bonus * self.cd_mult))

    def get_damage(self, atk_id:str) -> float:
        base_dmg = ATTACK_TYPES[atk_id][3]
        dmg_lvl  = self.upgrades.get(atk_id,0)
        return base_dmg * (1 + dmg_lvl*0.25) * self.dmg_mult

    def get_radius(self, atk_id:str) -> int:
        base_r = ATTACK_TYPES[atk_id][2]
        r_lvl  = self.upgrades.get(atk_id,0)
        return int(base_r * (1 + r_lvl*0.2) * self.radius_mult)

    def get_boss_damage(self, atk_id:str) -> float:
        return self.get_damage(atk_id) * self.boss_dmg_mult

    def switch(self):
        idx = self.unlocked.index(self.current)
        self.current = self.unlocked[(idx+1)%len(self.unlocked)]

    def check_unlock(self, total_xp:int) -> str | None:
        """Vérifie si de nouvelles attaques peuvent être débloquées. Retourne le nom si nouveau."""
        for atk_id, info in ATTACK_TYPES.items():
            unlock_xp = info[5]
            if total_xp >= unlock_xp and atk_id not in self.unlocked:
                self.unlocked.append(atk_id)
                return atk_id
        return None


class Player:
    BASE_R = 15
    DTAP_W = 16

    def __init__(self, auto=False, xp_sys=None, keys:dict=None, skin:str="cyan"):
        self.x=float(W//2); self.y=float(H-110)
        self.vx=0.0; self.vy=0.0
        self.trail=[]
        self.invincible=0
        self.auto=auto
        self.xp_sys=xp_sys
        self.keys=keys or {}
        self.skin=skin if skin in PLAYER_SKINS else "cyan"
        self._dtap={}; self._tel_cd=0
        self._ai_tx=float(W//2); self._ai_ty=float(H-110)
        self._ai_chg=0; self._ai_zig=0
        self.shrink_t=0; self.ghost_t=0
        self.attack_cd=0
        self.atk_sys  = AttackSystem()
        # Bonus de stats
        self.extra_speed = 1.0
        # Énergie
        self.energy_max  = ENERGY_MAX_BASE
        self.energy      = float(self.energy_max)
        self.turbo       = False

    def sync_from_upgrades(self):
        """Applique les améliorations persistantes (énergie max, vitesse) depuis atk_sys."""
        up = self.atk_sys.upgrades
        self.energy_max = ENERGY_MAX_BASE + up.get("energy_max", 0) * 15
        self.energy     = float(self.energy_max)
        self.extra_speed = 1.0 + up.get("move_spd", 0) * 0.08

    @property
    def R(self) -> int:
        return max(6, self.BASE_R-(4 if self.shrink_t>0 else 0))

    # ── Énergie ─────────────────────────────────────────────────────────────────
    def can_attack(self, atk_id:str) -> bool:
        """True si l'énergie suffit. L'ONDE (coût 0) est toujours autorisée."""
        return self.energy >= ENERGY_COST.get(atk_id, 0)

    def spend_energy(self, atk_id:str):
        self.energy = max(0.0, self.energy - ENERGY_COST.get(atk_id, 0))

    def regen_energy(self):
        if self.turbo:
            self.energy = max(0.0, self.energy - TURBO_DRAIN)
        else:
            self.energy = min(self.energy_max, self.energy + ENERGY_REGEN)

    def add_energy(self, amount:float):
        self.energy = min(self.energy_max, self.energy + amount)

    # ── IA ────────────────────────────────────────────────────────────────────
    def _ai_update(self, obstacles, pu_items, active, inv, tick, boss=None):
        lvl=self.xp_sys; ev=lvl.evade_range(); ac=0.85*lvl.accel_bonus()
        all_threats=list(obstacles)+(boss.bullets if boss else [])
        threats=sorted([(math.hypot(o.x-self.x,o.y-self.y),o) for o in all_threats],
                        key=lambda x:x[1].dmg/max(1,x[0]))
        best_pu=None; best_val=-1
        for pu in pu_items:
            d=math.hypot(pu.x-self.x,pu.y-self.y)
            val={"life":10,"shield":8,"bomb":7,"slow":6,"magnet":5,"xp":4,"coin15":3,"coin5":2}.get(pu.kind,1)/(max(1,d*0.01))
            if val>best_val: best_val=val; best_pu=pu

        fvx=fvy=0.0
        for dist,obs in threats[:3]:
            if dist<ev:
                urg=(ev-dist)/ev*(1+obs.dmg*0.3)
                dx=self.x-obs.x; dy=self.y-obs.y; nd=max(1,math.hypot(dx,dy))
                fvx+=dx/nd*urg; fvy+=dy/nd*urg

        # Fuir les lignes LAZERRRR
        if boss and boss.id in ("lazerrrr1","lazerrrr2"):
            for (lx,_) in getattr(boss,"_laz_lines",[]):
                if lx not in getattr(boss,"_safe_cols",[]):
                    dist_l=abs(self.x-lx)
                    if dist_l<120: fvx+=(self.x-lx)/max(1,dist_l)*2.0
            # Se diriger vers la zone sûre
            if boss._laz_phase=="warn" and boss._safe_cols:
                sx=boss._safe_cols[0]; dy_=H*0.7-self.y
                fvx+=(sx-self.x)/max(1,abs(sx-self.x))*1.5
                fvy+=dy_/max(1,abs(dy_))*0.8

        if boss and boss.id in ("winding","winding2"):
            target=boss.get_path_target() if hasattr(boss,"get_path_target") else None
            if target:
                dx=target[0]-self.x; dy=target[1]-self.y; d=max(1,math.hypot(dx,dy))
                if d<25 and hasattr(boss,"advance_path"): boss.advance_path()
                fvx+=dx/d*ac*0.8; fvy+=dy/d*ac*0.8

        if math.hypot(fvx,fvy)>0.1:
            if any(o.kind in("laser","phantom") and math.hypot(o.x-self.x,o.y-self.y)<100 for _,o in threats[:3]):
                self._ai_zig+=1; fvx+=math.sin(self._ai_zig*0.4)*2
            sp=math.hypot(fvx,fvy); fvx/=sp; fvy/=sp
            self.vx+=fvx*ac*1.6; self.vy+=fvy*ac*1.6
        elif best_pu and math.hypot(best_pu.x-self.x,best_pu.y-self.y)<180:
            dx=best_pu.x-self.x; dy=best_pu.y-self.y; d=max(1,math.hypot(dx,dy))
            self.vx+=dx/d*ac*0.7; self.vy+=dy/d*ac*0.7
        else:
            self._ai_chg-=1
            if self._ai_chg<=0:
                self._ai_tx=random.uniform(W*0.15,W*0.85)
                self._ai_ty=random.uniform(H*0.5,H*0.88); self._ai_chg=random.randint(35,80)
            dx=self._ai_tx-self.x; dy=self._ai_ty-self.y; d=max(1,math.hypot(dx,dy))
            self.vx+=dx/d*ac*0.45; self.vy+=dy/d*ac*0.45

        action=None
        if inv.get("bomb",0)>0 and len(all_threats)>=5:
            inv["bomb"]-=1; action="bomb"
        if inv.get("shield",0)>0 and self.invincible==0 and \
                any(math.hypot(o.x-self.x,o.y-self.y)<80 for _,o in threats[:2]):
            inv["shield"]-=1; active["shield"]=POWERUP_DUR["shield"]; self.invincible=POWERUP_DUR["shield"]
        if inv.get("slow",0)>0 and len(all_threats)>=7:
            inv["slow"]-=1; active["slow"]=POWERUP_DUR["slow"]
        if inv.get("magnet",0)>0 and active.get("magnet",0)==0 and best_pu:
            inv["magnet"]-=1; active["magnet"]=POWERUP_DUR["magnet"]
        if inv.get("shrink",0)>0 and active.get("shrink",0)==0 and len(all_threats)>=6:
            inv["shrink"]-=1; active["shrink"]=POWERUP_DUR["shrink"]; self.shrink_t=POWERUP_DUR["shrink"]
        if inv.get("ghost",0)>0 and active.get("ghost",0)==0 and \
                any(o.is_phantom for _,o in threats[:3]):
            inv["ghost"]-=1; active["ghost"]=POWERUP_DUR["ghost"]; self.ghost_t=POWERUP_DUR["ghost"]

        # IA attaque si boss étourdi ou projectiles proches
        close=sum(1 for d,o in threats if d<120)
        if self.attack_cd==0 and (close>=3 or (boss and boss.stun_t>0)):
            action=action or "attack"

        if self._tel_cd==0 and inv.get("teleport",0)>0 and sum(1 for d,o in threats if d<60)>=2:
            inv["teleport"]-=1; self._ai_teleport(threats)

        return action

    def _ai_teleport(self, threats):
        best_x=self.x; best_score=-99
        for tx in [W*0.15,W*0.5,W*0.85]:
            sc=sum(math.hypot(tx-o.x,self.y-o.y) for _,o in threats)
            if sc>best_score: best_score=sc; best_x=tx
        self.x=best_x; self.vx=0; self._tel_cd=40

    def update(self, keys_pressed, obstacles, pu_items, active, inv, tick,
               boss=None, mouse_attack=False):
        turbo_mult = 1.6 if (self.turbo and self.energy > 0) else 1.0
        ac=0.75*self.xp_sys.accel_bonus()*self.extra_speed*turbo_mult; fric=0.80; action=None
        if self.auto:
            action=self._ai_update(obstacles,pu_items,active,inv,tick,boss)
        else:
            K=self.keys
            if keys_pressed[K["left"]]:  self.vx-=ac
            if keys_pressed[K["right"]]: self.vx+=ac
            if keys_pressed[K["up"]]:    self.vy-=ac
            if keys_pressed[K["down"]]:  self.vy+=ac
            # Attaque clic droit
            if mouse_attack and self.attack_cd==0:
                action="attack"

        sp=math.hypot(self.vx,self.vy); ms=9*self.xp_sys.speed_bonus()*self.extra_speed*turbo_mult
        if sp>ms: self.vx,self.vy=self.vx/sp*ms,self.vy/sp*ms
        self.vx*=fric; self.vy*=fric
        self.x=max(self.R,min(W-self.R,self.x+self.vx))
        self.y=max(self.R,min(H-self.R,self.y+self.vy))
        self.trail.append((int(self.x),int(self.y)))
        if len(self.trail)>22: self.trail.pop(0)
        if self.invincible>0: self.invincible-=1
        if self._tel_cd>0:    self._tel_cd-=1
        if self.attack_cd>0:  self.attack_cd-=1
        if self.shrink_t>0:   self.shrink_t-=1; active["shrink"]=self.shrink_t
        if self.ghost_t>0:    self.ghost_t-=1;  active["ghost"]=self.ghost_t
        # Si plus d'énergie en turbo, on coupe le turbo
        if self.turbo and self.energy<=0: self.turbo=False
        self.regen_energy()
        return action

    def check_dtap(self, key, tick):
        if key not in self._dtap: self._dtap[key]=tick; return None
        last=self._dtap[key]
        if 0<tick-last<=self.DTAP_W and self._tel_cd==0:
            self._dtap[key]=-9999; self._tel_cd=45; return key
        else: self._dtap[key]=tick; return None

    def teleport(self, direction, particles):
        ox,oy=int(self.x),int(self.y)
        # éclats au point de départ
        for _ in range(28): particles.append(Particle(ox,oy,CYAN,1.8))
        K=self.keys; m=65
        if direction==K["left"]:   self.x=m
        elif direction==K["right"]:self.x=W-m
        elif direction==K["up"]:   self.y=m+10
        elif direction==K["down"]: self.y=H-m
        nx,ny=int(self.x),int(self.y)
        # traînée d'étincelles le long du trajet (effet de "saut" lumineux)
        steps=14
        for i in range(steps):
            t=i/steps
            tx=int(ox+(nx-ox)*t); ty=int(oy+(ny-oy)*t)
            col = PURPLE if i%2 else CYAN
            particles.append(Particle(tx,ty,col,1.2))
        # éclats à l'arrivée
        for _ in range(28): particles.append(Particle(nx,ny,MAGENTA,1.8))
        # on réinitialise la traînée visuelle pour éviter une ligne disgracieuse
        self.trail.clear()
        self.vx=self.vy=0

    def do_attack(self, mouse_pos=None) -> "AttackWave":
        atk  = self.atk_sys.current
        cd   = self.atk_sys.get_cooldown(atk)
        if self.turbo and self.energy > 0:
            cd = max(4, int(cd * 0.5))   # turbo = cadence ×2
        r    = self.atk_sys.get_radius(atk)
        self.attack_cd = cd
        return AttackWave(self.x, self.y, r-90,
                          atk_type=atk, mouse_pos=mouse_pos,
                          damage=self.atk_sys.get_damage(atk),
                          boss_dmg=self.atk_sys.get_boss_damage(atk))

    def draw(self, surf, tick):
        skin_name, skin_col, trail_col, _price, shape = PLAYER_SKINS.get(self.skin, PLAYER_SKINS["cyan"])
        # Traînée colorée selon le skin
        for i,(tx,ty) in enumerate(self.trail):
            a=i/max(1,len(self.trail)); r2=max(1,int(self.R*a*0.55))
            tc=(int(trail_col[0]*a),int(trail_col[1]*a),int(trail_col[2]*a))
            pygame.draw.circle(surf,tc,(tx,ty),r2)
        if self.invincible>0 and (tick//4)%2==0: return
        # Couleur : skin par défaut, mais shrink/ghost gardent leur indication
        col2 = PINK if self.shrink_t>0 else (PURPLE if self.ghost_t>0 else skin_col)
        ix,iy=int(self.x),int(self.y)
        if shape=="circle":
            neon_circ(surf,col2,(ix,iy),self.R,3)
        elif shape=="square":
            d=tuple(c//4 for c in col2)
            pygame.draw.rect(surf,d,pygame.Rect(ix-self.R-3,iy-self.R-3,2*self.R+6,2*self.R+6),border_radius=4)
            pygame.draw.rect(surf,col2,pygame.Rect(ix-self.R,iy-self.R,2*self.R,2*self.R),3,border_radius=3)
        elif shape=="triangle":
            r=self.R+2
            pts=[(ix,iy-r),(ix-r,iy+r),(ix+r,iy+r)]
            pygame.draw.polygon(surf,tuple(c//4 for c in col2),pts)
            pygame.draw.polygon(surf,col2,pts,3)
        elif shape=="diamond":
            r=self.R+2
            pts=[(ix,iy-r),(ix+r,iy),(ix,iy+r),(ix-r,iy)]
            pygame.draw.polygon(surf,tuple(c//4 for c in col2),pts)
            pygame.draw.polygon(surf,col2,pts,3)
        pygame.draw.circle(surf,WHITE,(ix,iy),4)
        # Arc de rechargement attaque
        if self.attack_cd>0:
            total=self.atk_sys.get_cooldown(self.atk_sys.current)
            prog=1-self.attack_cd/max(1,total)
            atk_col=ATTACK_TYPES[self.atk_sys.current][1]
            pygame.draw.arc(surf,atk_col,pygame.Rect(int(self.x)-22,int(self.y)-22,44,44),
                            -math.pi/2,-math.pi/2+math.tau*prog,2)
        if self._tel_cd>0:
            prog=1-self._tel_cd/45
            pygame.draw.arc(surf,MAGENTA,pygame.Rect(int(self.x)-26,int(self.y)-26,52,52),
                            -math.pi/2,-math.pi/2+math.tau*prog,2)
