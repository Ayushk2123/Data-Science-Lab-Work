

import pygame
import sys
import random
import math
import time

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
COLS, ROWS  = 25, 20
CELL        = 28          # pixels per grid cell
W           = COLS * CELL # 700
H           = ROWS * CELL # 560
HUD_H       = 60
WIN_W, WIN_H = W, H + HUD_H

FPS         = 60
BASE_SPEED  = 8           # ticks per second to update game logic
SPEED_DELTA = 1           # extra ticks/s per level
BONUS_LIFETIME = 7        # seconds bonus food lasts

# ── Colour palette ───────────────────────────
BG          = (5,   5,  16)
GRID_COL    = (0,  245, 255, 10)   # RGBA
NEON_GREEN  = (57,  255,  20)
NEON_CYAN   = (0,   245, 255)
NEON_PINK   = (255,  45, 120)
NEON_YELLOW = (255, 230,   0)
HUD_BG      = (10,  10,  28)
WHITE       = (230, 230, 230)
DIM         = (80,  80,  100)

# ─────────────────────────────────────────────
#  AUDIO  (synthesised with numpy-free method)
# ─────────────────────────────────────────────
import struct, array

def _build_tone(freq, duration, volume=0.4, wave='sine', sample_rate=44100):
    n_samples = int(sample_rate * duration)
    buf = array.array('h')
    peak = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        if wave == 'sine':
            v = math.sin(2 * math.pi * freq * t)
        elif wave == 'saw':
            v = 2 * (t * freq - math.floor(t * freq + 0.5))
        elif wave == 'square':
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        else:
            v = math.sin(2 * math.pi * freq * t)
        # Exponential decay envelope
        env = math.exp(-4 * t / duration)
        buf.append(int(v * env * peak))
    return buf

def _make_sound(buf, sample_rate=44100):
    """Convert array buffer to a pygame Sound object (mono)."""
    # Duplicate for stereo
    stereo = array.array('h')
    for s in buf:
        stereo.append(s)
        stereo.append(s)
    return pygame.sndarray.make_sound(
        __import__('numpy').frombuffer(stereo.tobytes(), dtype='int16').reshape(-1, 2)
    )


class SoundEngine:
    def __init__(self):
        self.enabled = True
        self._sounds = {}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            import numpy
            self._sounds['eat']      = self._build_eat()
            self._sounds['bonus']    = self._build_bonus()
            self._sounds['die']      = self._build_die()
            self._sounds['levelup']  = self._build_levelup()
        except Exception:
            self.enabled = False   # gracefully disable if numpy absent

    def _build_eat(self):
        b1 = _build_tone(600, 0.07, 0.35, 'sine')
        b2 = _build_tone(900, 0.06, 0.25, 'sine')
        combined = array.array('h', [b1[i] + (b2[i] if i < len(b2) else 0) for i in range(len(b1))])
        return _make_sound(combined)

    def _build_bonus(self):
        freqs = [440, 554, 659, 880]
        total = array.array('h', [0] * int(44100 * 0.35))
        for idx, f in enumerate(freqs):
            offset = int(44100 * 0.07 * idx)
            tone = _build_tone(f, 0.18, 0.3, 'sine')
            for i, s in enumerate(tone):
                if offset + i < len(total):
                    total[offset + i] = max(-32767, min(32767, total[offset + i] + s))
        return _make_sound(total)

    def _build_die(self):
        total_len = int(44100 * 0.55)
        total = array.array('h', [0] * total_len)
        specs = [(220, 0.0, 0.08, 'saw', 0.4),
                 (180, 0.08, 0.1, 'saw', 0.4),
                 (140, 0.18, 0.14, 'saw', 0.45),
                 (100, 0.32, 0.22, 'square', 0.55)]
        for freq, start, dur, wave, vol in specs:
            offset = int(44100 * start)
            tone = _build_tone(freq, dur, vol, wave)
            for i, s in enumerate(tone):
                if offset + i < total_len:
                    total[offset + i] = max(-32767, min(32767, total[offset + i] + s))
        return _make_sound(total)

    def _build_levelup(self):
        freqs = [523, 659, 784, 1047]
        total = array.array('h', [0] * int(44100 * 0.45))
        for idx, f in enumerate(freqs):
            offset = int(44100 * 0.08 * idx)
            tone = _build_tone(f, 0.22, 0.35, 'sine')
            for i, s in enumerate(tone):
                if offset + i < len(total):
                    total[offset + i] = max(-32767, min(32767, total[offset + i] + s))
        return _make_sound(total)

    def play(self, name):
        if self.enabled and name in self._sounds:
            self._sounds[name].play()


# ─────────────────────────────────────────────
#  PARTICLE SYSTEM
# ─────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 6)
        self.x  = x;  self.y  = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.color = color
        self.r = random.uniform(3, 6)

    def update(self):
        self.x  += self.vx;  self.y  += self.vy
        self.vx *= 0.88;     self.vy *= 0.88
        self.life -= 0.04

    def draw(self, surf, offset_y):
        if self.life <= 0:
            return
        alpha = int(255 * self.life)
        r = int(self.r * self.life)
        if r < 1:
            return
        col = (*self.color, alpha)
        # Draw onto a temporary surface for alpha
        tmp = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, col, (r+1, r+1), r)
        surf.blit(tmp, (int(self.x) - r - 1, int(self.y) - r - 1 + offset_y))


# ─────────────────────────────────────────────
#  HELPER — glow drawing
# ─────────────────────────────────────────────
def draw_glow_rect(surf, color, rect, radius=6, glow_radius=14, glow_alpha=90):
    """Draw a rounded rect with a soft glow halo."""
    # Glow layer
    gx, gy, gw, gh = rect[0] - glow_radius, rect[1] - glow_radius, rect[2] + glow_radius*2, rect[3] + glow_radius*2
    glow_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
    for step in range(glow_radius, 0, -3):
        a = int(glow_alpha * (step / glow_radius) ** 2)
        c = (*color, a)
        pygame.draw.rect(glow_surf, c, (glow_radius - step, glow_radius - step,
                                         gw - (glow_radius - step)*2, gh - (glow_radius - step)*2),
                         border_radius=radius + step)
    surf.blit(glow_surf, (gx, gy))
    # Solid body
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def draw_glow_circle(surf, color, pos, radius, glow_r=16, glow_alpha=100):
    glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
    for step in range(glow_r, 0, -3):
        a = int(glow_alpha * (step / glow_r) ** 2)
        pygame.draw.circle(glow_surf, (*color, a), (glow_r, glow_r), step)
    surf.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r))
    pygame.draw.circle(surf, color, pos, radius)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ─────────────────────────────────────────────
#  GAME CLASS
# ─────────────────────────────────────────────
class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("🐍  Snake Game")
        self.clock  = pygame.time.Clock()

        # Fonts
        self.font_big   = pygame.font.SysFont("Consolas", 46, bold=True)
        self.font_med   = pygame.font.SysFont("Consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 18)
        self.font_hud   = pygame.font.SysFont("Consolas", 20, bold=True)

        # Surfaces
        self.game_surf  = pygame.Surface((W, H))   # game area
        self.grid_surf  = self._make_grid_surf()

        # Sound
        self.sfx = SoundEngine()

        # High score persistence
        self.hi_score = self._load_hi()

        # State
        self.state = 'start'  # 'start' | 'playing' | 'paused' | 'gameover'
        self._init_game()

        # Toast
        self.toast_text   = ''
        self.toast_timer  = 0
        self.toast_color  = NEON_YELLOW

        # Flash
        self.flash_timer  = 0
        self.flash_color  = NEON_PINK

    # ── Persistence ──────────────────────────
    def _load_hi(self):
        try:
            with open('snake_hi.txt') as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def _save_hi(self):
        try:
            with open('snake_hi.txt', 'w') as f:
                f.write(str(self.hi_score))
        except Exception:
            pass

    # ── Grid surface (static, rendered once) ─
    def _make_grid_surf(self):
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for x in range(0, W + 1, CELL):
            pygame.draw.line(surf, (0, 245, 255, 8), (x, 0), (x, H))
        for y in range(0, H + 1, CELL):
            pygame.draw.line(surf, (0, 245, 255, 8), (0, y), (W, y))
        return surf

    # ── Init / Reset ─────────────────────────
    def _init_game(self):
        mid_x, mid_y = COLS // 2, ROWS // 2
        self.snake   = [(mid_x, mid_y), (mid_x-1, mid_y), (mid_x-2, mid_y)]
        self.dir     = (1, 0)
        self.next_dir = (1, 0)
        self.score   = 0
        self.level   = 1
        self.speed   = BASE_SPEED
        self.particles = []
        self.bonus_food   = None
        self.bonus_expiry = 0
        self.eat_count    = 0
        self._place_food()
        # Tick counter
        self._tick_accum  = 0.0

    def _place_food(self):
        occupied = set(self.snake)
        if self.bonus_food:
            occupied.add(self.bonus_food)
        while True:
            pos = (random.randint(0, COLS-1), random.randint(0, ROWS-1))
            if pos not in occupied:
                self.food = pos
                break

    def _spawn_bonus(self):
        occupied = set(self.snake) | {self.food}
        while True:
            pos = (random.randint(0, COLS-1), random.randint(0, ROWS-1))
            if pos not in occupied:
                self.bonus_food   = pos
                self.bonus_expiry = time.time() + BONUS_LIFETIME
                break

    # ── Game Logic Tick ───────────────────────
    def _game_tick(self):
        self.dir = self.next_dir
        hx, hy  = self.snake[0][0] + self.dir[0], self.snake[0][1] + self.dir[1]

        # Wall collision
        if not (0 <= hx < COLS and 0 <= hy < ROWS):
            return self._die()
        # Self collision
        if (hx, hy) in self.snake:
            return self._die()

        self.snake.insert(0, (hx, hy))

        ate_regular = (hx, hy) == self.food
        ate_bonus   = self.bonus_food and (hx, hy) == self.bonus_food

        if ate_regular:
            pts = self.level * 10
            self.score    += pts
            self.eat_count += 1
            if self.score > self.hi_score:
                self.hi_score = self.score
                self._save_hi()
            cx = hx * CELL + CELL//2
            cy = hy * CELL + CELL//2
            for _ in range(14):
                self.particles.append(Particle(cx, cy, NEON_PINK))
            self.sfx.play('eat')
            self._place_food()
            self._check_level()
            if self.eat_count % 5 == 0:
                self._spawn_bonus()
        elif ate_bonus:
            pts = self.level * 50
            self.score    += pts
            if self.score > self.hi_score:
                self.hi_score = self.score
                self._save_hi()
            cx = hx * CELL + CELL//2
            cy = hy * CELL + CELL//2
            for _ in range(20):
                self.particles.append(Particle(cx, cy, NEON_YELLOW))
            self.sfx.play('bonus')
            self.bonus_food = None
            self._show_toast(f'+{pts}  BONUS!', NEON_YELLOW)
        else:
            self.snake.pop()

        # Bonus expiry check
        if self.bonus_food and time.time() > self.bonus_expiry:
            self.bonus_food = None

    def _check_level(self):
        new_level = self.score // 100 + 1
        if new_level > self.level:
            self.level = new_level
            self.speed = BASE_SPEED + (self.level - 1) * SPEED_DELTA
            self.sfx.play('levelup')
            self._show_toast(f'LEVEL {self.level}  🚀', NEON_CYAN)

    def _die(self):
        self.state = 'gameover'
        self.sfx.play('die')
        self.flash_timer = 8   # frames of flash

    # ── Toast ─────────────────────────────────
    def _show_toast(self, text, color):
        self.toast_text  = text
        self.toast_timer = 90   # frames
        self.toast_color = color

    # ── Input ─────────────────────────────────
    def _handle_input(self, event):
        if event.type == pygame.QUIT:
            self._quit()

        if event.type == pygame.KEYDOWN:
            k = event.key
            if self.state == 'start':
                if k in (pygame.K_RETURN, pygame.K_SPACE):
                    self.state = 'playing'
            elif self.state == 'playing':
                if k == pygame.K_p:
                    self.state = 'paused'
                self._set_dir(k)
            elif self.state == 'paused':
                if k == pygame.K_p:
                    self.state = 'playing'
            elif self.state == 'gameover':
                if k == pygame.K_r:
                    self._init_game()
                    self.state = 'playing'

    def _set_dir(self, k):
        dirs = {
            pygame.K_UP:    (0, -1), pygame.K_w: (0, -1),
            pygame.K_DOWN:  (0,  1), pygame.K_s: (0,  1),
            pygame.K_LEFT:  (-1, 0), pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1,  0), pygame.K_d: (1,  0),
        }
        if k in dirs:
            nd = dirs[k]
            # Prevent reversing
            if nd[0] != -self.dir[0] or nd[1] != -self.dir[1]:
                self.next_dir = nd

    # ── Draw ──────────────────────────────────
    def _draw_game(self, dt):
        # Background
        self.game_surf.fill(BG)
        self.game_surf.blit(self.grid_surf, (0, 0))

        # Particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()
            p.draw(self.game_surf, 0)

        # Bonus food (pulsing star)
        if self.bonus_food:
            bx = self.bonus_food[0] * CELL + CELL // 2
            by = self.bonus_food[1] * CELL + CELL // 2
            pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
            r = int(CELL * 0.32 + 3 * pulse)
            draw_glow_circle(self.game_surf, NEON_YELLOW, (bx, by), r, glow_r=22, glow_alpha=120)
            # inner star
            self._draw_star(self.game_surf, bx, by, 5, r * 0.6, r * 0.28, (255, 255, 180))
            # countdown bar
            remaining = max(0, self.bonus_expiry - time.time()) / BONUS_LIFETIME
            bar_w = int(CELL * remaining)
            pygame.draw.rect(self.game_surf, NEON_YELLOW,
                             (self.bonus_food[0]*CELL, self.bonus_food[1]*CELL + CELL - 4, bar_w, 4))

        # Regular food (pulsing circle)
        fx = self.food[0] * CELL + CELL // 2
        fy = self.food[1] * CELL + CELL // 2
        pulse = 0.5 + 0.5 * math.sin(time.time() * 5)
        r = int(CELL * 0.30 + 2 * pulse)
        draw_glow_circle(self.game_surf, NEON_PINK, (fx, fy), r, glow_r=18, glow_alpha=130)

        # Snake
        length = len(self.snake)
        for i, seg in enumerate(self.snake):
            t   = i / max(length - 1, 1)
            col = lerp_color(NEON_CYAN, NEON_GREEN, t)
            x   = seg[0] * CELL + 2
            y   = seg[1] * CELL + 2
            sz  = CELL - 4
            glow_a = 120 if i == 0 else int(80 * (1 - t))
            draw_glow_rect(self.game_surf, col,
                           pygame.Rect(x, y, sz, sz),
                           radius=6, glow_radius=10, glow_alpha=glow_a)

            # Eyes on head
            if i == 0:
                ex_off = 1 if self.dir[0] > 0 else (-1 if self.dir[0] < 0 else 0)
                ey_off = 1 if self.dir[1] > 0 else (-1 if self.dir[1] < 0 else 0)
                if self.dir[0] != 0:   # horizontal
                    e1 = (x + sz*2//3, y + sz//4)
                    e2 = (x + sz*2//3, y + sz*3//4)
                else:                  # vertical
                    e1 = (x + sz//4,   y + sz*2//3)
                    e2 = (x + sz*3//4, y + sz*2//3)
                pygame.draw.circle(self.game_surf, BG, e1, 3)
                pygame.draw.circle(self.game_surf, BG, e2, 3)

        # Flash on death
        if self.flash_timer > 0:
            alpha = int(160 * self.flash_timer / 8)
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*NEON_PINK, alpha))
            self.game_surf.blit(fl, (0, 0))
            self.flash_timer -= 1

        # Toast
        if self.toast_timer > 0:
            alpha = min(255, self.toast_timer * 5)
            ts = self.font_med.render(self.toast_text, True, self.toast_color)
            ts.set_alpha(alpha)
            rx = (W - ts.get_width()) // 2
            ry = (H - ts.get_height()) // 2
            self.game_surf.blit(ts, (rx, ry))
            self.toast_timer -= 1

    def _draw_star(self, surf, cx, cy, points, outer_r, inner_r, color):
        verts = []
        for i in range(points * 2):
            angle = math.pi * i / points - math.pi / 2
            r     = outer_r if i % 2 == 0 else inner_r
            verts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        if len(verts) >= 3:
            pygame.draw.polygon(surf, color, verts)

    def _draw_hud(self):
        hud = pygame.Surface((WIN_W, HUD_H))
        hud.fill(HUD_BG)
        # Top border glow
        pygame.draw.line(hud, NEON_CYAN, (0, 0), (WIN_W, 0), 2)

        items = [
            ('SCORE',      str(self.score),    W // 4),
            ('HIGH SCORE', str(self.hi_score), W // 2),
            ('LEVEL',      str(self.level),    W * 3 // 4),
        ]
        for label, val, cx in items:
            lbl = self.font_small.render(label, True, DIM)
            val_surf = self.font_hud.render(val, True, NEON_CYAN)
            hud.blit(lbl,     (cx - lbl.get_width()//2,     6))
            hud.blit(val_surf,(cx - val_surf.get_width()//2, 28))

        self.screen.blit(hud, (0, H))

    # ── Overlay Screens ───────────────────────
    def _draw_start(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((5, 5, 16, 210))
        self.screen.blit(ov, (0, 0))

        cx = WIN_W // 2
        # Title
        t1 = self.font_big.render("SNAKE  GAME", True, NEON_CYAN)
        self.screen.blit(t1, (cx - t1.get_width()//2, WIN_H//2 - 130))
        # Subtitle
        t2 = self.font_small.render("The Classic, Reimagined", True, DIM)
        self.screen.blit(t2, (cx - t2.get_width()//2, WIN_H//2 - 75))
        # Controls
        controls = [
            ("Arrow Keys / WASD", "Move"),
            ("P",                  "Pause / Resume"),
            ("R",                  "Restart (after game over)"),
        ]
        y = WIN_H//2 - 30
        for keys, action in controls:
            k_surf = self.font_small.render(f"[ {keys} ]", True, NEON_GREEN)
            a_surf = self.font_small.render(action, True, WHITE)
            self.screen.blit(k_surf, (cx - 220, y))
            self.screen.blit(a_surf, (cx - 220 + k_surf.get_width() + 12, y))
            y += 30
        # Press Enter
        blink = int(time.time() * 2) % 2 == 0
        if blink:
            prompt = self.font_med.render("Press ENTER to Start", True, NEON_YELLOW)
            self.screen.blit(prompt, (cx - prompt.get_width()//2, WIN_H//2 + 90))

    def _draw_paused(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((5, 5, 16, 180))
        self.screen.blit(ov, (0, 0))
        cx = WIN_W // 2
        p  = self.font_big.render("PAUSED", True, NEON_CYAN)
        self.screen.blit(p, (cx - p.get_width()//2, WIN_H//2 - 40))
        hint = self.font_small.render("Press  P  to resume", True, DIM)
        self.screen.blit(hint, (cx - hint.get_width()//2, WIN_H//2 + 30))

    def _draw_gameover(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((5, 5, 16, 200))
        self.screen.blit(ov, (0, 0))
        cx = WIN_W // 2
        go = self.font_big.render("GAME  OVER", True, NEON_PINK)
        self.screen.blit(go, (cx - go.get_width()//2, WIN_H//2 - 140))
        # Stats
        stats = [
            ("Score",      str(self.score)),
            ("High Score", str(self.hi_score)),
            ("Level",      str(self.level)),
            ("Snake Len",  str(len(self.snake))),
        ]
        y = WIN_H//2 - 70
        for label, val in stats:
            lbl = self.font_small.render(label, True, DIM)
            v   = self.font_med.render(val, True, NEON_CYAN)
            self.screen.blit(lbl, (cx - 160, y))
            self.screen.blit(v,   (cx + 40,  y - 2))
            y += 38
        # Restart prompt
        blink = int(time.time() * 2) % 2 == 0
        if blink:
            r = self.font_med.render("Press  R  to play again", True, NEON_GREEN)
            self.screen.blit(r, (cx - r.get_width()//2, y + 12))

    # ── Main Loop ─────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0   # seconds

            for event in pygame.event.get():
                self._handle_input(event)

            # Game logic at variable tick rate
            if self.state == 'playing':
                self._tick_accum += dt * self.speed
                while self._tick_accum >= 1.0:
                    self._game_tick()
                    self._tick_accum -= 1.0

            # ── Render ──
            self._draw_game(dt)
            self.screen.blit(self.game_surf, (0, 0))
            self._draw_hud()

            if self.state == 'start':
                self._draw_start()
            elif self.state == 'paused':
                self._draw_paused()
            elif self.state == 'gameover':
                self._draw_gameover()

            pygame.display.flip()

    def _quit(self):
        self._save_hi()
        pygame.quit()
        sys.exit()
if __name__ == '__main__':
    game = SnakeGame()
    game.run()
