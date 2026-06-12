"""
core/save_manager.py
────────────────────
Gère la sauvegarde persistante dans  save/neon_save.json
Contenu :
  - keys          : mapping action → keycode pygame
  - boss_history  : {boss_id: {seen, defeated}}
  - hiscore       : record mode RUSH
  - hiscore_hardcore : record mode HARDCORE
"""

import json, os
from core.constants import DEFAULT_KEYS

# Chemin du fichier JSON  (racine du projet / save/)
_HERE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_PATH  = os.path.join(_HERE, "save", "neon_save.json")

_DEFAULTS = {
    "keys":              dict(DEFAULT_KEYS),
    "boss_history":      {},
    "hiscore":           0,
    "hiscore_hardcore":  0,
    "run_history":       {},
    "owned_skins":       ["cyan"],
    "selected_skin":     "cyan",
    "music_settings":    {"mode":"loop","shuffle":False,"selected":[],"resume":True},
}


def load() -> dict:
    """Charge la sauvegarde. Fusionne avec les valeurs par défaut si manquantes."""
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            # Compléter les clés manquantes
            for k, v in _DEFAULTS.items():
                if k not in data:
                    data[k] = (v.copy() if isinstance(v, (dict, list)) else v)
            # S'assurer que toutes les touches existent
            for k, v in DEFAULT_KEYS.items():
                if k not in data["keys"]:
                    data["keys"][k] = v
            # JSON stocke les entiers en str parfois
            data["keys"] = {k: int(v) for k, v in data["keys"].items()}
            return data
        except Exception:
            pass
    # Pas de fichier → valeurs par défaut
    return {k: (v.copy() if isinstance(v, dict) else v) for k, v in _DEFAULTS.items()}


def write(data: dict) -> None:
    """Sauvegarde le dict dans le JSON."""
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[save_manager] Erreur écriture : {e}")
