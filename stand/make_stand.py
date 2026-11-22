# -*- coding: utf-8 -*-
"""Concept drawing of a desk stand for the Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5 (landscape).

Writes ESP32-P4_stand_concept.svg next to this script. All lengths in mm.
Device numbers come from the 'Dimensions' drawing on docs.waveshare.com (see the notes in the sheet).
"""
import math
from pathlib import Path

OUT = Path(__file__).with_name("ESP32-P4_stand_concept.svg")

# ------------------------------------------------------------------ device (Waveshare drawing)
W, H, R = 95.11, 63.67, 7.30               # outline and corner radius (front view, landscape)
TF, TR, TFEET = 5.40, 13.50, 14.10          # front module thickness, thickness to rear face, with feet
INS_TB = (63.67 - 59.50) / 2                # rear housing inset top/bottom  (2.085)
INS_LR = (95.11 - 83.20) / 2                # rear housing inset left/right  (5.955)
ACT_W, ACT_H, ACT_RIGHT, ACT_TOP = 73.44, 48.96, 10.84, 7.34
ACT_LEFT = W - ACT_W - ACT_RIGHT
ACT_BOT = H - ACT_H - ACT_TOP
FEET_X = (11.55, W - 11.56)                 # rubber feet, from the left edge of the unit
FEET_Y = (7.59, 7.59 + 48.50)               # from the bottom edge
FOOT_D = 6.0                                # foot diameter: assumed, not on the drawing
TH = math.atan2(INS_TB, TR - TF)            # lean back so both rear-bottom edges rest on the floor
sT, cT = math.sin(TH), math.cos(TH)
DEG = math.degrees(TH)


def world(y, z):
    """Device (y up from its bottom edge, z toward the rear) -> floor frame (s toward the viewer, h up).
    Origin: the housing's rear-bottom edge B (y = INS_TB, z = TR)."""
    dy, dz = y - INS_TB, z - TR
    return (-dy * sT - dz * cT, dy * cT - dz * sT)


# ------------------------------------------------------------------ stand (design choices)
CL = 0.50                      # clearance on every side: the unit drops in freely
TS = 0.0                       # no side rails: the stand is exactly as wide as the unit
STOCK = 12.7                   # 0.500 in HDPE plate, CNC machined; the lip is the uncut top of the plate
EDGE_R = 1.0                   # radius on every edge of the outline
WP = W                         # pocket width (= the unit)
WS = W                         # overall width
S_REAR, S_FRONT = -16.0, 21.0  # base extent behind / in front of edge B (floor frame)
LIP_UP = 6.0                   # lip height measured up the bezel (screen starts 7.37 above the bottom edge)
DW_D, HOLE_D, DW_GAP = 6.35, 6.30, 0.5   # 1/4 in rod, press-fit hole, gap to the foot
RF = R + CL                    # pocket fillet radius (follows the unit's corner rounding)

# lip geometry (floor frame)
nF = (cT, sT)                  # screen normal (toward the viewer)
up = (-sT, cT)                 # up the unit's face
Fp = (world(0, 0)[0] + CL * nF[0], world(0, 0)[1] + CL * nF[1])
t0 = -Fp[1] / cT
LIP_FLOOR = (Fp[0] + t0 * up[0], 0.0)
LIP_TOP_IN = (Fp[0] + LIP_UP * up[0], Fp[1] + LIP_UP * up[1])
BASE = STOCK - LIP_TOP_IN[1]      # plate below the pocket floor
DW_EMBED = BASE                  # through holes: the rod is flush with the underside
S_TOP = S_FRONT - STOCK * math.tan(TH)   # front face bevelled to the screen angle: top edge of the lip
S_FLR = S_FRONT - BASE * math.tan(TH)    # where the bevelled face crosses the floor level
assert S_TOP - LIP_TOP_IN[0] > 3.0
# the unit's front-bottom corner must sit beyond the concave 1 mm fillet at the lip base
_tan = EDGE_R / math.tan((math.pi / 2 - TH) / 2)
_tcorner = (world(0, 0)[1] + CL * sT) / cT
assert _tcorner > _tan, (_tcorner, _tan)
# dowels (floor frame): vertical, perpendicular to the base. The foot's rear-most point is the top of its rim.
RIM_S, RIM_H = world(FEET_Y[0] + FOOT_D / 2, TFEET)
DW_FS = RIM_S - DW_GAP          # front surface of the dowel (s)
DW_CS = DW_FS - DW_D / 2        # axis of the dowel (s)
DW_TOP = RIM_H + 2.0            # top of the dowel above the floor
DW_LEN = DW_EMBED + DW_TOP      # total rod length
assert -DW_TOP * math.tan(TH) > DW_FS   # the housing's rear face stays clear of the dowel at its top
POST_X = [TS + fx for fx in FEET_X]   # dowel axes (x)

# ------------------------------------------------------------------ SVG helpers
parts = []


def add(s):
    parts.append(s)


def f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def poly(pts, fill, stroke="#22313a", sw=1.2, extra=""):
    add('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" %s/>'
        % (" ".join("%s,%s" % (f(x), f(y)) for x, y in pts), fill, stroke, f(sw), extra))


def line(x1, y1, x2, y2, stroke="#22313a", sw=1.0, dash=None, extra=""):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    add('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s %s/>'
        % (f(x1), f(y1), f(x2), f(y2), stroke, f(sw), d, extra))


def text(x, y, s, size=13, anchor="start", weight="normal", fill="#1b2730", rot=None, italic=False):
    r = ' transform="rotate(%s %s %s)"' % (f(rot), f(x), f(y)) if rot is not None else ""
    st = ' font-style="italic"' if italic else ""
    add('<text x="%s" y="%s" font-family="Arial, Helvetica, sans-serif" font-size="%s" text-anchor="%s" '
        'font-weight="%s" fill="%s"%s%s>%s</text>' % (f(x), f(y), f(size), anchor, weight, fill, r, st, s))


def rrect_path(x, y, w, h, rx, ry=None):
    ry = rx if ry is None else ry
    return ("M%s,%s h%s a%s,%s 0 0 1 %s,%s v%s a%s,%s 0 0 1 %s,%s h%s a%s,%s 0 0 1 %s,%s v%s a%s,%s 0 0 1 %s,%s z"
            % (f(x + rx), f(y), f(w - 2 * rx), f(rx), f(ry), f(rx), f(ry), f(h - 2 * ry),
               f(rx), f(ry), f(-rx), f(ry), f(-(w - 2 * rx)), f(rx), f(ry), f(-rx), f(-ry),
               f(-(h - 2 * ry)), f(rx), f(ry), f(rx), f(-ry)))


def dim_h(x1, x2, y, label, ext_from, size=12, off_text=-5):
    """Horizontal dimension with arrows; ext_from = y of the feature the extension lines start at."""
    line(x1, ext_from, x1, y + (6 if y > ext_from else -6), stroke="#555", sw=0.7)
    line(x2, ext_from, x2, y + (6 if y > ext_from else -6), stroke="#555", sw=0.7)
    line(x1, y, x2, y, stroke="#000", sw=0.9, extra='marker-start="url(#ar)" marker-end="url(#ar)"')
    text((x1 + x2) / 2, y + off_text, label, size=size, anchor="middle")


def dim_v(y1, y2, x, label, ext_from, size=12, off_text=-6):
    line(ext_from, y1, x + (6 if x > ext_from else -6), y1, stroke="#555", sw=0.7)
    line(ext_from, y2, x + (6 if x > ext_from else -6), y2, stroke="#555", sw=0.7)
    line(x, y1, x, y2, stroke="#000", sw=0.9, extra='marker-start="url(#ar)" marker-end="url(#ar)"')
    text(x + off_text, (y1 + y2) / 2, label, size=size, anchor="middle", rot=-90)


STAND, STAND_DK, UNIT, UNIT_DK = "#b9c7c6", "#8ea3a2", "#cfe2f4", "#3b6ea5"
SCREEN = "#1f2a36"
CW, CH = 1980, 1330

add('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (CW, CH, CW, CH))
add('<defs><marker id="ar" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#000"/></marker></defs>')
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (CW, CH))
add('<rect x="10" y="10" width="%d" height="%d" fill="none" stroke="#22313a" stroke-width="2"/>' % (CW - 20, CH - 20))

text(40, 58, "Desk stand for the Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5", 30, weight="bold")
text(40, 88, "Concept drawing, landscape. One CNC-machined part, 0.500 in HDPE plate, lip integral, plus two 1/4 in rods. Units: mm. "
             "Unit shown in blue; the stand in grey.", 16, fill="#44525c")

def round_path(pts, r):
    """closed polygon (pixel coordinates) with every corner rounded to radius r (px)"""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        a = (p0[0] - p1[0], p0[1] - p1[1])
        b = (p2[0] - p1[0], p2[1] - p1[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        a = (a[0] / la, a[1] / la)
        b = (b[0] / lb, b[1] / lb)
        ang = math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1])))
        d = r / math.tan(ang / 2)
        t1 = (p1[0] + a[0] * d, p1[1] + a[1] * d)
        t2 = (p1[0] + b[0] * d, p1[1] + b[1] * d)
        cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        out.append((t1, t2, 1 if cross > 0 else 0))
    d_ = "M%s,%s " % (f(out[0][0][0]), f(out[0][0][1]))
    for i, (t1, t2, sw) in enumerate(out):
        if i:
            d_ += "L%s,%s " % (f(t1[0]), f(t1[1]))
        d_ += "A%s,%s 0 0 %d %s,%s " % (f(r), f(r), sw, f(t2[0]), f(t2[1]))
    return d_ + "L%s,%s Z" % (f(out[0][0][0]), f(out[0][0][1]))


# ================================================================== VIEW 1: side section
S1 = 9.0
ox1, oy1 = 170, 790            # px of (s = S_REAR, h = 0)


def P1(s, h):
    return (ox1 + (s - S_REAR) * S1, oy1 - h * S1)


text(40, 135, "SIDE SECTION  (cut through the middle; screen faces right)", 17, weight="bold")
# dowel (behind the cut: dashed), with the through hole in the plate
# the plate with its integral lip, every outline edge rounded to 1 mm
prof = [P1(S_REAR, -BASE), P1(S_FRONT, -BASE), P1(S_TOP, LIP_TOP_IN[1]), P1(*LIP_TOP_IN), P1(*LIP_FLOOR), P1(S_REAR, 0)]
add('<path d="%s" fill="%s" stroke="#22313a" stroke-width="1.6"/>' % (round_path(prof, EDGE_R * S1), STAND))
# rod (behind the cut, dashed) and its through hole
poly([P1(DW_CS - DW_D / 2, -DW_EMBED), P1(DW_CS - DW_D / 2, DW_TOP), P1(DW_CS + DW_D / 2, DW_TOP), P1(DW_CS + DW_D / 2, -DW_EMBED)], "none", "#6f8180", 1.2, 'stroke-dasharray="5 3"')
# unit: front module + rear housing (+ feet)
fm = [world(0, 0), world(H, 0), world(H, TF), world(0, TF)]
hs = [world(INS_TB, TF), world(H - INS_TB, TF), world(H - INS_TB, TR), world(INS_TB, TR)]
poly([P1(*p) for p in fm], UNIT, UNIT_DK, 1.6)
poly([P1(*p) for p in hs], UNIT, UNIT_DK, 1.6)
for fy in FEET_Y:
    p = [world(fy - FOOT_D / 2, TR), world(fy + FOOT_D / 2, TR), world(fy + FOOT_D / 2, TFEET), world(fy - FOOT_D / 2, TFEET)]
    poly([P1(*q) for q in p], "#6b7b86", UNIT_DK, 1.0)
# screen glass line
sg = [world(ACT_BOT, 0.0), world(H - ACT_TOP, 0.0)]
line(*P1(*sg[0]), *P1(*sg[1]), stroke=SCREEN, sw=3.0)
# points A, B and the floor line
A, B = world(0, TF), world(INS_TB, TR)
line(*P1(S_REAR - 1.5, 0), *P1(S_FRONT + 3, 0), stroke="#c0392b", sw=1.0, dash="6 4")
for nm, pt, dx, dy in (("A", A, 14, -10), ("B", B, -18, -10)):
    cx, cy = P1(*pt)
    add('<circle cx="%s" cy="%s" r="4.2" fill="#c0392b"/>' % (f(cx), f(cy)))
    text(cx + dx, cy + dy, nm, 15, weight="bold", fill="#c0392b")
text(*P1(-2.0, -2.9), "floor: unit rests on A and B", 13, fill="#8a2a1d")
# tilt angle (vertical reference through the screen's lower front corner)
Fx, Fy = P1(*world(0, 0))
Tx, Ty = P1(*world(H, 0))
line(Fx, Fy, Fx, Fy - 66 * S1 * cT, stroke="#c0392b", sw=1.0, dash="6 4")
r_arc = 150
add('<path d="M%s,%s A%s,%s 0 0 0 %s,%s" fill="none" stroke="#c0392b" stroke-width="1.6"/>'
    % (f(Fx), f(Fy - r_arc), r_arc, r_arc, f(Fx - r_arc * sT), f(Fy - r_arc * cT)))
text(Fx + 14, Fy - r_arc - 6, "%.2f° back" % DEG, 18, weight="bold", fill="#c0392b")
text(Fx + 14, Fy - r_arc + 14, "tan = 2.085 / 8.10", 13, fill="#c0392b")
# dimensions
dim_h(P1(S_REAR, 0)[0], P1(S_FRONT, 0)[0], oy1 + BASE * S1 + 42, "base depth %.1f" % (S_FRONT - S_REAR), oy1 + BASE * S1)
dim_v(P1(0, -BASE)[1], P1(0, LIP_TOP_IN[1])[1], P1(S_FRONT, 0)[0] + 44, "%.1f (0.500 in)" % STOCK, P1(S_FRONT, 0)[0])
dim_v(P1(0, 0)[1], P1(0, LIP_TOP_IN[1])[1], P1(S_FRONT, 0)[0] + 96, "lip %.1f" % LIP_TOP_IN[1], P1(S_FRONT, 0)[0])
text(ox1, oy1 + BASE * S1 + 160, "lip covers only the bottom 6 mm of the bezel", 13, fill="#22313a")
text(ox1, oy1 + BASE * S1 + 178, "(the screen starts 7.4 mm up)", 13, fill="#22313a")
pb = P1(DW_CS, -DW_EMBED)
text(170, oy1 + BASE * S1 + 84, "2 rods, 1/4 in (6.35) dia x %.1f long (behind the cut)," % DW_LEN, 13, fill="#3d4b54")
text(170, oy1 + BASE * S1 + 100, "pressed into dia %.2f through holes, flush below; each rod" % HOLE_D, 13, fill="#3d4b54")
text(170, oy1 + BASE * S1 + 116, "stops the unit at the top of a lower foot", 13, fill="#3d4b54")
line(pb[0], pb[1] + 4, pb[0], oy1 + BASE * S1 + 70, stroke="#3d4b54", sw=0.8)

# ================================================================== VIEW 2: front view
S2 = 6.2
ox2, oy2 = 590, 585            # px of (x = 0, h = 0)


def P2(x, h):
    return (ox2 + x * S2, oy2 - h * S2)


text(ox2, 135, "FRONT VIEW", 17, weight="bold")
ux0 = TS                        # unit left edge in stand x
uh0, uh1 = world(0, 0)[1], world(H, 0)[1]   # unit front face from F (h) to the top
# base + rails + lip (lip drawn over the unit)
# posts (hidden behind the unit): dashed
for px in POST_X:
    poly([P2(px - DW_D / 2, 0), P2(px + DW_D / 2, 0), P2(px + DW_D / 2, DW_TOP), P2(px - DW_D / 2, DW_TOP)], "none", "#6f8180", 1.0,
         'stroke-dasharray="5 3"')
# the unit (front projection): scaled by cos(TH) vertically
ux, uy = P2(ux0, uh1)
add('<path d="%s" fill="%s" stroke="%s" stroke-width="1.8"/>'
    % (rrect_path(ux, uy, W * S2, (uh1 - uh0) * S2, R * S2, R * cT * S2), UNIT, UNIT_DK))
ax, ay = P2(ux0 + ACT_LEFT, uh0 + (ACT_BOT + ACT_H) * cT)
add('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (f(ax), f(ay), f(ACT_W * S2), f(ACT_H * cT * S2), SCREEN))
text(ax + ACT_W * S2 / 2, ay + ACT_H * cT * S2 / 2 + 5, "screen 73.44 × 48.96", 13, anchor="middle", fill="#9fb3c6")
# lip over the unit
add('<path d="%s" fill="%s" stroke="#22313a" stroke-width="1.6"/>' % (round_path([P2(0, -BASE), P2(WS, -BASE), P2(WS, LIP_TOP_IN[1]), P2(0, LIP_TOP_IN[1])], EDGE_R * S2), STAND))
# dimensions
dim_h(P2(0, 0)[0], P2(WS, 0)[0], oy2 + BASE * S2 + 38, "stand width %.2f = unit width" % WS, oy2 + BASE * S2)
dim_v(P2(0, 0)[1], P2(0, LIP_TOP_IN[1])[1], P2(0, 0)[0] - 30, "lip %.1f" % LIP_TOP_IN[1], P2(0, 0)[0])
dim_v(P2(0, -BASE)[1], P2(0, LIP_TOP_IN[1])[1], P2(WS, 0)[0] + 34, "plate %.1f" % STOCK, P2(WS, 0)[0])
# callouts: ports on the right, buttons + microSD on top
rx, ry = P2(WS, 33)
line(rx + 4, ry, rx + 70, ry, stroke="#1b2730", sw=1.2, extra='marker-start="url(#ar)"')
text(rx + 76, ry - 6, "USB-C ports", 14, weight="bold")
text(rx + 76, ry + 12, "(right side, nothing in the way)", 12)
tx, ty = P2(WS / 2, uh1)
line(tx, ty - 4, tx, ty - 38, stroke="#1b2730", sw=1.2, extra='marker-start="url(#ar)"')
text(tx, ty - 60, "top edge: PWR / RST buttons and microSD slot, open", 14, anchor="middle", weight="bold")
text(tx, ty - 44, "(nothing touches the top)", 12, anchor="middle")
# corner radius callout on the unit's top-left corner
add('<path d="M%s,%s A%s,%s 0 0 1 %s,%s" fill="none" stroke="#c0392b" stroke-width="2.6"/>'
    % (f(ux), f(uy + R * cT * S2), f(R * S2), f(R * cT * S2), f(ux + R * S2), f(uy)))
text(ux + R * S2 + 8, uy - 8, "R7.30 corners", 13, fill="#c0392b", weight="bold")

# ================================================================== VIEW 3: top view
S3 = 6.2
ox3, oy3 = 590, 905            # px of (x = 0, s = S_REAR)


def P3(x, s):
    return (ox3 + x * S3, oy3 + (s - S_REAR) * S3)


text(ox3, 870, "TOP VIEW  (front of the stand at the bottom)", 17, weight="bold")
bx, by = P3(0, S_REAR)
add('<path d="%s" fill="%s" stroke="#22313a" stroke-width="1.6"/>'
    % (rrect_path(bx, by, WS * S3, (S_FRONT - S_REAR) * S3, R * S3), STAND))
# 1 mm edge radius: tangent line just inside the outline
ix, iy = P3(EDGE_R, S_REAR + EDGE_R)
add('<path d="%s" fill="none" stroke="#6f8180" stroke-width="0.8"/>'
    % rrect_path(ix, iy, (WS - 2 * EDGE_R) * S3, (S_FRONT - S_REAR - 2 * EDGE_R) * S3, (R - EDGE_R) * S3))
# pocket floor
px0, py0 = P3(TS, S_REAR)
poly([P3(TS, S_REAR), P3(TS + WP, S_REAR), P3(TS + WP, LIP_FLOOR[0]), P3(TS, LIP_FLOOR[0])], "#e6eceb", "#22313a", 1.0)
# lip
poly([P3(TS, LIP_FLOOR[0]), P3(TS + WP, LIP_FLOOR[0]), P3(TS + WP, S_FRONT), P3(TS, S_FRONT)], STAND, "#22313a", 1.0)
line(*P3(0, S_TOP), *P3(WS, S_TOP), stroke="#22313a", sw=1.0)
text(P3(WS - 6, 0)[0], P3(0, (S_TOP + S_FRONT) / 2)[1] + 4, "front face bevelled %.2f° (parallel to the screen)" % DEG, 12, anchor="end", fill="#22313a")
# dowels (seen from above)
for px in POST_X:
    cx3, cy3 = P3(px, DW_CS)
    add('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#22313a" stroke-width="1.2"/>' % (f(cx3), f(cy3), f(DW_D / 2 * S3), STAND_DK))
# unit outline (ghost)
ugx, ugy = P3(ux0, world(H, TF)[0])
add('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" fill-opacity="0.22" stroke="%s" stroke-width="1.5" '
    'stroke-dasharray="6 3"/>' % (f(ugx), f(ugy), f(W * S3), f((world(0, 0)[0] - world(H, TF)[0]) * S3), f(R * S3), UNIT, UNIT_DK))
text(P3(WS / 2, -9)[0], P3(0, -9)[1], "unit (leaning back)", 13, anchor="middle", fill=UNIT_DK)
text(P3(WS / 2, S_REAR + 2)[0], P3(0, S_REAR + 2)[1] + 4, "open at the rear: cables and the 40-pin header stay free", 12,
     anchor="middle", fill="#44525c")
for px in POST_X:
    text(P3(px, 0)[0], P3(0, DW_CS)[1] - 30, "dowel", 12, anchor="middle")
dim_h(P3(0, 0)[0], P3(WS, 0)[0], P3(0, S_FRONT)[1] + 36, "%.2f" % WS, P3(0, S_FRONT)[1])
dim_v(P3(0, S_REAR)[1], P3(0, S_FRONT)[1], P3(0, 0)[0] - 36, "%.1f" % (S_FRONT - S_REAR), P3(0, 0)[0])
# corner radius
cx0, cy0 = P3(0, S_FRONT)
add('<path d="M%s,%s A%s,%s 0 0 0 %s,%s" fill="none" stroke="#c0392b" stroke-width="2.4"/>'
    % (f(cx0), f(cy0 - R * S3), f(R * S3), f(R * S3), f(cx0 + R * S3), f(cy0)))
text(cx0 + R * S3 + 8, cy0 - 10, "R7.30, same as the unit", 13, fill="#c0392b", weight="bold")

# ================================================================== VIEW 5: 3D sketch (orthographic)
psi, phi = math.radians(38), math.radians(24)
cam = (math.sin(psi) * math.cos(phi), math.sin(phi), math.cos(psi) * math.cos(phi))   # toward the camera (x, h, s)
rv = (math.cos(psi), 0.0, -math.sin(psi))
uvv = (cam[1] * rv[2] - cam[2] * rv[1], cam[2] * rv[0] - cam[0] * rv[2], cam[0] * rv[1] - cam[1] * rv[0])
S5, ox5, oy5 = 3.1, 1640, 400


def proj(p):                       # p = (x, h, s)
    X = p[0] * rv[0] + p[1] * rv[1] + p[2] * rv[2]
    Y = p[0] * uvv[0] + p[1] * uvv[1] + p[2] * uvv[2]
    return ox5 + X * S5, oy5 - Y * S5


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


LIGHT = (0.35, 0.80, 0.50)
LN = math.sqrt(dot(LIGHT, LIGHT))


def shade(base, n):
    k = 0.52 + 0.48 * max(0.0, dot(n, tuple(v / LN for v in LIGHT)))
    r, g, b = (int(base[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))


def solid(poly2d, mapper, color, stroke="#1d2a32", depth_axis_pairs=None):
    """Extrude a convex 2D polygon between two mappings; mapper(u, v, w) -> (x, h, s); w in {0, 1}."""
    n = len(poly2d)
    bot = [mapper(u, v, 0) for u, v in poly2d]
    top = [mapper(u, v, 1) for u, v in poly2d]
    cen = tuple(sum(p[i] for p in bot + top) / (2 * n) for i in range(3))
    faces = [bot[::-1], top] + [[bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]] for i in range(n)]
    drawn = []
    for fc in faces:
        nrm = cross(sub(fc[1], fc[0]), sub(fc[2], fc[0]))
        ln = math.sqrt(dot(nrm, nrm))
        if ln < 1e-9:
            continue
        nrm = tuple(v / ln for v in nrm)
        fcen = tuple(sum(p[i] for p in fc) / len(fc) for i in range(3))
        if dot(nrm, sub(fcen, cen)) < 0:
            nrm = tuple(-v for v in nrm)
        if dot(nrm, cam) <= 1e-6:
            continue
        drawn.append((dot(fcen, cam), fc, nrm))
    for _, fc, nrm in sorted(drawn, key=lambda t: t[0]):
        poly([proj(p) for p in fc], shade(color, nrm), stroke, 0.7)


def rounded_poly(x0, y0, x1, y1, r, seg=7):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


text(1430, 135, "3D SKETCH  (from the front, right and above)", 17, weight="bold")
# base: plan polygon (x, s) with rounded corners, extruded in h
bpoly = rounded_poly(0, S_REAR, WS, S_FRONT, R)
solid(bpoly, lambda u, v, w: (u, -BASE + w * BASE, v), STAND)
# dowels, then unit, then lip (far to near)
for px in POST_X:
    circ = [(px + DW_D / 2 * math.cos(a * math.pi / 8), DW_CS + DW_D / 2 * math.sin(a * math.pi / 8)) for a in range(16)]
    solid(circ, lambda u, v, w: (u, w * DW_TOP, v), STAND_DK)
# unit: front module and housing, plus screen and camera
def mapper_front(u, v, w):
    s_, h_ = world(v, TF * w)
    return (ux0 + u, h_, s_)


def mapper_house(u, v, w):
    s_, h_ = world(v, TF + (TR - TF) * w)
    return (ux0 + INS_LR + u, h_, s_)


solid(rounded_poly(0, 0, W, H, R), mapper_front, UNIT)
# screen: a dark quad on the front face
sq = [(ACT_LEFT, ACT_BOT), (ACT_LEFT + ACT_W, ACT_BOT), (ACT_LEFT + ACT_W, ACT_BOT + ACT_H), (ACT_LEFT, ACT_BOT + ACT_H)]
pts = []
for u, v in sq:
    s_, h_ = world(v, -0.05)
    pts.append(proj((ux0 + u, h_, s_)))
poly(pts, SCREEN, "#0c1218", 0.8)
solid([(0, INS_TB), (83.20, INS_TB), (83.20, H - INS_TB), (0, H - INS_TB)], mapper_house, UNIT)
solid([(LIP_FLOOR[0], 0.0), LIP_TOP_IN, (S_TOP, LIP_TOP_IN[1]), (S_FLR, 0.0)],
      lambda u, v, w: (TS + w * WP, v, u), STAND)
# USB ports hint on the unit's right edge (dark slots)
for hy0 in (24.0, 33.0):
    q = []
    for dz, dy in ((0.8, hy0), (4.6, hy0), (4.6, hy0 + 7.2), (0.8, hy0 + 7.2)):
        s_, h_ = world(dy, dz)
        q.append(proj((ux0 + W + 0.05, h_, s_)))
    poly(q, "#10171d", "#10171d", 0.6)
tx5, ty5 = proj((ux0 + W + 1, world(30, 3)[1], world(30, 3)[0]))
text(tx5 + 14, ty5 + 4, "USB-C", 13, weight="bold")

# ================================================================== notes
nx, ny = 1430, 700
text(nx, ny - 26, "KEY NUMBERS", 17, weight="bold")
rows = [
    ("Lean back (edges A and B on the floor)", "%.2f\u00b0" % DEG),
    ("Distance A to B along the floor", "%.2f" % math.hypot(TR - TF, INS_TB)),
    ("Clearance: lip, rods / sides", "0.5 / flush"),
    ("Plate width \u00d7 depth \u00d7 thickness", "%.1f \u00d7 %.1f \u00d7 %.1f" % (WS, S_FRONT - S_REAR, STOCK)),
    ("Plate below the pocket floor", "%.2f" % BASE),
    ("Rods: 1/4 in dia \u00d7 length", "6.35 \u00d7 %.1f" % DW_LEN),
    ("Holes: dia \u00d7 depth (through)", "%.2f \u00d7 %.1f" % (HOLE_D, BASE)),
    ("Edge radius, outline / plan corners", "%.1f / R%.2f" % (EDGE_R, R)),
    ("Lip: top width / front bevel", "%.1f / %.2f°" % (S_TOP - LIP_TOP_IN[0], DEG)),
]
for i, (k, v) in enumerate(rows):
    y = ny + i * 22
    text(nx, y, k, 13)
    text(nx + 510, y, v, 13, anchor="end", weight="bold")
    line(nx, y + 6, nx + 510, y + 6, stroke="#d5dde2", sw=0.8)

text(nx, ny + len(rows) * 22 + 30, "NOTES", 17, weight="bold")
notes = [
    "Material: 0.500 in (12.7 mm) HDPE plate. The pocket is milled %.2f mm" % LIP_TOP_IN[1],
    "below the top face; the uncut front strip is the lip (integral),",
    "its front face bevelled %.2f deg to match the screen." % DEG,
    "Edges: 1 mm radius on every edge of the outline, top and bottom,",
    "and in the lip/floor corner (2 mm end mill or smaller); the floor-level",
    "rim (rear and sides, top edge) is 0.5 mm: 1 mm will not build there.",
    "Rods: 1/4 in brass or aluminium, %.1f mm long, chamfer the top;" % DW_LEN,
    "the bottom end sits flush with the underside (file it flush).",
    "Holes: 2 x dia %.2f (0.248 in), through, at x = 11.55 and 83.55 from" % HOLE_D,
    "the left edge, axis %.1f mm behind edge B. 0.05 mm press fit; HDPE" % -DW_CS,
    "does not glue and creeps, so ream the holes and chamfer the mouth.",
    "Why rods: the unit's centre of mass is ~2 mm behind edge B; each",
    "rod stops it at the top of a lower foot (0.5 mm gap).",
    "Camera tip: keep the stand ~15 cm from a wall or the light sensor",
    "sees only the wall's shadow.",
    "Source: Waveshare drawing, read by eye. Foot diameter (6.0) and the",
    "lip height are my choices. Check against the real unit first.",
]
for i, n in enumerate(notes):
    text(nx, ny + len(rows) * 22 + 50 + i * 17, n, 12, fill="#2c3a43")

add("</svg>")
OUT.write_text("\n".join(parts), encoding="utf-8")
print("wrote", OUT, "| lean %.2f deg | dowel top %.2f len %.1f axis s=%.2f | lip top %.2f" % (DEG, DW_TOP, DW_LEN, DW_CS, LIP_TOP_IN[1]))
