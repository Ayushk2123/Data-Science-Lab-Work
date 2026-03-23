# 🐍 Snake Game

A classic **Snake Game** built with **Python** and **Pygame**, featuring neon visuals, particle effects, and synthesised sound effects.

---

## 📸 Preview

| Screen | Description |
|---|---|
| **Start Screen** | Title, controls guide, blinking prompt |
| **Game** | 25×20 neon grid, glowing snake & food |
| **Pause** | Overlay with resume hint |
| **Game Over** | Final score, high score, level, snake length |

---

## ✨ Features

- **Neon visuals** — glowing snake with cyan→green gradient, pulsing food, soft glow halos
- **Particle effects** — burst of particles on every food eaten
- **Synthesised audio** — unique tones for eating, bonus pickup, level up, and death (no audio files needed)
- **Bonus food** ⭐ — spawns every 5 eats, disappears after 7 seconds, worth 5× points
- **Level progression** — speed increases every 100 points
- **High score** — auto-saved to `snake_hi.txt` across sessions
- **Touch/keyboard support** — Arrow keys or WASD

---

## 🎮 Controls

| Key | Action |
|---|---|
| `↑ ↓ ← →` / `W A S D` | Move snake |
| `P` | Pause / Resume |
| `R` | Restart (game over screen) |
| `Enter` / `Space` | Start game |

---

## 📦 Requirements

- Python 3.8+
- [pygame](https://www.pygame.org/) ≥ 2.0
- [numpy](https://numpy.org/) (for synthesised sound)

Install dependencies:

```bash
pip install pygame numpy
```

---

## 🚀 Run

```bash
python snake.py
```

---

## 🗂 Scoring

| Event | Points |
|---|---|
| Eat regular food | `Level × 10` |
| Eat bonus food ⭐ | `Level × 50` |
| Level up | Every 100 points |

---

## 📁 File Structure

```
New folder/
├── snake.py        # Entire game (single file)
├── snake_hi.txt    # Auto-created — stores high score
└── README.md       # This file
```

---

## 📄 License

Free to use and modify for personal projects.
