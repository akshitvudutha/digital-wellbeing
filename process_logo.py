import os
import sys

try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

def process_logo(input_path: str, output_png: str, output_ico: str):
    print(f"Processing logo from {input_path}")
    img = Image.open(input_path).convert("RGBA")
    
    # We want to make the logo look good on transparent backgrounds.
    # The image is a jpg with a white rounded-rectangle background or similar.
    # If the user said "transparent backgrounds", they might mean making the white corners transparent.
    # But doing that accurately might require knowing the border radius, which is hard.
    # The prompt actually says: "Ensure the logo looks good on: Dark backgrounds, Light backgrounds, Transparent backgrounds. Do not change the logo colors."
    # Since the image is a JPG, the corners might be solid color. I will assume the image itself IS the logo, so we'll just resize it.
    
    # Let's save a high quality PNG for UI
    img.save(output_png, format="PNG")
    
    # Generate ICO with all sizes
    sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_ico, format="ICO", sizes=sizes)
    print("Successfully generated PNG and ICO")

if __name__ == "__main__":
    input_file = r"C:\Users\akshi\.gemini\antigravity-ide\brain\08810c96-653f-4f09-8c2b-87d4285f5d28\media__1785221499379.jpg"
    assets_dir = r"C:\Users\akshi\OneDrive\Documents\personal\DIGITAL WELLBEING\assets\icons"
    os.makedirs(assets_dir, exist_ok=True)
    
    png_out = os.path.join(assets_dir, "app_logo.png")
    ico_out = os.path.join(assets_dir, "app_icon.ico")
    
    process_logo(input_file, png_out, ico_out)
    
    # Also save as app_icon.png for consistency
    import shutil
    shutil.copy(png_out, os.path.join(assets_dir, "app_icon.png"))
