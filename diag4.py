import requests, io
from PIL import Image

url = "https://ssr.resume.tools/to-image/test123test123test123ab-2.jpeg?cache=2026-01-01T00:00Z&size=2000"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

img = Image.open(io.BytesIO(r.content))
rgb = img.convert("RGB")

extrema = rgb.getextrema()
print("Extrema:", extrema)
min_r, min_g, min_b = extrema[0][0], extrema[1][0], extrema[2][0]
print(f"Min RGB: {min_r}, {min_g}, {min_b}")
is_blank = min_r > 200 and min_g > 200 and min_b > 200
print(f"Is blank placeholder? {is_blank}")

# Let's also test a real image (just a random image from web)
r2 = requests.get("https://via.placeholder.com/150/000000/FFFFFF/?text=Real+Text")
img2 = Image.open(io.BytesIO(r2.content)).convert("RGB")
extrema2 = img2.getextrema()
print("\nReal image extrema:", extrema2)
is_blank2 = extrema2[0][0] > 200 and extrema2[1][0] > 200 and extrema2[2][0] > 200
print(f"Is blank placeholder? {is_blank2}")
