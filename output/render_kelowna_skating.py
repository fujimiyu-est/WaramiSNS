import math, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
OUT = sys.argv[1]
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
def F(s): return ImageFont.truetype(FONT, s)

# ---------------- content (verified sources, Nov 2026) ----------------
SCENES = [
    dict(kind="hook", dur=3.6),
    dict(kind="outdoor", dur=5.0, num="01", tag="屋外・無料", name="Stuart Park", sub="ダウンタウン湖畔の屋外リンク",
         lines=[("時間", "毎日 6:00〜23:00"), ("期間", "12月上旬〜2月末ごろ"), ("料金", "無料 ※天候・整備で休みあり")]),
    dict(kind="indoor", dur=4.8, num="02", tag="Kelowna", name="MNP Place", sub="4105 Gordon Dr・Leisure Rink",
         lines=[("いつ", "平日（感謝祭〜春休み）"), ("無料", "11/27(金) 18:30〜19:45"), ("メモ", "要オンライン登録・レンタル有")],
         palette=((40, 70, 140), (230, 60, 70))),
    dict(kind="indoor", dur=4.8, num="03", tag="Kelowna", name="Rutland Arena", sub="645 Dodd Rd",
         lines=[("無料", "12/13(日) 13:00〜15:00"), ("内容", "ファミリー・ホリデースケート"), ("メモ", "スケートレンタル有")],
         palette=((30, 110, 90), (240, 190, 60))),
    dict(kind="indoor", dur=5.0, num="04", tag="West Kelowna", name="Jim Lind Arena", sub="Mount Boucherie Complex",
         lines=[("いつ", "日曜 14:45〜16:00 ほか"), ("料金", "大人$5.85 / 子ども$3.50"), ("家族", "$14・レンタル$2.95")],
         palette=((110, 50, 120), (90, 200, 230))),
    dict(kind="outro", dur=3.6),
]
TOTAL = sum(s["dur"] for s in SCENES)
NF = int(TOTAL * FPS)

random.seed(7)
SNOW = [(random.random() * W, random.random() * H, random.uniform(2, 7), random.uniform(40, 120), random.random() * 6.28) for _ in range(170)]

def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3
def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))

def gradient(top, bot):
    a = np.linspace(0, 1, H)[:, None]
    arr = (np.array(top)[None, :] * (1 - a) + np.array(bot)[None, :] * a).astype(np.uint8)
    return Image.fromarray(np.repeat(arr[:, None, :], W, axis=1), "RGB")

BG_NIGHT = gradient((14, 22, 58), (70, 90, 160))
BG_ARENA = gradient((22, 26, 40), (60, 68, 92))

# ---------------- skaters ----------------
COATS = [(230, 70, 80), (60, 140, 230), (250, 190, 60), (120, 200, 120), (240, 130, 190), (250, 250, 250), (150, 100, 220), (255, 140, 60)]
def make_skaters(n, seed):
    r = random.Random(seed)
    sk = []
    for i in range(n):
        sk.append(dict(a0=r.random() * 6.28, sp=r.uniform(0.32, 0.55) * (1 if r.random() < 0.85 else -1),
                       lane=r.uniform(0.55, 1.0), coat=r.choice(COATS), scarf=r.choice(COATS), hat=r.choice(COATS),
                       kid=r.random() < 0.3, ph=r.random() * 6.28, pair=(i % 5 == 0)))
    return sk

def draw_skater(d, x, y, s, t, k, refl=None):
    # s = scale (~1 near, smaller far). y = foot line
    if k["kid"]: s *= 0.72
    stride = math.sin(t * 5.2 + k["ph"])
    lean = 8 * s * (1 if k["sp"] > 0 else -1)
    hip = (x, y - 70 * s)
    sh = (x + lean, y - 130 * s)
    head = (x + lean * 1.3, y - 158 * s)
    lw = max(3, int(13 * s))
    pants = (40, 45, 70)
    # legs
    for sgn in (1, -1):
        fx = x + sgn * stride * 26 * s
        knee = ((hip[0] + fx) / 2 + 6 * s, y - 36 * s)
        d.line([hip, knee, (fx, y - 4 * s)], fill=pants, width=lw, joint="curve")
        d.line([(fx - 14 * s, y), (fx + 16 * s, y)], fill=(235, 240, 250), width=max(2, int(5 * s)))
        d.line([(fx - 12 * s, y - 4 * s), (fx + 12 * s, y - 4 * s)], fill=(30, 30, 40), width=max(2, int(7 * s)))
    # body
    d.polygon([(hip[0] - 22 * s, hip[1] + 8 * s), (hip[0] + 22 * s, hip[1] + 8 * s), (sh[0] + 20 * s, sh[1]), (sh[0] - 20 * s, sh[1])], fill=k["coat"])
    # arms
    for sgn in (1, -1):
        sw = -stride * sgn
        hand = (sh[0] + sgn * 30 * s + sw * 10 * s, sh[1] + 52 * s)
        d.line([(sh[0] + sgn * 16 * s, sh[1] + 6 * s), hand], fill=k["coat"], width=max(3, int(11 * s)), joint="curve")
    # scarf trailing
    dirx = -1 if k["sp"] > 0 else 1
    wav = math.sin(t * 7 + k["ph"]) * 6 * s
    d.line([(sh[0], sh[1] + 2 * s), (sh[0] + dirx * 34 * s, sh[1] + 10 * s + wav), (sh[0] + dirx * 52 * s, sh[1] + 4 * s - wav)], fill=k["scarf"], width=max(3, int(9 * s)), joint="curve")
    # head + hat
    r = 17 * s
    d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=(245, 205, 175))
    d.pieslice([head[0] - r * 1.05, head[1] - r * 1.25, head[0] + r * 1.05, head[1] + r * 0.6], 180, 360, fill=k["hat"])
    d.ellipse([head[0] - 6 * s, head[1] - r * 1.55, head[0] + 6 * s, head[1] - r * 1.15], fill=(255, 255, 255))

def rink_and_skaters(img, t, cx, cy, rx, ry, skaters, ice=(205, 228, 245), rim=(255, 255, 255)):
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - rx - 14, cy - ry - 10, cx + rx + 14, cy + ry + 10], fill=rim)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=ice)
    # ice sheen + skate marks
    for i in range(7):
        rr = 0.25 + i * 0.11
        d.arc([cx - rx * rr, cy - ry * rr, cx + rx * rr, cy + ry * rr], 0, 360, fill=(255, 255, 255, 70), width=2)
    d.ellipse([cx - rx * 0.55, cy - ry * 0.75, cx + rx * 0.1, cy - ry * 0.2], fill=(255, 255, 255, 60))
    pos = []
    for k in skaters:
        a = k["a0"] + t * k["sp"]
        x = cx + math.cos(a) * rx * 0.8 * k["lane"]
        y = cy + math.sin(a) * ry * 0.72 * k["lane"] + 30
        s = 0.62 + 0.55 * ((y - (cy - ry)) / (2 * ry))
        pos.append((y, x, s, k))
        if k["pair"]:
            pos.append((y + 2, x + 46 * s, s, dict(k, coat=k["scarf"], scarf=k["coat"], kid=True, ph=k["ph"] + 1)))
    pos.sort(key=lambda p: p[0])
    for y, x, s, k in pos:
        d.ellipse([x - 34 * s, y - 7 * s, x + 34 * s, y + 7 * s], fill=(60, 90, 130, 60))
        draw_skater(d, x, y, s, t, k)

def snow(img, t, alpha=200, n=170):
    d = ImageDraw.Draw(img, "RGBA")
    for (x0, y0, r, v, ph) in SNOW[:n]:
        y = (y0 + t * v) % H
        x = (x0 + math.sin(t * 1.3 + ph) * 25) % W
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, alpha))

def mountains(d, base, col1, col2):
    pts = [(0, base)]
    for x in range(0, W + 60, 60):
        pts.append((x, base - 170 - 90 * math.sin(x / 170) - 60 * math.sin(x / 61 + 1)))
    pts += [(W, base)]
    d.polygon(pts, fill=col1)
    pts2 = [(0, base)] + [(x, base - 80 - 50 * math.sin(x / 120 + 2)) for x in range(0, W + 60, 60)] + [(W, base)]
    d.polygon(pts2, fill=col2)

def outdoor_bg(t):
    img = BG_NIGHT.copy()
    d = ImageDraw.Draw(img, "RGBA")
    # stars
    r = random.Random(3)
    for _ in range(90):
        x, y = r.random() * W, r.random() * 650
        a = int(120 + 120 * math.sin(t * 3 + x))
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255, max(0, a)))
    mountains(d, 820, (40, 55, 105), (30, 42, 85))
    # lake
    d.rectangle([0, 820, W, 960], fill=(35, 60, 115))
    for i in range(10):
        yy = 835 + i * 13
        d.line([(80 + 60 * math.sin(t + i), yy), (420 + 60 * math.sin(t + i), yy)], fill=(255, 220, 140, 50), width=3)
    # string lights
    for row in range(2):
        y0 = 720 + row * 40
        for i in range(24):
            x = 20 + i * 45
            y = y0 + 25 * math.sin(i * 0.7)
            c = [(255, 90, 90), (255, 220, 90), (100, 220, 255), (140, 255, 140)][(i + row) % 4]
            a = int(170 + 85 * math.sin(t * 4 + i))
            d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=c + (60,))
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=c + (a,))
    # tree
    tx, ty = 900, 900
    for i in range(4):
        w = 120 - i * 25
        d.polygon([(tx - w, ty - i * 55), (tx + w, ty - i * 55), (tx, ty - i * 55 - 110)], fill=(30, 110, 70))
    d.polygon([(tx, ty - 290), (tx + 14, ty - 262), (tx - 14, ty - 262)], fill=(255, 220, 80))
    d.rectangle([0, 950, W, H], fill=(225, 235, 248))
    return img

def indoor_bg(t, pal):
    img = BG_ARENA.copy()
    d = ImageDraw.Draw(img, "RGBA")
    # roof trusses + lights
    for i in range(9):
        x = i * 135
        d.line([(x, 120), (x + 135, 420)], fill=(90, 98, 120), width=6)
        d.line([(x + 135, 120), (x, 420)], fill=(90, 98, 120), width=6)
    d.line([(0, 120), (W, 120)], fill=(100, 108, 130), width=8)
    for i in range(5):
        x = 110 + i * 215
        d.ellipse([x - 26, 400, x + 26, 430], fill=(255, 250, 225))
        d.polygon([(x - 26, 415), (x + 26, 415), (x + 170, 980), (x - 170, 980)], fill=(255, 250, 220, 14))
    # stands
    for r in range(7):
        y = 520 + r * 50
        d.rectangle([0, y, W, y + 44], fill=lerp(pal[0], (20, 20, 30), r * 0.08))
        rr = random.Random(r)
        for i in range(0, W, 34):
            if rr.random() < 0.35:
                c = rr.choice(COATS)
                bob = 3 * math.sin(t * 4 + i)
                d.ellipse([i + 8, y + 4 + bob, i + 26, y + 22 + bob], fill=c + (200,))
    # banners
    for i in range(4):
        x = 140 + i * 250
        d.rectangle([x, 440, x + 110, 500], fill=pal[1])
    d.rectangle([0, 880, W, H], fill=(210, 222, 236))
    # boards
    d.rectangle([0, 870, W, 905], fill=(250, 250, 252))
    d.rectangle([0, 900, W, 910], fill=pal[1])
    return img

def rounded(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def text(d, xy, s, size, fill=(255, 255, 255), stroke=0, sfill=(0, 0, 0), anchor="la"):
    d.text(xy, s, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)

def info_overlay(img, sc, lt):
    d = ImageDraw.Draw(img, "RGBA")
    e = ease(lt / 0.45)
    # top badge
    x0 = 70 - int((1 - e) * 500)
    lab = f"{sc['num']}  {sc['tag']}"
    bw = int(d.textlength(lab, font=F(34))) + 60
    rounded(d, [x0, 150, x0 + bw, 215], 32, (255, 255, 255, 235))
    text(d, (x0 + bw // 2, 183), lab, 34, (25, 40, 90), anchor="mm")
    ey = ease((lt - 0.12) / 0.45)
    text(d, (70, 240 + int((1 - ey) * 40)), sc["name"], 104, (255, 255, 255, int(255 * ey)), stroke=8, sfill=(15, 25, 70))
    text(d, (74, 370), sc["sub"], 42, (255, 255, 255, int(255 * ey)), stroke=5, sfill=(15, 25, 70))
    # info card
    ce = ease((lt - 0.35) / 0.5)
    cy0 = 1250 + int((1 - ce) * 120)
    rounded(d, [50, cy0, 940, cy0 + 345], 36, (255, 255, 255, int(240 * ce)))
    rounded(d, [50, cy0, 64, cy0 + 345], 7, (60, 140, 230, int(255 * ce)))
    for i, (k, v) in enumerate(sc["lines"]):
        le = ease((lt - 0.55 - i * 0.18) / 0.35)
        if le <= 0: continue
        y = cy0 + 40 + i * 100
        xo = int((1 - le) * 60)
        rounded(d, [90 + xo, y, 220 + xo, y + 64], 18, (25, 60, 140, int(255 * le)))
        text(d, (155 + xo, y + 33), k, 34, (255, 255, 255, int(255 * le)), anchor="mm")
        text(d, (245 + xo, y + 33), v, 44, (20, 30, 60, int(255 * le)), anchor="lm")

def frame(fi):
    t = fi / FPS
    acc = 0
    for si, sc in enumerate(SCENES):
        if t < acc + sc["dur"] or si == len(SCENES) - 1:
            lt = t - acc; break
        acc += sc["dur"]
    k = sc["kind"]
    if k in ("hook", "outdoor", "outro"):
        img = outdoor_bg(t)
        rink_and_skaters(img, t, 540, 1080, 520, 175, SK_OUT)
        snow(img, t)
    else:
        img = indoor_bg(t, sc["palette"])
        rink_and_skaters(img, t, 540, 1080, 540, 185, SK_IN[si], ice=(222, 234, 246), rim=(245, 245, 250))
    d = ImageDraw.Draw(img, "RGBA")
    if k == "hook":
        d.rectangle([0, 0, W, H], fill=(10, 20, 60, 70))
        e = ease(lt / 0.5)
        sc_ = 0.7 + 0.3 * e
        text(d, (540, 300), "冬のケロウナで", int(78 * sc_), (255, 255, 255), stroke=7, sfill=(15, 25, 70), anchor="mm")
        text(d, (540, 420), "絶対やりたい！", int(98 * sc_), (255, 225, 90), stroke=8, sfill=(15, 25, 70), anchor="mm")
        e2 = ease((lt - 0.5) / 0.5)
        if e2 > 0:
            rounded(d, [120, 1300, 960, 1500], 50, (255, 255, 255, int(240 * e2)))
            text(d, (540, 1365), "パブリックスケート", 70, (25, 50, 120, int(255 * e2)), anchor="mm")
            text(d, (540, 1450), "おすすめ 4 選", 58, (230, 70, 80, int(255 * e2)), anchor="mm")
    elif k == "outro":
        d.rectangle([0, 0, W, H], fill=(10, 20, 60, 110))
        e = ease(lt / 0.5)
        text(d, (540, 330), "行く前に最新スケジュールを", 58, (255, 255, 255, int(255 * e)), stroke=6, sfill=(15, 25, 70), anchor="mm")
        text(d, (540, 420), "チェック！", 88, (255, 225, 90, int(255 * e)), stroke=8, sfill=(15, 25, 70), anchor="mm")
        e2 = ease((lt - 0.3) / 0.5)
        rounded(d, [90, 1260, 990, 1560], 40, (255, 255, 255, int(240 * e2)))
        text(d, (540, 1320), "時間は変更・休止になることがあります", 36, (90, 90, 110, int(255 * e2)), anchor="mm")
        text(d, (540, 1400), "kelowna.ca/skating", 52, (25, 60, 140, int(255 * e2)), anchor="mm")
        text(d, (540, 1480), "westkelownacity.ca", 52, (25, 60, 140, int(255 * e2)), anchor="mm")
        e3 = ease((lt - 1.2) / 0.4)
        if e3 > 0:
            text(d, (540, 1660), "保存して冬に行こう ⛸" if False else "保存して冬に行こう！", 60, (255, 255, 255, int(255 * e3)), stroke=6, sfill=(15, 25, 70), anchor="mm")
    else:
        info_overlay(img, sc, lt)
    # scene transition flash
    if si > 0 and lt < 0.18:
        a = int(255 * (1 - lt / 0.18))
        d.rectangle([0, 0, W, H], fill=(255, 255, 255, a))
    # progress bar
    d.rectangle([0, 0, int(W * t / TOTAL), 8], fill=(255, 225, 90))
    return img

SK_OUT = make_skaters(13, 1)
SK_IN = {i: make_skaters(11, 10 + i) for i in range(len(SCENES))}

# ---------------- music ----------------
def music(path):
    sr = 44100
    n = int(TOTAL * sr) + sr
    out = np.zeros(n)
    bpm = 104; beat = 60 / bpm
    chords = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 67]]
    mel = [76, 74, 71, 74, 76, 79, 76, 74, 72, 71, 69, 71, 72, 74, 71, 67]
    def note(f, start, dur, amp, decay):
        i0 = int(start * sr); L = int(dur * sr)
        if i0 >= n: return
        L = min(L, n - i0)
        tt = np.arange(L) / sr
        env = np.exp(-tt * decay) * np.minimum(1, tt * 200)
        w = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3.01 * f * tt)
        out[i0:i0 + L] += amp * env * w
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bars = int(TOTAL / (beat * 4)) + 2
    for b in range(bars):
        ch = chords[b % 4]
        for j in range(8):
            note(hz(ch[j % 4] - 12 + (12 if j % 4 == 3 else 0)), (b * 4 + j * 0.5) * beat, 1.2, 0.09, 3.5)
        note(hz(ch[0] - 24), b * 4 * beat, beat * 4, 0.16, 0.9)
        for j in range(4):
            note(hz(mel[(b * 4 + j) % 16]), (b * 4 + j) * beat, 1.0, 0.07, 2.5)
            note(hz(mel[(b * 4 + j) % 16] + 12), (b * 4 + j) * beat + 0.02, 0.8, 0.025, 4)
    # sleigh-bell shimmer
    rng = np.random.default_rng(1)
    for k in range(int(TOTAL / beat * 2)):
        i0 = int(k * beat / 2 * sr); L = int(0.08 * sr)
        if i0 + L < n:
            out[i0:i0 + L] += 0.03 * rng.standard_normal(L) * np.exp(-np.arange(L) / sr * 60)
    out = out[:int(TOTAL * sr)]
    fade = int(1.2 * sr); out[-fade:] *= np.linspace(1, 0, fade); out[:2000] *= np.linspace(0, 1, 2000)
    out = out / np.max(np.abs(out)) * 0.8
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    wav = OUT + ".wav"
    music(wav)
    if len(sys.argv) > 2:  # preview stills
        for fi in map(int, sys.argv[2:]):
            frame(fi).save(f"{OUT}_{fi}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                          "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for fi in range(NF):
        p.stdin.write(frame(fi).tobytes())
    p.stdin.close(); p.wait()
    print("done", NF, TOTAL)
