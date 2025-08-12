#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Colors
BG = (15, 18, 20)        # #0F1214
BRAND = (91, 209, 116)   # #5BD174
ACCENT = (42, 161, 152)  # #2AA198
TEXT = (11, 16, 13)      # dark text

out_dir = Path("assets/icon")
out_dir.mkdir(parents=True, exist_ok=True)

# Base size
SIZES = [256, 128, 64, 32, 16]
images = []
for size in SIZES:
    img = Image.new("RGBA", (size, size), BG + (255,))
    d = ImageDraw.Draw(img)
    # Rounded badge background
    pad = max(4, size // 16)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size // 6, fill=BG)
    # Simple leaf-like shape
    # Outer ellipse
    d.ellipse([size*0.28, size*0.20, size*0.78, size*0.72], fill=BRAND)
    # Vein (a subtle V)
    d.line([size*0.40, size*0.35, size*0.50, size*0.60], fill=ACCENT, width=max(2, size//32))
    d.line([size*0.60, size*0.35, size*0.50, size*0.60], fill=ACCENT, width=max(2, size//32))
    images.append(img)

# Save ICO with multiple sizes
ico_path = out_dir / "verdant.ico"
images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in SIZES])
print(f"✅ Generated {ico_path}") 