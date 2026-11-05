"""Figures for understanding and selection (matplotlib, static; used by notebooks and the typst doc).

Style rules (kept consistent across all figures):
* one y-scale per axes (no twin axes) - different quantities go to separate panels;
* entity colours are fixed: UIUC measured = slot 1 (blue), APC theory = slot 2 (orange),
  design envelope = slot 3 (aqua);
* context (motor characteristic lines, limits) is drawn in neutral greys;
* feasibility uses status colours only together with a text label.
"""

from __future__ import annotations

import math
from typing import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from .units import N_TO_GF, RADS_TO_RPM, rpm_to_rads

# ---- palette (dataviz reference instance, light mode) ----------------------
SURFACE = "#ffffff"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
C_MEASURED, C_THEORY, C_DESIGN = SERIES[0], SERIES[1], SERIES[2]
BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
             "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
GREY_RAMP = ["#c3c2b7", "#a9a79e", "#898781", "#6d6b66", "#52514e", "#3a3936"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
LW = 1.6

SEQ_BLUE = LinearSegmentedColormap.from_list("seq_blue", BLUE_RAMP)
SEQ_GREY = LinearSegmentedColormap.from_list("seq_grey", ["#fbfaf8", "#e9e8e2", "#c9c7bf", "#a9a79e"])


def source_color(ds) -> str:
    return {"measured": C_MEASURED, "theory": C_THEORY, "envelope": C_DESIGN}.get(ds.kind, INK2)


def use_style() -> None:
    mpl.rcParams.update({
        "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 9.5,
        "axes.labelcolor": INK2,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.facecolor": SURFACE,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "legend.labelcolor": INK,
        "lines.linewidth": LW,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "lines.dash_capstyle": "round",
        "lines.markersize": 6,
        "figure.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": SURFACE,
        "svg.fonttype": "path",
        "axes.unicode_minus": True,
        "text.color": INK,
    })


def _vline(ax, x, label, color=MUTED, y=0.97, ha="right"):
    ax.axvline(x, color=color, lw=1.0, zorder=1)
    ax.text(x, y, label, transform=ax.get_xaxis_transform(), ha=ha, va="top", fontsize=8, color=INK2,
            rotation=0, bbox=dict(fc=SURFACE, ec="none", pad=1.0))


def _dot(ax, x, y, color, size=7, zorder=5):
    ax.plot(x, y, "o", ms=size, color=color, mec=SURFACE, mew=1.6, zorder=zorder)


def _plot_source(ax, ds, rpm, values, label=None, **kw):
    """Solid inside the data range, dotted where extrapolated."""
    ext = ds.is_extrapolated(rpm)
    c = source_color(ds)
    inside = np.where(~ext, values, np.nan)
    ax.plot(rpm, inside, color=c, label=label or ds.label, **kw)
    if ext.any():
        # include the boundary points so the dotted part connects
        outside = np.where(ext | np.r_[ext[1:], False] | np.r_[False, ext[:-1]], values, np.nan)
        ax.plot(rpm, outside, color=c, ls=(0, (1.5, 2.2)), **kw)


# ---------------------------------------------------------------------------
# 1. propeller
# ---------------------------------------------------------------------------

def fig_prop_coefficients(datasets, rpm_limit: float, rpm_max_plot: float = 9_000):
    use_style()
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.3), constrained_layout=True)
    rpm = np.linspace(1000, rpm_max_plot, 400)
    for ds in datasets:
        _plot_source(axs[0], ds, rpm, ds.ct_at(rpm))
        _plot_source(axs[1], ds, rpm, ds.cp_at(rpm))
        _plot_source(axs[2], ds, rpm, ds.figure_of_merit(rpm))
        if ds.kind == "measured":
            for ax, v in zip(axs, (ds.ct, ds.cp, ds.figure_of_merit(ds.rpm))):
                ax.plot(ds.rpm, v, "o", ms=3.2, color=source_color(ds), mew=0, zorder=4)
    axs[0].set(title="推力係数 $C_T$", xlabel="回転数 [rpm]", ylim=(0.08, 0.15))
    axs[1].set(title="パワー係数 $C_P$", xlabel="回転数 [rpm]", ylim=(0.035, 0.06))
    axs[2].set(title="フィギュア・オブ・メリット FM", xlabel="回転数 [rpm]", ylim=(0.5, 0.8))
    for ax in axs:
        _vline(ax, rpm_limit, f"APC上限\n{rpm_limit:,.0f}", ha="left" if ax is axs[2] else "right")
    axs[0].legend(loc="lower right")
    axs[1].text(0.02, 0.04, "点線 = 実測範囲外の外挿 / 点 = 実測値", transform=axs[1].transAxes, fontsize=8, color=INK2)
    return fig


def fig_prop_dimensional(datasets, rho: float, rpm_limit: float, rpm_max_plot: float = 9000):
    use_style()
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.3), constrained_layout=True)
    rpm = np.linspace(500, rpm_max_plot, 400)
    for ds in datasets:
        _plot_source(axs[0], ds, rpm, ds.thrust(rpm, rho) * N_TO_GF)
        _plot_source(axs[1], ds, rpm, ds.torque(rpm, rho) * 1000)
        _plot_source(axs[2], ds, rpm, ds.power(rpm, rho))
    for ax, f, unit, fmt in ((axs[0], lambda d, r: d.thrust(r, rho) * N_TO_GF, "gf", "{:.0f} gf"),
                             (axs[1], lambda d, r: d.torque(r, rho) * 1000, "mN·m", "{:.0f} mN·m"),
                             (axs[2], lambda d, r: d.power(r, rho), "W", "{:.0f} W")):
        for ds in datasets:
            v = float(f(ds, rpm_limit))
            _dot(ax, rpm_limit, v, source_color(ds))
            ax.annotate(fmt.format(v), (rpm_limit, v), xytext=(-6, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=8, color=INK)
        _vline(ax, rpm_limit, "", y=0.97)
    axs[0].set(title="推力 T", xlabel="回転数 [rpm]", ylabel="[gf]")
    axs[1].set(title="トルク Q", xlabel="回転数 [rpm]", ylabel="[mN·m]")
    axs[2].set(title="軸動力 P", xlabel="回転数 [rpm]", ylabel="[W]")
    axs[0].legend(loc="upper left")
    for ax in axs:
        ax.set_ylim(bottom=0)
    fig.suptitle(f"ρ = {rho:.3f} kg/m³、縦線は APC 上限 {rpm_limit:,.0f} rpm", x=0.01, ha="left", fontsize=8.5,
                 color=INK2, fontweight="normal")
    return fig


# ---------------------------------------------------------------------------
# 2. motor / matching
# ---------------------------------------------------------------------------

def fig_matching(dt_list, duties: Sequence[float] = (0.2, 0.4, 0.6, 0.8, 1.0), rpm_max_plot: float = 11_000,
                 rpm_limit: float | None = None, title: str | None = None):
    """Torque-speed plane: motor lines for several duties x propeller load curve(s).

    dt_list: drivetrains sharing motor/ESC/source but possibly different prop models.
    """
    from .system import rpm_at_duty

    use_style()
    dt0 = dt_list[0]
    m, s, e = dt0.motor, dt0.source, dt0.esc
    fig, ax = plt.subplots(figsize=(6.8, 4.2), constrained_layout=True)
    rpm = np.linspace(1, rpm_max_plot, 400)
    omega = rpm_to_rads(rpm)
    greys = GREY_RAMP[: len(duties)][::-1] if len(duties) <= len(GREY_RAMP) else [MUTED] * len(duties)
    r_tot = lambda d: m.resistance(dt0.winding_temp_c) + e.r_on_ohm + d * d * s.r_series  # noqa: E731
    labels_q = []
    for d, c in zip(duties, greys):
        # exact torque-speed line including ESC and supply resistance:
        # I_m = (d (V_open - I_q R_s) - E) / (R + R_on + d^2 R_s),  Q = K_t (I_m - I_0)
        i_m = (d * (s.v_open - e.i_q_a * s.r_series) - m.back_emf(omega)) / r_tot(d)
        q = m.kt * (i_m - m.i0(omega))
        q = np.where(q > 0, q, np.nan)
        ax.plot(rpm, q * 1000, color=c, lw=1.1)
        # label at the zero-torque end (no-load speed)
        labels_q.append((d, rpm, q))
    for dt in dt_list:
        p = dt.prop
        _plot_source(ax, p, rpm, p.torque(rpm, dt.rho) * 1000, label=f"プロペラ負荷 ({p.label})")
        for d in duties:
            r = rpm_at_duty(dt, d)
            if np.isfinite(r) and 0 < r < rpm_max_plot:
                _dot(ax, r, float(p.torque(r, dt.rho)) * 1000, source_color(p), size=6)
    if rpm_limit:
        _vline(ax, rpm_limit, f"APC上限 {rpm_limit:,.0f} rpm", y=0.80, ha="left")
    top = float(dt0.prop.torque(rpm_max_plot, dt0.rho)) * 1000 * 1.35
    for d, rr, qq in labels_q:  # label each motor line where it leaves the top edge
        k = np.where(np.isfinite(qq) & (qq * 1000 <= top))[0]
        if len(k) and rr[k[0]] < rpm_max_plot * 0.97:
            ax.text(rr[k[0]], top * 0.985, f"duty {d:.0%}".replace("%", " %"), fontsize=7.5, color=INK2,
                    ha="left", va="top", bbox=dict(fc=SURFACE, ec="none", pad=0.6))
    ax.set(xlim=(0, rpm_max_plot), ylim=(0, top), xlabel="回転数 [rpm]", ylabel="トルク [mN·m]",
           title=title or f"運転点 = モータ特性線 × プロペラ負荷線  ({m.name}, 電源 {s.v_open:.1f} V)")
    ax.plot([], [], color=GREY_RAMP[2], lw=1.1, label="モータ特性線 (duty 一定)")
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.62))
    return fig


def fig_kv_tradeoff(frame, esc, spec, prop_nominal, prop_design, kv=None):
    """Same frame, different winding: what changes and what does not."""
    from .selection import _drivetrain, voltage_band
    from .system import at_rpm

    use_style()
    kv = np.linspace(500, 2000, 61) if kv is None else kv
    v_rec = np.empty_like(kv)
    i_m = np.empty_like(kv)
    i_in = np.empty_like(kv)
    p_cu = np.empty_like(kv)
    p_0 = np.empty_like(kv)
    for j, k in enumerate(kv):
        mm = frame.with_kv(k)
        _, v_rec[j], _ = voltage_band(mm, esc, spec, prop_nominal, prop_design)
        op = at_rpm(_drivetrain(prop_nominal, mm, esc, v_rec[j], spec, temp_c=25.0), spec.rpm_max).scalar()
        i_m[j], i_in[j], p_cu[j], p_0[j] = op["i_motor"], op["i_in"], op["p_cu"], op["p_noload"]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.2), constrained_layout=True)
    axs[0].plot(kv, v_rec, color=SERIES[0])
    axs[0].set(title="必要な電源電圧", xlabel="Kv [rpm/V]", ylabel="[V]", ylim=(0, None))
    axs[1].plot(kv, i_m, color=SERIES[0], label="モータ相電流 $I_m$")
    axs[1].plot(kv, i_in, color=SERIES[1], label="電源側電流 $I_{in}$")
    axs[1].set(title="最大回転時の電流", xlabel="Kv [rpm/V]", ylabel="[A]", ylim=(0, None))
    axs[1].legend(loc="upper left")
    axs[2].plot(kv, p_cu, color=SERIES[0], label="銅損 $I^2R$")
    axs[2].plot(kv, p_0, color=SERIES[1], label="無負荷損 $I_0E$")
    axs[2].set(title="モータ損失 (同一フレーム)", xlabel="Kv [rpm/V]", ylabel="[W]",
               ylim=(0, max(p_cu.max(), p_0.max()) * 2))
    axs[2].legend(loc="upper left")
    for ax in axs:
        _vline(ax, frame.kv, f"基準 Kv{frame.kv:.0f}", y=0.15, ha="left")
    fig.suptitle(f"同じフレーム({frame.name})を巻き替えて Kv だけ変えた場合 — {spec.rpm_max:,.0f} rpm 時、duty {spec.duty_target:.0%} 設計",
                 x=0.01, ha="left", fontsize=8.5, color=INK2, fontweight="normal")
    return fig


def fig_efficiency_map(dt, rpm_max_plot: float = 10_000, rpm_limit: float | None = None):
    """Motor efficiency over (rpm, torque) with the propeller load line."""
    use_style()
    m = dt.motor
    rpm = np.linspace(300, rpm_max_plot, 220)
    q_top = float(dt.prop.torque(rpm_max_plot, dt.rho)) * 1.5
    q = np.linspace(q_top / 300, q_top, 200)
    R, Q = np.meshgrid(rpm, q)
    W = rpm_to_rads(R)
    eta = m.efficiency(Q, W, dt.winding_temp_c)
    fig, ax = plt.subplots(figsize=(6.8, 4.2), constrained_layout=True)
    levels = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.88, 0.9]
    cf = ax.contourf(R, Q * 1000, eta, levels=[0.0] + levels + [1.0], cmap=SEQ_GREY)
    cs = ax.contour(R, Q * 1000, eta, levels=levels, colors=INK2, linewidths=0.5)
    ax.clabel(cs, fmt=lambda v: f"{v:.0%}".replace("%", " %"), fontsize=7.5, colors=INK)
    p = dt.prop
    _plot_source(ax, p, rpm, p.torque(rpm, dt.rho) * 1000, label=f"プロペラ負荷 ({p.label})")
    # current limit line (if rated)
    if m.i_max_a:
        q_lim = (m.i_max_a - m.i0(W[0])) * m.kt
        if np.nanmin(q_lim) < q_top:
            ax.plot(rpm, q_lim * 1000, color=STATUS["critical"], lw=1.1)
            ax.text(rpm[-1], q_lim[-1] * 1000, f"定格電流 {m.i_max_a:g} A ", fontsize=8, color=INK, va="bottom", ha="right")
        else:
            ax.text(0.98, 0.97, f"定格電流 {m.i_max_a:g} A の線は図より上 (余裕大)", transform=ax.transAxes,
                    fontsize=8, color=INK2, ha="right", va="top", bbox=dict(fc=SURFACE, ec="none", pad=1.5))
    if rpm_limit:
        _vline(ax, rpm_limit, f"APC上限 {rpm_limit:,.0f}", y=0.62, ha="left")
    cb = fig.colorbar(cf, ax=ax, shrink=0.9)
    cb.set_label("モータ効率 η", color=INK2)
    cb.outline.set_visible(False)
    ax.set(xlim=(rpm[0], rpm[-1]), ylim=(0, q_top * 1000), xlabel="回転数 [rpm]", ylabel="トルク [mN·m]",
           title=f"モータ効率マップ ({m.name})")
    ax.legend(loc="upper left")
    ax.grid(False)
    return fig


# ---------------------------------------------------------------------------
# 3. selection map
# ---------------------------------------------------------------------------

def fig_kv_v_map(kvmap, spec, candidates=None, esc_lines=None, psu_vmax: float = 40.0, title=None):
    """The selection map: supply voltage vs Kv.

    candidates: list of (label, kv, v_lo, v_rec, v_hi)
    esc_lines : list of (label, v) drawn as horizontal limits
    """
    use_style()
    fig, ax = plt.subplots(figsize=(7.6, 5.0), constrained_layout=True)
    K, V = np.meshgrid(kvmap.kv, kvmap.v)
    levels = np.arange(0.55, 0.851, 0.05)
    cf = ax.contourf(K, V, np.clip(kvmap.duty_nominal, 0.0, 1.5), levels=levels, cmap=SEQ_BLUE, extend="neither")
    # smooth masks from the band edges (computed by root finding, not from the grid)
    ax.fill_between(kvmap.kv, kvmap.v[0], kvmap.v_lo, color="#ecebe6", lw=0, zorder=2)
    ax.fill_between(kvmap.kv, kvmap.v_hi, kvmap.v[-1], color="#f4f3ef", lw=0, zorder=2)
    ax.plot(kvmap.kv, kvmap.v_lo, color=INK2, lw=1.0, zorder=3)
    ax.plot(kvmap.kv, kvmap.v_hi, color=INK2, lw=1.0, zorder=3)
    ax.plot(kvmap.kv, kvmap.v_rec, color=INK, lw=1.2, ls=(0, (4, 3)), zorder=3)
    kx = lambda frac: kvmap.kv[0] + frac * (kvmap.kv[-1] - kvmap.kv[0])  # noqa: E731
    ax.text(kx(0.10), kvmap.v[0] + 1.0, f"{spec.rpm_max:,.0f} rpm に届かない (設計モデルで duty > {spec.duty_design_max:.0%})",
            fontsize=8, color=INK2, ha="left", va="bottom", zorder=4)
    ax.text(kx(0.62), kvmap.v[-1] * 0.78, f"電圧過大\n(公称モデルで duty < {spec.duty_nominal_min:.0%})",
            fontsize=8, color=INK2, ha="center", va="center", zorder=4)
    kr = kx(0.80)
    vr = float(np.interp(kr, kvmap.kv, kvmap.v_rec))
    ax.annotate(f"推奨電圧 (設計 duty {spec.duty_target:.0%})", (kr, vr), xytext=(kx(0.72), vr + 7),
                fontsize=8, color=INK, ha="left", zorder=8,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.7, shrinkA=0, shrinkB=2))
    for lab, v in (esc_lines or []):
        ax.axhline(v, color=MUTED, lw=0.9, zorder=3)
        ax.text(kvmap.kv[-1], v, f" {lab}", fontsize=7.5, color=INK2, va="center", ha="left", clip_on=False)
    ax.axhline(psu_vmax, color=INK2, lw=1.0, zorder=3)
    ax.text(kvmap.kv[-1], psu_vmax, " PWR401L 上限", fontsize=7.5, color=INK2, va="center", ha="left", clip_on=False)
    cands = sorted(candidates or [], key=lambda c: c[1])
    prev_kv, stagger = -1e9, 0
    for lab, kv, v_lo, v_rec, v_hi in cands:
        stagger = (stagger + 1) % 3 if kv - prev_kv < 40 else 0
        prev_kv = kv
        ax.plot([kv, kv], [v_lo, v_hi], color=INK, lw=1.8, solid_capstyle="round", zorder=6)
        _dot(ax, kv, v_rec, INK, size=6.0, zorder=7)
        ax.annotate(lab, (kv, v_hi), xytext=(0, 3 + 11 * stagger), textcoords="offset points", ha="center",
                    va="bottom", fontsize=8, color=INK, zorder=7, fontweight="bold")
    cb = fig.colorbar(cf, ax=ax, shrink=0.85, ticks=levels)
    cb.set_label(f"{spec.rpm_max:,.0f} rpm での duty (公称モデル)", color=INK2)
    cb.ax.set_yticklabels([f"{l:.0%}" for l in levels])
    cb.outline.set_visible(False)
    ax.set(xlim=(kvmap.kv[0], kvmap.kv[-1]), ylim=(kvmap.v[0], kvmap.v[-1]), xlabel="モータ Kv [rpm/V]",
           ylabel="電源設定電圧 [V]", title=title or "選定マップ: Kv × 電源電圧")
    ax.grid(color=GRID, lw=0.5)
    return fig


# ---------------------------------------------------------------------------
# 4. throttle / test prediction
# ---------------------------------------------------------------------------

def fig_throttle_curve(dt_list, rpm_limit: float | None = None, n: int = 60):
    from .system import at_duty

    use_style()
    duty = np.linspace(0.02, dt_list[0].esc.d_max, n)
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.2), constrained_layout=True)
    for dt in dt_list:
        op = at_duty(dt, duty)
        c = source_color(dt.prop)
        axs[0].plot(duty * 100, op.rpm, color=c, label=dt.prop.label)
        axs[1].plot(duty * 100, op.thrust_n * N_TO_GF, color=c, label=dt.prop.label)
        axs[2].plot(duty * 100, op.i_motor, color=c, label=f"$I_m$ ({dt.prop.label})")
        axs[2].plot(duty * 100, op.i_in, color=c, ls=(0, (1.5, 2.2)), label=f"$I_{{in}}$ ({dt.prop.label})")
    if rpm_limit:
        axs[0].axhline(rpm_limit, color=MUTED, lw=1.0)
        axs[0].text(98, rpm_limit, f"APC上限 {rpm_limit:,.0f}", va="bottom", ha="right", fontsize=8, color=INK2)
    axs[0].set(title="回転数", xlabel="ESC duty [%]", ylabel="[rpm]", ylim=(0, None))
    axs[1].set(title="推力", xlabel="ESC duty [%]", ylabel="[gf]", ylim=(0, None))
    axs[2].set(title="電流", xlabel="ESC duty [%]", ylabel="[A]", ylim=(0, None))
    axs[0].legend(loc="upper left")
    axs[2].legend(loc="upper left", fontsize=7.5)
    m, s = dt_list[0].motor, dt_list[0].source
    fig.suptitle(f"{m.name} / 電源 {s.v_open:.1f} V", x=0.01, ha="left", fontsize=8.5, color=INK2,
                 fontweight="normal")
    return fig


def fig_power_breakdown(rows):
    """Stacked horizontal bars: where the electrical input goes at rpm_max.

    rows: list of (label, op_dict) using keys p_shaft, p_cu, p_noload, p_esc, p_lead
    """
    use_style()
    keys = [("p_shaft", "軸動力(プロペラへ)", SERIES[0]), ("p_cu", "銅損", SERIES[1]),
            ("p_noload", "無負荷損(鉄損等)", SERIES[2]), ("p_esc", "ESC損失", SERIES[3]),
            ("p_lead", "配線損失", SERIES[4])]
    fig, ax = plt.subplots(figsize=(7.6, 0.55 * len(rows) + 1.3), constrained_layout=True)
    y = np.arange(len(rows))[::-1]
    for yi, (lab, op) in zip(y, rows):
        left = 0.0
        for k, name, c in keys:
            w = op[k]
            ax.barh(yi, w, left=left, height=0.5, color=c, edgecolor=SURFACE, linewidth=1.5)
            left += w
        ax.text(left + 0.8, yi, f"{left:.1f} W  (η={op['p_shaft'] / left:.0%})".replace("%", " %"),
                va="center", fontsize=8, color=INK)
    ax.set_yticks(y, [r[0] for r in rows])
    from matplotlib.patches import Patch

    ax.legend(handles=[Patch(color=c, label=name) for _, name, c in keys], loc="lower left",
              bbox_to_anchor=(0.0, 1.0), ncol=5, fontsize=8, handlelength=1.2, borderaxespad=1.6)
    ax.set(xlabel="電力 [W]")
    ax.set_title("最大回転時の電力の行き先", pad=28)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(sum(op[k] for k, _, _ in keys) for _, op in rows) * 1.25)
    return fig


def fig_measurement_uncertainty(prop, stand, rho: float, rpm_min: float = 1000, rpm_max: float = 8125):
    use_style()
    rpm = np.linspace(rpm_min, rpm_max, 300)
    t = prop.thrust(rpm, rho)
    q = prop.torque(rpm, rho)
    ut, uq = stand.coefficient_rel_uncertainty(t, q)
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.3), constrained_layout=True)
    uq_abs = stand.torque_uncertainty(q)
    axs[0].fill_between(rpm, np.maximum(q - uq_abs, 1e-5) * 1000, (q + uq_abs) * 1000, color=SERIES[1], alpha=0.18, lw=0)
    axs[0].plot(rpm, q * 1000, color=SERIES[1])
    axs[0].set_yscale("log")
    axs[0].set(title="予測トルク ± 1585 公差 (対数軸)", xlabel="回転数 [rpm]", ylabel="[mN·m]", ylim=(0.3, 100))
    axs[0].axhline(stand.torque_tol_abs_nm * 1000, color=MUTED, lw=0.9)
    axs[0].text(rpm[-1], stand.torque_tol_abs_nm * 1000, "公差の絶対項 1 mN·m", ha="right", va="bottom", fontsize=8,
                color=INK2)
    axs[1].plot(rpm, ut * 100, color=SERIES[0], label="$C_T$ (推力)")
    axs[1].plot(rpm, uq * 100, color=SERIES[1], label="$C_P$ (トルク)")
    for lvl in (5, 10):
        axs[1].axhline(lvl, color=MUTED, lw=0.8)
    axs[1].set(title="係数の相対不確かさ (公差を偏り扱い)", xlabel="回転数 [rpm]", ylabel="[%]", ylim=(0, 40))
    axs[1].legend(loc="upper right")
    for x in (2000, 3000, 4000):
        k = int(np.argmin(np.abs(rpm - x)))
        axs[1].annotate(f"{uq[k] * 100:.0f} %", (rpm[k], uq[k] * 100), xytext=(4, 4), textcoords="offset points",
                        fontsize=8, color=INK)
        _dot(axs[1], rpm[k], uq[k] * 100, SERIES[1], size=5)
    fig.suptitle(f"{stand.name}: 推力/トルクの公差 = 0.5 % ∓ 0.001 (kgf, N·m)、回転数 0.2 %、密度 1 % を仮定",
                 x=0.01, ha="left", fontsize=8.5, color=INK2, fontweight="normal")
    return fig


def fig_candidate_dots(evals, metrics):
    """Small multiples of dot plots: one panel per metric, one row per candidate.

    metrics: list of (title, unit, fn(eval)->float, limit or None)
    """
    use_style()
    n = len(metrics)
    fig, axs = plt.subplots(1, n, figsize=(2.3 * n + 1.8, 0.42 * len(evals) + 1.3), sharey=True,
                            constrained_layout=True)
    y = np.arange(len(evals))[::-1]
    for ax, (title, unit, fn, lim) in zip(np.atleast_1d(axs), metrics):
        vals = np.array([fn(e) for e in evals], dtype=float)
        for yi, v, e in zip(y, vals, evals):
            if not np.isfinite(v):
                ax.text(0, yi, " 定格不明", fontsize=7.5, color=INK2, va="center")
                continue
            c = SERIES[0] if e.feasible else STATUS["critical"]
            ax.plot([0, v], [yi, yi], color=GRID, lw=1.0, zorder=1)
            _dot(ax, v, yi, c, size=6.5)
            ax.text(v, yi + 0.18, f"{v:.3g}", fontsize=7.5, color=INK2, ha="center", va="bottom")
        if lim is not None:
            ax.axvline(lim, color=MUTED, lw=1.0)
        ax.set_title(f"{title} [{unit}]" if unit else title, fontsize=9)
        ax.set_xlim(0, max(np.nanmax(vals), lim or 0) * 1.25)
        ax.grid(axis="y", visible=False)
    np.atleast_1d(axs)[0].set_yticks(y, [e.motor.name for e in evals])
    np.atleast_1d(axs)[0].set_ylim(-0.6, len(evals) - 0.2)
    return fig


# ---------------------------------------------------------------------------
# 5. regeneration risk with a lab supply
# ---------------------------------------------------------------------------

def fig_regen(prop, rho: float, j_kgm2: float, v0: float, v_limit: float, fractions=(1.0, 0.3, 0.1),
              rpm_from: float = 8125.0, rpm_max: float = 8125.0):
    from .regen import bus_voltage_after, kinetic_energy, natural_decel_rpm_per_s

    use_style()
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.4), constrained_layout=True)
    c = np.logspace(-4, -1, 200)  # 100 uF .. 100 mF
    e = float(kinetic_energy(j_kgm2, rpm_from))
    for f, col in zip(fractions, SERIES):
        axs[0].plot(c * 1e6, bus_voltage_after(v0, e, c, f), color=col, label=f"回生割合 {f:.0%}".replace("%", " %"))
    axs[0].axhline(v_limit, color=STATUS["critical"], lw=1.1)
    axs[0].text(c[-1] * 1e6, v_limit, "ESC 定格上限 ", ha="right", va="bottom", fontsize=8, color=INK)
    axs[0].axhline(v0, color=MUTED, lw=0.9)
    axs[0].text(c[0] * 1e6, v0, f" 設定 {v0:.1f} V", ha="left", va="bottom", fontsize=8, color=INK2)
    axs[0].set_xscale("log")
    axs[0].set(title=f"{rpm_from:,.0f} rpm から急停止したときの母線電圧 (吸収先なし)", xlabel="母線の静電容量 [µF]",
               ylabel="[V]", ylim=(0, max(3 * v_limit, 2 * v0)))
    axs[0].legend(loc="upper right")
    rpm = np.linspace(500, rpm_max, 200)
    axs[1].plot(rpm, natural_decel_rpm_per_s(prop, rho, j_kgm2, rpm), color=SERIES[0])
    axs[1].set(title="空力トルクだけで減速する速さ (これより遅く下げれば回生しない)", xlabel="回転数 [rpm]",
               ylabel="[rpm/s]", ylim=(0, None))
    fig.suptitle(f"回転体の慣性モーメント J = {j_kgm2 * 1e7:.0f} g·cm²、運動エネルギー {e:.1f} J ({rpm_from:,.0f} rpm)",
                 x=0.01, ha="left", fontsize=8.5, color=INK2, fontweight="normal")
    return fig


def fig_validation(tests, props, rho: float = 1.2):
    """Model / measured ratios for independent manufacturer tests with the same propeller."""
    from .validation import predict

    use_style()
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.2), constrained_layout=True, sharey=False)
    thr = [t for t in tests if t.thrust_g]
    full = [t for t in tests if t.throttle == "full"]
    for ax, sel, key, meas, title in ((axs[0], thr, "thrust_g", lambda t: t.thrust_g, "推力 (同じ回転数で比較)"),
                                      (axs[1], full, "i_motor", lambda t: t.current_a, "電流 (全開点: 電源電流 ≈ モータ電流)")):
        y = np.arange(len(sel))[::-1]
        for k, p in enumerate(props):
            ratios = np.array([predict(t, p, rho)[key] / meas(t) for t in sel])
            off = (k - (len(props) - 1) / 2) * 0.18
            for yi, rr in zip(y, ratios):
                _dot(ax, rr, yi + off, source_color(p), size=7)
            ax.plot([], [], "o", color=source_color(p), label=p.label)
        ax.axvline(1.0, color=INK2, lw=1.0)
        ax.axvspan(0.95, 1.05, color=GRID, alpha=0.6, lw=0)
        ax.set_yticks(y, [f"{t.label}\n{t.rpm:,.0f} rpm" for t in sel], fontsize=8)
        ax.set(title=title, xlabel="モデル / メーカー実測", xlim=(0.85, 1.22))
        ax.grid(axis="y", visible=False)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="outside lower center", ncol=2)
    fig.suptitle(f"APC 8×3.8SF を使ったメーカー試験値との比較 (ρ = {rho} kg/m³ を仮定、灰帯 ±5 %)", x=0.01, ha="left",
                 fontsize=8.5, color=INK2, fontweight="normal")
    return fig


def fig_compatibility(matrix, motors, escs):
    """Motor x ESC status grid (OK / 注意 / NG), labelled so colour is never the only cue."""
    use_style()
    n, m = len(motors), len(escs)
    fig, ax = plt.subplots(figsize=(1.15 * m + 3.2, 0.36 * n + 1.6), constrained_layout=True)
    for i, row in enumerate(matrix):
        for j, ev in enumerate(row):
            if not ev.feasible:
                c, lab = STATUS["critical"], "NG"
            elif ev.warnings:
                c, lab = STATUS["warning"], "注意"
            else:
                c, lab = STATUS["good"], "OK"
            ax.add_patch(mpl.patches.FancyBboxPatch((j + 0.08, n - 1 - i + 0.12), 0.84, 0.76,
                                                    boxstyle="round,pad=0,rounding_size=0.08", fc=c, ec="none",
                                                    alpha=0.9))
            ax.text(j + 0.5, n - 1 - i + 0.5, lab, ha="center", va="center", fontsize=8,
                    color=INK if c == STATUS["warning"] else "#ffffff", fontweight="bold")
    ax.set_xlim(0, m)
    ax.set_ylim(0, n)
    ax.set_xticks(np.arange(m) + 0.5, [e.name.replace(" (", "\n(") for e in escs], fontsize=7.5, rotation=30, ha="right")
    ax.set_yticks(np.arange(n)[::-1] + 0.5, [mm.name for mm in motors], fontsize=8)
    ax.tick_params(length=0)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title("モータ × ESC の適合 (推奨電圧で評価。NG=必須条件違反、注意=推奨条件違反)")
    return fig



def fig_regen_transient(results, v_limit: float, ramp_sweep=None, title_note: str = ""):
    """Left: bus voltage after an abrupt throttle drop for several protections.
    Right (optional): peak bus voltage versus throttle ramp-down time (no protection).

    results: list of TransientResult; ramp_sweep: (ramp_s array, v_peak array)
    """
    use_style()
    n = 2 if ramp_sweep is not None else 1
    fig, axs = plt.subplots(1, n, figsize=(5.2 * n, 3.4), constrained_layout=True, squeeze=False)
    ax = axs[0, 0]
    for r, c in zip(results, SERIES):
        ax.plot(r.t * 1000, r.v_bus, color=c, label=f"{r.protection.name} (最大 {r.v_peak:.1f} V)")
    ax.axhline(v_limit, color=STATUS["critical"], lw=1.1)
    ax.text(ax.get_xlim()[1] if False else results[0].t[-1] * 1000, v_limit, "ESC 定格上限 ", ha="right", va="bottom",
            fontsize=8, color=INK)
    ax.set(title="スロットル急減時の母線電圧", xlabel="時間 [ms]", ylabel="[V]", ylim=(0, None))
    ax.legend(loc="upper right", fontsize=7.5)
    if ramp_sweep is not None:
        ax2 = axs[0, 1]
        ramp, vp = ramp_sweep
        ax2.plot(np.asarray(ramp) * 1000, vp, color=SERIES[0])
        ax2.axhline(v_limit, color=STATUS["critical"], lw=1.1)
        ax2.set(title="絞る速さと母線電圧の最大値 (対策なし)", xlabel="スロットルを下げきるまでの時間 [ms]",
                ylabel="[V]", ylim=(0, None))
    if title_note:
        fig.suptitle(title_note, x=0.01, ha="left", fontsize=8.5, color=INK2, fontweight="normal")
    return fig
