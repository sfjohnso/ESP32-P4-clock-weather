# Generates img_app_clock.c (112x112 ARGB8888 LVGL image) and img_app_clock.png.
# Run with a normal Python that has Pillow: python gen_icon.py
import math
from PIL import Image, ImageDraw

S, N = 4, 112                      # supersample factor, final size
W = N * S
im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
navy, ring, tick, hand, coral = (24, 33, 56), (143, 163, 196), (200, 212, 232), (232, 238, 252), (255, 107, 107)

d.rounded_rectangle([0, 0, W - 1, W - 1], radius=26 * S, fill=navy)
c, R = W / 2, 38 * S
d.ellipse([c - R, c - R, c + R, c + R], outline=ring, width=3 * S)
for i in range(12):
    a = math.radians(i * 30)
    r0, r1 = R - (9 if i % 3 == 0 else 6) * S, R - 3 * S
    d.line([c + r0 * math.sin(a), c - r0 * math.cos(a), c + r1 * math.sin(a), c - r1 * math.cos(a)],
           fill=tick, width=(3 if i % 3 == 0 else 2) * S)

def hand(deg, length, width, color):
    a = math.radians(deg)
    x, y = c + length * math.sin(a), c - length * math.cos(a)
    d.line([c, c, x, y], fill=color, width=width * S)
    d.ellipse([x - width * S / 2, y - width * S / 2, x + width * S / 2, y + width * S / 2], fill=color)

hand(300, 20 * S, 5, (232, 238, 252))                                       # hour hand ~10
hand(60, 29 * S, 4, (232, 238, 252))                                       # minute hand ~2
hand(180, 31 * S, 2, coral)                                                # second hand
d.ellipse([c - 4 * S, c - 4 * S, c + 4 * S, c + 4 * S], fill=coral)

im = im.resize((N, N), Image.LANCZOS)
im.save("img_app_clock.png")

px = bytearray()
for r, g, b, a in im.getdata():
    px += bytes((b, g, r, a))                    # LVGL ARGB8888 is B,G,R,A in memory
rows = [", ".join(f"0x{v:02x}" for v in px[i:i + 16]) for i in range(0, len(px), 16)]
with open("img_app_clock.c", "w") as f:
    f.write('''#include "lvgl.h"

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST uint8_t img_app_clock_map[] = {
  ''' + ",\n  ".join(rows) + '''
};

const lv_image_dsc_t img_app_clock = {
  .header.cf = LV_COLOR_FORMAT_ARGB8888,
  .header.magic = LV_IMAGE_HEADER_MAGIC,
  .header.w = 112,
  .header.h = 112,
  .data_size = 112 * 112 * 4,
  .data = img_app_clock_map,
};
''')
print("ok", len(px))
