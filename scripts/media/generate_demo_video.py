"""
generate_demo_video.py — Production rendering pipeline for Notch 60s NYC Showcase Film.
Engineered for NYC YouTube Showcase Submission.
Premium Finishing Pass:
- Exactly 60.0 seconds (1800 frames @ 30fps, 1080p Full HD).
- Music DRIVES the edit: Synchronized to 106 BPM musical grid across 14 progression segments.
- Compressed Dashboard Section (0–11.5s):
    Home: 4.5s (0.0s – 4.5s)
    Usage: 3.5s (4.5s – 8.0s)
    Insights: 3.5s (8.0s – 11.5s)
- Hero Focus Mode (11.5s – 23.5s / 12.0s):
    Setup -> Start Focus -> 25:00 Active Ring -> Section D Climax Drop (18.0s) Discord Intercepted!
- App Timer (23.5s – 31.5s / 8.0s):
    Select App -> Set Limit Slider -> Section B3 Drop Active Budget Card (24m left · 21m used / 45m limit).
- App Locker (31.5s – 40.0s / 8.5s):
    Locked App -> Fast Windows Hello Scan -> Section D Drop Biometric Verified Checkmark!
- SleepGuard (40.0s – 52.5s / 12.5s):
    Armed 30m Inactivity Established -> 60s Warning Countdown Popup (01:00 -> 00:59 -> 00:58) -> Cancel Click -> Power Action Aborted Safely.
- Final Hero Shot (52.5s – 60.0s / 7.5s):
    Real Notch Home Dashboard Hero Shot -> Commercial Tagline -> Breathes and Resolves with Music Reverb Tail.
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

# Environment
os.environ["PYTHONIOENCODING"] = "utf-8"

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = BASE_DIR / "website" / "public" / "images" / "app"
LOGO_PATH = BASE_DIR / "website" / "public" / "notch-logo.png"
_scratch_audio = BASE_DIR / "scratch" / "media" / "reference_music.wav"
REF_AUDIO_PATH = _scratch_audio if _scratch_audio.exists() else BASE_DIR / "reference_music.wav"
OUTPUT_VIDEO = BASE_DIR / "scratch" / "media" / "Notch_Product_Demo_NYC_Showcase.mp4"

# ── Video Specifications ───────────────────────────────────────────────────────
WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_SECONDS = 60.0
TOTAL_FRAMES = int(FPS * TOTAL_SECONDS)  # Exactly 1800 frames
AUDIO_SAMPLE_RATE = 48000

WIN_CX = WIDTH // 2
WIN_CY = 465

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

# ── Easing & Interpolation Functions ───────────────────────────────────────────
def clamp(v, min_v=0.0, max_v=1.0):
    return max(min_v, min(max_v, float(v)))

def lerp(a, b, t):
    return a + (b - a) * t

def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def ease_out_cubic(t):
    t = clamp(t)
    return 1 - math.pow(1 - t, 3)

def ease_in_cubic(t):
    t = clamp(t)
    return t * t * t

def smoothstep(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)

# ── Window Frame & Shadow Pre-compositing ──────────────────────────────────────
print("[1/5] Pre-rendering framed Windows 11 UI assets and dynamic dialog states...", flush=True)

def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing asset: {path}")
    return Image.open(path).convert("RGBA")

# Build SleepGuard dynamic variants from base countdown asset
def create_sleepguard_variants():
    base_countdown = load_rgba(ASSETS_DIR / "sleepguard-countdown-dark.png")
    bg_color = (17, 21, 28, 255)
    orange_color = (245, 158, 11, 255)
    emerald_color = (16, 185, 129, 255)
    font_time = get_font(54, bold=True)
    font_bold = get_font(26, bold=True)
    font_sub = get_font(16)

    # 1. 01:00 (Original countdown)
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

# Build active App Timer variant (showing configured Brave Browser budget)
def create_active_timer_asset() -> Image.Image:
    base = load_rgba(ASSETS_DIR / "app-timer-dark.png")
    font_name = get_font(16, bold=True)
    font_pill = get_font(12, bold=True)
    font_sub = get_font(13)
    font_kpi = get_font(24, bold=True)
    font_btn = get_font(12)

    img = base.copy()
    draw = ImageDraw.Draw(img)

    # Update KPI: '1 app' with exact matching background fill
    draw.rectangle([295, 142, 420, 180], fill=(15, 18, 24, 255))
    draw.text((297, 145), '1 app', font=font_kpi, fill=(16, 185, 129, 255))

    # Cover the 'No Application Timers Configured' frame
    draw.rectangle([260, 275, 1380, 580], fill=(13, 17, 23, 255))

    # Draw active Timer App Card matching ui/pages/app_timer.py
    card_x1, card_y1, card_x2, card_y2 = 260, 275, 1380, 375
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=10, fill=(18, 24, 34, 255), outline=(255, 255, 255, 25), width=1)

    # Brave Browser Lion icon from home screenshot
    home_src = load_rgba(ASSETS_DIR / "home-dark.png")
    brave_ico = home_src.crop((312, 414, 346, 452)).resize((34, 38), Image.Resampling.LANCZOS)
    img.paste(brave_ico, (card_x1 + 18, card_y1 + 18), brave_ico)

    # Title
    draw.text((card_x1 + 68, card_y1 + 16), 'Brave Browser', font=font_name, fill=(255, 255, 255, 255))

    # Remaining pill badge (24m left)
    pw = draw.textlength('24m left', font=font_pill)
    px = card_x1 + 68 + int(draw.textlength('Brave Browser', font=font_name)) + 14
    draw.rounded_rectangle([px, card_y1 + 15, px + int(pw) + 16, card_y1 + 35], radius=9, fill=(16, 185, 129, 35), outline=(16, 185, 129, 180), width=1)
    draw.text((px + 8, card_y1 + 17), '24m left', font=font_pill, fill=(16, 185, 129, 255))

    # Subtitle
    draw.text((card_x1 + 68, card_y1 + 42), '21m used / 45m daily limit', font=font_sub, fill=(156, 163, 175, 255))

    # Progress bar (47% used)
    bx1 = card_x1 + 68
    by1 = card_y1 + 68
    bx2 = card_x2 - 120
    by2 = by1 + 6
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=3, fill=(35, 45, 60, 255))
    fill_w = int((bx2 - bx1) * 0.47)
    draw.rounded_rectangle([bx1, by1, bx1 + fill_w, by2], radius=3, fill=(16, 185, 129, 255))

    # Edit button on right
    draw.rounded_rectangle([card_x2 - 95, card_y1 + 25, card_x2 - 25, card_y1 + 62], radius=6, fill=(26, 34, 48, 255), outline=(255, 255, 255, 25), width=1)
    draw.text((card_x2 - 76, card_y1 + 36), 'Edit', font=font_btn, fill=(200, 215, 230, 255))

    return img

# Build Discord blocked dialog composited directly over focus_active (hero cause -> result)
def create_focus_blocked_asset() -> Image.Image:
    focus_active = load_rgba(ASSETS_DIR / "focus-active-dark.png")
    blocked_src = load_rgba(ASSETS_DIR / "blocked-app-dark.png")

    modal = blocked_src.crop((523, 232, 917, 592))
    mw, mh = modal.size

    mask = Image.new('L', (mw, mh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, mw, mh], radius=14, fill=255)

    bordered_modal = modal.copy()
    ImageDraw.Draw(bordered_modal).rounded_rectangle([0, 0, mw - 1, mh - 1], radius=14, outline=(255, 255, 255, 45), width=1)

    shadow = Image.new('RGBA', (mw + 40, mh + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([20, 24, 20 + mw, 24 + mh], radius=16, fill=(0, 0, 0, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))

    comp = focus_active.copy()
    comp.paste(shadow, (523 - 20, 232 - 20), shadow)
    comp.paste(bordered_modal, (523, 232), mask)
    return comp

sg_60, sg_59, sg_58, sg_cancelled = create_sleepguard_variants()
timer_active_img = create_active_timer_asset()
focus_blocked_img = create_focus_blocked_asset()

RAW_ASSETS = {
    "home": load_rgba(ASSETS_DIR / "home-dark.png"),
    "usage": load_rgba(ASSETS_DIR / "usage-dark.png"),
    "focus_preflight": load_rgba(ASSETS_DIR / "focus-preflight-dark.png"),
    "focus_active": load_rgba(ASSETS_DIR / "focus-active-dark.png"),
    "focus_blocked": focus_blocked_img,
    "timer_config": load_rgba(ASSETS_DIR / "app-timer-config-dark.png"),
    "timer_active": timer_active_img,
    "app_locker": load_rgba(ASSETS_DIR / "app-locker-dark.png"),
    "auth": load_rgba(ASSETS_DIR / "authentication-dark.png"),
    "insights": load_rgba(ASSETS_DIR / "insights-dark.png"),
    "sleepguard": load_rgba(ASSETS_DIR / "sleepguard-dark.png"),
    "sg_60": sg_60,
    "sg_59": sg_59,
    "sg_58": sg_58,
    "sg_cancelled": sg_cancelled,
    "logo": load_rgba(LOGO_PATH),
}

# Pre-render framed window with rounded corners (14px), 1px subtle border, and soft drop shadow
def create_framed_window(src_img: Image.Image, corner_rad: int = 14) -> Image.Image:
    w, h = src_img.size
    pad = 48
    total_w = w + pad * 2
    total_h = h + pad * 2

    frame = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Multi-layered soft gaussian shadow
    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    d_sh = ImageDraw.Draw(shadow)
    d_sh.rounded_rectangle([pad, pad + 14, pad + w, pad + h + 14], radius=corner_rad + 4, fill=(0, 0, 0, 160))
    d_sh.rounded_rectangle([pad - 4, pad + 8, pad + w + 4, pad + h + 18], radius=corner_rad + 6, fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    frame.paste(shadow, (0, 0), shadow)

    # Window content mask
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=corner_rad, fill=255)
    
    # 1px border
    bordered_src = src_img.copy()
    ImageDraw.Draw(bordered_src).rounded_rectangle([0, 0, w - 1, h - 1], radius=corner_rad, outline=(255, 255, 255, 38), width=1)

    frame.paste(bordered_src, (pad, pad), mask)
    return frame

FRAMED_WINDOWS = {}
for name, raw_img in RAW_ASSETS.items():
    if name != "logo":
        FRAMED_WINDOWS[name] = create_framed_window(raw_img)
        print(f"  Pre-rendered framed asset: {name}", flush=True)

# ── Base Desktop & Windows 11 Environment ──────────────────────────────────────
def create_base_wallpaper() -> Image.Image:
    wall = Image.new("RGBA", (WIDTH, HEIGHT), (6, 8, 12, 255))

    # Top-center emerald glow
    glow_em = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d_em = ImageDraw.Draw(glow_em)
    for r in range(450, 0, -25):
        alpha = int(22 * (1.0 - r / 450.0))
        d_em.ellipse([WIDTH//2 - r*1.6, -80 - r, WIDTH//2 + r*1.6, 450 + r], fill=(16, 185, 129, alpha))
    glow_em = glow_em.filter(ImageFilter.GaussianBlur(55))
    wall = Image.alpha_composite(wall, glow_em)

    # Subtle bottom-right indigo ambient
    glow_in = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d_in = ImageDraw.Draw(glow_in)
    for r in range(360, 0, -30):
        alpha = int(16 * (1.0 - r / 360.0))
        d_in.ellipse([WIDTH - 220 - r, HEIGHT - 160 - r, WIDTH - 220 + r, HEIGHT - 160 + r], fill=(99, 102, 241, alpha))
    glow_in = glow_in.filter(ImageFilter.GaussianBlur(60))
    wall = Image.alpha_composite(wall, glow_in)

    return wall

BASE_WALLPAPER = create_base_wallpaper()

def draw_taskbar(canvas: Image.Image, time_sec: float):
    tb_h = 48
    tb_y = HEIGHT - tb_h
    tb_overlay = Image.new("RGBA", (WIDTH, tb_h), (11, 15, 23, 225))
    
    tb_draw = ImageDraw.Draw(tb_overlay)
    tb_draw.line([(0, 0), (WIDTH, 0)], fill=(255, 255, 255, 20), width=1)
    
    # Windows 11 Start and Search icons
    cx = WIDTH // 2
    tile_color = (0, 164, 239, 230)
    tb_draw.rounded_rectangle([cx - 45, 14, cx - 35, 24], radius=2, fill=tile_color)
    tb_draw.rounded_rectangle([cx - 33, 14, cx - 23, 24], radius=2, fill=tile_color)
    tb_draw.rounded_rectangle([cx - 45, 26, cx - 35, 36], radius=2, fill=tile_color)
    tb_draw.rounded_rectangle([cx - 33, 26, cx - 23, 36], radius=2, fill=tile_color)

    tb_draw.ellipse([cx - 10, 15, cx + 2, 27], outline=(255, 255, 255, 180), width=2)
    tb_draw.line([(cx + 1, 26), (cx + 7, 32)], fill=(255, 255, 255, 180), width=2)

    # Active Notch icon in taskbar
    logo_thumb = RAW_ASSETS["logo"].resize((24, 24), Image.Resampling.LANCZOS)
    tb_overlay.paste(logo_thumb, (cx + 20, 12), logo_thumb)
    tb_draw.rounded_rectangle([cx + 26, 42, cx + 38, 44], radius=1, fill=(16, 185, 129, 255))

    # System Tray
    rx = WIDTH - 220
    pulse_alpha = int(180 + 75 * math.sin(time_sec * 4.0))
    tb_draw.ellipse([rx - 4, 16, rx + 14, 34], fill=(16, 185, 129, 30))
    tb_draw.ellipse([rx, 20, rx + 10, 30], fill=(16, 185, 129, pulse_alpha))
    
    tb_draw.arc([rx + 26, 17, rx + 44, 35], start=210, end=330, fill=(255, 255, 255, 180), width=2)
    tb_draw.arc([rx + 30, 22, rx + 40, 32], start=210, end=330, fill=(255, 255, 255, 200), width=2)
    tb_draw.point((rx + 35, 30), fill=(255, 255, 255, 220))

    tb_draw.polygon([(rx + 54, 21), (rx + 58, 21), (rx + 64, 16), (rx + 64, 34), (rx + 58, 29), (rx + 54, 29)], fill=(255, 255, 255, 190))
    tb_draw.arc([rx + 62, 19, rx + 72, 31], start=300, end=60, fill=(255, 255, 255, 180), width=1)

    font_clock = get_font(13)
    tb_draw.text((rx + 90, 16), "10:42 AM", font=font_clock, fill=(240, 243, 246, 230))

    canvas.paste(tb_overlay, (0, tb_y), tb_overlay)

def render_window_fast(canvas: Image.Image, name: str, center_x: float, center_y: float, 
                       scale: float = 1.0, alpha: float = 1.0):
    if alpha <= 0.005:
        return
    
    base_frame = FRAMED_WINDOWS.get(name)
    if not base_frame:
        return

    fw, fh = base_frame.size
    dst_w = int(fw * scale)
    dst_h = int(fh * scale)
    
    if abs(scale - 1.0) > 0.005:
        scaled_frame = base_frame.resize((dst_w, dst_h), Image.Resampling.BILINEAR)
    else:
        scaled_frame = base_frame

    top_left_x = int(center_x - dst_w / 2)
    top_left_y = int(center_y - dst_h / 2)

    if alpha < 0.99:
        r, g, b, a = scaled_frame.split()
        a = a.point(lambda p: int(p * alpha))
        scaled_frame = Image.merge("RGBA", (r, g, b, a))

    canvas.paste(scaled_frame, (top_left_x, top_left_y), scaled_frame)

# ── Clean Product Lower-Third Typography Card ─────────────────────────────────
def draw_lower_third(canvas: Image.Image, tag: str, title: str, subtitle: str, alpha: float = 1.0, y_pos: int = 926):
    if alpha <= 0.005:
        return
    
    card_w = 680
    card_h = 76
    card_x = (WIDTH - card_w) // 2
    
    card = Image.new("RGBA", (card_w, card_h), (10, 14, 22, int(235 * alpha)))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=12, outline=(255, 255, 255, int(35 * alpha)), width=1)
    
    # Category tag with emerald dot
    d.ellipse([20, 14, 28, 22], fill=(16, 185, 129, int(255 * alpha)))
    font_tag = get_font(10, bold=True)
    d.text((34, 11), tag.upper(), font=font_tag, fill=(16, 185, 129, int(240 * alpha)))
    
    # Clean product title
    font_title = get_font(17, bold=True)
    d.text((20, 29), title, font=font_title, fill=(255, 255, 255, int(255 * alpha)))
    
    # Subtitle
    font_sub = get_font(11)
    d.text((20, 52), subtitle, font=font_sub, fill=(160, 175, 195, int(230 * alpha)))
    
    c_mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(c_mask).rounded_rectangle([0, 0, card_w, card_h], radius=12, fill=int(255 * alpha))
    canvas.paste(card, (card_x, y_pos), c_mask)

# ── Smooth Cursor Animation ────────────────────────────────────────────────────
def draw_cursor(canvas: Image.Image, x: float, y: float, click_progress: float = 0.0, alpha: float = 1.0):
    if alpha <= 0.01:
        return
    ix = int(x)
    iy = int(y)
    
    # Click ripple
    if 0.0 < click_progress <= 1.0:
        rip_r = int(10 + click_progress * 32)
        rip_alpha = int(220 * (1.0 - click_progress) * alpha)
        ripple = Image.new("RGBA", (rip_r * 2 + 4, rip_r * 2 + 4), (0, 0, 0, 0))
        d_rip = ImageDraw.Draw(ripple)
        d_rip.ellipse([2, 2, rip_r * 2 + 2, rip_r * 2 + 2], outline=(16, 185, 129, rip_alpha), width=2)
        canvas.paste(ripple, (ix - rip_r - 2, iy - rip_r - 2), ripple)

    cursor_img = Image.new("RGBA", (28, 36), (0, 0, 0, 0))
    d_c = ImageDraw.Draw(cursor_img)
    points = [(2, 2), (2, 24), (7, 19), (12, 29), (16, 27), (11, 17), (19, 17)]
    sh_points = [(p[0] + 2, p[1] + 2) for p in points]
    d_c.polygon(sh_points, fill=(0, 0, 0, int(120 * alpha)))
    d_c.polygon(points, fill=(0, 0, 0, int(240 * alpha)))
    in_points = [(p[0] + 1, p[1] + 1) for p in points]
    d_c.polygon(in_points[:3] + [(11, 28), (15, 26)] + in_points[5:], fill=(255, 255, 255, int(255 * alpha)))
    
    canvas.paste(cursor_img, (ix, iy), cursor_img)

# ── Scene 1: Home Dashboard (0.0s – 4.5s) ─────────────────────────────────────
def render_scene_home(canvas: Image.Image, t: float, alpha: float):
    p = clamp(t / 4.5)
    scale = 0.99 + 0.035 * smoothstep(p)
    
    # 0.0s - 0.8s: Quick Logo bloom that seamlessly gives way to the full Home dashboard
    if t < 0.8:
        lp = t / 0.8
        cx, cy = WIDTH // 2, 430
        glow_r = int(120 * ease_out_cubic(lp))
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d_g = ImageDraw.Draw(glow)
        d_g.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=(16, 185, 129, int(35 * alpha)))
        canvas.paste(glow, (0, 0), glow)

        logo_sz = int(110 * lerp(0.85, 1.0, ease_out_cubic(lp)))
        logo_thumb = RAW_ASSETS["logo"].resize((logo_sz, logo_sz), Image.Resampling.BILINEAR)
        canvas.paste(logo_thumb, (cx - logo_sz // 2, cy - logo_sz // 2), logo_thumb)

        draw = ImageDraw.Draw(canvas)
        font_brand = get_font(46, bold=True)
        bw = draw.textlength("NOTCH", font=font_brand)
        draw.text((cx - bw // 2, cy + 80), "NOTCH", font=font_brand, fill=(255, 255, 255, int(255 * alpha)))
        return

    # 0.8s - 4.5s: Home dashboard in full action
    home_alpha = alpha
    if t < 1.2:
        home_alpha = alpha * ease_out_cubic((t - 0.8) / 0.4)

    render_window_fast(canvas, "home", WIN_CX, WIN_CY, scale=scale, alpha=home_alpha)

    # Brisk cursor sweep: screen time -> top app -> sidebar Usage
    if t < 3.2:
        cur_p = clamp((t - 1.2) / 2.0)
        cx = lerp(1360, 580, ease_in_out_cubic(cur_p))
        cy = lerp(850, 360, ease_in_out_cubic(cur_p))
        draw_cursor(canvas, cx, cy, alpha=home_alpha)
    else:
        cur_p = clamp((t - 3.2) / 1.3)
        cx = lerp(580, 180, ease_in_out_cubic(cur_p))
        cy = lerp(360, 205, ease_in_out_cubic(cur_p))
        clicking = (cur_p > 0.80)
        click_prog = (cur_p - 0.80) / 0.20 if clicking else 0.0
        draw_cursor(canvas, cx, cy, click_progress=click_prog, alpha=home_alpha)

    lt_alpha = home_alpha
    if t < 1.4:
        lt_alpha = home_alpha * ease_out_cubic((t - 1.0) / 0.4)
    elif t > 4.2:
        lt_alpha = home_alpha * (1.0 - ease_in_cubic((t - 4.2) / 0.3))

    draw_lower_third(
        canvas,
        tag="DASHBOARD",
        title="UNDERSTAND YOUR USAGE",
        subtitle="Real-time screen time, active vs idle tracking, and top applications at a glance",
        alpha=lt_alpha
    )

# ── Scene 2: Usage Trends & Real-Time Tracking (4.5s – 8.0s) ──────────────────
def render_scene_usage(canvas: Image.Image, t: float, alpha: float):
    p = clamp((t - 4.5) / 3.5)
    scale = 1.00 + 0.035 * smoothstep(p)
    render_window_fast(canvas, "usage", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

    # Cursor sweeps timeline intensity -> snaps to sidebar Insights
    if p < 0.70:
        cur_p = p / 0.70
        cx = lerp(450, 780, ease_in_out_cubic(cur_p))
        cy = 390
        draw_cursor(canvas, cx, cy, alpha=alpha)
    else:
        cur_p = (p - 0.70) / 0.30
        cx = lerp(780, 180, ease_in_out_cubic(cur_p))
        cy = lerp(390, 245, ease_in_out_cubic(cur_p))
        clicking = (cur_p > 0.80)
        click_prog = (cur_p - 0.80) / 0.20 if clicking else 0.0
        draw_cursor(canvas, cx, cy, click_progress=click_prog, alpha=alpha)

    lt_alpha = alpha
    if t < 4.8:
        lt_alpha = alpha * ease_out_cubic((t - 4.5) / 0.3)
    elif t > 7.7:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 7.7) / 0.3))

    draw_lower_third(
        canvas,
        tag="ACTIVITY",
        title="UNDERSTAND YOUR USAGE",
        subtitle="Automatic background process tracking across applications and browsers",
        alpha=lt_alpha
    )

# ── Scene 3: Intelligent Insights (8.0s – 11.5s) ──────────────────────────────
def render_scene_insights(canvas: Image.Image, t: float, alpha: float):
    p = clamp((t - 8.0) / 3.5)
    scale = 1.01 + 0.035 * smoothstep(p)
    render_window_fast(canvas, "insights", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

    # Cursor glides over productivity score (78%) & donut chart -> snaps to Focus in sidebar
    if p < 0.70:
        cur_p = p / 0.70
        cx = lerp(680, 1080, ease_in_out_cubic(cur_p))
        cy = lerp(420, 460, math.sin(cur_p * math.pi))
        draw_cursor(canvas, cx, cy, alpha=alpha)
    else:
        cur_p = (p - 0.70) / 0.30
        cx = lerp(1080, 180, ease_in_out_cubic(cur_p))
        cy = lerp(460, 320, ease_in_out_cubic(cur_p))
        clicking = (cur_p > 0.80)
        click_prog = (cur_p - 0.80) / 0.20 if clicking else 0.0
        draw_cursor(canvas, cx, cy, click_progress=click_prog, alpha=alpha)

    lt_alpha = alpha
    if t < 8.3:
        lt_alpha = alpha * ease_out_cubic((t - 8.0) / 0.3)
    elif t > 11.2:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 11.2) / 0.3))

    draw_lower_third(
        canvas,
        tag="INSIGHTS",
        title="UNDERSTAND YOUR USAGE",
        subtitle="Productivity score and hourly usage breakdown reveal lost hours",
        alpha=lt_alpha
    )

# ── Scene 4: Focus Mode — Hero Feature (11.5s – 23.5s) ────────────────────────
def render_scene_focus(canvas: Image.Image, t: float, alpha: float):
    # Phase 1: 11.5s – 14.5s: Focus setup (preflight)
    if t < 14.5:
        part_p = clamp((t - 11.5) / 3.0)
        scale = 1.015 + 0.02 * smoothstep(part_p)
        render_window_fast(canvas, "focus_preflight", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        cur_x = lerp(620, 960, ease_in_out_cubic(part_p))
        cur_y = lerp(660, 600, ease_in_out_cubic(part_p))
        clicking = (part_p > 0.85)
        click_prog = (part_p - 0.85) / 0.15 if clicking else 0.0
        draw_cursor(canvas, cur_x, cur_y, click_progress=click_prog, alpha=alpha)

        t_tag = "FOCUS MODE"
        t_sub = "1. Configure Focus · Whitelist essential tools, block distracting apps"

    # Phase 2: 14.5s – 18.0s: Active Focus 25:00 countdown ring & armed monitor
    elif t < 18.0:
        part_p = clamp((t - 14.5) / 3.5)
        scale = 1.025 + 0.03 * smoothstep(part_p)
        render_window_fast(canvas, "focus_active", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        # Subtle breathing emerald aura
        vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        dv = ImageDraw.Draw(vignette)
        dv.rectangle([0, 0, WIDTH, HEIGHT], outline=(16, 185, 129, int((35 + 20 * math.sin(t * 6.0)) * alpha)), width=3)
        canvas.paste(vignette, (0, 0), vignette)

        t_tag = "FOCUS MODE"
        t_sub = "2. Focus Session Active · Distraction Guard armed at the Windows OS level"

    # Phase 3: 18.0s – 23.5s: HERO INTERCEPTION (Discord Blocked on Climax Drop!)
    else:
        part_p = clamp((t - 18.0) / 5.5)
        scale = 1.03 + 0.035 * smoothstep(part_p)
        render_window_fast(canvas, "focus_blocked", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        cur_p = min(1.0, part_p * 1.6)
        cur_x = lerp(850, 960, ease_in_out_cubic(cur_p))
        cur_y = lerp(660, 560, ease_in_out_cubic(cur_p))
        clicking = (cur_p > 0.85)
        click_prog = (cur_p - 0.85) / 0.15 if clicking else 0.0
        draw_cursor(canvas, cur_x, cur_y, click_progress=click_prog, alpha=alpha)

        t_tag = "HERO MOMENT · FOCUS MODE"
        t_sub = "3. Active Interception · Notch actively intercepts and closes restricted apps"

    lt_alpha = alpha
    if t < 11.8:
        lt_alpha = alpha * ease_out_cubic((t - 11.5) / 0.3)
    elif t > 23.2:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 23.2) / 0.3))

    draw_lower_third(
        canvas,
        tag=t_tag,
        title="BLOCK DISTRACTIONS",
        subtitle=t_sub,
        alpha=lt_alpha
    )

# ── Scene 5: App Timer (23.5s – 31.5s) ────────────────────────────────────────
def render_scene_timer(canvas: Image.Image, t: float, alpha: float):
    # Phase 1: 23.5s – 27.0s: Select app & set limit slider
    if t < 27.0:
        part_p = clamp((t - 23.5) / 3.5)
        scale = 1.015 + 0.02 * smoothstep(part_p)
        render_window_fast(canvas, "timer_config", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        cur_x = lerp(600, 920, ease_in_out_cubic(part_p))
        cur_y = lerp(540, 560, ease_in_out_cubic(part_p))
        clicking = (part_p > 0.85)
        click_prog = (part_p - 0.85) / 0.15 if clicking else 0.0
        draw_cursor(canvas, cur_x, cur_y, click_progress=click_prog, alpha=alpha)

        t_sub = "1. Set Time Limit · Allocate daily budgets for distracting apps"

    # Phase 2: 27.0s – 31.5s: Active budget card on Section B3 drop!
    else:
        part_p = clamp((t - 27.0) / 4.5)
        scale = 1.02 + 0.03 * smoothstep(part_p)
        render_window_fast(canvas, "timer_active", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        t_sub = "2. Budget Active · Proactive remaining time tracking prevents overuse"

    lt_alpha = alpha
    if t < 23.8:
        lt_alpha = alpha * ease_out_cubic((t - 23.5) / 0.3)
    elif t > 31.2:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 31.2) / 0.3))

    draw_lower_third(
        canvas,
        tag="APP TIMER",
        title="SET APP LIMITS",
        subtitle=t_sub,
        alpha=lt_alpha
    )

# ── Scene 6: App Locker & Windows Hello (31.5s – 40.0s) ───────────────────────
def render_scene_app_locker(canvas: Image.Image, t: float, alpha: float):
    # Phase 1: 31.5s – 34.5s: Protected app launch
    if t < 34.5:
        part_p = clamp((t - 31.5) / 3.0)
        scale = 1.015 + 0.02 * smoothstep(part_p)
        render_window_fast(canvas, "app_locker", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        cur_x = lerp(520, 1120, ease_in_out_cubic(part_p))
        cur_y = lerp(320, 390, ease_in_out_cubic(part_p))
        clicking = (part_p > 0.78)
        click_prog = (part_p - 0.78) / 0.22 if clicking else 0.0
        draw_cursor(canvas, cur_x, cur_y, click_progress=click_prog, alpha=alpha)

        t_sub = "1. App Protected · Hardware biometric gatekeeper for private apps"

    # Phase 2: 34.5s – 40.0s: Fast Windows Hello scan -> Instant verified checkmark on drop!
    else:
        auth_p = clamp((t - 34.5) / 5.5)
        render_window_fast(canvas, "app_locker", WIN_CX, WIN_CY, scale=1.03, alpha=alpha)

        modal_scale = lerp(0.97, 1.03, ease_out_cubic(min(1.0, auth_p * 2.0)))
        render_window_fast(canvas, "auth", WIN_CX, WIN_CY, scale=modal_scale, alpha=alpha)

        if t < 36.5:
            # 2 quick concentric radar scan pulses
            scan_cycle = ((t - 34.5) * 1.8) % 1.0
            scan_r = int(16 + scan_cycle * 42)
            scan_alpha = int(180 * (1.0 - scan_cycle) * alpha)
            scan_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            ds = ImageDraw.Draw(scan_layer)
            ds.ellipse([WIN_CX - scan_r, WIN_CY - 20 - scan_r, WIN_CX + scan_r, WIN_CY - 20 + scan_r], outline=(16, 185, 129, scan_alpha), width=2)
            canvas.paste(scan_layer, (0, 0), scan_layer)

            t_sub = "2. Windows Hello · Fingerprint, facial recognition, or PIN prompt"
        else:
            # Verified checkmark lands on Climax Drop!
            v_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            dv = ImageDraw.Draw(v_layer)
            dv.ellipse([WIN_CX - 24, WIN_CY - 44, WIN_CX + 24, WIN_CY + 4], fill=(16, 185, 129, int(235 * alpha)))
            dv.line([(WIN_CX - 10, WIN_CY - 20), (WIN_CX - 2, WIN_CY - 12), (WIN_CX + 10, WIN_CY - 28)], fill=(255, 255, 255, int(255 * alpha)), width=3)
            canvas.paste(v_layer, (0, 0), v_layer)

            t_sub = "3. Access Granted · Real Windows Hello identity confirmation"

    lt_alpha = alpha
    if t < 31.8:
        lt_alpha = alpha * ease_out_cubic((t - 31.5) / 0.3)
    elif t > 39.7:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 39.7) / 0.3))

    draw_lower_third(
        canvas,
        tag="APP LOCKER",
        title="PROTECT ACCESS",
        subtitle=t_sub,
        alpha=lt_alpha
    )

# ── Scene 7: SleepGuard (40.0s – 52.5s) ───────────────────────────────────────
def render_scene_sleepguard(canvas: Image.Image, t: float, alpha: float):
    # Phase 1: 40.0s – 43.5s: SleepGuard Armed (30m threshold clearly established)
    if t < 43.5:
        part_p = clamp((t - 40.0) / 3.5)
        scale = 1.01 + 0.025 * smoothstep(part_p)
        render_window_fast(canvas, "sleepguard", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        t_tag = "SLEEPGUARD"
        t_title = "SLEEPGUARD"
        t_sub = "1. Armed & Monitoring · Shutdown after 30 minutes of uninterrupted inactivity"

    # Phase 2: 43.5s – 48.0s: 60-Second Warning popup countdown
    elif t < 48.0:
        sub_p = clamp((t - 43.5) / 4.5)
        render_window_fast(canvas, "sleepguard", WIN_CX, WIN_CY, scale=1.02, alpha=alpha)

        scale = lerp(1.05, 1.10, ease_out_cubic(min(1.0, sub_p * 1.5)))
        if t < 45.0:
            sg_name = "sg_60"  # 01:00
        elif t < 46.5:
            sg_name = "sg_59"  # 00:59
        else:
            sg_name = "sg_58"  # 00:58
        render_window_fast(canvas, sg_name, WIN_CX, WIN_CY, scale=scale, alpha=alpha)

        t_tag = "SLEEPGUARD"
        t_title = "60-SECOND CANCELLATION WARNING"
        t_sub = "2. Inactivity Reached · 60-second grace cancellation countdown before action"

    # Phase 3: 48.0s – 52.5s: Cancel click -> Power Action Aborted Safely
    else:
        render_window_fast(canvas, "sleepguard", WIN_CX, WIN_CY, scale=1.02, alpha=alpha)

        if t < 48.5:
            render_window_fast(canvas, "sg_58", WIN_CX, WIN_CY, scale=1.10, alpha=alpha)
            cur_p = (t - 48.0) / 0.5
            cur_x = lerp(700, 620, ease_in_out_cubic(cur_p))
            cur_y = lerp(450, 525, ease_in_out_cubic(cur_p))
            clicking = (cur_p > 0.6)
            click_prog = (cur_p - 0.6) / 0.4 if clicking else 0.0
            draw_cursor(canvas, cur_x, cur_y, click_progress=click_prog, alpha=alpha)
        else:
            render_window_fast(canvas, "sg_cancelled", WIN_CX, WIN_CY, scale=1.10, alpha=alpha)
            draw_cursor(canvas, 620, 525, click_progress=0.0, alpha=alpha * clamp(1.0 - (t - 48.5) / 1.5))

        t_tag = "SLEEPGUARD"
        t_title = "POWER ACTION ABORTED"
        t_sub = "3. Safe Resumption · User activity or Cancel immediately aborts action"

    lt_alpha = alpha
    if t < 40.3:
        lt_alpha = alpha * ease_out_cubic((t - 40.0) / 0.3)
    elif t > 52.2:
        lt_alpha = alpha * (1.0 - ease_in_cubic((t - 52.2) / 0.3))

    draw_lower_third(
        canvas,
        tag=t_tag,
        title=t_title,
        subtitle=t_sub,
        alpha=lt_alpha
    )

# ── Scene 8: Final Notch Application Hero Shot (52.5s – 60.0s) ────────────────
def render_scene_final(canvas: Image.Image, t: float, alpha: float):
    p = clamp((t - 52.5) / 7.5)
    scale = 1.01 + 0.035 * smoothstep(p)
    render_window_fast(canvas, "home", WIN_CX, WIN_CY, scale=scale, alpha=alpha)

    # Clean centered final commercial tagline card
    card_w = 720
    card_h = 94
    card = Image.new("RGBA", (card_w, card_h), (10, 14, 22, int(240 * alpha)))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=16, outline=(255, 255, 255, int(35 * alpha)), width=1)

    d.ellipse([24, 18, 32, 26], fill=(16, 185, 129, int(255 * alpha)))
    font_brand = get_font(13, bold=True)
    d.text((38, 15), "NOTCH", font=font_brand, fill=(255, 255, 255, int(255 * alpha)))

    font_tag = get_font(19, bold=True)
    d.text((24, 38), "Control your machine. Not the other way around.", font=font_tag, fill=(255, 255, 255, int(255 * alpha)))

    font_sub = get_font(12)
    meta_txt = "WINDOWS 10 & 11  ·  100% LOCAL-FIRST  ·  ZERO CLOUD SYNC  ·  v3.1.6"
    d.text((24, 66), meta_txt, font=font_sub, fill=(160, 175, 195, int(230 * alpha)))

    c_mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(c_mask).rounded_rectangle([0, 0, card_w, card_h], radius=16, fill=int(255 * alpha))
    canvas.paste(card, ((WIDTH - card_w) // 2, 914), c_mask)

    # Gentle fade to black during final 0.8s
    if t > 59.2:
        fade_black = (t - 59.2) / 0.8
        black_curtain = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, int(255 * fade_black)))
        canvas.paste(black_curtain, (0, 0), black_curtain)

# ── Master Frame Synthesizer with Synchronized Transitions ────────────────────
def render_frame(frame_idx: int) -> np.ndarray:
    t = frame_idx / float(FPS)
    canvas = BASE_WALLPAPER.copy()

    # Draw Windows 11 taskbar once Home is active
    if t >= 0.8:
        tb_alpha = clamp((t - 0.8) / 0.4)
        draw_taskbar(canvas, t)

    # 1. Home Dashboard (0.0s – 4.5s)
    if t < 4.5:
        render_scene_home(canvas, t, 1.0)

    # 2. Usage Trends (4.5s – 8.0s: match cut on Section B2 downbeat)
    elif t < 8.0:
        render_scene_usage(canvas, t, 1.0)

    # 3. Intelligent Insights (8.0s – 11.5s: match cut on Section B2/B3 downbeat)
    elif t < 11.5:
        render_scene_insights(canvas, t, 1.0)

    # 4. Focus Mode — Hero Feature (11.5s – 23.5s: match cut on downbeat)
    elif t < 23.5:
        render_scene_focus(canvas, t, 1.0)

    # 5. App Timer (23.5s – 31.5s: match cut on downbeat)
    elif t < 31.5:
        render_scene_timer(canvas, t, 1.0)

    # 6. App Locker (31.5s – 40.0s: match cut on downbeat)
    elif t < 40.0:
        render_scene_app_locker(canvas, t, 1.0)

    # 7. SleepGuard (40.0s – 52.5s: match cut on downbeat)
    elif t < 52.5:
        if t > 52.2:
            p = (t - 52.2) / 0.3
            render_scene_sleepguard(canvas, t, 1.0 - smoothstep(p))
            render_scene_final(canvas, t, smoothstep(p))
        else:
            render_scene_sleepguard(canvas, t, 1.0)

    # 8. Final Hero Shot (52.5s – 60.0s: Section E resolution & commercial card)
    else:
        render_scene_final(canvas, t, 1.0)

    return np.array(canvas.convert("RGB"))

# ── Master 60-Second Soundtrack Extended From Reference Music ─────────────────
print("[2/5] Synthesizing synchronized 60-second reference soundtrack with sound cues...", flush=True)

def synthesize_audio() -> Path:
    audio_path = BASE_DIR / "notch_master_soundtrack.wav"
    sr = AUDIO_SAMPLE_RATE

    if not REF_AUDIO_PATH.exists():
        raise FileNotFoundError(f"Missing reference audio: {REF_AUDIO_PATH}")

    with wave.open(str(REF_AUDIO_PATH), "rb") as wf:
        orig = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).reshape(-1, 2)
    orig_f = orig.astype(np.float32) / 32768.0

    def sec(s): return int(s * sr)

    # Beat-matched musical sections (106 BPM grid, exact zero-crossings)
    A = orig_f[sec(0.0) : sec(3.598)]      # Ambient intro
    B1 = orig_f[sec(3.598) : sec(8.130)]   # Main groove 1
    B2 = orig_f[sec(8.130) : sec(12.654)]  # Main groove 2
    B3 = orig_f[sec(12.654) : sec(17.177)] # Groove with high percs
    C = orig_f[sec(17.177) : sec(21.712)]  # Breakdown & tension riser
    D = orig_f[sec(21.712) : sec(26.243)]  # Heavy climax drop
    E = orig_f[sec(26.243) : sec(30.720)]  # Resolution & reverb tail

    # Progression engineered for dynamic narrative arc across 60.0 seconds:
    # 0.0 - 4.5s  : B1 (Groove 1 kicks in with Home dashboard)
    # 4.5 - 9.0s  : B2 (Groove 2 driving Usage and Insights)
    # 9.0 - 13.5s : B3 (Groove 3 with percs for Insights -> Focus Setup)
    # 13.5 - 18.0s: C  (Tension Riser for Focus Active session)
    # 18.0 - 22.5s: D  (HEAVY CLIMAX DROP: Distracting app blocked!)
    # 22.5 - 27.0s: B2 (Groove for App Timer limit slider)
    # 27.0 - 31.5s: B3 (Groove for App Timer active budget card)
    # 31.5 - 36.0s: C  (Tension Riser for App Locker & Windows Hello scan)
    # 36.0 - 40.5s: D  (CLIMAX HIT: Biometric Verified checkmark!)
    # 40.5 - 45.0s: B1 (Groove for SleepGuard armed & monitoring)
    # 45.0 - 49.5s: B2 (Groove for 60s warning countdown)
    # 49.5 - 53.5s: C  (Transition Riser for Power Action Aborted)
    # 53.5 - 60.0s: E  (Outro resolution chord and decaying reverb tail)
    sections = [B1, B2, B3, C, D, B2, B3, C, D, B1, B2, C, E, E[:sec(2.2)]]

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

    # Fade out last 0.8s for smooth final resolution
    fade_len = int(0.8 * sr)
    extended[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)[:, None]

    # Add restrained, subtle UI audio cues synchronized to key moments
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

    add_click(extended, 4.2)                    # Sidebar Usage tab click on downbeat
    add_click(extended, 7.7)                    # Sidebar Insights tab click on downbeat
    add_click(extended, 11.2)                   # Sidebar Focus tab click on downbeat
    add_click(extended, 14.2)                   # Start Focus Session button click
    add_chime(extended, 14.5, 523.25, 783.99)   # Focus activation chime
    add_chime(extended, 18.0, 440.0, 659.25)    # Distraction blocked alert (on Section D heavy drop!)
    add_click(extended, 26.5)                   # App timer limit save click
    add_click(extended, 33.8)                   # App locker locked app launch click
    add_chime(extended, 36.5, 880.0, 1318.5)    # Windows Hello biometric verified double-chime (on Section D hit!)
    add_chime(extended, 43.5, 587.33, 880.0)    # SleepGuard 60s warning tone
    add_click(extended, 48.2)                   # SleepGuard Cancel click
    add_chime(extended, 48.5, 659.25, 987.77)   # Power action safely aborted chime

    # Limiter & Normalization
    peak = np.max(np.abs(extended))
    if peak > 0.95:
        extended = extended * (0.95 / peak)

    audio_data = (extended * 32767).astype(np.int16)
    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_data.tobytes())

    print(f"  Synthesized master 60s soundtrack ({audio_path.stat().st_size / 1024 / 1024:.2f} MB)", flush=True)
    return audio_path

# ── Main Video Encoding Orchestrator ──────────────────────────────────────────
def main():
    start_time = time.time()
    audio_file = synthesize_audio()

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_raw_video = BASE_DIR / "temp_notch_video.mp4"
    if temp_raw_video.exists():
        temp_raw_video.unlink()
    if OUTPUT_VIDEO.exists():
        OUTPUT_VIDEO.unlink()

    print(f"[3/5] Encoding {TOTAL_FRAMES} frames ({TOTAL_SECONDS:.1f}s @ {FPS}fps) at {WIDTH}x{HEIGHT} Full HD...", flush=True)
    
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

    # DEVNULL prevents OS pipe buffer deadlock
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

    # Step 4: Multiplex Audio and Video into Final Production MP4
    print("[4/5] Multiplexing H.264 video with synchronized master AAC audio...", flush=True)
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
    print(f"[SUCCESS] Notch Final NYC Showcase Video created successfully!", flush=True)
    print(f"  Output File: {OUTPUT_VIDEO.name}", flush=True)
    print(f"  Full Path:   {OUTPUT_VIDEO}", flush=True)
    print(f"  Resolution:  {WIDTH}x{HEIGHT} (1080p Full HD)", flush=True)
    print(f"  Duration:    {TOTAL_SECONDS:.1f} seconds ({TOTAL_FRAMES} frames @ {FPS} fps)", flush=True)
    print(f"  File Size:   {file_size_mb:.2f} MB", flush=True)
    print(f"  Total Render Time: {total_time:.1f} seconds", flush=True)
    print(f"==========================================================================", flush=True)

if __name__ == "__main__":
    main()
