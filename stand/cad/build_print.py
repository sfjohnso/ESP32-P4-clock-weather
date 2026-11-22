"""3D-printable stand base (STL + STEP), pocket for the board, leaning back 14.43 deg.

Features:
  * the lip's rear face leans back parallel to the screen (an overhang, but 14.4 deg from
    vertical is fine for FDM, no supports);
  * two printed rear stops (12 x 4 mm blocks, 10 mm above the floor);
  * two relief grooves in the pocket floor, so that whichever edge of the unit is at the bottom (USB right:
    the plain edge; USB left: the edge with PWR/RST/microSD) has room for a card or a button, while edges
    A and B (the only places the unit touches the floor) keep a narrow land.
The unit is 180-degree symmetric (outline, rear housing inset, four feet), so the same pocket takes it either way
up; that is checked below with a model of the unit in both orientations.
Part frame (mm): x across, y depth (0 = rear edge, 37 = front edge on the bottom face), z up (0 = underside).
"""
import math, os
import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "make_stand.py"), encoding="utf-8").read()
g = {"__file__": os.path.join(HERE, "..", "make_stand.py")}
exec(src, g)

W, H, R = g["W"], g["H"], g["R"]
STOCK, BASE, EDGE_R = g["STOCK"], g["BASE"], g["EDGE_R"]
S_REAR, S_FRONT, S_TOP = g["S_REAR"], g["S_FRONT"], g["S_TOP"]
LIP_FLOOR_S = g["LIP_FLOOR"][0]
LIP_TOP_S = g["LIP_TOP_IN"][0]
TH, sT, cT, TAN = g["TH"], g["sT"], g["cT"], math.tan(g["TH"])
TF, TR, TFEET, INS_TB, INS_LR = g["TF"], g["TR"], g["TFEET"], g["INS_TB"], g["INS_LR"]
FEET_X, FEET_Y, FOOT_D = g["FEET_X"], g["FEET_Y"], g["FOOT_D"]
DEPTH = S_FRONT - S_REAR
Y = lambda s: s - S_REAR
Z = lambda h: h + BASE

# ------------------------------------------------------------------ stand body
GROOVE = 3.0                     # relief depth below the pocket floor
LAND = 1.4                       # half-width of the land under edge B and under edge A
A_S = g["world"](0, TF)[0]       # floor contact line A (front module's rear-bottom edge), s = 8.36
B_S = 0.0                        # floor contact line B (housing's rear-bottom edge)
assert abs(g["world"](0, TF)[1]) < 1e-6 and abs(g["world"](INS_TB, TR)[0]) < 1e-6

prof = [(Y(S_REAR), 0), (Y(S_FRONT), 0), (Y(S_TOP), STOCK), (Y(LIP_TOP_S), STOCK),
        (Y(LIP_FLOOR_S), BASE), (Y(S_REAR), BASE)]
body = cq.Workplane("YZ").polyline(prof).close().extrude(W)
plan = cq.Workplane("XY").rect(W, DEPTH, centered=False).extrude(STOCK).edges("|Z").fillet(R)
body = body.intersect(plan)


def _vertical(e):
    bb = e.BoundingBox()
    return e.geomType() == "LINE" and abs(bb.xmax - bb.xmin) < 1e-6 and abs(bb.ymax - bb.ymin) < 1e-6


def _floor_rim(e):
    bb = e.BoundingBox()
    return abs(bb.zmin - BASE) < 1e-3 and abs(bb.zmax - BASE) < 1e-3 and bb.ymax < Y(LIP_FLOOR_S) + 2


def _fillet(wp, edges, r):
    return cq.Workplane(obj=wp.val()).newObject(edges).fillet(r)


edges = [e for e in body.val().Edges() if not _vertical(e)]
body = _fillet(body, [e for e in edges if not _floor_rim(e)], EDGE_R)
body = _fillet(body, [e for e in body.val().Edges() if not _vertical(e) and _floor_rim(e)], 0.5)

# relief grooves, cut across the full width (open at both sides)
G1 = (B_S + LAND, A_S - LAND)                      # between the lands under B and A
G2 = (A_S + LAND, LIP_FLOOR_S)                     # from the land under A to the lip
lean = GROOVE * TAN                                # the lip's leaning rear face continues down into the groove


def cut_prism(pts):
    return cq.Workplane("YZ").workplane(offset=-1).polyline(pts).close().extrude(W + 2)


body = body.cut(cut_prism([(Y(G1[0]), BASE + 1), (Y(G1[1]), BASE + 1), (Y(G1[1]), BASE - GROOVE), (Y(G1[0]), BASE - GROOVE)]))
body = body.cut(cut_prism([(Y(G2[0]), BASE + 1), (Y(LIP_FLOOR_S - 1 * TAN) , BASE + 1), (Y(LIP_FLOOR_S), BASE),
                           (Y(LIP_FLOOR_S + lean), BASE - GROOVE), (Y(G2[0]), BASE - GROOVE)]))

# rear stops: each stops the unit 0.5 mm behind the top of a rear foot
RIM_S, RIM_H = g["world"](FEET_Y[0] + FOOT_D / 2, TFEET)
STOP_FRONT = RIM_S - g["DW_GAP"]                   # front face of the stop (s)
STOP_T, STOP_W = 4.0, 12.0
STOP_TOP = RIM_H + 2.0
assert -STOP_TOP * TAN > STOP_FRONT                # the housing's rear face stays clear of the stop at its top
for fx in FEET_X:
    blk = (cq.Workplane("XY").box(STOP_W, STOP_T, Z(STOP_TOP) + 0.0, centered=False)
           .translate((fx - STOP_W / 2, Y(STOP_FRONT - STOP_T), 0)))
    blk = blk.edges("|Z").fillet(1.5).faces(">Z").edges().fillet(1.0)
    body = body.union(blk)

solid = body.val()
assert solid.isValid() and len(body.solids().vals()) == 1
bb = solid.BoundingBox()
print("valid solid | volume %.2f cm3 | bbox x %.2f y %.2f z %.2f" % (solid.Volume() / 1000, bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin))

# ------------------------------------------------------------------ the unit, for clearance checks
def place(shape, ty, tz):
    """device frame -> part frame: (x, y, z) -> (x, -sT*y - cT*z + ty, cT*y - sT*z + tz) = rotation about x by 90 deg + lean"""
    return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90 + g["DEG"]).translate(cq.Vector(0, ty, tz))


def unit_solid(flipped):
    front = cq.Workplane("XY").rect(W, H, centered=False).extrude(TF).edges("|Z").fillet(R)
    house = (cq.Workplane("XY").workplane(offset=TF).center(0, 0).moveTo(INS_LR, INS_TB)
             .rect(W - 2 * INS_LR, H - 2 * INS_TB, centered=False).extrude(TR - TF).edges("|Z").fillet(3.0))
    u = front.union(house)
    for fx in FEET_X:
        for fy in FEET_Y:
            u = u.union(cq.Workplane("XY").workplane(offset=TR).center(fx, fy).circle(FOOT_D / 2).extrude(TFEET - TR))
    if flipped:   # turned 180 deg about the screen normal: USB on the other side, ports edge down
        u = u.rotate((W / 2, H / 2, 0), (W / 2, H / 2, 1), 180)
    ty = INS_TB * sT + TR * cT - S_REAR
    tz = -INS_TB * cT + TR * sT + BASE + 0.001
    return place(u.val(), ty, tz), u


def move(shape, dy):
    return shape.moved(cq.Location(cq.Vector(0, dy, 0)))


for flipped in (False, True):
    unit, _ = unit_solid(flipped)
    v0 = unit.intersect(solid).Volume()
    res = []
    for dy in (-0.40, 0.40, -0.80, 0.70):
        res.append("%+.2f mm: %s" % (dy, "clear" if move(unit, dy).intersect(solid).Volume() < 0.01 else "touches"))
    print("unit %-22s overlap at rest %.4f mm3 | slide %s" % ("USB left (flipped)" if flipped else "USB right", v0, " | ".join(res)))
    assert v0 < 0.01

# the ports edge, in the flipped orientation, must clear the stand wherever a card/button could stick out:
# an imaginary 2.5 mm slab under the unit's bottom faces (front module face and housing face)
unit_f, _ = unit_solid(True)
ty = INS_TB * sT + TR * cT - S_REAR
tz = -INS_TB * cT + TR * sT + BASE + 0.001


def free_protrusion(y0, z):
    """flipped unit: how far (mm) something can stick out of its ports-edge face at depth z before it hits the stand"""
    t = 0.0
    while t < 4.0:
        yf = H - (y0 + t + 0.1)                      # device y after the 180 deg flip
        Yp, Zp = -sT * yf - cT * z + ty, cT * yf - sT * z + tz
        if solid.isInside(cq.Vector(W / 2, Yp, Zp)) or Zp < 0:
            break
        t += 0.1
    return t


for name, y0, za, zb in (("front-module face (5.4 thick)", H, 0.0, TF), ("housing face", H - INS_TB, TF, TR)):
    zs = np.arange(za + 0.1, zb, 0.25)
    fp = [(z, free_protrusion(y0, z)) for z in zs]
    ok = [z for z, t in fp if t >= 2.0]
    print("ports edge down, %-30s free protrusion: min %.1f mm, >= 2 mm over %.1f of %.1f mm of the face (blocked near the contact line: z %s)"
          % (name, min(t for _, t in fp), len(ok) * 0.25, zb - za, ["%.1f" % z for z, t in fp if t < 2.0][:1] + ["..."] + ["%.1f" % z for z, t in fp if t < 2.0][-1:]))

# ------------------------------------------------------------------ exports
step = os.path.join(HERE, "ESP32-P4_stand_print.step")
stl = os.path.join(HERE, "ESP32-P4_stand_print.stl")
cq.exporters.export(body, step)
cq.exporters.export(body, stl, tolerance=0.01, angularTolerance=0.1)

# STL sanity: watertight (every edge shared by two triangles, opposite directions) and volume
raw = open(stl, "rb").read()
if raw[:5] == b"solid" and b"facet" in raw[:300]:
    raise SystemExit("ASCII STL not handled")
n = int(np.frombuffer(raw, np.uint32, 1, 80)[0])
rec = np.frombuffer(raw, np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), n, 84)
v = np.round(rec["v"].reshape(-1, 3), 4)
_, idx = np.unique(v, axis=0, return_inverse=True)
tri = idx.reshape(-1, 3)
edges = {}
for a, b, c in tri:
    if a == b or b == c or a == c:
        continue   # zero-area sliver after rounding
    for p, q in ((a, b), (b, c), (c, a)):
        edges[(p, q)] = edges.get((p, q), 0) + 1
bad = sum(1 for (p, q), k in edges.items() if (k != 1 or edges.get((q, p), 0) != 1) and len({p, q}) == 2)
vol = np.einsum("ij,ij->", rec["v"][:, 0], np.cross(rec["v"][:, 1], rec["v"][:, 2])) / 6
print("STL: %d triangles, %d unmatched edges, volume %.2f cm3 (CAD %.2f cm3)" % (n, bad, vol / 1000, solid.Volume() / 1000))

# ------------------------------------------------------------------ tip-over estimate (assumptions!)
cx = solid.Center()
plate_s, plate_h = cx.y + S_REAR, cx.z - BASE
udev, ucad = unit_solid(False)
uc = udev.Center()
unit_s, unit_h = uc.y + S_REAR, uc.z - BASE
solid_pla = solid.Volume() / 1000 * 1.24
for infill in (0.35, 1.0):
    mp = solid_pla * infill
    for mu in (40, 90):
        Ms = (mp * plate_s + mu * unit_s) / (mp + mu)
        Mh = (mp * (plate_h + BASE) + mu * (unit_h + BASE)) / (mp + mu)
        d, hh = Ms - S_REAR, Mh - BASE                    # from the rear bottom edge of the plate
        print("plate %.0f g (PLA, solid %.0f g) + unit %d g: COM %.1f mm ahead of the rear edge, %.1f mm up -> tips at %.0f deg"
              % (mp, solid_pla, mu, d, hh, math.degrees(math.atan2(d, hh))))
print("files:", step, stl)
