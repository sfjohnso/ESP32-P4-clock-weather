# Desk stand for the Waveshare ESP32-P4 3.5 inch board

A 3D-printed stand. The board leans back 14.43 degrees (both rear-bottom edges rest on one flat
surface), sits in a pocket with a small lip at the front, and the stand is as wide as the board. The
board is symmetric, so the same pocket holds it USB-right or USB-left.

## To print it

`cad/ESP32-P4_stand_print.stl` (or the `.step`). Print it flat, no supports. 100% infill is
recommended: the stand is light, and at 35% infill it tips back at 30-33 degrees instead of 34-43.
About 25 g of PLA; printed commercially it cost about $6 each. It works well.

Two relief grooves in the pocket floor leave room for the microSD card and buttons when the board is
flipped, and two printed stops at the rear keep the board from sliding.

## Regenerating

Python with `cadquery` (tested with 2.7.0):

    python cad/build_print.py

`make_stand.py` holds the dimensions; the build script reads it. The board's dimensions were read from
Waveshare's drawing; the foot diameter and lip height are my choices.
