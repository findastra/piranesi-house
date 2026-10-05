"""The ruin on the east isle: a roofless colonnade whose fallen columns lie across the tops of the standing ones,
overgrown with ivy, with hammocks slung between the columns and a garden table laid with fruit.
Ruin-local coordinates (Unity axes), origin on the ground at the ruin centre. Shared by ivy.py and layout2.py."""
COL_H = 10.6          # Column mesh height (base at 0)
BASE_Y = -0.35        # bases sunk into the sand so every capital is level
TOP = BASE_Y + COL_H
SHAFT_R = 0.45
ROWS = (-3.5, 3.5)
XS = (-9.2, -4.6, 0.0, 4.6, 9.2)
STUMPS = [(9.2, 3.5), (-9.2, -3.5)]          # broken: drums instead of full columns
COLUMNS = [(x, z) for z in ROWS for x in XS if (x, z) not in STUMPS]
BEAM_Y = TOP + SHAFT_R
# fallen columns: e = Unity euler (x, y, z); a Column rotated x=90 lies along +z from its base, then yawed by y
BEAMS = [
    dict(p=(-4.6, BEAM_Y, -5.3), e=(90, 0, 0)),
    dict(p=(0.0, BEAM_Y, -5.3), e=(90, 0, 0)),
    dict(p=(4.6, BEAM_Y + 0.02, -5.3), e=(90, 0, 3)),
    # one more lies lengthwise on top of two of the cross beams, along the north row
    dict(p=(-9.4, BEAM_Y + 2 * SHAFT_R, 3.5), e=(90, 90, 0)),
]
HAMMOCKS = [((-2.3, -3.5), 90), ((2.3, -3.5), 90), ((-2.3, 3.5), 90)]   # centre (x, z), yaw; anchors land on the columns
HAMMOCK_Y = 1.3
TABLE = (0.0, 0.0)
