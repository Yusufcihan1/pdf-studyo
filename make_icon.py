"""Uygulama simgesi: çivit yuvarlak kare üstünde beyaz belge ve kıvılcım."""
from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((40, 40, S - 40, S - 40), radius=220, fill=(79, 70, 229, 255))
# belge
x0, y0, x1, y1, fold = 300, 200, 724, 824, 150
d.polygon([(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)], fill="white")
d.polygon([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=(199, 203, 245, 255))
for i, w in enumerate((300, 300, 220)):
    d.rounded_rectangle((x0 + 62, 460 + i * 80, x0 + 62 + w, 490 + i * 80), radius=15, fill=(199, 203, 245, 255))
# kıvılcım
cx, cy, r = 724, 690, 150
pts = [(cx, cy - r), (cx + r * .28, cy - r * .28), (cx + r, cy), (cx + r * .28, cy + r * .28), (cx, cy + r),
       (cx - r * .28, cy + r * .28), (cx - r, cy), (cx - r * .28, cy - r * .28)]
d.ellipse((cx - r * 1.05, cy - r * 1.05, cx + r * 1.05, cy + r * 1.05), fill=(79, 70, 229, 255))
d.polygon(pts, fill=(250, 204, 21, 255))
img.save("app/static/icon.png", sizes=[(256, 256)]) if False else img.resize((256, 256), Image.LANCZOS).save("app/static/icon.png")
img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.resize((256, 256), Image.LANCZOS).save("icon.png")
