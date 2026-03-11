#!/usr/bin/env python3
"""
Generate promotional concept images for the DJspectrum README.

Creates a stylized mockup of the spectrum analyzer display
and a DJ booth scene composition.

Usage:
    python scripts/generate_promo.py
"""

import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# === 1. Generate a realistic spectrum analyzer frame ===

WIDTH = 344
HEIGHT = 86
N_BARS = 172
BAR_W = 2
GAP = 1

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return int(a + (b - a) * t + 0.5)

# 6-stop gradient
R = [255, 255, 255,   0,   0,   0]
G = [  0, 128, 255, 255, 255,   0]
B = [  0,   0,   0,   0, 255, 255]

# Generate plausible bar heights (simulated music)
random.seed(42)
bars = []
for i in range(N_BARS):
    t = i / (N_BARS - 1)
    # Bass heavy with mid presence and treble rolloff
    base = 0.7 * math.exp(-((t - 0.08) ** 2) / 0.01)  # bass peak
    base += 0.5 * math.exp(-((t - 0.25) ** 2) / 0.03)  # low-mid
    base += 0.35 * math.exp(-((t - 0.45) ** 2) / 0.04)  # mid
    base += 0.2 * math.exp(-((t - 0.7) ** 2) / 0.05)   # presence
    base += random.gauss(0, 0.12)
    base = max(0.05, min(1.0, base))
    bars.append(int(base * HEIGHT))

# Peaks slightly above bars
peaks = [min(HEIGHT, b + random.randint(2, 6)) for b in bars]

# Render
img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
pixels = img.load()

for i in range(N_BARS):
    bh = bars[i]
    pk = peaks[i]
    x = i * BAR_W

    # Bar color from gradient
    t = i / (N_BARS - 1)
    p = t * 5.0
    seg = int(p)
    u = p - seg
    if seg > 4: seg, u = 4, 1.0
    br = lerp(R[seg], R[seg+1], u)
    bg = lerp(G[seg], G[seg+1], u)
    bb = lerp(B[seg], B[seg+1], u)

    strength = bh / HEIGHT

    for yy in range(bh):
        y = HEIGHT - 1 - yy
        # Bottom fade
        fade_len = min(bh, 6 + int(bh * 64.0 / HEIGHT))
        s = 1.0
        if yy < fade_len:
            uf = yy / max(1, fade_len - 1)
            min_s = max(0.015, (0.20 - 0.12 * strength) / 8.0)
            s = min_s + (1.0 - min_s) * uf
        if s < 0.09:
            continue

        # Purple shift near top
        ubar = yy / max(1, bh - 1)
        pmix = max(0.0, min(1.0, (ubar - 0.70) / 0.30))
        pmix = pmix * pmix * strength

        r0 = int(br * s)
        g0 = int(bg * s)
        b0 = int(bb * s)
        pr = int(255 * s)
        pb = int(255 * s)

        fr = lerp(r0, pr, pmix)
        fg = lerp(g0, 0, pmix)
        fb = lerp(b0, pb, pmix)

        for dx in range(min(BAR_W - GAP, WIDTH - x)):
            if 0 <= x + dx < WIDTH and 0 <= y < HEIGHT:
                pixels[x + dx, y] = (fr, fg, fb)

    # Peak dot
    if pk > 0:
        py = HEIGHT - pk - 1
        if 0 <= py < HEIGHT:
            for dx in range(min(BAR_W - GAP, WIDTH - x)):
                if 0 <= x + dx < WIDTH:
                    pixels[x + dx, py] = (255, 255, 255)

# Save raw spectrum frame
img.save("images/spectrum_demo_frame.png")
print("Saved images/spectrum_demo_frame.png")

# === 2. Create upscaled hero image with glow effect ===

SCALE = 6
hero_w = WIDTH * SCALE
hero_h = HEIGHT * SCALE

# Upscale with nearest neighbor (pixel art look)
hero = img.resize((hero_w, hero_h), Image.NEAREST)

# Add subtle glow
glow = hero.filter(ImageFilter.GaussianBlur(radius=8))
hero_pixels = hero.load()
glow_pixels = glow.load()
for y in range(hero_h):
    for x in range(hero_w):
        r1, g1, b1 = hero_pixels[x, y]
        r2, g2, b2 = glow_pixels[x, y]
        # Screen blend
        fr = min(255, r1 + r2 // 3)
        fg = min(255, g1 + g2 // 3)
        fb = min(255, b1 + b2 // 3)
        hero_pixels[x, y] = (fr, fg, fb)

# Add dark background frame
padded_w = hero_w + 80
padded_h = hero_h + 120
canvas = Image.new("RGB", (padded_w, padded_h), (8, 8, 16))
draw = ImageDraw.Draw(canvas)

# Panel bezel (dark gray border)
bx = 36
by = 30
draw.rectangle([bx-4, by-4, bx + hero_w + 3, by + hero_h + 3], fill=(30, 30, 35))
draw.rectangle([bx-2, by-2, bx + hero_w + 1, by + hero_h + 1], fill=(15, 15, 20))
canvas.paste(hero, (bx, by))

# Title text below
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except:
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 28)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

title = "DJspectrum"
subtitle = "344x86 Real-Time Audio Spectrum Analyzer  |  172 Bars  |  Per-Bar AGC  |  Home Assistant"
tbbox = draw.textbbox((0, 0), title, font=title_font)
tw = tbbox[2] - tbbox[0]
draw.text(((padded_w - tw) // 2, by + hero_h + 16), title, fill=(255, 255, 255), font=title_font)

sbbox = draw.textbbox((0, 0), subtitle, font=sub_font)
sw = sbbox[2] - sbbox[0]
draw.text(((padded_w - sw) // 2, by + hero_h + 52), subtitle, fill=(140, 140, 160), font=sub_font)

canvas.save("images/hero_spectrum.png", quality=95)
print(f"Saved images/hero_spectrum.png ({padded_w}x{padded_h})")

# === 3. Create a DJ booth concept scene ===

SCENE_W = 1200
SCENE_H = 800

scene = Image.new("RGB", (SCENE_W, SCENE_H), (5, 2, 15))
sd = ImageDraw.Draw(scene)

# Dark club background gradient
for y in range(SCENE_H):
    t = y / SCENE_H
    r = int(5 + 15 * (1 - t))
    g = int(2 + 5 * (1 - t))
    b = int(15 + 25 * (1 - t))
    sd.line([(0, y), (SCENE_W, y)], fill=(r, g, b))

# DJ booth (dark rectangle)
booth_y = 450
sd.rectangle([100, booth_y, 1100, 750], fill=(20, 18, 25))
sd.rectangle([100, booth_y, 1100, booth_y + 8], fill=(35, 30, 45))

# LED panels in front of booth (the spectrum display)
panel_x = 200
panel_y = booth_y + 40
panel_display_w = 700
panel_display_h = int(700 * 86 / 344)

# Glow behind panels
for g_size in range(40, 0, -2):
    alpha = int(15 * (40 - g_size) / 40)
    sd.rectangle(
        [panel_x - g_size, panel_y - g_size,
         panel_x + panel_display_w + g_size, panel_y + panel_display_h + g_size],
        fill=(alpha, alpha // 3, alpha)
    )

# Paste scaled spectrum into scene
spectrum_scene = img.resize((panel_display_w, panel_display_h), Image.NEAREST)
scene.paste(spectrum_scene, (panel_x, panel_y))

# Panel bezel
sd.rectangle(
    [panel_x - 3, panel_y - 3, panel_x + panel_display_w + 2, panel_y + panel_display_h + 2],
    outline=(50, 45, 60), width=2
)

# DJ figure silhouette (simplified)
# Head
sd.ellipse([540, 280, 620, 360], fill=(15, 12, 22))
# Body
sd.polygon([(530, 360), (630, 360), (660, booth_y + 5), (500, booth_y + 5)], fill=(15, 12, 22))
# Arms reaching to decks
sd.polygon([(500, 380), (350, booth_y - 10), (360, booth_y + 10), (510, 400)], fill=(15, 12, 22))
sd.polygon([(630, 380), (780, booth_y - 10), (770, booth_y + 10), (620, 400)], fill=(15, 12, 22))

# CDJ/mixer shapes on booth
sd.rectangle([250, booth_y + 10, 450, booth_y + 35], fill=(12, 10, 18), outline=(40, 35, 50))
sd.rectangle([480, booth_y + 10, 720, booth_y + 35], fill=(12, 10, 18), outline=(40, 35, 50))
sd.rectangle([750, booth_y + 10, 950, booth_y + 35], fill=(12, 10, 18), outline=(40, 35, 50))

# Small indicator lights on equipment
for lx in range(280, 440, 30):
    color = random.choice([(0, 255, 0), (255, 100, 0), (0, 180, 255)])
    sd.ellipse([lx, booth_y + 15, lx + 4, booth_y + 19], fill=color)
for lx in range(510, 710, 25):
    color = random.choice([(255, 0, 0), (0, 255, 0), (255, 180, 0)])
    sd.ellipse([lx, booth_y + 18, lx + 3, booth_y + 21], fill=color)

# Atmospheric light beams from above
for beam_x in [300, 580, 860]:
    for yy in range(0, 350):
        spread = yy * 0.3
        alpha = max(0, int(25 * (1 - yy / 350)))
        beam_color = random.choice([(alpha, 0, alpha), (0, 0, alpha), (alpha, 0, alpha // 2)])
        sd.line([(beam_x - spread, yy), (beam_x + spread, yy)], fill=beam_color)

# Crowd silhouettes at bottom
for cx in range(50, 1150, 35):
    ch = random.randint(30, 60)
    cy = SCENE_H - ch
    head_r = random.randint(8, 12)
    sd.ellipse([cx - head_r, cy - head_r * 2, cx + head_r, cy], fill=(8, 5, 12))
    sd.rectangle([cx - head_r + 2, cy, cx + head_r - 2, SCENE_H], fill=(8, 5, 12))

# "DJspectrum" label
try:
    scene_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 36)
    scene_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
except:
    try:
        scene_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        scene_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        scene_font = ImageFont.load_default()
        scene_sub = ImageFont.load_default()

# Corner watermark
sd.text((30, 20), "DJspectrum", fill=(180, 140, 255), font=scene_font)
sd.text((30, 62), "Real-time spectrum analyzer for the DJ booth", fill=(100, 90, 130), font=scene_sub)

scene.save("images/dj_booth_concept.png", quality=95)
print(f"Saved images/dj_booth_concept.png ({SCENE_W}x{SCENE_H})")

print("\nAll promo images generated!")
print("\nFor a photorealistic version, use this AI image prompt:")
print("=" * 70)
print("""
PROMPT FOR AI IMAGE GENERATORS (DALL-E / Midjourney / Stable Diffusion):

"Professional photograph of a female DJ performing at a nightclub,
standing behind CDJ decks and a mixer. Mounted on the front of the
DJ booth facing the crowd is a wide, thin LED panel display showing
a colorful real-time audio spectrum analyzer with vertical bars in
a rainbow gradient from red (left/bass) through orange, yellow,
green, cyan to blue (right/treble). The bars pulse with the music.
White peak dots float above each bar. The panel is approximately
60cm wide and 16cm tall, with a subtle purple glow. Dark nightclub
atmosphere with dramatic overhead lighting, crowd silhouettes in
foreground. Photorealistic, high quality, editorial photography."
""")
print("=" * 70)
