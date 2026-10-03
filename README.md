# Asteroids

A classic Asteroids-style arcade game written in Python with [pyglet](https://pyglet.org/).
I built it as a learning project while teaching myself to program.

## Features

- Ship with rotation, acceleration, braking and a thruster flame
- Meteors of random size and speed; smaller ones are worth more points
- Difficulty levels — from level 5, UFOs appear and shoot at the player
- 3 lives, fullscreen mode
- Sound effects (shooting, explosions, losing a life)
- Local leaderboard (top 3 players) saved to `scores.csv`

## Requirements

- Python 3.8+
- pyglet

```
pip install pyglet
```

The `.ogg` sounds need a decoder; if pyglet can't play them (e.g. FFmpeg is not installed),
the game simply runs without those sounds.

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
| F11 / F10 | Fullscreen on / off |

## Credits

Graphics: [Space Shooter Redux](https://kenney.nl/assets/space-shooter-redux) by Kenney (CC0).

## Author

Sophia
