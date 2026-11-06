"""Photo wiring diagrams. Run with .venv/bin/python scripts/make_wiring.py."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "images"
OUT = ROOT / "docs" / "figures"

INK, INK2, MUTED, CARD = "#1a1a1a", "#52514e", "#898781", "#d9d8d2"
RED, BLACK, PHASE, SIG, ESTOP, USB = "#d03b3b", "#2b2b2b", "#8a8a8a", "#eb6834", "#0ca30c", "#2a78d6"
OPT = "#8153ac"
FONT = ["Futura PT", "FTT-Cezanne", "Noto Sans CJK JP"]


def trim(im: Image.Image, tol: int = 18) -> Image.Image:
    """Crop away a uniform background (taken from the corner pixel)."""
    import numpy as np

    a = np.asarray(im).astype(int)
    bg = a[2, 2, :3]
    alpha = a[:, :, 3]
    mask = (np.abs(a[:, :, :3] - bg).max(axis=2) > tol) & (alpha > 10)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return im
    m = 6
    return im.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, im.width), min(ys.max() + m, im.height)))


def card(ax, name, x, y, w, h, title, sub="", bg="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=bg, ec=CARD, lw=1.0,
                                zorder=2))
    if name:
        im = trim(Image.open(IMG / name).convert("RGBA"))
        iw, ih = im.size
        pad = 0.8
        bw, bh = w - 2 * pad, h - 2 * pad
        s = min(bw / iw, bh / ih)
        dw, dh = iw * s, ih * s
        x0, y0 = x + (w - dw) / 2, y + (h - dh) / 2
        ax.imshow(im, extent=(x0, x0 + dw, y0, y0 + dh), zorder=3, interpolation="lanczos")
    ax.text(x + w / 2, y - 1.2, title, ha="center", va="top", fontsize=8.6, color=INK, fontweight="bold", zorder=5)
    if sub:
        ax.text(x + w / 2, y - 4.0, sub, ha="center", va="top", fontsize=7.0, color=INK2, zorder=5, linespacing=1.3)


def wire(ax, pts, color, lw=2.2, ls="-", z=1.5):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="round", solid_joinstyle="round", zorder=z)


def pair(ax, pts, dy=1.0):
    """+ (red) and - (black) conductors drawn side by side."""
    wire(ax, [(x, y + dy / 2) for x, y in pts], RED)
    wire(ax, [(x, y - dy / 2) for x, y in pts], BLACK)


def label(ax, x, y, text, ha="center", va="bottom", color=INK2, size=7.0):
    ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color, zorder=6, linespacing=1.3,
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", OUT / f"{name}.png")


def power_diagram():
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set(xlim=(0, 105), ylim=(-2, 65), aspect="equal")
    ax.axis("off")

    card(ax, "psu.jpg", 1, 34, 18, 20, "安定化電源 菊水 PWR401L",
         "背面出力\n12.7 V / CC 10 A / OVP 16 V")
    card(ax, "cp30fm_1p.jpg", 28, 39, 11, 15, "DC ブレーカ", "CP30FM-1P015 / 15 A")
    card(ax, "stand.png", 49, 30, 17, 24, "Tyto Robotics 1585", "電圧・電流・推力・トルク計測")
    card(ax, "esc.jpg", 84, 40, 20, 14, "ESC Skywalker 40A V2",
         "ブレーキ OFF・DEO OFF\n低電圧カット OFF")
    card(ax, "motor.jpg", 75, 12, 11, 11, "モータ", "Dualsky ECO\n2316C 880KV")
    card(ax, "prop.jpg", 92, 12, 12, 11, "プロペラ", "APC 8×3.8SF")

    wire(ax, [(19, 45.6), (28, 45.6)], RED)
    wire(ax, [(39, 45.6), (49, 45.6)], RED)
    wire(ax, [(19, 44.4), (23.5, 44.4), (23.5, 31.5),
              (44, 31.5), (44, 44.4), (49, 44.4)], BLACK)
    label(ax, 23.5, 48, "14 AWG", size=6.6)
    pair(ax, [(66, 51), (84, 51)], dy=1.2)
    label(ax, 75, 54, "ESC 電源線を直接ねじ固定", size=6.6)

    for dy in (-1.2, 0, 1.2):
        wire(ax, [(84, 44 + dy), (80 + dy, 44 + dy), (80 + dy, 23)], PHASE, lw=1.6)
    label(ax, 84, 29, "3.5 mm バレット", ha="left", va="center", size=6.6)
    wire(ax, [(86, 17.5), (92, 17.5)], MUTED, lw=1)

    wire(ax, [(96, 54), (96, 62), (57.5, 62), (57.5, 54)], SIG, lw=1.6, ls="--")
    label(ax, 77, 62.5, "ESC 信号：PWM・GND（BEC 赤線は絶縁）", size=6.6)

    card(ax, "optical_rpm.jpg", 63, 13, 9, 8, "光学 RPM プローブ")
    wire(ax, [(63, 17), (61, 17), (61, 22), (69, 22), (69, 34), (66, 34)], OPT, lw=1.6, ls="--")
    label(ax, 69.8, 27, "S1", ha="left", size=6.6, color=OPT)
    ax.annotate("", xy=(76, 16), xytext=(72, 16),
                arrowprops=dict(arrowstyle="->", color=OPT, lw=1.2))

    ax.add_patch(FancyBboxPatch((48.5, 1), 17, 7, boxstyle="round,pad=0,rounding_size=1.2",
                               fc="#f4f3ef", ec=CARD, lw=1, zorder=2))
    ax.text(57, 4.5, "PC (RCbenchmark)", ha="center", va="center", fontsize=7.4, color=INK, zorder=5)
    wire(ax, [(55, 8), (55, 22), (47, 22), (47, 35), (49, 35)], USB, lw=1.6)
    label(ax, 54, 12, "USB", ha="right", va="center", size=6.6)

    card(ax, "estop_xw1e_bv411mr.jpg", 1, 3, 14, 11,
         "非常停止（1a1b）", "XW1E-BV411MR")
    wire(ax, [(15, 8.5), (21.5, 8.5), (21.5, 37), (19, 37)], ESTOP, lw=1.8)
    label(ax, 23, 20, "J1 ケーブル\nOP03-PWR-01", ha="left", va="center", size=6.6)

    for i, (c, t, ls) in enumerate(((RED, "電源 +", "-"), (BLACK, "電源 −", "-"),
            (PHASE, "モータ三相", "-"), (SIG, "ESC 信号", "--"),
            (OPT, "光学 RPM", "--"), (ESTOP, "非常停止 (J1)", "-"), (USB, "USB", "-"))):
        yy = 11 - i * 1.6
        wire(ax, [(31, yy), (34, yy)], c, lw=2, ls=ls)
        ax.text(34.8, yy, t, va="center", fontsize=6.6, color=INK2)
    save(fig, "wiring")


def estop_diagram():
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.set(xlim=(0, 100), ylim=(7, 63), aspect="equal")
    ax.axis("off")
    card(ax, "j1_op03.jpg", 2, 44, 22, 17, "OP03-PWR-01")
    card(ax, "estop_xw1e_bv411mr.jpg", 76, 44, 22, 17, "XW1E-BV411MR（1a1b）")
    ax.add_patch(FancyBboxPatch((2, 10), 31, 29, boxstyle="round,pad=0,rounding_size=1.2",
                               fc="white", ec=CARD, lw=1, zorder=2))
    ax.text(17.5, 38, "PWR401L  J1", fontsize=10, ha="center", va="top", color=INK)
    for y, name, c in [(33, "17  OUTPUT CONT", ESTOP), (27, "15  A GND", ESTOP),
                       (21, "16  SHUT DOWN", SIG), (15, " 5  A GND", SIG)]:
        ax.text(4, y, name, fontsize=9, color=INK, va="center")
        wire(ax, [(33, y), (70, y)], c, lw=1.8)
        ax.plot(70, y, "o", ms=4, color=c)
    wire(ax, [(70, 33), (70, 27)], ESTOP, lw=1.8)
    wire(ax, [(70, 15), (72, 20)], SIG, lw=1.8)
    ax.text(74, 30, "11–12  b 接点（通常：閉）", fontsize=8.5, color=ESTOP, va="center")
    ax.text(74, 18, "33–34  a 接点（通常：開）", fontsize=8.5, color=SIG, va="center")
    save(fig, "estop_wiring")


def main():
    from propmotor.plotting import register_local_fonts
    register_local_fonts()
    plt.rcParams["font.family"] = FONT
    OUT.mkdir(parents=True, exist_ok=True)
    power_diagram()
    estop_diagram()


if __name__ == "__main__":
    main()
