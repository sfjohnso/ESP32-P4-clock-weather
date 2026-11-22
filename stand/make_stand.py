# -*- coding: utf-8 -*-
"""Dimensions and geometry of the desk stand for the Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5 (landscape).

cad/build_print.py reads the constants in this file. All lengths in mm.
Device numbers come from the 'Dimensions' drawing on docs.waveshare.com.
"""
import math
from pathlib import Path


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
