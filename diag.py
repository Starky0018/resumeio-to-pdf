"""Run with: .venv\Scripts\python.exe diag.py YOUR_TOKEN_HERE"""
import sys, requests, io
from PIL import Image

token = sys.argv[1] if len(sys.argv) > 1 else "test123test123test123ab"
print(f"Token: {token}\n")

for page in range(1, 6):
    url = f"https://ssr.resume.tools/to-image/{token}-{page}.jpeg?cache=2026-01-01T00:00Z&size=2000"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    ct = r.headers.get("Content-Type", "?")
    size = len(r.content)
    print(f"Page {page}: status={r.status_code} | size={size:>8} bytes | type={ct}")
    if r.status_code == 200 and size > 100:
        try:
            img = Image.open(io.BytesIO(r.content))
            rgb = img.convert("RGB")
            # Sample 25 pixels
            w, h = rgb.size
            pixels = [rgb.getpixel((x, y)) for x in range(0, w, w//5) for y in range(0, h, h//5)]
            avg = tuple(sum(c)//len(pixels) for c in zip(*pixels))
            variance = sum(abs(c - 255) for c in avg)
            print(f"         img={img.format} {img.mode} {img.size} | avg_rgb={avg} | off_white={variance}")
            print(f"         VERDICT: {'BLANK placeholder' if variance < 15 else 'REAL content'}")
        except Exception as e:
            print(f"         Not an image: {e}")
    print()
