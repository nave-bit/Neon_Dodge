"""
core/sound_manager.py
─────────────────────
Gestionnaire de sons et musique pour NEON DODGE.

Sons disponibles :
  attack    — onde d'attaque
  teleport  — téléportation
  levelup   — passage de niveau
  boss      — intro boss
  hit       — joueur touché
  collect   — item collecté
  boom      — explosion bombe
  shield    — activation bouclier

Musiques :
  music.ogg       — musique de jeu normale
  boss_fight.ogg  — musique de combat boss

Usage :
    from core.sound_manager import init, play, play_music, stop_music, set_volume
    init()           # une fois après pygame.init()
    play("attack")
    play_music("normal")
"""

import pygame, os

_HERE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# On cherche les fichiers son dans assets/ ET assets/sounds/
_SDIRS  = [os.path.join(_HERE, "assets"),
           os.path.join(_HERE, "assets", "sounds")]
_SDIR   = _SDIRS[0]   # conservé pour compat

def _find_file(filename: str):
    """Retourne le premier chemin existant pour `filename` parmi les dossiers son."""
    for d in _SDIRS:
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return p
    return None

_sounds : dict = {}
_volume_sfx   : float = 0.6
_volume_music : float = 0.35
_current_music: str   = ""
_enabled      : bool  = True
_warned_missing: set  = set()   # pour n'avertir qu'une fois par fichier manquant

# ── Jukebox (musiques de jeu) ────────────────────────────────────────────────
# Réglages persistants (chargés depuis la save par configure_jukebox()) :
_jukebox = {
    "mode":        "loop",      # "loop" (1 seule en boucle) ou "playlist"
    "shuffle":     False,       # playlist aléatoire
    "selected":    [],          # liste de fichiers de musique de jeu cochés
    "resume":      True,        # True = reprendre après interruption, False = piste suivante
    "allow_interrupt": True,    # boss/boutique peuvent-ils couper la musique de jeu
}
_jb_index   = 0          # index courant dans la playlist
_jb_pos_ms  = 0          # position mémorisée pour reprise
_jb_offset  = 0          # offset de départ du play() courant (pour reprise correcte)
_jb_current = ""         # fichier de jeu en cours
_in_context = False      # True si une musique de contexte (boss/shop) joue actuellement


def list_game_music() -> list:
    """Retourne la liste (fichier, libellé) des musiques de jeu trouvées dans assets."""
    found = []
    seen = set()
    for d in _SDIRS:
        if not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            low = fn.lower()
            if fn in seen: continue
            # Toute musique de jeu : music*.ogg/.mp3 (exclut shop/boss_fight)
            if (low.endswith((".ogg", ".mp3"))
                    and low not in ("shop.ogg", "boss_fight.ogg")
                    and (low.startswith("music") or low.startswith("track"))):
                label = _GAME_MUSIC_LABELS.get(fn, os.path.splitext(fn)[0].replace("_", " ").title())
                found.append((fn, label)); seen.add(fn)
    return found

# Mapping nom → fichier
_SFX_FILES = {
    "attack":      "attack.wav",
    "teleport":    "teleport.wav",
    "levelup":     "levelup.wav",
    "boss":        "boss.wav",
    "boss_killed": "boss_killed.wav",
    "boss_spawn":  "boss_spawn.wav",
    "boss_spawn2": "boss_spawn_laser2.wav",
    "buy_item":    "buy_item.wav",
    "laser":       "laser.wav",
    "game_end":    "game_end.wav",
    # Sons générés synthétiquement si fichier absent
    "hit":      None,
    "collect":  None,
    "boom":     None,
    "shield":   None,
}

# Musiques de CONTEXTE (interrompent la musique de jeu)
_CONTEXT_MUSIC = {
    "boss":   "boss_fight.ogg",
    "shop":   "shop.ogg",
}

# Musiques de JEU : détectées automatiquement (tout fichier music_*.ogg dans assets).
# On garde un libellé lisible pour chacune.
_GAME_MUSIC_LABELS = {
    "music_chill.ogg":  "Chill",
    "music_piano.ogg":  "Piano",
    "music_teckno.ogg": "Techno",
    "music.ogg":        "Original",
}


def _make_beep(freq: int, duration_ms: int, volume: float = 0.4,
               wave: str = "sine") -> pygame.mixer.Sound | None:
    """
    Génère un son synthétique si le fichier .wav n'existe pas.
    Nécessite numpy (optionnel).
    """
    try:
        import numpy as np
        sr   = 44100
        t    = np.linspace(0, duration_ms / 1000, int(sr * duration_ms / 1000), False)
        if wave == "sine":
            data = np.sin(2 * np.pi * freq * t)
        elif wave == "square":
            data = np.sign(np.sin(2 * np.pi * freq * t))
        else:
            data = np.random.uniform(-1, 1, len(t))  # noise

        # Envelope fade-out
        env  = np.linspace(1.0, 0.0, len(t))
        data = (data * env * volume * 32767).astype(np.int16)
        stereo = np.column_stack([data, data])
        return pygame.sndarray.make_sound(stereo)
    except Exception:
        return None


def init() -> None:
    """Initialise le mixer et charge tous les sons disponibles."""
    global _sounds
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception as e:
        print(f"[sound] Mixer init échoué : {e}"); return

    # Charger les fichiers .wav/.ogg (cherche dans assets/ et assets/sounds/)
    for name, filename in _SFX_FILES.items():
        if filename:
            path = _find_file(filename)
            if path:
                try:
                    _sounds[name] = pygame.mixer.Sound(path)
                    _sounds[name].set_volume(_volume_sfx)
                except Exception as e:
                    print(f"[sound] Impossible de charger {filename}: {e}")

    # Synthèse pour les sons sans fichier
    fallbacks = {
        "hit":     (_make_beep(120,  180, 0.5, "noise"), 0.5),
        "collect": (_make_beep(880,   80, 0.3, "sine"),  0.3),
        "boom":    (_make_beep(60,   400, 0.6, "noise"), 0.6),
        "shield":  (_make_beep(660,  200, 0.3, "sine"),  0.3),
        "laser":   (_make_beep(1400, 120, 0.35,"square"),0.35),
    }
    for name, (snd, vol) in fallbacks.items():
        if name not in _sounds and snd:
            _sounds[name] = snd
            _sounds[name].set_volume(vol)

    print(f"[sound] Sons chargés : {list(_sounds.keys())}")


def play(name: str, volume: float | None = None) -> None:
    """Joue un effet sonore. Silencieux si désactivé ou son manquant."""
    if not _enabled: return
    snd = _sounds.get(name)
    if snd:
        if volume is not None:
            snd.set_volume(max(0.0, min(1.0, volume)))
        snd.play()


# ── Jukebox : configuration & lecture ────────────────────────────────────────
def configure_jukebox(settings: dict) -> None:
    """Charge les réglages du jukebox (depuis la save)."""
    if not isinstance(settings, dict): return
    for k in ("mode", "shuffle", "selected", "resume", "allow_interrupt"):
        if k in settings:
            _jukebox[k] = settings[k]
    # Sécurité : ne garder que des musiques qui existent
    avail = {fn for fn, _ in list_game_music()}
    _jukebox["selected"] = [f for f in _jukebox.get("selected", []) if f in avail]
    if not _jukebox["selected"] and avail:
        _jukebox["selected"] = [sorted(avail)[0]]


def get_jukebox() -> dict:
    """Retourne les réglages courants (pour l'interface)."""
    return _jukebox


def _start_track(path: str, loop: bool, fade_ms: int = 600,
                 start_pos_ms: int = 0) -> None:
    global _jb_offset
    try:
        pygame.mixer.music.fadeout(fade_ms // 2)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(_volume_music)
        loops = -1 if loop else 0
        if start_pos_ms > 0:
            pygame.mixer.music.play(loops, start=start_pos_ms/1000.0, fade_ms=fade_ms)
            _jb_offset = start_pos_ms
        else:
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            _jb_offset = 0
    except Exception as e:
        print(f"[sound] Erreur lecture musique : {e}")


def play_game_music(fade_ms: int = 800, force_first: bool = False) -> None:
    """Démarre la musique de jeu selon le mode (boucle ou playlist)."""
    global _jb_current, _jb_index, _in_context
    _in_context = False
    if not _enabled: return
    sel = _jukebox.get("selected") or [fn for fn, _ in list_game_music()]
    if not sel:
        return  # aucune musique de jeu disponible
    if force_first or _jb_current not in sel:
        _jb_index = 0
        _jb_current = sel[0]
    fn = sel[_jb_index % len(sel)]
    _jb_current = fn
    path = _find_file(fn)
    if not path:
        if fn not in _warned_missing:
            print(f"[sound] Musique introuvable : {fn}")
            _warned_missing.add(fn)
        return
    loop = (_jukebox.get("mode") == "loop")
    _start_track(path, loop, fade_ms)


def _advance_playlist() -> None:
    """Passe à la piste suivante (aléatoire ou ordonnée)."""
    global _jb_index, _jb_current
    sel = _jukebox.get("selected") or []
    if len(sel) <= 1: return
    if _jukebox.get("shuffle"):
        import random
        nxt = _jb_index
        while nxt == _jb_index:
            nxt = random.randrange(len(sel))
        _jb_index = nxt
    else:
        _jb_index = (_jb_index + 1) % len(sel)
    _jb_current = sel[_jb_index]


def update_music() -> None:
    """À appeler chaque frame : enchaîne la playlist quand une piste finit."""
    if not _enabled or _in_context: return
    if _jukebox.get("mode") != "playlist": return
    if not pygame.mixer.music.get_busy():
        _advance_playlist()
        play_game_music(fade_ms=400)


def play_context_music(track: str, fade_ms: int = 600) -> None:
    """Lance une musique de contexte (boss/shop) qui interrompt la musique de jeu."""
    global _in_context, _jb_pos_ms
    if not _enabled: return
    # Si l'utilisateur a désactivé l'interruption, on laisse la musique de jeu continuer
    if not _jukebox.get("allow_interrupt", True):
        return
    filename = _CONTEXT_MUSIC.get(track)
    if not filename: return
    path = _find_file(filename)
    if not path:
        if filename not in _warned_missing:
            print(f"[sound] Musique introuvable : {filename}")
            _warned_missing.add(filename)
        return
    # Mémoriser la position de la musique de jeu pour une éventuelle reprise
    if not _in_context:
        try:
            pos = pygame.mixer.music.get_pos()  # ms depuis le dernier play()
            _jb_pos_ms = max(0, _jb_offset + pos)
        except Exception:
            _jb_pos_ms = 0
    _in_context = True
    _start_track(path, loop=True, fade_ms=fade_ms)


def end_context_music(fade_ms: int = 600) -> None:
    """Fin d'un contexte (boss/shop) : revient à la musique de jeu."""
    global _in_context
    if not _enabled:
        _in_context = False
        return
    resume = _jukebox.get("resume", True)
    if resume and _jb_current:
        # Reprendre la musique de jeu là où elle s'était arrêtée
        _in_context = False
        path = _find_file(_jb_current)
        if path:
            loop = (_jukebox.get("mode") == "loop")
            _start_track(path, loop, fade_ms, start_pos_ms=_jb_pos_ms)
        else:
            play_game_music(fade_ms)
    else:
        # Passer à la suivante (ou redémarrer)
        if _jukebox.get("mode") == "playlist":
            _advance_playlist()
        _in_context = False
        play_game_music(fade_ms)


# ── Compatibilité : ancien play_music("normal"/"boss"/"shop") ────────────────
def play_music(track: str = "normal", fade_ms: int = 800) -> None:
    """Compat : 'normal' -> musique de jeu ; 'boss'/'shop' -> contexte."""
    if track in _CONTEXT_MUSIC:
        play_context_music(track, fade_ms)
    else:
        # retour à la musique de jeu
        if _in_context:
            end_context_music(fade_ms)
        else:
            play_game_music(fade_ms)


# ── Aperçu (interface de sélection) ──────────────────────────────────────────
def preview_music(filename: str) -> None:
    """Joue un extrait d'une musique pour l'écouter dans l'interface (boucle)."""
    if not _enabled: return
    path = _find_file(filename)
    if path:
        _start_track(path, loop=True, fade_ms=200)


def stop_music(fade_ms: int = 600) -> None:
    """Arrête toute musique avec fondu."""
    global _current_music, _in_context
    pygame.mixer.music.fadeout(fade_ms)
    _current_music = ""
    _in_context = False


def set_sfx_volume(v: float) -> None:
    """Règle le volume des effets (0.0 → 1.0)."""
    global _volume_sfx
    _volume_sfx = max(0.0, min(1.0, v))
    for snd in _sounds.values():
        snd.set_volume(_volume_sfx)


def set_music_volume(v: float) -> None:
    """Règle le volume de la musique (0.0 → 1.0)."""
    global _volume_music
    _volume_music = max(0.0, min(1.0, v))
    pygame.mixer.music.set_volume(_volume_music)


def toggle() -> bool:
    """Active/désactive tous les sons. Retourne le nouvel état."""
    global _enabled
    _enabled = not _enabled
    if _enabled:
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()
    return _enabled
