"""
core/recorder.py
────────────────
Capture les frames pygame et les encode en .mp4 via opencv.
opencv-python est optionnel : si absent, la sauvegarde est désactivée silencieusement.

Usage :
    from core.recorder import Recorder
    rec = Recorder()
    rec.start()
    # chaque frame :
    rec.capture(screen)
    # fin de partie :
    path = rec.stop_and_save()
"""

import os, datetime

try:
    import cv2
    import numpy as np
    CV2_OK = True
except ImportError:
    CV2_OK = False

# Dossier de sortie vidéo
_VIDEO_DIR = r"Z:\EVAN\Suivi de stage\autre\essaie"


class Recorder:
    FPS    = 60
    FOURCC = "mp4v"

    def __init__(self):
        self.frames: list = []
        self.active: bool = False

    def start(self) -> None:
        """Démarre un nouvel enregistrement (efface les frames précédentes)."""
        self.frames = []
        self.active = True

    def capture(self, surf) -> None:
        """Capture une frame pygame.Surface. Appeler à chaque flip()."""
        if self.active:
            self.frames.append(surf.copy())

    def stop_and_save(self) -> str | None:
        """
        Arrête l'enregistrement et encode le .mp4.
        Retourne le chemin du fichier ou None si échec / opencv absent.
        """
        self.active = False

        if not CV2_OK:
            print("[recorder] opencv-python non installé — pip install opencv-python")
            self.frames = []
            return None

        if not self.frames:
            print("[recorder] Aucune frame capturée.")
            return None

        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(_VIDEO_DIR, f"neon_dodge_{ts}.mp4")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError:
            # Dossier réseau inaccessible → fallback local
            path = f"neon_dodge_{ts}.mp4"

        fw, fh = self.frames[0].get_size()
        out    = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*self.FOURCC), self.FPS, (fw, fh))

        import pygame
        for s in self.frames:
            arr = pygame.surfarray.array3d(s).transpose(1, 0, 2)
            out.write(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

        out.release()
        self.frames = []
        print(f"[recorder] Vidéo enregistrée : {path}")
        return path
