"""Stand base as a solid (STEP) and a flat outline (DXF) for Send Cut Send.

All numbers come from ../make_stand.py (the drawing generator), so the drawing and the part agree.
Part frame (mm): x = across the width (left edge of the unit = 0, as you face the screen),
y = depth (0 at the rear edge, plate front at the bottom = 37.0), z = up (0 = underside, pocket floor = BASE, lip top = 12.7).
"""
import math, os, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "make_stand.py"), encoding="utf-8").read()
g = {"__file__": os.path.join(HERE, "..", "make_stand.py")}
exec(src[:src.index("# ------------------------------------------------------------------ SVG helpers")], g)

W = g["W"]; R = g["R"]; STOCK = g["STOCK"]; BASE = g["BASE"]; EDGE_R = g["EDGE_R"]
S_REAR, S_FRONT, S_TOP = g["S_REAR"], g["S_FRONT"], g["S_TOP"]
LIP_FLOOR_S = g["LIP_FLOOR"][0]
LIP_TOP_S, LIP_TOP_H = g["LIP_TOP_IN"]
HOLE_D = g["HOLE_D"]; HOLE_Y = g["DW_CS"] - S_REAR; HOLE_X = list(g["FEET_X"])
DEPTH = S_FRONT - S_REAR

def Y(s):            # floor-frame s  ->  part y
    return s - S_REAR
def Z(h):            # floor-frame h  ->  part z
    return h + BASE

# side profile in the (y, z) plane, extruded along x
prof = [(Y(S_REAR), 0), (Y(S_FRONT), 0), (Y(S_TOP), STOCK), (Y(LIP_TOP_S), Z(LIP_TOP_H)),
        (Y(LIP_FLOOR_S), BASE), (Y(S_REAR), BASE)]
assert abs(Z(LIP_TOP_H) - STOCK) < 1e-6, (Z(LIP_TOP_H), STOCK)
# the profile's top-front point (S_TOP, STOCK) coincides with the lip top: fix: lip top flat from LIP_TOP_S to S_TOP
prof = [(Y(S_REAR), 0), (Y(S_FRONT), 0), (Y(S_TOP), STOCK), (Y(LIP_TOP_S), STOCK),
        (Y(LIP_FLOOR_S), BASE), (Y(S_REAR), BASE)]
body = cq.Workplane("YZ").polyline(prof).close().extrude(W)          # YZ plane normal is +x

# plan outline with R7.30 corners (vertical cut, as a contour pass)
plan = cq.Workplane("XY").rect(W, DEPTH, centered=False).extrude(STOCK).edges("|Z").fillet(R)
body = body.intersect(plan)

# 1 mm radius on every edge. The top edge of the rim at pocket-floor level (rear and both sides) can only take
# 0.5 mm: the front corner arc (R7.30) starts 0.8 mm before the lip wall, and a 1 mm fillet there will not build.
def _is_vertical(e):
    bb = e.BoundingBox()
    return e.geomType() == "LINE" and abs(bb.xmax - bb.xmin) < 1e-6 and abs(bb.ymax - bb.ymin) < 1e-6

def _floor_rim(e):
    bb = e.BoundingBox()
    return abs(bb.zmin - BASE) < 1e-3 and abs(bb.zmax - BASE) < 1e-3 and bb.ymax < Y(LIP_FLOOR_S) + 2

def _fillet(wp, edges, r):
    return cq.Workplane(obj=wp.val()).newObject(edges).fillet(r)

edges = [e for e in body.val().Edges() if not _is_vertical(e)]
body = _fillet(body, [e for e in edges if not _floor_rim(e)], EDGE_R)
rim = [e for e in body.val().Edges() if not _is_vertical(e) and _floor_rim(e)]
body = _fillet(body, rim, 0.5)

# two through holes for the 1/4 in rods
for hx in HOLE_X:
    body = body.cut(cq.Workplane("XY").workplane(offset=-1).center(hx, HOLE_Y).circle(HOLE_D / 2).extrude(BASE + 2))

solid = body.val()
assert solid.isValid()
print("valid solid | volume %.1f mm3 | bbox x %.2f y %.2f z %.2f" % (solid.Volume(), *[
    (solid.BoundingBox().xmax - solid.BoundingBox().xmin),
    (solid.BoundingBox().ymax - solid.BoundingBox().ymin),
    (solid.BoundingBox().zmax - solid.BoundingBox().zmin)]))

step = os.path.join(HERE, "ESP32-P4_stand_base.step")
cq.exporters.export(body, step)

# flat DXF: the plan outline (bottom footprint, R7.30 corners) and the two holes, in millimetres
import ezdxf
doc = ezdxf.new("R2010", setup=True)
doc.units = ezdxf.units.MM
msp = doc.modelspace()
doc.layers.add("CUT", color=7)
x0, y0, x1, y1, r = 0.0, 0.0, W, DEPTH, R
msp.add_line((x0 + r, y0), (x1 - r, y0), dxfattribs={"layer": "CUT"})
msp.add_arc((x1 - r, y0 + r), r, 270, 360, dxfattribs={"layer": "CUT"})
msp.add_line((x1, y0 + r), (x1, y1 - r), dxfattribs={"layer": "CUT"})
msp.add_arc((x1 - r, y1 - r), r, 0, 90, dxfattribs={"layer": "CUT"})
msp.add_line((x1 - r, y1), (x0 + r, y1), dxfattribs={"layer": "CUT"})
msp.add_arc((x0 + r, y1 - r), r, 90, 180, dxfattribs={"layer": "CUT"})
msp.add_line((x0, y1 - r), (x0, y0 + r), dxfattribs={"layer": "CUT"})
msp.add_arc((x0 + r, y0 + r), r, 180, 270, dxfattribs={"layer": "CUT"})
for hx in HOLE_X:
    msp.add_circle((hx, HOLE_Y), HOLE_D / 2, dxfattribs={"layer": "CUT"})
dxf = os.path.join(HERE, "ESP32-P4_stand_base_outline.dxf")
doc.saveas(dxf)
print("wrote", step, dxf)
print("holes at x=%s y=%.2f (from the rear edge), dia %.2f; plate %.2f x %.2f x %.2f" % (HOLE_X, HOLE_Y, HOLE_D, W, DEPTH, STOCK))
