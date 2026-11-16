"""
generate_short_video.py — Production rendering pipeline for Notch YouTube Short (9:16 vertical).
Engineered specifically for YouTube Shorts (1080x1920 @ 30fps, 59.5s).
Rebuilt from ground up for high UI scale, cinematic mobile framing, beat-synced pacing,
and zero PowerPoint/slideshow cards.
"""
from __future__ import annotations

import os
import sys
import math
import time
import wave
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

os.environ["PYTHONIOENCODING"] = "utf-8"

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = BASE_DIR / "website" / "public" / "images" / "app"
LOGO_PATH = BASE_DIR / "website" / "public" / "notch-logo.png"
_scratch_audio = BASE_DIR / "scratch" / "media" / "reference_music.wav"
REF_AUDIO_PATH = _scratch_audio if _scratch_audio.exists() else BASE_DIR / "reference_music.wav"
OUTPUT_VIDEO = BASE_DIR / "scratch" / "media" / "Notch_YouTube_Short.mp4"

# ── Specifications ─────────────────────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920
FPS = 30
TOTAL_SECONDS = 59.5
TOTAL_FRAMES = int(FPS * TOTAL_SECONDS)  # 1785 frames
AUDIO_SAMPLE_RATE = 48000

# Fonts (Native Windows Segoe UI Family)
FONT_REGULAR_PATH = "C:/Windows/Fonts/segoeui.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"
FONT_SEMILIGHT_PATH = "C:/Windows/Fonts/segoeuisl.ttf"

def get_font(size: int, bold: bool = False, light: bool = False):
    try:
        if bold:
            return ImageFont.truetype(FONT_BOLD_PATH, size)
        elif light:
            return ImageFont.truetype(FONT_SEMILIGHT_PATH, size)
        return ImageFont.truetype(FONT_REGULAR_PATH, size)
    except Exception:
        return ImageFont.load_default()

def clamp(v, min_v=0.0, max_v=1.0):
    return max(min_v, min(max_v, float(v)))

def ease_out_cubic(t):
    t = clamp(t)
    return 1.0 - math.pow(1.0 - t, 3)

def ease_in_out_cubic(t):
    t = clamp(t)
    return 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

def smoothstep(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)

# ── Load Raw High-Resolution Assets ────────────────────────────────────────────
print("[1/5] Loading authentic Notch UI assets and states...", flush=True)

def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing asset: {path}")
    return Image.open(path).convert("RGBA")

RAW_HOME = load_rgba(ASSETS_DIR / "home-dark.png")
RAW_USAGE = load_rgba(ASSETS_DIR / "usage-dark.png")
RAW_INSIGHTS = load_rgba(ASSETS_DIR / "insights-dark.png")
RAW_FOCUS_ACTIVE = load_rgba(ASSETS_DIR / "focus-active-dark.png")
RAW_FOCUS_PREFLIGHT = load_rgba(ASSETS_DIR / "focus-preflight-dark.png")
RAW_BLOCKED = load_rgba(ASSETS_DIR / "blocked-app-dark.png")
RAW_TIMER = load_rgba(ASSETS_DIR / "app-timer-dark.png")
RAW_TIMER_CONFIG = load_rgba(ASSETS_DIR / "app-timer-config-dark.png")
RAW_LOCKER = load_rgba(ASSETS_DIR / "app-locker-dark.png")
RAW_AUTH = load_rgba(ASSETS_DIR / "authentication-dark.png")
RAW_SLEEPGUARD = load_rgba(ASSETS_DIR / "sleepguard-dark.png")
RAW_LOGO = load_rgba(LOGO_PATH)

# Authentic Discord Blocked Modal
DISCORD_MODAL = RAW_BLOCKED.crop((523, 232, 917, 592))

# ── Pre-composite Dynamic States ───────────────────────────────────────────────
def create_active_timer_asset() -> Image.Image:
    base = load_rgba(ASSETS_DIR / "app-timer-dark.png")
    font_name = get_font(16, bold=True)
    font_pill = get_font(12, bold=True)
    font_sub = get_font(13)
    font_kpi = get_font(24, bold=True)
    font_btn = get_font(12)

    img = base.copy()
    draw = ImageDraw.Draw(img)

    # Update KPI: '1 app'
    draw.rectangle([295, 142, 420, 180], fill=(15, 18, 24, 255))
    draw.text((297, 145), '1 app', font=font_kpi, fill=(16, 185, 129, 255))

    # Cover empty placeholder area completely across 710 width down to 480
    draw.rectangle([255, 242, 965, 480], fill=(13, 17, 23, 255))

    card_x1, card_y1, card_x2, card_y2 = 260, 260, 960, 395
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=12, fill=(18, 24, 34, 255), outline=(255, 255, 255, 25), width=1)

    # Brave Browser Lion icon from home screenshot
    brave_ico = RAW_HOME.crop((312, 414, 346, 452)).resize((42, 46), Image.Resampling.LANCZOS)
    img.paste(brave_ico, (card_x1 + 22, card_y1 + 22), brave_ico)

    font_name = get_font(22, bold=True)
    font_pill = get_font(16, bold=True)
    font_sub = get_font(15)
    font_btn = get_font(14)

    draw.text((card_x1 + 80, card_y1 + 18), 'Brave Browser', font=font_name, fill=(255, 255, 255, 255))

    # Prominent pill: '24m LEFT'
    pill_x1, pill_y1, pill_x2, pill_y2 = card_x1 + 245, card_y1 + 16, card_x1 + 360, card_y1 + 46
    draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=6, fill=(13, 52, 38, 255), outline=(16, 185, 129, 255), width=1)
    draw.text((pill_x1 + 14, pill_y1 + 5), '24m LEFT', font=font_pill, fill=(52, 211, 153, 255))

    # Subtext: '21m used / 45m daily limit'
    draw.text((card_x1 + 80, card_y1 + 52), '21m used / 45m daily limit', font=font_sub, fill=(156, 163, 175, 255))

    # Progress bar: 21/45 = 46.7%
    bar_x1, bar_y, bar_x2 = card_x1 + 80, card_y1 + 86, card_x2 - 115
    bar_w = bar_x2 - bar_x1
    draw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y + 8], radius=4, fill=(30, 41, 59, 255))
    fill_w = int(bar_w * (21.0 / 45.0))
    draw.rounded_rectangle([bar_x1, bar_y, bar_x1 + fill_w, bar_y + 8], radius=4, fill=(16, 185, 129, 255))

    # Edit button
    btn_x1, btn_y1, btn_x2, btn_y2 = card_x2 - 100, card_y1 + 32, card_x2 - 24, card_y1 + 72
    draw.rounded_rectangle([btn_x1, btn_y1, btn_x2, btn_y2], radius=6, fill=(25, 33, 44, 255), outline=(255, 255, 255, 20), width=1)
    draw.text((btn_x1 + 22, btn_y1 + 10), 'Edit', font=font_btn, fill=(203, 213, 225, 255))

    return img

RAW_TIMER_ACTIVE = create_active_timer_asset()

# Build SleepGuard variants from countdown asset
def create_sleepguard_variants():
    base_countdown = load_rgba(ASSETS_DIR / "sleepguard-countdown-dark.png")
    bg_color = (17, 21, 28, 255)
    orange_color = (245, 158, 11, 255)
    emerald_color = (16, 185, 129, 255)
    font_time = get_font(54, bold=True)
    font_bold = get_font(26, bold=True)
    font_sub = get_font(16)

    # 1. 01:00
    img_60 = base_countdown.copy()

    # 2. 00:59
    img_59 = base_countdown.copy()
    d59 = ImageDraw.Draw(img_59)
    d59.rectangle([600, 360, 840, 460], fill=bg_color)
    tw = d59.textlength("00:59", font=font_time)
    d59.text(((1440 - tw) // 2, 375), "00:59", font=font_time, fill=orange_color)

    # 3. 00:58
    img_58 = base_countdown.copy()
    d58 = ImageDraw.Draw(img_58)
    d58.rectangle([600, 360, 840, 460], fill=bg_color)
    tw = d58.textlength("00:58", font=font_time)
    d58.text(((1440 - tw) // 2, 375), "00:58", font=font_time, fill=orange_color)

    # 4. Cancelled / User activity detected state
    img_cancelled = base_countdown.copy()
    dc = ImageDraw.Draw(img_cancelled)
    dc.rectangle([450, 310, 990, 560], fill=bg_color)
    cx = 720
    dc.ellipse([cx - 26, 340, cx + 26, 392], fill=(16, 185, 129, 36), outline=emerald_color, width=2)
    dc.line([(cx - 11, 366), (cx - 3, 374), (cx + 11, 358)], fill=(255, 255, 255), width=3)
    
    txt1 = "Power Action Aborted"
    t1_w = dc.textlength(txt1, font=font_bold)
    dc.text(((1440 - t1_w) // 2, 412), txt1, font=font_bold, fill=(255, 255, 255))

    txt2 = "User activity detected. System resumed normal operation."
    t2_w = dc.textlength(txt2, font=font_sub)
    dc.text(((1440 - t2_w) // 2, 452), txt2, font=font_sub, fill=(156, 163, 175))

    return img_60, img_59, img_58, img_cancelled

RAW_SG_60, RAW_SG_59, RAW_SG_58, RAW_SG_ABORTED = create_sleepguard_variants()

# Build Access Granted variant for App Locker
def create_auth_granted_asset() -> Image.Image:
    auth_v = RAW_AUTH.crop((538, 290, 902, 549)).copy()
    avd = ImageDraw.Draw(auth_v)
    cx = auth_v.width // 2
    cy = 44
    # Replace key with green verified circle checkmark
    avd.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=(16, 185, 129, 255))
    avd.line([(cx - 9, cy), (cx - 2, cy + 7), (cx + 9, cy - 7)], fill=(255, 255, 255, 255), width=3)
    return auth_v

AUTH_GRANTED = create_auth_granted_asset()

# ── Ambient Background Pre-rendering ───────────────────────────────────────────
print("[2/5] Pre-rendering ambient full-bleed backdrops for zero-empty-space staging...", flush=True)

def make_ambient_backdrop(src: Image.Image, dim_alpha: int = 95, blur_radius: int = 20) -> Image.Image:
    bw, bh = src.size
    scale = max(WIDTH / float(bw), HEIGHT / float(bh))
    sw, sh = int(bw * scale), int(bh * scale)
    bg_scaled = src.resize((sw, sh), Image.Resampling.LANCZOS)
    cx, cy = (sw - WIDTH) // 2, (sh - HEIGHT) // 2
    cropped = bg_scaled.crop((cx, cy, cx + WIDTH, cy + HEIGHT)).convert("RGBA")
    
    # Soft lens blur + subtle dark tint
    blurred = cropped.filter(ImageFilter.GaussianBlur(blur_radius))
    dim = Image.new("RGBA", (WIDTH, HEIGHT), (6, 9, 14, dim_alpha))
    return Image.alpha_composite(blurred, dim)

BG_HOME = make_ambient_backdrop(RAW_HOME, dim_alpha=90, blur_radius=18)
BG_USAGE = make_ambient_backdrop(RAW_USAGE, dim_alpha=95, blur_radius=20)
BG_INSIGHTS = make_ambient_backdrop(RAW_INSIGHTS, dim_alpha=95, blur_radius=20)
BG_FOCUS_SETUP = make_ambient_backdrop(RAW_FOCUS_PREFLIGHT, dim_alpha=100, blur_radius=22)
BG_FOCUS_ACTIVE = make_ambient_backdrop(RAW_FOCUS_ACTIVE, dim_alpha=95, blur_radius=20)
BG_BLOCKED = make_ambient_backdrop(RAW_BLOCKED, dim_alpha=105, blur_radius=22)
BG_TIMER_CONFIG = make_ambient_backdrop(RAW_TIMER_CONFIG, dim_alpha=95, blur_radius=20)
BG_TIMER_ACTIVE = make_ambient_backdrop(RAW_TIMER_ACTIVE, dim_alpha=95, blur_radius=20)
BG_LOCKER = make_ambient_backdrop(RAW_LOCKER, dim_alpha=95, blur_radius=20)
BG_AUTH = make_ambient_backdrop(RAW_AUTH, dim_alpha=100, blur_radius=20)
BG_SLEEPGUARD = make_ambient_backdrop(RAW_SLEEPGUARD, dim_alpha=95, blur_radius=20)
BG_SG_COUNTDOWN = make_ambient_backdrop(RAW_SG_60, dim_alpha=105, blur_radius=22)

# ── Dynamic Scene Compositor ───────────────────────────────────────────────────
def draw_cinematic_text(canvas: Image.Image, text: str, y: int = 220, color=(255, 255, 255), alpha: float = 1.0):
    if alpha <= 0.01:
        return
    d = ImageDraw.Draw(canvas)
    font = get_font(38, bold=True)
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (WIDTH - tw) // 2

    # Drop shadow
    d.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, int(220 * alpha)))
    fill_col = (*color, int(255 * alpha)) if len(color) == 3 else color
    d.text((x, y), text, font=font, fill=fill_col)

def stage_hero_ui(
    canvas: Image.Image,
    src_img: Image.Image,
    crop_box: tuple[int, int, int, int],
    target_w: int = 1030,
    pos_y: int = 320,
    corner_r: int = 16,
    border_color=(255, 255, 255, 36),
    alpha: float = 1.0,
    zoom_factor: float = 1.0
):
    if alpha <= 0.01 or zoom_factor <= 0.01:
        return
    
    cropped = src_img.crop(crop_box)
    cw, ch = cropped.size
    
    final_w = int(target_w * zoom_factor)
    final_h = int(ch * (final_w / float(cw)))
    if final_w <= 0 or final_h <= 0:
        return
    
    scaled = cropped.resize((final_w, final_h), Image.Resampling.LANCZOS).convert("RGBA")

    # Clean 1px border
    if border_color:
        b_alpha = int(border_color[3] * alpha) if len(border_color) == 4 else int(40 * alpha)
        b_col = (*border_color[:3], b_alpha)
        ImageDraw.Draw(scaled).rounded_rectangle([0, 0, final_w - 1, final_h - 1], radius=corner_r, outline=b_col, width=1)

    # Position
    px = (WIDTH - final_w) // 2
    py = int(pos_y - (final_h - int(ch * (target_w / float(cw)))) / 2)

    # Soft ambient drop shadow
    pad = 28
    shadow = Image.new("RGBA", (final_w + pad*2, final_h + pad*2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([pad, pad + 8, pad + final_w, pad + final_h + 8], radius=corner_r + 4, fill=(0, 0, 0, int(200 * alpha)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    canvas.paste(shadow, (px - pad, py - pad), shadow)

    # Mask
    mask = Image.new("L", (final_w, final_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, final_w, final_h], radius=corner_r, fill=int(255 * alpha))

    canvas.paste(scaled, (px, py), mask)

# ── Scene 1: Fast Hook (0.0s – 2.5s) ───────────────────────────────────────────
# Very quick authentic cuts: Home -> Focus Active -> Discord Blocked -> SleepGuard Warning
def render_scene_hook(t: float) -> Image.Image:
    if t < 0.625:
        # Cut 1: Home dashboard 3h 3m
        canvas = BG_HOME.copy()
        p = clamp(t / 0.625)
        stage_hero_ui(canvas, RAW_HOME, (255, 20, 965, 835), target_w=1030, pos_y=320, zoom_factor=1.0 + 0.03 * p)
    elif t < 1.25:
        # Cut 2: Focus Active 25:00
        canvas = BG_FOCUS_ACTIVE.copy()
        p = clamp((t - 0.625) / 0.625)
        stage_hero_ui(canvas, RAW_FOCUS_ACTIVE, (455, 95, 1155, 720), target_w=1030, pos_y=360, zoom_factor=1.0 + 0.03 * p)
    elif t < 1.875:
        # Cut 3: Discord Blocked
        canvas = BG_BLOCKED.copy()
        p = clamp((t - 1.25) / 0.625)
        stage_hero_ui(canvas, DISCORD_MODAL, (0, 0, DISCORD_MODAL.width, DISCORD_MODAL.height), target_w=980, pos_y=440, border_color=(239, 68, 68, 120), zoom_factor=1.0 + 0.03 * p)
    else:
        # Cut 4: SleepGuard Warning 01:00
        canvas = BG_SG_COUNTDOWN.copy()
        p = clamp((t - 1.875) / 0.625)
        stage_hero_ui(canvas, RAW_SG_60, (498, 290, 942, 553), target_w=1000, pos_y=500, border_color=(245, 158, 11, 140), zoom_factor=1.0 + 0.03 * p)

    # Clean hook overlay across the scene
    draw_cinematic_text(canvas, "I BUILT A TOOL TO CONTROL MY SCREEN TIME", y=200)
    return canvas

# ── Scene 2: Home Dashboard (2.5s – 7.0s) ─────────────────────────────────────
# Show actual Notch Home dashboard at a large readable scale.
# Zoom/pan toward important screen-time metric and activity information.
def render_scene_home(t: float) -> Image.Image:
    canvas = BG_HOME.copy()
    p = clamp((t - 2.5) / 4.5)
    zoom = 1.0 + 0.05 * smoothstep(p)
    draw_cinematic_text(canvas, "KNOW WHERE YOUR TIME GOES.", y=210)
    # Crop: Greeting + Screen Time + Top Apps + Categories (710 x 815 -> height 1180px)
    stage_hero_ui(canvas, RAW_HOME, (255, 20, 965, 835), target_w=1030, pos_y=305, zoom_factor=zoom)
    return canvas

# ── Scene 3: Usage + Insights (7.0s – 11.0s) ──────────────────────────────────
# Graphs and data large enough to understand on a phone.
def render_scene_usage_insights(t: float) -> Image.Image:
    if t < 9.2:
        # 7.0 - 9.2s: Usage screen with 24-hour bar chart & metric tiles
        canvas = BG_USAGE.copy()
        p = clamp((t - 7.0) / 2.2)
        draw_cinematic_text(canvas, "SEE THE PATTERNS.", y=210)
        stage_hero_ui(canvas, RAW_USAGE, (250, 115, 1395, 835), target_w=1030, pos_y=330, zoom_factor=1.0 + 0.03 * smoothstep(p))
    else:
        # 9.2 - 11.0s: Insights screen with productivity & category allocations
        canvas = BG_INSIGHTS.copy()
        p = clamp((t - 9.2) / 1.8)
        draw_cinematic_text(canvas, "SEE THE PATTERNS.", y=210)
        stage_hero_ui(canvas, RAW_INSIGHTS, (250, 115, 1395, 835), target_w=1030, pos_y=330, zoom_factor=1.0 + 0.03 * smoothstep(p))
    return canvas

# ── Scene 4: Focus Mode (Hero Feature · 11.0s – 25.0s) ────────────────────────
# Focus setup -> Focus Active with 25:00 -> Discord attempt -> Discord BLOCKED
def render_scene_focus(t: float) -> Image.Image:
    # Phase A: 11.0 - 14.5s: Focus setup / preflight
    if t < 14.5:
        canvas = BG_FOCUS_SETUP.copy()
        p = clamp((t - 11.0) / 3.5)
        draw_cinematic_text(canvas, "FOCUS MODE", y=240)
        stage_hero_ui(canvas, RAW_FOCUS_PREFLIGHT, (450, 110, 1150, 720), target_w=1030, pos_y=340, zoom_factor=1.0 + 0.03 * smoothstep(p))
        # Button click indicator at 14.0s
        if t >= 13.8:
            d = ImageDraw.Draw(canvas)
            # Subtle pulse around Start Focus Session
            d.rectangle([640, 1110, 930, 1160], outline=(16, 185, 129, 180), width=2)
    # Phase B: 14.5 - 18.0s: Active 25:00 countdown timer prominent
    elif t < 18.0:
        canvas = BG_FOCUS_ACTIVE.copy()
        p = clamp((t - 14.5) / 3.5)
        draw_cinematic_text(canvas, "BLOCK DISTRACTIONS", y=230)
        stage_hero_ui(canvas, RAW_FOCUS_ACTIVE, (455, 95, 1155, 720), target_w=1030, pos_y=330, zoom_factor=1.0 + 0.04 * smoothstep(p))
    # Phase C: 18.0 - 25.0s: CLIMAX DROP — Discord BLOCKED!
    else:
        canvas = BG_BLOCKED.copy()
        p = clamp((t - 18.0) / 7.0)
        draw_cinematic_text(canvas, "DISCORD BLOCKED", y=300)
        # Scale punch on beat drop at 18.0s
        drop_p = clamp((t - 18.0) / 0.35)
        pop_zoom = 1.0 + 0.08 * (1.0 - ease_out_cubic(drop_p))
        stage_hero_ui(
            canvas,
            DISCORD_MODAL,
            (0, 0, DISCORD_MODAL.width, DISCORD_MODAL.height),
            target_w=980,
            pos_y=420,
            corner_r=16,
            border_color=(239, 68, 68, 140),
            zoom_factor=pop_zoom,
            alpha=ease_out_cubic(drop_p)
        )
    return canvas

# ── Scene 5: App Timer (25.0s – 34.0s) ────────────────────────────────────────
# Configure app -> daily limit -> active timer -> remaining time (24m left readable)
def render_scene_timer(t: float) -> Image.Image:
    if t < 29.5:
        # Phase A: 25.0 - 29.5s: Configure daily limit dialog
        canvas = BG_TIMER_CONFIG.copy()
        p = clamp((t - 25.0) / 4.5)
        draw_cinematic_text(canvas, "SET LIMITS BEFORE YOU LOSE CONTROL.", y=170)
        stage_hero_ui(canvas, RAW_TIMER_CONFIG, (450, 72, 989, 719), target_w=1010, pos_y=270, zoom_factor=1.0 + 0.02 * smoothstep(p))
    else:
        # Phase B: 29.5 - 34.0s: Active budget with Brave 24m left prominent
        canvas = BG_TIMER_ACTIVE.copy()
        p = clamp((t - 29.5) / 4.5)
        draw_cinematic_text(canvas, "SET LIMITS BEFORE YOU LOSE CONTROL.", y=280)
        stage_hero_ui(canvas, RAW_TIMER_ACTIVE, (255, 115, 965, 415), target_w=1000, pos_y=460, zoom_factor=1.0 + 0.03 * smoothstep(p))
    return canvas

# ── Scene 6: App Locker (34.0s – 42.0s) ───────────────────────────────────────
# Locked application -> authentication -> access granted
def render_scene_app_locker(t: float) -> Image.Image:
    if t < 37.0:
        # Phase A: 34.0 - 37.0s: Locked applications screen
        canvas = BG_LOCKER.copy()
        p = clamp((t - 34.0) / 3.0)
        draw_cinematic_text(canvas, "PROTECT THE APPS THAT MATTER.", y=220)
        stage_hero_ui(canvas, RAW_LOCKER, (250, 95, 1395, 750), target_w=1030, pos_y=330, zoom_factor=1.0 + 0.02 * smoothstep(p))
    elif t < 39.5:
        # Phase B: 37.0 - 39.5s: Authentication dialog (Strict mode PIN)
        canvas = BG_AUTH.copy()
        p = clamp((t - 37.0) / 2.5)
        draw_cinematic_text(canvas, "PROTECT THE APPS THAT MATTER.", y=330)
        stage_hero_ui(canvas, RAW_AUTH, (538, 290, 902, 549), target_w=960, pos_y=430, zoom_factor=1.0 + 0.02 * smoothstep(p))
    else:
        # Phase C: 39.5 - 42.0s: Access granted! Verified emerald checkmark lands on beat
        canvas = BG_AUTH.copy()
        draw_cinematic_text(canvas, "PROTECT THE APPS THAT MATTER.", y=330)
        stage_hero_ui(canvas, AUTH_GRANTED, (0, 0, AUTH_GRANTED.width, AUTH_GRANTED.height), target_w=960, pos_y=430, border_color=(16, 185, 129, 160))
    return canvas

# ── Scene 7: SleepGuard (42.0s – 53.0s) ───────────────────────────────────────
# Armed -> 01:00 warning -> 00:59 / 00:58 countdown -> Power Action Aborted
def render_scene_sleepguard(t: float) -> Image.Image:
    if t < 44.5:
        # Phase A: 42.0 - 44.5s: SleepGuard armed & monitoring
        canvas = BG_SLEEPGUARD.copy()
        p = clamp((t - 42.0) / 2.5)
        draw_cinematic_text(canvas, "EVEN YOUR SLEEP GETS A GUARDRAIL.", y=220)
        stage_hero_ui(canvas, RAW_SLEEPGUARD, (250, 95, 1395, 620), target_w=1030, pos_y=330, zoom_factor=1.0 + 0.02 * smoothstep(p))
    elif t < 48.5:
        # Phase B: 44.5 - 48.5s: 60-Second Warning popup countdown
        canvas = BG_SG_COUNTDOWN.copy()
        draw_cinematic_text(canvas, "EVEN YOUR SLEEP GETS A GUARDRAIL.", y=360)
        if t < 46.0:
            sg_src = RAW_SG_60
        elif t < 47.2:
            sg_src = RAW_SG_59
        else:
            sg_src = RAW_SG_58
        stage_hero_ui(canvas, sg_src, (498, 290, 942, 553), target_w=1000, pos_y=480, border_color=(245, 158, 11, 150))
    else:
        # Phase C: 48.5 - 53.0s: Payoff — Power Action Aborted!
        canvas = BG_SG_COUNTDOWN.copy()
        draw_cinematic_text(canvas, "POWER ACTION ABORTED", y=360, color=(16, 185, 129))
        stage_hero_ui(canvas, RAW_SG_ABORTED, (498, 290, 942, 553), target_w=1000, pos_y=480, border_color=(16, 185, 129, 160))
    return canvas

# ── Scene 8: Strong Brand Ending (53.0s – 59.5s) ──────────────────────────────
# Actual Notch application as the main visual. No tiny cards.
def render_scene_final(t: float) -> Image.Image:
    canvas = BG_HOME.copy()
    p = clamp((t - 53.0) / 6.5)
    zoom = 1.0 + 0.04 * smoothstep(p)
    
    # Authentic Notch Home dashboard in upper 65% of screen
    stage_hero_ui(canvas, RAW_HOME, (255, 20, 965, 835), target_w=1030, pos_y=160, zoom_factor=zoom, border_color=(255, 255, 255, 25))

    # Dark gradient veil over lower branding area
    veil = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for vy in range(1160, HEIGHT):
        vf = (vy - 1160) / float(HEIGHT - 1160)
        alpha_v = int(255 * min(1.0, vf * 1.5))
        vd.line([(0, vy), (WIDTH, vy)], fill=(8, 11, 16, alpha_v))
    canvas.paste(veil, (0, 0), veil)

    # Clean official branding centered in lower third
    d = ImageDraw.Draw(canvas)
    logo_size = 72
    logo_lg = RAW_LOGO.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    canvas.paste(logo_lg, ((WIDTH - logo_size) // 2, 1370), logo_lg)

    font_notch = get_font(48, bold=True)
    bw = d.textbbox((0, 0), "NOTCH", font=font_notch)[2] - d.textbbox((0, 0), "NOTCH", font=font_notch)[0]
    d.text(((WIDTH - bw) // 2, 1460), "NOTCH", font=font_notch, fill=(255, 255, 255))

    font_t1 = get_font(32, bold=True)
    bw1 = d.textbbox((0, 0), "Control your machine.", font=font_t1)[2] - d.textbbox((0, 0), "Control your machine.", font=font_t1)[0]
    d.text(((WIDTH - bw1) // 2, 1530), "Control your machine.", font=font_t1, fill=(255, 255, 255))

    font_t2 = get_font(32, bold=True)
    bw2 = d.textbbox((0, 0), "Not the other way around.", font=font_t2)[2] - d.textbbox((0, 0), "Not the other way around.", font=font_t2)[0]
    d.text(((WIDTH - bw2) // 2, 1575), "Not the other way around.", font=font_t2, fill=(16, 185, 129))

    font_meta = get_font(15)
    meta_str = "WINDOWS  ·  LOCAL-FIRST  ·  NO CLOUD SYNC"
    bwm = d.textbbox((0, 0), meta_str, font=font_meta)[2] - d.textbbox((0, 0), meta_str, font=font_meta)[0]
    d.text(((WIDTH - bwm) // 2, 1655), meta_str, font=font_meta, fill=(148, 163, 184))

    # Fade out last 0.6s
    if t > 58.9:
        fade = (t - 58.9) / 0.6
        curtain = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, int(255 * fade)))
        canvas.paste(curtain, (0, 0), curtain)

    return canvas

# ── Master Frame Dispatcher ───────────────────────────────────────────────────
def render_frame(frame_idx: int) -> np.ndarray:
    t = frame_idx / float(FPS)

    if t < 2.5:
        canvas = render_scene_hook(t)
    elif t < 7.0:
        canvas = render_scene_home(t)
    elif t < 11.0:
        canvas = render_scene_usage_insights(t)
    elif t < 25.0:
        canvas = render_scene_focus(t)
    elif t < 34.0:
        canvas = render_scene_timer(t)
    elif t < 42.0:
        canvas = render_scene_app_locker(t)
    elif t < 53.0:
        canvas = render_scene_sleepguard(t)
    else:
        canvas = render_scene_final(t)

    return np.array(canvas.convert("RGB"))

# ── Audio Synthesis for 59.5-second Short ───────────────────────────────────────
print("[3/5] Synthesizing synchronized 59.5-second reference soundtrack with sound cues...", flush=True)

def synthesize_audio() -> Path:
    audio_path = BASE_DIR / "notch_short_soundtrack.wav"
    sr = AUDIO_SAMPLE_RATE

    with wave.open(str(REF_AUDIO_PATH), "rb") as wf:
        orig = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).reshape(-1, 2)
    orig_f = orig.astype(np.float32) / 32768.0

    def sec(s): return int(s * sr)

    B1 = orig_f[sec(3.598) : sec(8.130)]
    B2 = orig_f[sec(8.130) : sec(12.654)]
    B3 = orig_f[sec(12.654) : sec(17.177)]
    C  = orig_f[sec(17.177) : sec(21.712)]
    D  = orig_f[sec(21.712) : sec(26.243)]
    E  = orig_f[sec(26.243) : sec(30.720)]

    sections = [B1, B2, B3, C, D, B2, B3, C, D, B1, B2, C, E, E[:sec(1.7)]]

    def crossfade_concat(chunks, xfade_ms=35):
        xfade_samples = int((xfade_ms / 1000.0) * sr)
        out = chunks[0]
        for nxt in chunks[1:]:
            xf = min(xfade_samples, len(out), len(nxt))
            fade_out = np.linspace(1.0, 0.0, xf)[:, None]
            fade_in = np.linspace(0.0, 1.0, xf)[:, None]
            overlap = out[-xf:] * np.sqrt(fade_out) + nxt[:xf] * np.sqrt(fade_in)
            out = np.vstack([out[:-xf], overlap, nxt[xf:]])
        return out

    extended = crossfade_concat(sections, xfade_ms=35)
    target_len = int(TOTAL_SECONDS * sr)
    if len(extended) > target_len:
        extended = extended[:target_len]
    elif len(extended) < target_len:
        pad = np.zeros((target_len - len(extended), 2), dtype=np.float32)
        extended = np.vstack([extended, pad])

    fade_len = int(0.7 * sr)
    extended[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)[:, None]

    # Beat cues aligned with visual transition hits
    def add_click(arr, at_time, gain=0.08):
        idx = int(at_time * sr)
        dur = int(0.03 * sr)
        if idx + dur < len(arr):
            t = np.linspace(0, 0.03, dur, False)
            s = gain * np.sin(2 * np.pi * 2400 * t) * np.exp(-140.0 * t)
            arr[idx:idx+dur, 0] += s
            arr[idx:idx+dur, 1] += s

    def add_chime(arr, at_time, f1=880, f2=1320, dur=0.4, gain=0.06):
        idx = int(at_time * sr)
        l = int(dur * sr)
        if idx + l < len(arr):
            t = np.linspace(0, dur, l, False)
            s = gain * (np.sin(2*np.pi*f1*t) + 0.7*np.sin(2*np.pi*f2*t)) * np.exp(-9.0 * t)
            arr[idx:idx+l, 0] += s * 0.7
            arr[idx:idx+l, 1] += s * 0.7

    # Hook cuts
    add_click(extended, 0.625)
    add_click(extended, 1.25)
    add_click(extended, 1.875)
    add_click(extended, 2.50)

    # Feature transitions
    add_click(extended, 7.0)
    add_click(extended, 9.2)
    add_click(extended, 11.0)
    add_chime(extended, 14.5, gain=0.05)
    add_chime(extended, 18.0, f1=523, f2=1046, gain=0.10)  # Discord Blocked Climax!
    add_click(extended, 25.0)
    add_click(extended, 29.5)
    add_click(extended, 34.0)
    add_click(extended, 37.0)
    add_chime(extended, 39.5, f1=1046, f2=1318, gain=0.08)  # Access Granted!
    add_click(extended, 42.0)
    add_chime(extended, 45.0, f1=440, f2=880, gain=0.06)   # 60s Warning!
    add_chime(extended, 48.5, f1=880, f2=1760, gain=0.08)  # Power Action Aborted!
    add_click(extended, 53.0)

    max_val = np.max(np.abs(extended))
    if max_val > 0.95:
        extended = extended * (0.95 / max_val)

    int_audio = (extended * 32767.0).astype(np.int16)
    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_audio.tobytes())

    return audio_path

# ── Main Rendering Pipeline ────────────────────────────────────────────────────
def main():
    start_time = time.time()
    audio_file = synthesize_audio()

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_raw_video = BASE_DIR / "temp_short_raw.mp4"

    if temp_raw_video.exists():
        temp_raw_video.unlink()
    if OUTPUT_VIDEO.exists():
        OUTPUT_VIDEO.unlink()

    print(f"[4/5] Encoding {TOTAL_FRAMES} frames ({TOTAL_SECONDS:.1f}s @ {FPS}fps) at {WIDTH}x{HEIGHT} 9:16 Vertical...", flush=True)

    ffmpeg_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(temp_raw_video)
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for frame_idx in range(TOTAL_FRAMES):
        frame_rgb = render_frame(frame_idx)
        proc.stdin.write(frame_rgb.tobytes())

        if frame_idx % 300 == 0 or frame_idx == TOTAL_FRAMES - 1:
            elapsed = time.time() - start_time
            fps_actual = (frame_idx + 1) / max(0.1, elapsed)
            percent = ((frame_idx + 1) / TOTAL_FRAMES) * 100
            rem_sec = (TOTAL_FRAMES - frame_idx) / max(1.0, fps_actual)
            print(f"  Frame {frame_idx + 1:4d} / {TOTAL_FRAMES} ({percent:5.1f}%) | {fps_actual:5.1f} fps | Est. remaining: {rem_sec:4.1f}s", flush=True)

    proc.stdin.close()
    proc.wait()

    print("[5/5] Multiplexing vertical H.264 video with synchronized master AAC audio...", flush=True)
    mux_cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(temp_raw_video),
        "-i", str(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(OUTPUT_VIDEO)
    ]
    mux_proc = subprocess.run(mux_cmd, capture_output=True, text=True)
    if mux_proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio muxing failed: {mux_proc.stderr}")

    if temp_raw_video.exists():
        temp_raw_video.unlink()
    if audio_file.exists():
        audio_file.unlink()

    total_time = time.time() - start_time
    file_size_mb = OUTPUT_VIDEO.stat().st_size / (1024 * 1024)
    print(f"\n==========================================================================", flush=True)
    print(f"[SUCCESS] Rebuilt Notch YouTube Short rendered successfully!", flush=True)
    print(f"  Output File: {OUTPUT_VIDEO.name}", flush=True)
    print(f"  Full Path:   {OUTPUT_VIDEO}", flush=True)
    print(f"  Resolution:  {WIDTH}x{HEIGHT} (9:16 Vertical Full HD)", flush=True)
    print(f"  Duration:    {TOTAL_SECONDS:.1f} seconds ({TOTAL_FRAMES} frames @ {FPS} fps)", flush=True)
    print(f"  File Size:   {file_size_mb:.2f} MB", flush=True)
    print(f"  Total Render Time: {total_time:.1f} seconds", flush=True)
    print(f"==========================================================================", flush=True)

if __name__ == "__main__":
    main()
