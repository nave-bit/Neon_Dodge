# Neon Dodge

Un jeu d'arcade en Python où le but est d'**esquiver** des projectiles le plus longtemps possible. Plutôt que de tester les réflexes, le jeu mise sur l'anticipation : beaucoup de projectiles, mais lents, qu'il faut éviter en se déplaçant intelligemment.

> Mon premier projet de jeu vidéo.

## Fonctionnalités

- Plusieurs types de projectiles (pebble, bolt, shard, bomb, phantom, meteor)
- Système d'expérience (XP) avec montée en difficulté progressive
- Combats de **boss** avec attaques variées et phases
- Boutique, skins, énergie et améliorations
- Plusieurs niveaux de difficulté : BASIC, BRUTAL, DESTRUCTEUR, DIVIN, CAUCHEMAR
- Musique et effets sonores, avec un jukebox intégré (playlist, boucle, aléatoire)
- Sauvegarde des scores et des réglages

## Comment jouer

Il faut avoir **Python** et la bibliothèque **pygame** installés.

```bash
pip install pygame
```

Ensuite, lancer le jeu :

```bash
python main.py
```

Sous Windows, on peut aussi double-cliquer sur `lancer.bat`.

## Structure du projet

```
neon_dodge/
  main.py          # boucle principale du jeu
  lancer.bat       # lancement rapide sous Windows
  assets/          # sons et musiques
  core/            # constantes, sauvegarde, gestion du son
  systems/         # XP, interface (HUD), boutique
  entities/        # joueur, projectiles, boss, particules
  screens/         # écrans titre, game over, transitions, mode boss
  save/            # sauvegarde locale
```

## Contrôles

Les contrôles et la légende sont affichés directement dans le jeu. Touche **J** (ou bouton 🎵 MUSIQUE) pour ouvrir le menu musique.

## À venir

- Bonus avancés
- Mode aventurier et checkpoints
- Multijoueur

---

Projet personnel en cours de développement.
