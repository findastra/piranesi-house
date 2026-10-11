"""Texture for the wrist menu: Piranesi on Audible + buy the book, as QR codes (VRChat worlds cannot open web pages)."""
import os, math, numpy as np, qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond[wght].ttf')
FONT_I = os.path.join(HERE, '..', 'assets', 'fonts', 'CormorantGaramond-Italic[wght].ttf')
OUT = os.path.join(HERE, '..', 'out', 'Textures', 'HandMenu_Card.png')
AUDIBLE = 'https://www.audible.com/pd/Piranesi-Audiobook/1526622416'
BOOK = 'https://bookshop.org/p/books/piranesi-susanna-clarke/15861178'

def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        try: f.set_variation_by_axes([weight])
        except Exception: pass
    return f

def qr_img(url, px):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=3, box_size=10)
    q.add_data(url); q.make(fit=True)
    im = q.make_image(fill_color=(28, 24, 20), back_color=(250, 246, 236)).convert('RGB')
    return im.resize((px, px), Image.NEAREST)

def main():
    W, H = 1024, 1280
    rng = np.random.default_rng(7)
    # warm marble ground with soft grey veins
    y, x = np.mgrid[0:H, 0:W] / 1024.0
    n = np.zeros((H, W))
    for k in range(5):
        f = 2 ** k * 1.3; ph = rng.uniform(0, 6, 2)
        n += np.sin(x * f * 6.1 + np.sin(y * f * 4.3 + ph[0]) * 1.7 + ph[1]) / 2 ** k
    vein = np.exp(-np.abs(n) * 9) * 0.10
    base = np.stack([0.955 - vein, 0.935 - vein * 1.02, 0.885 - vein * 1.05], -1)
    im = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(im)
    gold = (176, 132, 58); ink = (40, 34, 30); soft = (92, 80, 70)
    for (m, w) in ((22, 6), (40, 2)):
        d.rounded_rectangle([m, m, W - m, H - m], radius=26, outline=gold, width=w)
    # sunburst ornament (the gate window motif)
    cx, cy = W // 2, 150
    for k in range(19):
        a = math.pi * k / 18
        r0, r1 = 46, (96 if k % 2 == 0 else 74)
        d.line([(cx + r0 * math.cos(a), cy - r0 * math.sin(a)), (cx + r1 * math.cos(a), cy - r1 * math.sin(a))], fill=gold, width=4)
    d.pieslice([cx - 40, cy - 40, cx + 40, cy + 40], 180, 360, fill=gold)
    d.line([(cx - 140, cy + 6), (cx + 140, cy + 6)], fill=gold, width=3)
    t = font(FONT, 128, 600); d.text((W / 2, 300), 'Piranesi', font=t, fill=ink, anchor='mm')
    s = font(FONT_I, 44, 500); d.text((W / 2, 390), 'by Susanna Clarke', font=s, fill=soft, anchor='mm')
    s2 = font(FONT_I, 36, 500); d.text((W / 2, 440), 'audiobook read by Chiwetel Ejiofor', font=s2, fill=soft, anchor='mm')
    # two QR panels
    qs = 360
    for i, (label, sub, url) in enumerate((('Listen on Audible', 'opens Piranesi on Audible', AUDIBLE),
                                           ('Buy the book', 'bookshop.org · supports local bookshops', BOOK))):
        pw = 430; x0 = 62 + i * (pw + 40)
        px = x0 + (pw - qs) // 2
        d.rounded_rectangle([x0, 500, x0 + pw, 1010], radius=18, fill=(250, 246, 236), outline=gold, width=3)
        im.paste(qr_img(url, qs), (px, 520))
        lf = font(FONT, 46, 700); d.text((x0 + pw / 2, 920), label, font=lf, fill=ink, anchor='mm')
        sf = font(FONT_I, 27, 500); d.text((x0 + pw / 2, 966), sub, font=sf, fill=soft, anchor='mm')
    nf = font(FONT_I, 30, 500)
    for k, line in enumerate(('Scan a code with your phone camera.',
                              'VRChat worlds cannot open websites or sign you in',
                              'from inside the world, so the links live here.')):
        d.text((W / 2, 1080 + k * 40), line, font=nf, fill=soft, anchor='mm')
    sm = font(FONT, 24, 500); d.text((W / 2, 1222), 'raise your left hand in front of your face (VR)  ·  press M (desktop)', font=sm, fill=gold, anchor='mm')
    im.save(OUT)
    print('card', OUT)

if __name__ == '__main__':
    main()
