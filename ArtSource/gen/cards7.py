"""v3 card textures shown in front of the player (unlit): the Far Hall Quests tally (0..6 / 6) and one card per quest prize."""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kit3e import _card, _font, FONT, FONT_I
import plan7 as PL
OUT = os.path.join(HERE, '..', 'out', 'Textures')
gold = (176, 132, 58); ink = (40, 34, 30); soft = (92, 80, 70)
def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def wrap(d, text, font, width):
    words = text.split(); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) > width and cur: lines.append(cur); cur = w
        else: cur = t
    if cur: lines.append(cur)
    return lines

W, H = 1024, 384
for n in range(7):
    im = _card(W, H); d = ImageDraw.Draw(im)
    for (m, w) in ((14, 5), (28, 2)): d.rounded_rectangle([m, m, W - m, H - m], radius=20, outline=gold, width=w)
    d.text((W / 2, 78), 'FAR HALL QUESTS', font=_font(FONT, 54, 700), fill=soft, anchor='mm')
    d.text((W / 2, 190), f'{n} / 6', font=_font(FONT, 150, 600), fill=ink, anchor='mm')
    for k, q in enumerate(PL.QUESTS):
        fam = PL.EXITS[q['exit']]['family']; col = hexrgb(PL.FAMILY_COLORS_INK[fam])
        cx = W / 2 + (k - 2.5) * 84; cy = 312
        pts = [(cx, cy - 24), (cx + 18, cy), (cx, cy + 24), (cx - 18, cy)]
        d.polygon(pts, fill=col if k < n else None, outline=col, width=4)
    im.save(os.path.join(OUT, f'Quests_{n}.png'))
for k, q in enumerate(PL.QUESTS):
    fam = PL.EXITS[q['exit']]['family']; col = hexrgb(PL.FAMILY_COLORS_INK[fam])
    im = _card(W, 512); d = ImageDraw.Draw(im)
    for (m, w) in ((14, 6), (30, 2)): d.rounded_rectangle([m, m, W - m, 512 - m], radius=20, outline=col, width=w)
    d.text((W / 2, 70), q['hall'].upper(), font=_font(FONT, 40, 700), fill=col, anchor='mm')
    d.text((W / 2, 150), q['prize'], font=_font(FONT, 72, 600), fill=ink, anchor='mm')
    d.text((W / 2, 225), 'You are the ' + q['role'], font=_font(FONT_I, 46, 500), fill=soft, anchor='mm')
    f = _font(FONT_I, 38, 500)
    for i, ln in enumerate(wrap(d, q['lesson'], f, W - 160)):
        d.text((W / 2, 300 + i * 46), ln, font=f, fill=ink, anchor='mm')
    d.text((W / 2, 455), f'Far Hall Quest {k + 1} of 6', font=_font(FONT, 32, 600), fill=soft, anchor='mm')
    im.save(os.path.join(OUT, f'QuestCard_{k}.png'))
print('quest cards written')
