import time
from PIL import ImageGrab

def take_desktop_screenshot(output_path):
    print("Taking full desktop screenshot...")
    img = ImageGrab.grab(all_screens=True)
    img.save(output_path)
    print(f"Desktop screenshot saved to {output_path}")
    return True

if __name__ == "__main__":
    take_desktop_screenshot(r"C:\Users\akshi\.gemini\antigravity-ide\brain\08810c96-653f-4f09-8c2b-87d4285f5d28\scratch\live_desktop.png")
