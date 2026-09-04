#!/usr/bin/env python3
"""Scene Generator for BUSY Bar Screen Saver.

Generates procedural 72x16 pixel art scenes, animated scene sequences,
and converts arbitrary images or GIFs into optimized BUSY Bar scenes.
"""

from __future__ import annotations

import argparse
import colorsys
import math
import os
import random
import sys
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

WIDTH = 72
HEIGHT = 16
APP_DIR = Path(__file__).resolve().parent
DEFAULT_SCENES_DIR = APP_DIR / "scenes"


# ============================================================================
# Procedural Scene Generators (72x16 RGB)
# ============================================================================

def gen_synthwave(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Retro 80s outrun synthwave horizon with neon sun and moving grid."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (10, 4, 25, 255))
    draw = ImageDraw.Draw(img)

    horizon_y = 9

    # Sky gradient: deep purple (top) to warm magenta/orange (horizon)
    for y in range(horizon_y):
        t = y / max(1, horizon_y - 1)
        r = int(25 + 200 * t)
        g = int(5 + 40 * (t ** 1.5))
        b = int(45 + 50 * (1 - t))
        draw.line([(0, y), (WIDTH - 1, y)], fill=(r, g, b, 255))

    # Sun in the center
    cx, cy, r_sun = 36, 7, 5
    for y in range(cy - r_sun, cy + r_sun + 1):
        if 0 <= y < horizon_y:
            # Cut horizontal black scanlines in lower half of sun
            if y >= cy and (y - cy) % 2 == 1:
                continue
            dx = math.sqrt(max(0, r_sun * r_sun - (y - cy) * (y - cy)))
            x0 = int(cx - dx)
            x1 = int(cx + dx)
            # Sun gradient: bright yellow top to hot pink bottom
            st = (y - (cy - r_sun)) / (2 * r_sun)
            sr = 255
            sg = int(220 * (1 - st) + 50 * st)
            sb = int(30 * (1 - st) + 160 * st)
            draw.line([(x0, y), (x1, y)], fill=(sr, sg, sb, 255))

    # Mountain silhouettes in background
    mountains = [
        (0, 8), (8, 6), (15, 8), (22, 5), (30, 8),
        (42, 8), (50, 5), (58, 8), (65, 6), (71, 8)
    ]
    for i in range(len(mountains) - 1):
        x_a, y_a = mountains[i]
        x_b, y_b = mountains[i + 1]
        for x in range(x_a, x_b + 1):
            t = (x - x_a) / max(1, (x_b - x_a))
            my = int(y_a + t * (y_b - y_a))
            # Don't cover center sun completely, just ground level
            if abs(x - cx) > 4:
                draw.line([(x, my), (x, horizon_y - 1)], fill=(20, 10, 35, 255))

    # Horizon glow line
    draw.line([(0, horizon_y), (WIDTH - 1, horizon_y)], fill=(255, 60, 180, 255))

    # Ground perspective grid
    # Perspective longitudinal lines vanishing towards (cx, horizon_y)
    v_lines = [-50, -25, -5, 10, 24, 36, 48, 62, 77, 97, 122]
    for vx in v_lines:
        draw.line([(cx, horizon_y), (vx, HEIGHT - 1)], fill=(0, 180, 220, 180))

    # Transverse moving grid lines
    offset = (frame / total_frames)
    for i in range(4):
        p = ((i + offset) % 4) / 4.0
        # Exponential spacing for perspective
        gy = int(horizon_y + 1 + (HEIGHT - horizon_y - 1) * (p ** 1.8))
        if horizon_y < gy < HEIGHT:
            alpha = int(120 + 135 * p)
            draw.line([(0, gy), (WIDTH - 1, gy)], fill=(0, 220, 240, alpha))

    return img


def gen_matrix(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Cascading green digital rain Matrix code."""
    random.seed(42)
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    columns = []
    for col in range(0, WIDTH, 2):
        speed = random.choice([0.8, 1.0, 1.2, 1.5, 2.0])
        start_y = random.uniform(-10, 10)
        trail_len = random.randint(5, 12)
        columns.append((col, speed, start_y, trail_len))

    for col, speed, start_y, trail_len in columns:
        head_y = int(start_y + frame * speed * (HEIGHT / total_frames * 2)) % (HEIGHT + trail_len + 5) - 3
        for i in range(trail_len):
            y = head_y - i
            if 0 <= y < HEIGHT:
                if i == 0:
                    # Bright white / light green head
                    color = (220, 255, 230, 255)
                elif i < 3:
                    # Vivid matrix green
                    color = (0, 255, 70, 255)
                else:
                    # Fading dark green
                    fade = 1.0 - (i / trail_len)
                    color = (0, int(180 * fade), int(40 * fade), 255)
                draw.point((col, y), fill=color)

    return img


def gen_fireplace(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Cozy fireplace with flickering flame particles and glowing embers."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (8, 4, 4, 255))
    draw = ImageDraw.Draw(img)

    # Hearth border / stone base
    draw.line([(0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)], fill=(40, 30, 30, 255))

    # Logs at the bottom center
    draw.line([(22, HEIGHT - 2), (50, HEIGHT - 2)], fill=(65, 32, 15, 255))
    draw.line([(25, HEIGHT - 3), (47, HEIGHT - 3)], fill=(50, 25, 10, 255))

    # Fire simulation with seeded noise based on frame
    random.seed(frame * 17 + 101)
    fire_palette = [
        (255, 255, 230, 255),  # White-hot
        (255, 220, 50, 255),   # Yellow
        (255, 140, 20, 255),   # Bright Orange
        (230, 60, 10, 255),    # Red-Orange
        (160, 20, 10, 255),    # Deep Red
        (80, 10, 10, 255),     # Dark Ember
    ]

    cx = 36
    for i in range(70):
        # Center-weighted particle emission
        px = int(random.gauss(cx, 7))
        if 20 <= px <= 52:
            dist_center = abs(px - cx) / 16.0
            max_h = int(12 * (1.0 - dist_center) + random.uniform(-1, 2))
            h = random.randint(1, max(1, max_h))
            py = (HEIGHT - 3) - h
            if 0 <= py < HEIGHT:
                temp = (py - (HEIGHT - 12)) / 9.0  # 0 at top, 1 at bottom
                temp = max(0.0, min(1.0, temp + random.uniform(-0.15, 0.15)))
                idx = int((1.0 - temp) * (len(fire_palette) - 1))
                draw.point((px, py), fill=fire_palette[idx])

    # Ember sparks lifting into the chimney
    for _ in range(8):
        ex = random.randint(26, 46)
        ey = random.randint(1, 6)
        draw.point((ex, ey), fill=(255, 180, 50, random.randint(150, 255)))

    return img


def gen_aquarium(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Deep ocean aquarium with swimming fish, coral, and rising bubbles."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (2, 10, 30, 255))
    draw = ImageDraw.Draw(img)

    # Water vertical gradient
    for y in range(HEIGHT - 2):
        t = y / max(1, HEIGHT - 3)
        r = int(2 + 4 * t)
        g = int(35 * (1 - t * 0.5))
        b = int(90 * (1 - t * 0.4))
        draw.line([(0, y), (WIDTH - 1, y)], fill=(r, g, b, 255))

    # Sandy seabed
    draw.line([(0, HEIGHT - 2), (WIDTH - 1, HEIGHT - 2)], fill=(160, 130, 80, 255))
    draw.line([(0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)], fill=(120, 95, 55, 255))

    # Seaweed stalks swaying
    sway = math.sin(frame * 2 * math.pi / total_frames)
    seaweed_xs = [6, 12, 58, 66]
    for sx in seaweed_xs:
        for seg in range(6):
            sy = HEIGHT - 3 - seg
            cur_sway = int(sway * (seg / 3.0))
            color = (20, 160 + seg * 12, 40, 255)
            draw.point((sx + cur_sway, sy), fill=color)

    # Coral branch on the right
    draw.point((62, HEIGHT - 3), fill=(220, 80, 90, 255))
    draw.point((63, HEIGHT - 4), fill=(220, 80, 90, 255))
    draw.point((61, HEIGHT - 4), fill=(220, 80, 90, 255))
    draw.point((63, HEIGHT - 5), fill=(240, 110, 120, 255))

    # Rising air bubbles
    for i in range(5):
        bx = 15 + i * 11
        by = int((HEIGHT - 3) - ((frame * 1.5 + i * 4) % (HEIGHT - 4)))
        draw.point((bx, by), fill=(140, 220, 255, 200))

    # Swimming tropical clownfish (orange / white bands)
    # Fish 1: swimming right
    fish1_x = int((frame / total_frames) * (WIDTH + 14)) - 10
    fish1_y = 6 + int(math.sin(frame * 2 * math.pi / total_frames) * 1.5)
    if -6 < fish1_x < WIDTH + 6:
        draw.point((fish1_x, fish1_y), fill=(255, 120, 0, 255))
        draw.point((fish1_x - 1, fish1_y), fill=(255, 255, 255, 255))
        draw.point((fish1_x - 2, fish1_y), fill=(255, 100, 0, 255))
        draw.point((fish1_x - 3, fish1_y), fill=(255, 255, 255, 255))
        draw.point((fish1_x - 4, fish1_y - 1), fill=(255, 120, 0, 255))
        draw.point((fish1_x - 4, fish1_y + 1), fill=(255, 120, 0, 255))
        draw.point((fish1_x + 1, fish1_y), fill=(0, 0, 0, 255))  # eye/nose

    # Fish 2: small neon blue fish swimming left
    fish2_x = WIDTH - int(((frame * 1.2) / total_frames) * (WIDTH + 12)) + 6
    fish2_y = 11 + int(math.cos(frame * 2 * math.pi / total_frames) * 1.2)
    if -4 < fish2_x < WIDTH + 4:
        draw.point((fish2_x, fish2_y), fill=(0, 255, 255, 255))
        draw.point((fish2_x + 1, fish2_y), fill=(0, 180, 255, 255))
        draw.point((fish2_x + 2, fish2_y), fill=(0, 100, 220, 255))

    return img


def gen_starfield(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Deep space starfield with glowing nebula, twinkling stars, and shooting star."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (2, 2, 8, 255))
    draw = ImageDraw.Draw(img)

    # Soft cosmic nebula clouds (magenta / cyan haze)
    for x in range(WIDTH):
        for y in range(HEIGHT):
            n1 = math.sin(x * 0.08 + y * 0.15) * math.cos(y * 0.25)
            n2 = math.cos(x * 0.12 - y * 0.18)
            if n1 > 0.3:
                alpha = int(45 * (n1 - 0.3))
                draw.point((x, y), fill=(160, 20, 140, alpha))
            if n2 > 0.4:
                alpha = int(40 * (n2 - 0.4))
                draw.point((x, y), fill=(10, 80, 160, alpha))

    # Twinkling stars (fixed positions, variable brightness)
    random.seed(99)
    star_positions = [(random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1), random.uniform(0, 2 * math.pi)) for _ in range(40)]
    for sx, sy, phase in star_positions:
        twinkle = (math.sin(frame * 2 * math.pi / total_frames + phase) + 1.0) / 2.0
        brightness = int(80 + 175 * twinkle)
        color = (brightness, brightness, int(brightness * 0.95), 255)
        draw.point((sx, sy), fill=color)

    # Distant planet
    draw.point((56, 4), fill=(180, 100, 230, 255))
    draw.point((57, 4), fill=(220, 130, 255, 255))
    draw.point((56, 5), fill=(140, 70, 190, 255))
    draw.point((57, 5), fill=(180, 100, 230, 255))

    # Occasional shooting star streak
    shoot_t = (frame % total_frames) / total_frames
    if 0.2 <= shoot_t <= 0.5:
        progress = (shoot_t - 0.2) / 0.3
        hx = int(10 + progress * 55)
        hy = int(2 + progress * 8)
        draw.point((hx, hy), fill=(255, 255, 255, 255))
        draw.point((hx - 1, hy), fill=(200, 230, 255, 200))
        draw.point((hx - 2, hy - 1), fill=(100, 180, 255, 130))

    return img


def gen_cyberpunk_city(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Cyberpunk skyline with lit skyscraper windows, neon lights, and moon."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 6, 16, 255))
    draw = ImageDraw.Draw(img)

    # Crescent Moon
    mx, my = 60, 3
    draw.point((mx, my), fill=(255, 255, 200, 255))
    draw.point((mx + 1, my), fill=(255, 255, 220, 255))
    draw.point((mx, my + 1), fill=(255, 255, 200, 255))
    draw.point((mx + 1, my + 1), fill=(255, 255, 240, 255))

    # Skyscrapers definitions: (x_start, width, height, base_color)
    buildings = [
        (0, 8, 12, (20, 22, 38)),
        (7, 9, 9, (15, 17, 30)),
        (15, 7, 14, (25, 28, 48)),
        (21, 10, 11, (18, 20, 35)),
        (30, 8, 15, (30, 32, 55)),
        (37, 7, 8, (16, 18, 32)),
        (43, 9, 13, (24, 26, 44)),
        (51, 8, 10, (18, 20, 35)),
        (58, 8, 14, (28, 30, 50)),
        (65, 7, 11, (20, 22, 38)),
    ]

    for bx, bw, bh, bcol in buildings:
        by = HEIGHT - bh
        draw.rectangle([bx, by, bx + bw - 1, HEIGHT - 1], fill=(*bcol, 255))

        # Antenna with blinking red beacon
        if bh >= 13:
            ant_x = bx + bw // 2
            draw.line([(ant_x, by - 2), (ant_x, by)], fill=(80, 80, 100, 255))
            blink = (frame % 4 < 2)
            beacon_col = (255, 30, 30, 255) if blink else (80, 10, 10, 255)
            draw.point((ant_x, by - 3), fill=beacon_col)

        # Windows
        random.seed(bx * 31 + bh)
        for wy in range(by + 2, HEIGHT - 1, 2):
            for wx in range(bx + 1, bx + bw - 1, 2):
                if random.random() < 0.45:
                    win_col = random.choice([
                        (255, 230, 100, 255),  # Warm yellow
                        (0, 230, 255, 255),    # Cyan neon
                        (255, 60, 160, 255),   # Magenta neon
                        (200, 220, 255, 255),  # White
                    ])
                    draw.point((wx, wy), fill=win_col)

    # Neon billboard on center building
    neon_blink = (frame % 8 < 5)
    billboard_col = (255, 20, 120, 255) if neon_blink else (70, 10, 40, 255)
    draw.line([(32, HEIGHT - 11), (35, HEIGHT - 11)], fill=billboard_col)

    return img


def gen_aurora(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Aurora borealis waving across starry sky over mountain pine trees."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (4, 6, 18, 255))
    draw = ImageDraw.Draw(img)

    # Background stars
    random.seed(55)
    for _ in range(25):
        sx = random.randint(0, WIDTH - 1)
        sy = random.randint(0, 9)
        draw.point((sx, sy), fill=(200, 220, 255, random.randint(120, 240)))

    # Waving Aurora ribbons
    phase = frame * 2 * math.pi / total_frames
    for x in range(WIDTH):
        wave1 = math.sin(x * 0.12 + phase) * 2.5 + math.cos(x * 0.08 - phase * 0.5) * 1.5
        ay = 4 + wave1
        for y in range(0, 11):
            dist = abs(y - ay)
            if dist < 4:
                glow = 1.0 - (dist / 4.0)
                g = int(240 * glow)
                r = int(50 * (1 - glow) + 120 * glow * (y / 10.0))
                b = int(120 + 120 * (1 - glow))
                draw.point((x, y), fill=(r, g, b, int(180 * glow)))

    # Mountain peaks
    mountains = [
        (0, 11), (12, 8), (25, 12), (38, 7), (52, 11), (64, 8), (71, 10)
    ]
    for i in range(len(mountains) - 1):
        x_a, y_a = mountains[i]
        x_b, y_b = mountains[i + 1]
        for x in range(x_a, x_b + 1):
            t = (x - x_a) / max(1, (x_b - x_a))
            my = int(y_a + t * (y_b - y_a))
            draw.line([(x, my), (x, HEIGHT - 1)], fill=(12, 16, 26, 255))
            if my <= 9:
                draw.point((x, my), fill=(180, 210, 240, 200))

    # Pine tree silhouettes along bottom
    tree_xs = [4, 9, 17, 28, 33, 45, 57, 62, 69]
    for tx in tree_xs:
        draw.line([(tx, HEIGHT - 4), (tx, HEIGHT - 1)], fill=(5, 8, 12, 255))
        draw.point((tx - 1, HEIGHT - 2), fill=(5, 8, 12, 255))
        draw.point((tx + 1, HEIGHT - 2), fill=(5, 8, 12, 255))
        draw.point((tx, HEIGHT - 5), fill=(8, 14, 18, 255))

    return img


def gen_game_of_life(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Conway's Game of Life evolving colony on 72x16 grid."""
    grid = [[0] * WIDTH for _ in range(HEIGHT)]
    random.seed(1234)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if random.random() < 0.22:
                grid[y][x] = 1

    sim_steps = frame + 5
    for _ in range(sim_steps):
        new_grid = [[0] * WIDTH for _ in range(HEIGHT)]
        for y in range(HEIGHT):
            for x in range(WIDTH):
                neighbors = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny = (y + dy) % HEIGHT
                        nx = (x + dx) % WIDTH
                        neighbors += (grid[ny][nx] > 0)
                if grid[y][x] > 0:
                    if neighbors in (2, 3):
                        new_grid[y][x] = min(5, grid[y][x] + 1)
                else:
                    if neighbors == 3:
                        new_grid[y][x] = 1
        grid = new_grid

    img = Image.new("RGBA", (WIDTH, HEIGHT), (2, 2, 10, 255))
    draw = ImageDraw.Draw(img)

    age_colors = [
        (0, 0, 0, 255),
        (0, 255, 220, 255),   # Newborn: bright cyan
        (60, 255, 80, 255),   # Young: lime green
        (255, 220, 0, 255),   # Mature: yellow
        (255, 80, 160, 255),  # Old: hot pink
        (180, 50, 255, 255),  # Elder: electric purple
    ]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            age = grid[y][x]
            if age > 0:
                draw.point((x, y), fill=age_colors[min(age, len(age_colors) - 1)])

    return img


def gen_pacman(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Retro 80s arcade maze with Pac-Man eating dots chased by ghosts."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Maze blue borders top & bottom
    draw.line([(0, 1), (WIDTH - 1, 1)], fill=(0, 50, 220, 255))
    draw.line([(0, 14), (WIDTH - 1, 14)], fill=(0, 50, 220, 255))

    # Corridor dots
    pac_x = int((frame / total_frames) * (WIDTH + 24)) - 10
    mouth_open = (frame % 4 < 2)

    for dx in range(3, WIDTH - 2, 4):
        if dx > pac_x + 3:
            draw.point((dx, 8), fill=(255, 220, 160, 255))

    # Large power pellet at right
    if WIDTH - 6 > pac_x + 3 and (frame % 6 < 3):
        draw.rectangle([WIDTH - 7, 7, WIDTH - 6, 9], fill=(255, 220, 160, 255))

    # Pac-Man
    py = 8
    if -5 <= pac_x <= WIDTH + 5:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    if mouth_open and dx >= 0 and abs(dy) <= dx:
                        continue
                    draw.point((pac_x + dx, py + dy), fill=(255, 230, 0, 255))

    # Ghost 1: Blinky (Red)
    g1_x = pac_x - 12
    if -6 <= g1_x <= WIDTH + 6:
        _draw_ghost(draw, g1_x, py, (255, 0, 0, 255), frame)

    # Ghost 2: Inky (Cyan)
    g2_x = pac_x - 22
    if -6 <= g2_x <= WIDTH + 6:
        _draw_ghost(draw, g2_x, py, (0, 255, 255, 255), frame)

    return img


def _draw_ghost(draw: ImageDraw.ImageDraw, gx: int, gy: int, color: tuple, frame: int) -> None:
    """Helper to draw a classic retro 5x5 arcade ghost."""
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dy == -2 and (dx == -2 or dx == 2):
                continue
            if dy == 2 and ((dx + frame) % 2 == 0):
                continue
            draw.point((gx + dx, gy + dy), fill=color)
    draw.point((gx - 1, gy - 1), fill=(255, 255, 255, 255))
    draw.point((gx + 1, gy - 1), fill=(255, 255, 255, 255))
    draw.point((gx, gy - 1), fill=(0, 0, 200, 255))
    draw.point((gx + 2, gy - 1), fill=(0, 0, 200, 255))


def gen_lava_lamp(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Hypnotic glowing metaballs floating in a retro lava lamp."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (12, 2, 20, 255))
    draw = ImageDraw.Draw(img)

    t = frame * 2 * math.pi / total_frames
    blobs = [
        (14 + math.sin(t) * 4, 8 + math.cos(t * 1.2) * 5, 5.0),
        (28 + math.cos(t * 0.8) * 6, 8 + math.sin(t) * 4, 4.5),
        (44 + math.sin(t * 1.4) * 5, 8 - math.cos(t * 0.9) * 5, 5.5),
        (58 + math.cos(t * 1.1) * 4, 8 + math.sin(t * 1.3) * 4, 4.0),
    ]

    for x in range(WIDTH):
        for y in range(HEIGHT):
            sum_field = 0.0
            for bx, by, br in blobs:
                d2 = (x - bx) ** 2 + (y - by) ** 2
                if d2 > 0:
                    sum_field += (br * br) / d2
                else:
                    sum_field += 10.0

            if sum_field > 0.9:
                glow = min(1.0, (sum_field - 0.9) / 1.1)
                r = int(220 + 35 * glow)
                g = int(30 + 200 * (glow ** 1.8))
                b = int(120 * (1.0 - glow))
                draw.point((x, y), fill=(r, g, b, 255))

    return img


def gen_sunset_beach(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Tropical sunset with palm tree silhouette and ocean wave reflections."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (20, 5, 25, 255))
    draw = ImageDraw.Draw(img)

    horizon_y = 9

    # Sunset sky gradient
    for y in range(horizon_y):
        t = y / max(1, horizon_y - 1)
        r = int(180 + 75 * t)
        g = int(40 + 120 * t)
        b = int(80 * (1 - t))
        draw.line([(0, y), (WIDTH - 1, y)], fill=(r, g, b, 255))

    # Sun setting on horizon
    sx, sy, sr = 45, horizon_y, 4
    for y in range(sy - sr, horizon_y):
        dx = math.sqrt(max(0, sr * sr - (y - sy) * (y - sy)))
        draw.line([(int(sx - dx), y), (int(sx + dx), y)], fill=(255, 240, 90, 255))

    # Ocean water with sunset reflection
    wave_shift = (frame / total_frames) * 2 * math.pi
    for y in range(horizon_y, HEIGHT):
        t = (y - horizon_y) / max(1, HEIGHT - horizon_y - 1)
        base_col = (int(10 + 20 * t), int(20 + 30 * t), int(60 + 40 * t), 255)
        draw.line([(0, y), (WIDTH - 1, y)], fill=base_col)

        glitter_w = int(6 + (y - horizon_y) * 2)
        wave_flicker = math.sin(y * 2.0 + wave_shift)
        if wave_flicker > -0.2:
            gx0 = sx - glitter_w // 2
            gx1 = sx + glitter_w // 2
            draw.line([(gx0, y), (gx1, y)], fill=(255, int(160 + 60 * wave_flicker), 50, 220))

    # Palm tree silhouette
    trunk_pts = [(6, HEIGHT - 1), (7, 12), (9, 8), (12, 4)]
    for i in range(len(trunk_pts) - 1):
        x0, y0 = trunk_pts[i]
        x1, y1 = trunk_pts[i + 1]
        draw.line([(x0, y0), (x1, y1)], fill=(10, 5, 8, 255), width=2)

    top_x, top_y = 12, 4
    frond_deltas = [
        (-7, -1), (-6, 3), (1, -3), (6, -2), (7, 2)
    ]
    for fdx, fdy in frond_deltas:
        draw.line([(top_x, top_y), (top_x + fdx, top_y + fdy)], fill=(8, 4, 6, 255))

    return img


def gen_rainbow_wave(frame: int = 0, total_frames: int = 16) -> Image.Image:
    """Classic demoscene sine wave plasma effect cycling full RGB spectrum."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    t = (frame / total_frames) * 2 * math.pi
    for x in range(WIDTH):
        for y in range(HEIGHT):
            v1 = math.sin(x * 0.15 + t)
            v2 = math.sin(y * 0.35 - t * 1.5)
            v3 = math.sin((x + y) * 0.12 + t * 0.7)
            v = (v1 + v2 + v3 + 3.0) / 6.0
            hue = (v + (frame / total_frames)) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.95, 1.0)
            draw.point((x, y), fill=(int(r * 255), int(g * 255), int(b * 255), 255))

    return img


PRESETS: dict[str, Callable[[int, int], Image.Image]] = {
    "synthwave": gen_synthwave,
    "matrix": gen_matrix,
    "fireplace": gen_fireplace,
    "aquarium": gen_aquarium,
    "starfield": gen_starfield,
    "cyberpunk_city": gen_cyberpunk_city,
    "aurora": gen_aurora,
    "game_of_life": gen_game_of_life,
    "pacman": gen_pacman,
    "lava_lamp": gen_lava_lamp,
    "sunset_beach": gen_sunset_beach,
    "rainbow_wave": gen_rainbow_wave,
}


# ============================================================================
# Image & GIF Conversion Engine
# ============================================================================

def convert_image(
    input_path: Path,
    output_path: Path,
    mode: str = "crop",
    enhance: bool = True,
    dither: bool = False,
) -> Path:
    """Convert any external image file to 72x16 pixel art PNG.

    Modes:
      - crop: scales to fill 72x16 and center-crops (recommended for photos/wallpapers)
      - fit: scales to fit inside 72x16 with black borders
      - stretch: stretches to exactly 72x16
    """
    with Image.open(input_path) as orig:
        img = orig.convert("RGBA")

    w, h = img.size
    if mode == "stretch":
        resized = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    elif mode == "fit":
        scale = min(WIDTH / w, HEIGHT / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
        resized = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        ox = (WIDTH - nw) // 2
        oy = (HEIGHT - nh) // 2
        resized.paste(scaled, (ox, oy))
    else:  # "crop"
        scale = max(WIDTH / w, HEIGHT / h)
        nw, nh = max(WIDTH, int(w * scale)), max(HEIGHT, int(h * scale))
        scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - WIDTH) // 2
        top = (nh - HEIGHT) // 2
        resized = scaled.crop((left, top, left + WIDTH, top + HEIGHT))

    if enhance:
        rgb = resized.convert("RGB")
        enh_contrast = ImageEnhance.Contrast(rgb).enhance(1.25)
        enh_color = ImageEnhance.Color(enh_contrast).enhance(1.3)
        resized = enh_color.convert("RGBA")

    if dither:
        rgb = resized.convert("RGB")
        dithered = rgb.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        resized = dithered.convert("RGBA")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resized.save(output_path, format="PNG")
    return output_path


def convert_gif(
    input_path: Path,
    output_dir: Path,
    max_frames: int = 24,
    mode: str = "crop",
    enhance: bool = True,
) -> Path:
    """Extract and optimize frames from an animated GIF into a scene folder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(input_path) as gif:
        total_gif_frames = getattr(gif, "n_frames", 1)
        step = max(1, total_gif_frames // max_frames)
        frame_idx = 0

        for f in range(0, total_gif_frames, step):
            if frame_idx >= max_frames:
                break
            gif.seek(f)
            frame_img = gif.convert("RGBA")
            frame_path = output_dir / f"{frame_idx:03d}.png"

            w, h = frame_img.size
            if mode == "stretch":
                resized = frame_img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            elif mode == "fit":
                scale = min(WIDTH / w, HEIGHT / h)
                nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                scaled = frame_img.resize((nw, nh), Image.Resampling.LANCZOS)
                resized = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
                ox = (WIDTH - nw) // 2
                oy = (HEIGHT - nh) // 2
                resized.paste(scaled, (ox, oy))
            else:  # crop
                scale = max(WIDTH / w, HEIGHT / h)
                nw, nh = max(WIDTH, int(w * scale)), max(HEIGHT, int(h * scale))
                scaled = frame_img.resize((nw, nh), Image.Resampling.LANCZOS)
                left = (nw - WIDTH) // 2
                top = (nh - HEIGHT) // 2
                resized = scaled.crop((left, top, left + WIDTH, top + HEIGHT))

            if enhance:
                rgb = resized.convert("RGB")
                enh = ImageEnhance.Contrast(rgb).enhance(1.2)
                resized = ImageEnhance.Color(enh).enhance(1.25).convert("RGBA")

            resized.save(frame_path, format="PNG")
            frame_idx += 1

    return output_dir


# ============================================================================
# CLI and Interactive Interface
# ============================================================================

def generate_preset(
    preset_name: str,
    output_dir: Path,
    animated: bool = False,
    frames: int = 16,
) -> Path:
    """Generate a preset either as a static PNG or an animated folder of frames."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {', '.join(PRESETS.keys())}")

    gen_func = PRESETS[preset_name]
    output_dir.mkdir(parents=True, exist_ok=True)

    if not animated:
        out_file = output_dir / f"{preset_name}.png"
        img = gen_func(0, 1)
        img.save(out_file, format="PNG")
        return out_file
    else:
        scene_folder = output_dir / preset_name
        scene_folder.mkdir(parents=True, exist_ok=True)
        for i in range(frames):
            frame_img = gen_func(i, frames)
            frame_img.save(scene_folder / f"{i:03d}.png", format="PNG")
        return scene_folder


def interactive_menu(output_dir: Path) -> None:
    """Interactive wizard for generating scenes."""
    print("=" * 60)
    print("      BUSY Bar Screen Saver — Scene Generator")
    print("=" * 60)
    print(f"Target Output Folder: {output_dir.resolve()}\n")
    print("Select an option:")
    print("  1. Generate All Default Starter Scenes (Static)")
    print("  2. Generate All Animated Scenes (Multi-frame loops)")
    print("  3. Generate a Specific Preset")
    print("  4. Convert an Image or GIF File")
    print("  5. Convert All Images in a Folder")
    print("  6. List All Presets")
    print("  0. Exit")
    print("-" * 60)

    choice = input("Enter choice (0-6) [1]: ").strip() or "1"

    if choice == "0":
        print("Goodbye!")
        return

    if choice == "1":
        print(f"\nGenerating all {len(PRESETS)} static scenes...")
        for name in PRESETS:
            res = generate_preset(name, output_dir, animated=False)
            print(f"  [+] Created: {res.name}")
        print("\nAll default static scenes generated successfully!")

    elif choice == "2":
        print(f"\nGenerating all {len(PRESETS)} animated scene packs (16 frames each)...")
        for name in PRESETS:
            res = generate_preset(name, output_dir, animated=True, frames=16)
            print(f"  [+] Created animated pack: {res.name}/")
        print("\nAll animated scenes generated successfully!")

    elif choice == "3":
        print("\nAvailable Presets:")
        preset_keys = list(PRESETS.keys())
        for i, name in enumerate(preset_keys, 1):
            print(f"  {i}. {name}")
        p_choice = input(f"\nSelect preset (1-{len(preset_keys)}) or name: ").strip()
        selected_name = None
        if p_choice.isdigit() and 1 <= int(p_choice) <= len(preset_keys):
            selected_name = preset_keys[int(p_choice) - 1]
        elif p_choice in PRESETS:
            selected_name = p_choice
        else:
            print(f"Invalid preset choice: {p_choice}")
            return

        anim_choice = input("Generate as animated scene? (y/N): ").strip().lower()
        is_anim = anim_choice == "y"
        res = generate_preset(selected_name, output_dir, animated=is_anim, frames=16)
        print(f"\n[+] Generated {selected_name} at: {res}")

    elif choice == "4":
        file_path_str = input("\nEnter path to image or GIF file: ").strip().strip("'\"")
        file_path = Path(file_path_str)
        if not file_path.is_file():
            print(f"File not found: {file_path}")
            return

        if file_path.suffix.lower() == ".gif":
            out_name = file_path.stem
            out_folder = output_dir / out_name
            print(f"Converting animated GIF frames to {out_folder}...")
            convert_gif(file_path, out_folder)
            print(f"[+] Converted GIF scene into: {out_folder}")
        else:
            out_name = f"{file_path.stem}.png"
            out_file = output_dir / out_name
            print(f"Converting image to {out_file}...")
            convert_image(file_path, out_file)
            print(f"[+] Converted image saved to: {out_file}")

    elif choice == "5":
        dir_path_str = input("\nEnter path to folder containing images: ").strip().strip("'\"")
        dir_path = Path(dir_path_str)
        if not dir_path.is_dir():
            print(f"Directory not found: {dir_path}")
            return
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        count = 0
        for item in dir_path.iterdir():
            if item.suffix.lower() in exts:
                out_file = output_dir / f"{item.stem}.png"
                convert_image(item, out_file)
                print(f"  [+] Converted: {item.name} -> {out_file.name}")
                count += 1
        print(f"\nConverted {count} images to {output_dir}")

    elif choice == "6":
        print("\nAvailable Presets:")
        for name in PRESETS:
            print(f"  - {name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BUSY Bar Screen Saver Scene Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Generate all static preset scenes")
    parser.add_argument("--preset", action="append", help="Preset name to generate (can be repeated)")
    parser.add_argument("--animated", action="store_true", help="Generate preset as animated multi-frame scene")
    parser.add_argument("--frames", type=int, default=16, help="Number of frames for animated presets")
    parser.add_argument("--convert", type=Path, help="Convert an image or GIF file to 72x16 scene")
    parser.add_argument("--convert-folder", type=Path, help="Convert all images in a folder")
    parser.add_argument("--mode", choices=["crop", "fit", "stretch"], default="crop", help="Image conversion mode")
    parser.add_argument("--dither", action="store_true", help="Apply Floyd-Steinberg dithering during conversion")
    parser.add_argument("--output", type=Path, default=DEFAULT_SCENES_DIR, help="Output scenes directory")
    parser.add_argument("--list", action="store_true", help="List all available presets")
    parser.add_argument("--interactive", action="store_true", help="Run interactive wizard")

    args = parser.parse_args()

    out_dir = args.output.resolve()

    if args.list:
        print("Available presets:")
        for name in PRESETS:
            print(f"  - {name}")
        return

    # If no flags given, enter interactive mode
    if len(sys.argv) == 1 or args.interactive:
        interactive_menu(out_dir)
        return

    if args.all:
        print(f"Generating all presets into {out_dir} (animated={args.animated})...")
        for name in PRESETS:
            res = generate_preset(name, out_dir, animated=args.animated, frames=args.frames)
            print(f"  [+] Created: {res}")
        print("Done!")

    if args.preset:
        for name in args.preset:
            res = generate_preset(name, out_dir, animated=args.animated, frames=args.frames)
            print(f"[+] Created preset {name}: {res}")

    if args.convert:
        if args.convert.suffix.lower() == ".gif":
            res = convert_gif(args.convert, out_dir / args.convert.stem, mode=args.mode)
            print(f"[+] Converted GIF frames into: {res}")
        else:
            out_file = out_dir / f"{args.convert.stem}.png"
            res = convert_image(args.convert, out_file, mode=args.mode, dither=args.dither)
            print(f"[+] Converted image to: {res}")

    if args.convert_folder:
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        count = 0
        for item in args.convert_folder.iterdir():
            if item.suffix.lower() in exts:
                out_file = out_dir / f"{item.stem}.png"
                convert_image(item, out_file, mode=args.mode, dither=args.dither)
                print(f"  [+] Converted: {item.name} -> {out_file.name}")
                count += 1
        print(f"Converted {count} images from {args.convert_folder} into {out_dir}")


if __name__ == "__main__":
    main()
