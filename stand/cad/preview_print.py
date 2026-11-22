import cadquery as cq, subprocess
b = cq.importers.importStep("ESP32-P4_stand_print.step")
ink = r"C:\Program Files\Inkscape\bin\inkscape.exe"
for name, d in (("iso_front", (1, 1.4, 0.9)), ("iso_rear", (-1, -1.2, 0.8)), ("side", (1, 0, 0))):
    svg = "print_%s.svg" % name
    cq.exporters.export(b, svg, opt=dict(width=1100, height=520, marginLeft=30, marginTop=30, showAxes=False,
                                         projectionDir=d, strokeWidth=0.3, strokeColor=(20, 30, 40), showHidden=False))
    subprocess.run([ink, svg, "--export-type=png", "--export-filename=print_%s.png" % name, "--export-background=white", "--export-width=1500"], check=True, capture_output=True)
print("ok")
