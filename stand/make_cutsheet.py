"""Full-size cut sheet (US Letter PDF) for the stand base: top, front and side views at 1:1, a 4:1 section,
a dimension table and a build order. Numbers come from make_stand.py. SVG (1 unit = 1 mm) -> Inkscape PDF.

Difference from the STEP: the rabbet wall is vertical (the STEP leans it back 14.43 deg = an undercut that a
router cannot cut). Part frame: x across, y depth (0 = rear edge, 37 = front edge on the bottom face),
z up (0 = underside).
"""
import math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "make_stand.py"), encoding="utf-8").read()
g = {"__file__": os.path.join(HERE, "make_stand.py")}
exec(src[:src.index("# ------------------------------------------------------------------ SVG helpers")], g)

W, R, STOCK, BASE, TH, DEG = g["W"], g["R"], g["STOCK"], g["BASE"], g["TH"], g["DEG"]
S_REAR, S_FRONT = g["S_REAR"], g["S_FRONT"]
DEPTH = S_FRONT - S_REAR
WALL_Y = g["LIP_FLOOR"][0] - S_REAR            # vertical rabbet wall, from the rear edge
TAN = math.tan(TH)
TOP_Y = DEPTH - STOCK * TAN                    # top edge of the bevel, from the rear edge
HOLE_D, HOLE_Y, HX, ROD_LEN = g["HOLE_D"], g["DW_CS"] - S_REAR, list(g["FEET_X"]), g["DW_LEN"]
WALL_U = DEPTH - WALL_Y                        # same, measured from the front edge
TOP_U = STOCK * TAN
assert WALL_U > TOP_U + 2.5

# the unit must clear a vertical wall standing where the leaning wall started
cs, ch = g["world"](0, 0)
print("unit front-bottom corner s=%.2f h=%.2f ; wall at s=%.2f" % (cs, ch, g["LIP_FLOOR"][0]))
assert ch >= 0 and cs < g["LIP_FLOOR"][0] - 0.3

PW, PH = 215.9, 279.4
out = []


def f(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def add(s):
    out.append(s)


def line(x1, y1, x2, y2, w=0.15, col="#000", dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    add('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s/>' % (f(x1), f(y1), f(x2), f(y2), col, w, d))


def poly(pts, fill="none", stroke="#000", w=0.4, dash=None, close=True):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    tag = "polygon" if close else "polyline"
    add('<%s points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s/>'
        % (tag, " ".join("%s,%s" % (f(x), f(y)) for x, y in pts), fill, stroke, w, d))


def text(x, y, s, size=2.8, anchor="start", rot=0, bold=False, col="#000"):
    t = ' transform="rotate(%s %s %s)"' % (rot, f(x), f(y)) if rot else ""
    s = s.replace("&", "&amp;")
    add('<text x="%s" y="%s" font-family="Arial, Helvetica, sans-serif" font-size="%s" text-anchor="%s" fill="%s"%s%s>%s</text>'
        % (f(x), f(y), size, anchor, col, ' font-weight="bold"' if bold else "", t, s))


def arrow(x, y, dx, dy, ln=2.4):
    """tip at (x, y); the body extends from the tip along (dx, dy)"""
    px, py = -dy, dx
    hw = 0.65
    poly([(x, y), (x + dx * ln + px * hw, y + dy * ln + py * hw), (x + dx * ln - px * hw, y + dy * ln - py * hw)],
         fill="#000", stroke="none", w=0)


def hdim(x1, x2, y, label, yf1, yf2=None, size=2.8):
    yf2 = yf1 if yf2 is None else yf2
    s = 1 if y > yf1 else -1
    line(x1, yf1 + s * 0.8, x1, y + s * 1.5)
    line(x2, yf2 + s * 0.8, x2, y + s * 1.5)
    line(x1, y, x2, y)
    a = min(2.4, abs(x2 - x1) / 2.8)
    arrow(x1, y, 1, 0, a)
    arrow(x2, y, -1, 0, a)
    text((x1 + x2) / 2, y - 0.9, label, size, "middle")


def vdim(y1, y2, x, label, xf, side=1, size=2.8, rot=False):
    s = 1 if x > xf else -1
    line(xf + s * 0.8, y1, x + s * 1.5, y1)
    line(xf + s * 0.8, y2, x + s * 1.5, y2)
    line(x, y1, x, y2)
    a = min(2.4, abs(y2 - y1) / 2.8)
    top, bot = min(y1, y2), max(y1, y2)
    arrow(x, top, 0, 1, a)
    arrow(x, bot, 0, -1, a)
    mid = (y1 + y2) / 2
    if rot:
        text(x + (3.2 if side > 0 else -0.9), mid, label, size, "middle", rot=-90)
    elif side > 0:
        text(x + 2.0, mid + 1.0, label, size, "start")
    else:
        text(x - 2.0, mid + 1.0, label, size, "end")


def dot(x, y):
    add('<circle cx="%s" cy="%s" r="0.55" fill="#000"/>' % (f(x), f(y)))


def rrect(x0, y0, w, h, r):
    return ("M%s,%s H%s A%s,%s 0 0 1 %s,%s V%s A%s,%s 0 0 1 %s,%s H%s A%s,%s 0 0 1 %s,%s V%s A%s,%s 0 0 1 %s,%s Z"
            % (f(x0 + r), f(y0), f(x0 + w - r), f(r), f(r), f(x0 + w), f(y0 + r), f(y0 + h - r), f(r), f(r), f(x0 + w - r),
               f(y0 + h), f(x0 + r), f(r), f(r), f(x0), f(y0 + h - r), f(y0 + r), f(r), f(r), f(x0 + r), f(y0)))


def cl(x1, y1, x2, y2):
    line(x1, y1, x2, y2, 0.15, "#000", "4 1 0.8 1")


# ---------------------------------------------------------------------------------------------- page
add('<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" viewBox="0 0 %s %s">' % (PW, PH, PW, PH))
add('<rect width="%s" height="%s" fill="#fff"/>' % (PW, PH))
text(12, 11, "ESP32-P4 DESK STAND \u2013 BASE, FULL SIZE", 5.2, bold=True)
text(12, 16.5, "Print at 100% (Actual size, not \u201cFit to page\u201d). Views are 1:1 except the 4:1 section. Dimensions in mm; inches in the table.", 2.6)
line(12, 23, 112, 23, 0.3)
for i in range(11):
    line(12 + 10 * i, 23, 12 + 10 * i, 23 - (2.2 if i % 5 == 0 else 1.2), 0.3)
text(12, 27, "0", 2.4, "middle")
text(62, 27, "50", 2.4, "middle")
text(112, 27, "100", 2.4, "middle")
text(120, 24, "Scale check: this bar must measure 100 mm (3.937 in).", 2.6)

# ------------------------------------------------------------------------------------------- top view
Tx0, Ty0 = 36.0, 42.0
cyc = DEPTH - R


def arc_left(ya, yb, n=30):
    a0 = math.asin(min(1.0, (ya - cyc) / R))
    a1 = math.asin(min(1.0, (yb - cyc) / R))
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((R - R * math.cos(a), cyc + R * math.sin(a)))
    return pts


def mirror(pts):
    return [(W - x, y) for x, y in pts]


def arc_x(y):
    return R - math.sqrt(max(0.0, R * R - (y - cyc) ** 2))


def T(pts):
    return [(Tx0 + x, Ty0 + y) for x, y in pts]


xw, xt = arc_x(WALL_Y), arc_x(TOP_Y)
text(12, 33, "TOP VIEW", 3.6, bold=True)
add('<path d="%s" fill="#f1f1f1"/>' % rrect(Tx0, Ty0, W, DEPTH, R))
poly(T([(xw, WALL_Y)] + mirror(arc_left(WALL_Y, TOP_Y)) + arc_left(TOP_Y, WALL_Y)), "#fff", "none", 0)
poly(T(arc_left(TOP_Y, DEPTH) + mirror(arc_left(DEPTH, TOP_Y))), "#cfcfcf", "none", 0)
line(Tx0 + xw, Ty0 + WALL_Y, Tx0 + W - xw, Ty0 + WALL_Y, 0.3)
line(Tx0 + xt, Ty0 + TOP_Y, Tx0 + W - xt, Ty0 + TOP_Y, 0.3)
add('<path d="%s" fill="none" stroke="#000" stroke-width="0.45"/>' % rrect(Tx0, Ty0, W, DEPTH, R))
for hx in HX:
    add('<circle cx="%s" cy="%s" r="%s" fill="#fff" stroke="#000" stroke-width="0.35"/>' % (f(Tx0 + hx), f(Ty0 + HOLE_Y), f(HOLE_D / 2)))
    cl(Tx0 + hx - 5.5, Ty0 + HOLE_Y, Tx0 + hx + 5.5, Ty0 + HOLE_Y)
    cl(Tx0 + hx, Ty0 + HOLE_Y - 5.5, Tx0 + hx, Ty0 + HOLE_Y + 5.5)
# labels inside the part
d45 = R * (1 - math.cos(math.pi / 4))
line(Tx0 + 17.5, Ty0 + 3.7, Tx0 + d45, Ty0 + d45, 0.15)
dot(Tx0 + d45, Ty0 + d45)
text(Tx0 + 18.5, Ty0 + 4.6, "R%.2f, all 4 plan corners" % R, 2.6)
text(Tx0 + 19, Ty0 + 11.2, "2 holes, dia %.2f (1/4 in), through" % HOLE_D, 2.6)
text(Tx0 + W / 2, Ty0 + 18.5, "RABBET FLOOR (open at rear and ends)", 2.6, "middle")
line(Tx0 + 24, Ty0 + 25.2, Tx0 + 24, Ty0 + (WALL_Y + TOP_Y) / 2 - 0.4, 0.15)
dot(Tx0 + 24, Ty0 + (WALL_Y + TOP_Y) / 2)
text(Tx0 + 21, Ty0 + 24.2, "lip top (flat)", 2.6)
line(Tx0 + 66, Ty0 + 25.2, Tx0 + 66, Ty0 + (TOP_Y + DEPTH) / 2 - 0.4, 0.15)
dot(Tx0 + 66, Ty0 + (TOP_Y + DEPTH) / 2)
text(Tx0 + 63, Ty0 + 24.2, "bevel face", 2.6)
# dimensions
hdim(Tx0, Tx0 + W, Ty0 - 4.5, "%.2f" % W, Ty0)
yb = Ty0 + DEPTH + 7
hdim(Tx0, Tx0 + HX[0], yb, "%.2f" % HX[0], Ty0 + DEPTH)
hdim(Tx0 + HX[0], Tx0 + HX[1], yb, "%.2f" % (HX[1] - HX[0]), Ty0 + HOLE_Y + 3.2)
hdim(Tx0 + HX[1], Tx0 + W, yb, "%.2f" % (W - HX[1]), Ty0 + DEPTH)
line(Tx0 + HX[0], Ty0 + HOLE_Y + 5.6, Tx0 + HX[0], yb + 1.5, 0.15)
line(Tx0 + HX[1], Ty0 + HOLE_Y + 5.6, Tx0 + HX[1], yb + 1.5, 0.15)
vdim(Ty0, Ty0 + HOLE_Y, Tx0 - 7, "%.2f" % HOLE_Y, Tx0, side=-1, rot=True)
xr = Tx0 + W + 7
vdim(Ty0, Ty0 + WALL_Y, xr, "%.2f" % WALL_Y, Tx0 + W)
vdim(Ty0 + WALL_Y, Ty0 + TOP_Y, xr, "%.2f" % (TOP_Y - WALL_Y), Tx0 + W, size=2.4)
vdim(Ty0 + TOP_Y, Ty0 + DEPTH, xr, "%.2f" % (DEPTH - TOP_Y), Tx0 + W, size=2.4)
vdim(Ty0, Ty0 + DEPTH, Tx0 + W + 30, "%.2f" % DEPTH, Tx0 + W + 7, rot=True)

# ------------------------------------------------------------------------------------------ front view
Fx0, Fy0 = Tx0, 98.0


def Fz(z):
    return Fy0 + STOCK - z


text(12, 94, "FRONT VIEW", 3.6, bold=True)
poly([(Fx0, Fz(0)), (Fx0 + W, Fz(0)), (Fx0 + W, Fz(STOCK)), (Fx0, Fz(STOCK))], "#fff", "#000", 0.45)
curve = []
for i in range(31):
    z = STOCK * i / 30
    curve.append((arc_x(DEPTH - z * TAN), z))
poly([(Fx0 + x, Fz(z)) for x, z in curve], "none", "#000", 0.3, close=False)
poly([(Fx0 + W - x, Fz(z)) for x, z in curve], "none", "#000", 0.3, close=False)
line(Fx0, Fz(BASE), Fx0 + W, Fz(BASE), 0.25, "#000", "2 1")
for hx in HX:
    for sx in (-1, 1):
        line(Fx0 + hx + sx * HOLE_D / 2, Fz(0), Fx0 + hx + sx * HOLE_D / 2, Fz(BASE), 0.25, "#000", "2 1")
text(Fx0 + W / 2, Fz(STOCK) - 2.0, "dashed = hidden (rabbet floor, rod holes)", 2.4, "middle")
vdim(Fz(BASE), Fz(0), Fx0 - 6, "%.2f" % BASE, Fx0, side=-1)
vdim(Fz(STOCK), Fz(BASE), Fx0 - 6, "%.2f" % (STOCK - BASE), Fx0, side=-1)
vdim(Fz(STOCK), Fz(0), Fx0 - 24, "%.2f" % STOCK, Fx0, side=-1, rot=True)

# -------------------------------------------------------------------------------------------- side view
Sx0 = 156.0


def prof(k, ox, oy):
    """side profile (front = left); oy = svg y of z = 0; scale k"""
    pts = [(0, 0), (DEPTH, 0), (DEPTH, BASE), (WALL_U, BASE), (WALL_U, STOCK), (TOP_U, STOCK)]
    return [(ox + k * u, oy - k * z) for u, z in pts]


text(Sx0 - 6, 94, "RIGHT SIDE VIEW", 3.6, bold=True)
poly(prof(1, Sx0, Fz(0)), "#fff", "#000", 0.45)
uh = DEPTH - HOLE_Y
for sx in (-1, 1):
    line(Sx0 + uh + sx * HOLE_D / 2, Fz(0), Sx0 + uh + sx * HOLE_D / 2, Fz(BASE), 0.25, "#000", "2 1")
text(Sx0, Fz(0) + 4.5, "FRONT", 2.4)
text(Sx0 + DEPTH, Fz(0) + 4.5, "REAR", 2.4, "end")
text(Sx0 + DEPTH / 2, Fz(0) + 9, "1:1 gauge for the bevel", 2.4, "middle")

# ----------------------------------------------------------------------------------------- 4:1 section
K = 4.0
X4, Y4 = 26.0, 140.0          # Y4 = svg y of the top face (z = STOCK)
Z0 = Y4 + K * STOCK           # svg y of z = 0
text(12, 120, "SIDE SECTION, 4:1 (to read dimensions; not full size)", 3.6, bold=True)
poly(prof(K, X4, Z0), "#f1f1f1", "#000", 0.5)
poly([(X4, Z0), (X4, Z0 - K * STOCK), (X4 + K * TOP_U, Z0 - K * STOCK)], "none", "#000", 0.25, "2 1")
for sx in (-1, 1):
    line(X4 + K * (uh + sx * HOLE_D / 2), Z0, X4 + K * (uh + sx * HOLE_D / 2), Z0 - K * BASE, 0.25, "#000", "2 1")
cl(X4 + K * uh, Z0 + 4, X4 + K * uh, Z0 - K * BASE - 3)
# angle at the bottom-front corner
rr = 30.0
a = [(X4 + rr * math.sin(TH * i / 20), Z0 - rr * math.cos(TH * i / 20)) for i in range(21)]
poly(a, "none", "#000", 0.25, close=False)
line(X4, Z0, X4, Z0 - K * STOCK - 2, 0.15, "#000", "4 1 0.8 1")
text(X4 - 3, Z0 - 31, "%.2f\u00b0" % DEG, 2.8, "end")
text(X4 - 3, Z0 - 27.5, "= blade tilt", 2.4, "end")
text(X4 - 3, Z0 - K * STOCK + 6, "waste", 2.4, "end")
# horizontal dimensions above
yd1, yd2 = Y4 - 6, Y4 - 14
hdim(X4, X4 + K * TOP_U, yd1, "%.2f" % TOP_U, Y4, size=2.6)
hdim(X4 + K * TOP_U, X4 + K * WALL_U, yd1, "%.2f" % (WALL_U - TOP_U), Y4, size=2.6)
hdim(X4 + K * WALL_U, X4 + K * DEPTH, yd2, "%.2f  rabbet width, from the rear edge" % WALL_Y, Y4 + K * (STOCK - BASE), Y4)
text(X4 + K * TOP_U / 2, yd1 - 4.4, "bevel setback", 2.2, "middle")
text(X4 + K * (TOP_U + WALL_U) / 2 + 6, yd1 - 4.4, "lip top", 2.2, "middle")
# vertical dimensions at the rear
xv = X4 + K * DEPTH + 9
vdim(Z0 - K * BASE, Z0, xv, "%.2f  floor thickness" % BASE, X4 + K * DEPTH)
vdim(Z0 - K * STOCK, Z0 - K * BASE, xv, "%.2f  rabbet depth" % (STOCK - BASE), X4 + K * WALL_U)
# horizontal dimensions below
yb1, yb2 = Z0 + 7, Z0 + 14
hdim(X4, X4 + K * DEPTH, yb1, "%.2f  depth of the bottom face" % DEPTH, Z0)
hdim(X4 + K * uh, X4 + K * DEPTH, yb2, "%.2f" % HOLE_Y, Z0 + 4)
text(X4 + K * uh - 2, yb2 - 0.9, "hole axis to rear edge", 2.6, "end")
text(X4 + K * uh + 8, Z0 - K * BASE - 4, "dia %.2f through" % HOLE_D, 2.4)

# ------------------------------------------------------------------------------------ table and notes
ty = 212.0
text(12, ty, "KEY DIMENSIONS", 3.4, bold=True)
text(78, ty, "mm", 2.6, "end", bold=True)
text(104, ty, "inches", 2.6, "end", bold=True)
I = lambda v: "%.3f" % (v / 25.4)
rows = [
    ("Blank length (left-right)", "%.2f" % W, I(W)),
    ("Blank depth (bottom face)", "%.2f" % DEPTH, I(DEPTH)),
    ("Thickness", "%.2f" % STOCK, "0.500"),
    ("Rabbet depth, from the top", "%.2f" % (STOCK - BASE), I(STOCK - BASE)),
    ("Floor thickness under the rabbet", "%.2f" % BASE, I(BASE)),
    ("Rabbet width, from the rear edge", "%.2f" % WALL_Y, I(WALL_Y)),
    ("Lip top, flat width", "%.2f" % (TOP_Y - WALL_Y), I(TOP_Y - WALL_Y)),
    ("Bevel setback at the top", "%.2f" % TOP_U, I(TOP_U)),
    ("Bevel angle from vertical", "%.2f deg" % DEG, ""),
    ("Hole x from the left edge", "%.2f / %.2f" % tuple(HX), "%s / %s" % (I(HX[0]), I(HX[1]))),
    ("Hole y from the rear edge", "%.2f" % HOLE_Y, I(HOLE_Y)),
    ("Hole diameter (use 1/4 in bit)", "%.2f" % HOLE_D, "0.250"),
    ("Plan corner radius", "%.2f" % R, I(R)),
    ("Rod: 1/4 in dia, length", "%.1f" % ROD_LEN, I(ROD_LEN)),
]
for i, (k, mm, inch) in enumerate(rows):
    y = ty + 5 + i * 3.7
    if i % 2 == 0:
        add('<rect x="11" y="%s" width="95" height="3.7" fill="#f1f1f1"/>' % f(y - 2.8))
    text(12, y, k, 2.6)
    text(78, y, mm, 2.6, "end")
    text(104, y, inch, 2.6, "end")

text(112, ty, "BUILD ORDER", 3.4, bold=True)
steps = [
    "1  Blank: 0.500 in stock, 95.11 long, 37.4 deep, ends square.",
    "2  Rabbet along the whole rear edge: 30.46 wide, 7.28 deep,",
    "    open at the rear and both ends, square inside corner.",
    "3  Bevel the front edge: blank flat, blade tilted 14.43 deg;",
    "    the cut must leave the bottom edge 37.00 from the rear edge.",
    "    Test on scrap; the side view is a 1:1 gauge for the angle.",
    "4  Drill the 2 holes, 1/4 in, through, at the marked centres.",
    "5  Round the 4 plan corners to R7.30 (top view = template).",
    "6  Last: ease all edges about 1 mm (1/32 in).",
    "7  Rods: 1/4 in brass or aluminium, 15.5 long (0.610 in),",
    "    chamfer the top. Epoxy into wood; HDPE will not glue:",
    "    drill 6.0 mm and press the rod in.",
]
for i, s in enumerate(steps):
    text(112, ty + 5 + i * 3.6, s, 2.6)
text(112, ty + 5 + 13 * 3.6, "The rabbet wall is vertical here so a router or dado can cut it.", 2.3, col="#444")
text(112, ty + 5 + 14 * 3.6 - 0.4, "The STEP file leans it back 14.43 deg (an undercut). Dimensions", 2.3, col="#444")
text(112, ty + 5 + 15 * 3.6 - 0.8, "were read by eye from Waveshare's drawing: test-fit the unit.", 2.3, col="#444")
add("</svg>")

svg = os.path.join(HERE, "ESP32-P4_stand_cutsheet.svg")
open(svg, "w", encoding="utf-8").write("\n".join(out))
pdf = os.path.join(HERE, "ESP32-P4_stand_cutsheet.pdf")
ink = r"C:\Program Files\Inkscape\bin\inkscape.exe"
subprocess.run([ink, svg, "--export-type=pdf", "--export-filename=" + pdf, "--export-text-to-path"], check=True)
print("wrote", pdf)
