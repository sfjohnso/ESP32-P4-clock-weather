# Desk stand for the Waveshare ESP32-P4 3.5 inch board

The board leans back 14.43 degrees (both rear-bottom edges rest on one flat surface), sits in a pocket
with a small lip at the front, and the stand is as wide as the board. The board is symmetric, so the
same pocket holds it USB-right or USB-left.

## To print it

`cad/ESP32-P4_stand_print.stl` (or the `.step`). Print it flat, no supports. 100% infill is
recommended: the stand is light, and at 35% infill it tips back at 30-33 degrees instead of 34-43.
About 25 g of PLA. Printed and used on 2026-11: it works well.

The printed version has two relief grooves in the pocket floor (room for the microSD card and buttons
when the board is flipped) and two printed rear stops in place of rods.

## To machine it instead

`cad/ESP32-P4_stand_base.step` and `cad/ESP32-P4_stand_base_outline.dxf` are the CNC version: 0.500 in
HDPE with two 1/4 in rods. `ESP32-P4_stand_cutsheet.pdf` is a 1:1 cut sheet for a table saw and router
(its rabbet wall is vertical; the STEP leans it back, which a router cannot cut).

## Regenerating

Python with `cadquery` (tested with 2.7.0) and `ezdxf`:

    python cad/build_print.py      # print STL + STEP
    python cad/build_base.py       # CNC STEP + DXF

`make_stand.py` holds the dimensions and drawings; the build scripts read it. The unit's dimensions were
read from Waveshare's drawing, the foot diameter and lip height are my choices.
`make_cutsheet.py` needs Inkscape (the path is set near the end of the file).
