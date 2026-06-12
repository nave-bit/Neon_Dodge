"""systems/xp_system.py — v5.0 — XP double usage : niveau + points d'amélioration"""
from core.constants import XP_PER_LEVEL

class XPSystem:
    def __init__(self):
        self.level        = 1
        self.xp           = 0
        self.xp_next      = XP_PER_LEVEL
        self.total_xp_ever= 0   # XP total gagné = monnaie d'amélioration
        self.upgrade_xp   = 0   # XP disponible pour acheter des améliorations

    def add(self, amount:int) -> bool:
        self.xp           += amount
        self.total_xp_ever+= amount
        self.upgrade_xp   += amount
        leveled = False
        while self.xp >= self.xp_next:
            self.xp      -= self.xp_next
            self.level   += 1
            self.xp_next  = int(XP_PER_LEVEL*(1+self.level*0.15))
            leveled        = True
        return leveled

    def spend_upgrade_xp(self, amount:int) -> bool:
        if self.upgrade_xp >= amount:
            self.upgrade_xp -= amount; return True
        return False

    @property
    def progress(self): return self.xp/self.xp_next

    def speed_bonus(self):  return 1.0+(self.level-1)*0.035
    def accel_bonus(self):  return 1.0+(self.level-1)*0.04
    def evade_range(self):  return 120+self.level*7
