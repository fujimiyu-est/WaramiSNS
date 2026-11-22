import subprocess, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
PREVIEW = [float(x) for x in sys.argv[3:]]
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
_fc = {}
def F(s):
    if s not in _fc: _fc[s] = ImageFont.truetype(FONT, s)
    return _fc[s]

def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

# segments: (kind, src_start, src_dur, speed or hold, out_dur, overlay)
SEGS = [
    dict(kind="clip", ss=8.0, sd=1.35, out=2.6, ov="hook"),
    dict(kind="still", ss=1.0, out=3.6, ov=dict(num="1", area="Kelowna", name="MNP Place",
         rows=[("いつ", "平日（感謝祭〜春休み）"), ("無料日", "11/27(金) 18:30〜19:45"), ("メモ", "要オンライン登録・レンタル有")])),
    dict(kind="still", ss=3.0, out=3.6, ov=dict(num="2", area="Kelowna", name="Rutland Arena",
         rows=[("無料日", "12/13(日) 13:00〜15:00"), ("内容", "ファミリー・ホリデースケート"), ("メモ", "スケートレンタル有")])),
    dict(kind="still", ss=5.0, out=3.6, ov=dict(num="3", area="Kelowna", name="Memorial Arena",
         rows=[("場所", "ダウンタウン・1945年の老舗"), ("メモ", "レンタルなし・自分の靴で"), ("時間", "公式サイトで要確認")])),
    dict(kind="still", ss=7.0, out=3.6, ov=dict(num="4", area="West Kelowna", name="Jim Lind Arena",
         rows=[("いつ", "日曜 14:45〜16:00 ほか"), ("料金", "大人$5.85 / 子ども$3.50"), ("家族", "$14・レンタル$2.95")])),
    dict(kind="clip", ss=10.0, sd=3.2, out=3.2, ov="bonus"),
    dict(kind="clip", ss=13.25, sd=2.0, out=2.6, ov="outro"),
]
TOTAL = sum(s["out"] for s in SEGS)

def read_clip(ss, sd, out):
    """yield `out*FPS` frames covering src [ss, ss+sd] (slowed if out > sd)"""
    n = int(round(out * FPS))
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", str(ss), "-t", str(sd), "-i", SRC,
           "-vf", f"setpts={out/sd:.5f}*PTS,fps={FPS},scale={W}:{H}", "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        b = p.stdout.read(W * H * 3)
        if len(b) == W * H * 3: last = Image.frombytes("RGB", (W, H), b)
        yield last
    p.stdout.close(); p.wait()

def read_still(ss):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(ss), "-i", SRC, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE).stdout
    return Image.frombytes("RGB", (W, H), b)

def T(d, xy, s, size, fill=(255, 255, 255, 255), stroke=0, sfill=(0, 0, 0, 255), anchor="la"):
    d.text(xy, s, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)

def a(c, al): return c[:3] + (int(255 * al),)

def caption_box(d, cx, cy, s, size, fg, bg, al):
    col = {(255, 222, 60): (255, 222, 60), (220, 50, 70): (255, 95, 115)}.get(tuple(bg), (255, 255, 255))
    T(d, (cx, cy), s, size, a(col, al), stroke=max(5, size // 9), sfill=a((0, 0, 0), al), anchor="mm")

def overlay(img, seg, lt, t):
    ov = seg["ov"]
    d = ImageDraw.Draw(img, "RGBA")
    if ov == "hook":
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, 60))
        e = ease(lt / 0.4)
        caption_box(d, 540, 430, "冬のケロウナで", 64, (255, 255, 255), (20, 20, 20), e)
        e2 = ease((lt - 0.25) / 0.4)
        caption_box(d, 540, 560, "絶対やりたい⛸".replace("⛸", ""), 92, (20, 20, 20), (255, 222, 60), e2)
        e3 = ease((lt - 0.6) / 0.4)
        caption_box(d, 540, 700, "パブリックスケート 4選", 66, (255, 255, 255), (220, 50, 70), e3)
    elif ov == "bonus":
        e = ease(lt / 0.4)
        caption_box(d, 540, 300, "おまけ：湖畔の屋外リンク", 54, (20, 20, 20), (255, 222, 60), e)
        caption_box(d, 540, 410, "Stuart Park（無料）", 70, (255, 255, 255), (20, 20, 20), e)
        e2 = ease((lt - 0.4) / 0.4)
        y0 = 1330 + int((1 - e2) * 60)
        rows = [("時間", "毎日 6:00〜23:00"), ("期間", "12月上旬〜2月末ごろ（天候次第）")]
        for i, (k, v) in enumerate(rows):
            y = y0 + 40 + i * 95
            T(d, (80, y + 33), k, 44, a((255, 222, 60), e2), stroke=6, sfill=a((0, 0, 0), e2), anchor="lm")
            T(d, (215, y + 33), v, 46, a((255, 255, 255), e2), stroke=6, sfill=a((0, 0, 0), e2), anchor="lm")
    elif ov == "outro":
        e = ease(lt / 0.4)
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(80 * e)))
        caption_box(d, 540, 420, "時間は変わることがあるので", 52, (255, 255, 255), (20, 20, 20), e)
        caption_box(d, 540, 530, "行く前に公式サイトをチェック！", 58, (20, 20, 20), (255, 222, 60), e)
        e2 = ease((lt - 0.5) / 0.4)
        caption_box(d, 540, 1380, "kelowna.ca/skating", 48, (255, 255, 255), (20, 60, 140), e2)
        caption_box(d, 540, 1490, "westkelownacity.ca", 48, (255, 255, 255), (20, 60, 140), e2)
        e3 = ease((lt - 1.0) / 0.4)
        caption_box(d, 540, 660, "保存して冬に行こう！", 60, (255, 255, 255), (220, 50, 70), e3)
    else:
        # number badge top-right of map card area + info card over the lower part
        e = ease(lt / 0.35)
        lab = f"{ov['num']} / 4   {ov['area']}"
        caption_box(d, 540, 960 + int((1 - e) * 40), lab, 48, (20, 20, 20), (255, 222, 60), e)
        e2 = ease((lt - 0.2) / 0.4)
        y0 = 1010 + int((1 - e2) * 80)
        for i, (k, v) in enumerate(ov["rows"]):
            le = ease((lt - 0.45 - i * 0.2) / 0.35)
            if le <= 0: continue
            y = y0 + 32 + i * 100
            xo = int((1 - le) * 50)
            T(d, (60 + xo, y + 34), k, 44, a((255, 222, 60), le), stroke=6, sfill=a((0, 0, 0), le), anchor="lm")
            T(d, (230 + xo, y + 34), v, 48, a((255, 255, 255), le), stroke=6, sfill=a((0, 0, 0), le), anchor="lm")
    # progress bar
    d.rectangle([0, 0, int(W * t / TOTAL), 10], fill=(255, 222, 60, 255))

def frames():
    t0 = 0.0
    for seg in SEGS:
        n = int(round(seg["out"] * FPS))
        if seg["kind"] == "clip":
            src = read_clip(seg["ss"], seg["sd"], seg["out"])
        else:
            base = read_still(seg["ss"])
            def zoomed(base=base, n=n):
                for i in range(n):
                    z = 1.0 + 0.05 * i / n
                    cw, ch = W / z, H / z
                    x0, y0 = (W - cw) / 2, (H - ch) * 0.3
                    yield base.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
            src = zoomed()
        for i, fr in enumerate(src):
            lt = i / FPS
            yield t0 + lt, seg, lt, fr
        t0 += seg["out"]

if PREVIEW:
    for t, seg, lt, fr in frames():
        if any(abs(t - p) < 0.5 / FPS for p in PREVIEW):
            img = fr.copy(); overlay(img, seg, lt, t); img.save(f"{OUT}_{t:.1f}.png")
    sys.exit()

enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", OUT],
                       stdin=subprocess.PIPE)
for t, seg, lt, fr in frames():
    img = fr.copy(); overlay(img, seg, lt, t)
    enc.stdin.write(img.tobytes())
enc.stdin.close(); enc.wait()
print("done", TOTAL)
