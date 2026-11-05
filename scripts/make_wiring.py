"""Wiring diagram: product photos collaged on a canvas with the connections drawn on top.

    .venv/bin/python scripts/make_wiring.py   -> docs/figures/wiring.png

Photos are in docs/images (sources: docs/images/SOURCES.md).
"""

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


def main() -> None:
    from propmotor.plotting import register_local_fonts

    register_local_fonts()
    plt.rcParams["font.family"] = FONT
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set_xlim(0, 105)
    ax.set_ylim(-2, 65)
    ax.set_aspect("equal")
    ax.axis("off")

    # ---- power path (left to right) ---------------------------------------
    card(ax, "psu.jpg", 1, 34, 18, 20, "安定化電源 菊水 PWR401L", "背面の出力端子を使う\n12.7 V / CC 10 A / OVP 16 V")
    card(ax, "banana.jpg", 22.5, 42, 11, 6, "", "")
    card(ax, "breaker.jpg", 37, 37, 11, 14, "DC ブレーカ 15 A", "主遮断と過電流保護\n(写真は外観例, DC 定格品を使う)")
    card(ax, "stand.png", 53, 30, 16, 24, "Tyto Robotics 1585", "電圧・電流・推力・トルク計測\nESC 信号出力・光学回転計")
    card(ax, "wago.jpg", 73, 48, 9, 7, "", "")
    label(ax, 77.5, 55.5, "WAGO 221: ESC の裸線と\nXT60 ピグテールを接続", size=6.6)
    card(ax, "esc.jpg", 87, 40, 18, 14, "ESC  Skywalker 40A V2", "ブレーキ OFF・DEO OFF\n低電圧カット OFF")
    card(ax, "motor.jpg", 75, 12, 11, 11, "モータ", "Dualsky ECO\n2316C 880KV")
    card(ax, "prop.jpg", 92, 12, 12, 11, "プロペラ", "APC 8×3.8SF\n(LPARM12SF リング)")

    pair(ax, [(19, 45), (37, 45)])
    label(ax, 28, 41, "バナナ→XT60 ケーブル (14 AWG)", va="top", size=6.6)
    pair(ax, [(48, 45), (53, 45)])
    pair(ax, [(69, 51.5), (73, 51.5)])
    pair(ax, [(82, 51.5), (87, 51.5)])

    # motor phases: ESC left side -> motor (3.5 mm bullets, no soldering)
    for k, dy in enumerate((-1.2, 0, 1.2)):
        wire(ax, [(87, 44 + dy), (82.5 + dy, 44 + dy), (82.5 + dy, 23)], PHASE, lw=1.6)
    label(ax, 85, 30, "3.5 mm バレット\n(挿すだけ)", ha="left", va="center", size=6.6)
    # the motor sits on the stand, the prop on the motor
    ax.annotate("", xy=(75, 19), xytext=(69.5, 31), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0,
                                                                   connectionstyle="arc3,rad=0.2"), zorder=4)
    label(ax, 71.5, 27, "スタンドの\n取付板に固定", ha="left", size=6.4)
    ax.plot([86, 92], [17.5, 17.5], color=MUTED, lw=1.0, zorder=4)

    # ESC throttle signal from the stand
    wire(ax, [(100, 54), (100, 62), (61, 62), (61, 54)], SIG, lw=1.6, ls=(0, (4, 2)))
    label(ax, 80.5, 62.5, "ESC 信号線 (サーボ PWM 50 Hz, 1000–2000 µs)", size=6.6)

    # PC
    ax.add_patch(FancyBboxPatch((52.5, 1), 17, 7, boxstyle="round,pad=0,rounding_size=1.2", fc="#f4f3ef", ec=CARD,
                                lw=1.0, zorder=2))
    ax.text(61, 4.5, "PC (RCbenchmark)\nスロットル・カットオフ", ha="center", va="center", fontsize=7.4, color=INK,
            zorder=5, linespacing=1.3)
    wire(ax, [(61, 8), (61, 21.5)], USB, lw=1.6)
    label(ax, 62, 11, "USB", ha="left", va="center", size=6.6)

    # emergency stop -> PWR401L J1 (output control; no DC current is switched)
    card(ax, "estop.jpg", 1, 3, 14, 11, "非常停止 (1a1b)", "")
    wire(ax, [(15, 8.5), (23, 8.5), (23, 37), (19, 37)], ESTOP, lw=1.8)
    label(ax, 24.5, 20, "J1 ケーブル (OP03-PWR-01)\nb 接点 → J1-15/17 (OUTPUT CONT)\na 接点 → J1-15/16 (SHUT DOWN)",
          ha="left", va="center", size=6.6)

    # legend
    lx, ly = 32, 0.5
    for i, (c, t, ls) in enumerate(((RED, "電源 +", "-"), (BLACK, "電源 −", "-"), (PHASE, "モータ三相", "-"),
                                    (SIG, "ESC 信号", (0, (4, 2))), (ESTOP, "非常停止 (J1)", "-"), (USB, "USB", "-"))):
        yy = ly + 7.5 - i * 1.5
        ax.plot([lx, lx + 3], [yy, yy], color=c, lw=2.0, ls=ls)
        ax.text(lx + 3.8, yy, t, va="center", fontsize=6.6, color=INK2)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "wiring.png", dpi=220, bbox_inches="tight", facecolor="white")
    print("wrote", OUT / "wiring.png")


if __name__ == "__main__":
    main()
