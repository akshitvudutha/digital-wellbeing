# Programmatic branding generator for Digital Wellbeing
import os
from pathlib import Path
from PIL import Image, ImageDraw

def generate_branding():
    icon_dir = Path("assets/icons")
    icon_dir.mkdir(parents=True, exist_ok=True)

    svg_path = icon_dir / "app_icon.svg"
    png_path = icon_dir / "app_icon.png"
    ico_path = icon_dir / "app_icon.ico"

    # 1. Generate SVG Vector Icon (Squircle background with intersecting balance rings)
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#02d0fd;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#0078d4;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#7c3aed;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <!-- Rounded Squircle Base -->
  <rect x="44" y="44" width="424" height="424" rx="110" fill="url(#glassGrad)" filter="url(#shadow)" />
  
  <!-- Left Intersecting Glass Loop -->
  <ellipse cx="206" cy="256" rx="90" ry="90" fill="none" stroke="#ffffff" stroke-width="16" stroke-opacity="0.8" />
  
  <!-- Right Intersecting Glass Loop -->
  <ellipse cx="306" cy="256" rx="90" ry="90" fill="none" stroke="#ffffff" stroke-width="16" stroke-opacity="0.8" />
  
  <!-- Center Core Glow -->
  <circle cx="256" cy="256" r="30" fill="#ffffff" fill-opacity="0.9" />
</svg>
"""
    svg_path.write_text(svg_content, encoding="utf-8")
    print(f"[OK] Generated Vector SVG icon at {svg_path}")

    # 2. Draw Premium Raster PNG Icon using Pillow (Squircle + Masked Gradients)
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Helper function to interpolate a 3-stop gradient colors
    def get_gradient_color(y, height):
        # Stop 0 (Cyan): #02d0fd -> (2, 208, 253)
        # Stop 1 (Blue): #0078d4 -> (0, 120, 212)
        # Stop 2 (Violet): #7c3aed -> (124, 58, 237)
        ratio = y / height
        if ratio < 0.5:
            local_ratio = ratio * 2.0
            r = int(2 + (0 - 2) * local_ratio)
            g = int(208 + (120 - 208) * local_ratio)
            b = int(253 + (212 - 253) * local_ratio)
        else:
            local_ratio = (ratio - 0.5) * 2.0
            r = int(0 + (124 - 0) * local_ratio)
            g = int(120 + (58 - 120) * local_ratio)
            b = int(212 + (237 - 212) * local_ratio)
        return (r, g, b, 255)

    # Make squircle mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([44, 44, 468, 468], radius=110, fill=255)

    # Generate full gradient background
    grad_img = Image.new("RGBA", (size, size))
    grad_draw = ImageDraw.Draw(grad_img)
    for y in range(size):
        color = get_gradient_color(y, size)
        grad_draw.line((0, y, size, y), fill=color)

    # Paste gradient onto base image using the squircle mask
    img.paste(grad_img, (0, 0), mask)

    # Draw transparent rings and core glow on top
    draw = ImageDraw.Draw(img)
    # Left ring
    draw.ellipse(
        [206 - 90, 256 - 90, 206 + 90, 256 + 90],
        outline=(255, 255, 255, 204),
        width=16
    )
    # Right ring
    draw.ellipse(
        [306 - 90, 256 - 90, 306 + 90, 256 + 90],
        outline=(255, 255, 255, 204),
        width=16
    )
    # Center glow
    draw.ellipse(
        [256 - 30, 256 - 30, 256 + 30, 256 + 30],
        fill=(255, 255, 255, 230)
    )

    img.save(png_path, "PNG")
    print(f"[OK] Generated high-res PNG icon at {png_path}")

    # 3. Save as Windows Multi-Resolution ICO
    img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"[OK] Generated multi-resolution ICO icon at {ico_path}")
    print("[SUCCESS] All custom branding assets created successfully.")

if __name__ == "__main__":
    generate_branding()
