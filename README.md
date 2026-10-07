# Asteroids

A classic Asteroids-style arcade game written in Python with [pyglet](https://pyglet.org/).
I built it as a learning project while teaching myself to program.

## Features

- Ship with rotation, inertia (it keeps drifting), braking and a thruster flame
- Short invulnerability (the ship blinks) after the ship appears
- Meteors of random size and speed; big ones break into smaller pieces, and smaller ones are worth more points
- Difficulty levels: meteors come more often and fly faster with each level, and from level 5 UFOs appear and shoot at the player
- More meteors in a bigger window, so a maximized game isn't easier
- Pause (also automatic when you switch to another window)
- 3 lives, resizable window (can be maximized) and fullscreen mode
- Sound effects (shooting, explosions, losing a life)
- Local leaderboard (top 3 players) saved to `scores.csv`

## Requirements

- Python 3.8+
- pyglet

```
pip install pyglet
```

## Running the game

```
python Asteroids.py
```

## Controls

| Key | Action |
| --- | --- |
| ↑ / W | Accelerate (also starts the game / continues after losing a life) |
| ← / A, → / D | Rotate |
| ↓ / S | Brake |
| Space / left mouse button | Shoot |
| Enter | Confirm name / restart after game over |
| P / Esc | Pause / continue |
| F11 | Toggle fullscreen (F10 also leaves fullscreen) |

## Credits

Graphics: [Space Shooter Redux](https://kenney.nl/assets/space-shooter-redux) by Kenney (CC0).

## Author

Sophia
