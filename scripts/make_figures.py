"""Generate every figure (SVG) and the key numbers (JSON) used by docs/main.typ.

    .venv/bin/python scripts/make_figures.py

Figures go to docs/figures/, numbers to docs/generated/values.json, and a candidate
table to docs/generated/candidates.json. The typst document only *reads* these files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import propmotor as pm  # noqa: E402
from propmotor import plotting as P  # noqa: E402
from propmotor.catalog import load_escs, load_motors  # noqa: E402
from propmotor.regen import kinetic_energy, prop_inertia_estimate, rotor_inertia_estimate  # noqa: E402
from propmotor.selection import TestSpec, best_esc, compatibility, evaluate, kv_voltage_map  # noqa: E402
from propmotor.transient import BusProtection, throttle_drop  # noqa: E402
from propmotor.validation import load_tests, predict  # noqa: E402
from propmotor.stand import TYTO_1585  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
GEN = ROOT / "docs" / "generated"

# ---- test conditions -------------------------------------------------------
ROOM = dict(temp_c=20.0, pressure_pa=101_325.0, rel_humidity=0.5)
PROP_MASS_KG = 0.0071  # APC 8x3.8SF: 0.25 oz (APC product page)
ROTOR = dict(bell_mass_kg=0.020, bell_radius_m=0.014)  # 22xx outrunner bell, approx.
REFERENCE_MOTOR = "Dualsky ECO 2316C-V2 (880)"  # recommendation (see docs/main.typ, section 6)
JP_ONLY = True  # candidates restricted to parts purchasable in Japan
ESC_LINES = [("2S ESC (7.6 V)", 8.4 * 0.9), ("3S (11.3 V)", 12.6 * 0.9), ("4S (15.1 V)", 16.8 * 0.9),
             ("6S (22.7 V)", 25.2 * 0.9)]


def save(fig, name):
    fig.savefig(FIG / f"{name}.svg")
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), n)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    rho = pm.air_density(**ROOM)
    lim = pm.apc_rpm_limit(8.0)
    apc, uiuc, design = pm.apc_8x3_8sf_theory(), pm.apc_8x3_8sf_measured(), pm.apc_8x3_8sf_design()
    spec = TestSpec(rpm_max=lim, rho=rho)
    values: dict = {"rho": r(rho, 4), "room": ROOM, "rpm_limit": r(lim, 0), "spec": spec.__dict__}

    # ---- propeller ---------------------------------------------------------
    save(P.fig_prop_coefficients([uiuc, apc], lim), "prop_coefficients")
    save(P.fig_prop_dimensional([uiuc, apc], rho, lim), "prop_dimensional")
    for key, ds in (("uiuc", uiuc), ("apc", apc)):
        values[key] = {
            "ct_lim": r(ds.ct_at(lim), 4), "cp_lim": r(ds.cp_at(lim), 4), "fm_lim": r(ds.figure_of_merit(lim)),
            "thrust_n": r(ds.thrust(lim, rho)), "thrust_gf": r(ds.thrust(lim, rho) * pm.units.N_TO_GF, 0),
            "torque_nm": r(ds.torque(lim, rho), 4), "power_w": r(ds.power(lim, rho), 1),
            "rpm_range": [r(x, 0) for x in ds.rpm_range],
            "ct_3000": r(ds.ct_at(3000), 4), "cp_3000": r(ds.cp_at(3000), 4),
            "ct_7000": r(ds.ct_at(7000), 4), "cp_7000": r(ds.cp_at(7000), 4),
        }
    values["tip_mach_lim"] = r(uiuc.tip_mach(lim, ROOM["temp_c"]))
    values["disk_area"] = r(uiuc.disk_area(), 5)
    values["p_ideal_lim"] = r(uiuc.ideal_power(uiuc.thrust(lim, rho), rho), 1)

    # ---- candidates ----------------------------------------------------------
    try:
        motors, escs = load_motors(jp_only=JP_ONLY), load_escs(jp_only=JP_ONLY)
    except FileNotFoundError:
        motors, escs = [], []
    generic = pm.generic_esc(v_max=25.2, i_cont_a=30.0, name="汎用ESC 30A/6S")
    evals = [best_esc(m, escs, spec, uiuc, design) for m in motors] if escs else \
            [evaluate(m, generic, None, spec, uiuc, design) for m in motors]
    ref_ev = next((e for e in evals if e.motor.name == REFERENCE_MOTOR), None)
    if ref_ev is None:
        ref_m = pm.Motor("仮 2212/920Kv", kv=920, r_ohm=0.12, i0_a=0.4, i_max_a=15)
        ref_ev = evaluate(ref_m, generic, None, spec, uiuc, design)
    ref = ref_ev.motor
    src = pm.DCSource(name="PWR401L", v_open=ref_ev.v_set, r_series=spec.r_leads, i_limit=40.0)
    dts = [pm.Drivetrain(prop=uiuc, motor=ref, esc=ref_ev.esc, source=src, rho=rho),
           pm.Drivetrain(prop=apc, motor=ref, esc=ref_ev.esc, source=src, rho=rho)]

    # ---- physics figures with the reference motor -------------------------------
    save(P.fig_matching(dts, rpm_limit=lim), "matching")
    save(P.fig_kv_tradeoff(ref, generic, spec, uiuc, design), "kv_tradeoff")
    save(P.fig_efficiency_map(dts[0], rpm_limit=lim), "efficiency_map")
    save(P.fig_throttle_curve(dts, rpm_limit=lim), "throttle")
    save(P.fig_power_breakdown([("公称 (UIUC)", ref_ev.nominal), ("設計 (APC)", ref_ev.design)]), "power_breakdown")
    save(P.fig_measurement_uncertainty(uiuc, TYTO_1585, rho, rpm_max=lim), "measurement_uncertainty")

    km = kv_voltage_map(ref, generic, spec, uiuc, design, kv=np.linspace(400, 2000, 41), v=np.linspace(4, 40, 73))
    cand = [(str(i + 1), e.motor.kv, e.v_band[0], e.v_set, e.v_band[1]) for i, e in enumerate(evals)] or \
           [(ref.name, ref.kv, ref_ev.v_band[0], ref_ev.v_set, ref_ev.v_band[1])]
    save(P.fig_kv_v_map(km, spec, candidates=cand, esc_lines=ESC_LINES,
                        title=f"選定マップ: Kv × 電源電圧 (色帯は {ref.name} と同じ大きさのモータ。番号は候補表)"), "kv_v_map")

    if evals:
        save(P.fig_compatibility(compatibility(motors, escs, spec, uiuc, design), motors, escs), "compatibility")
        metrics = [
            ("推奨電源電圧", "V", lambda e: e.v_set, None),
            ("最大回転時の相電流", "A", lambda e: e.design["i_motor"], None),
            ("モータ損失", "W", lambda e: e.design["p_cu"] + e.design["p_noload"], None),
            ("モータ効率", "%", lambda e: 100 * e.nominal["eta_motor"], None),
            ("電流定格に対する比", "%", lambda e: 100 * e.design["i_motor"] / e.motor.i_max_a if e.motor.i_max_a else math.nan, 70),
            ("モータ定数 Km", "mN·m/√W", lambda e: 1000 * e.motor.km, None),
        ]
        save(P.fig_candidate_dots(evals, metrics), "candidates")
        save(P.fig_power_breakdown([(e.motor.name, e.nominal) for e in evals]), "candidates_power")

    # ---- validation against manufacturer data -------------------------------------
    tests = load_tests()
    save(P.fig_validation(tests, [uiuc, apc]), "validation")
    values["validation"] = [{
        "label": t.label, "rpm": t.rpm, "thrust_g": t.thrust_g, "current_a": t.current_a, "throttle": t.throttle,
        "uiuc": {k: r(x, 3) for k, x in predict(t, uiuc).items()}, "apc": {k: r(x, 3) for k, x in predict(t, apc).items()},
    } for t in tests]

    # ---- regeneration ----------------------------------------------------------
    j = prop_inertia_estimate(PROP_MASS_KG, uiuc.diameter_m) + rotor_inertia_estimate(**ROTOR)
    save(P.fig_regen(uiuc, rho, j, v0=ref_ev.v_set, v_limit=ref_ev.esc.v_max, rpm_from=lim), "regen")
    values["regen"] = {"j_kgm2": j, "j_gcm2": r(j * 1e7, 0), "energy_lim_j": r(kinetic_energy(j, lim), 2),
                       "prop_mass_g": PROP_MASS_KG * 1000}

    # ---- safety: regeneration transients (docs/safety.typ) -------------------------
    dt_ref = pm.Drivetrain(prop=uiuc, motor=ref, esc=ref_ev.esc,
                           source=pm.DCSource("PSU", ref_ev.v_set, spec.r_leads, 10.0), rho=rho)
    d0 = float(pm.required_duty(dt_ref, lim))
    v_clamp = float(math.ceil(ref_ev.v_set + 2.0))  # maxon DSR 70/30: threshold in 1 V steps
    prots = [BusProtection("対策なし (ESC 内蔵 330 µF)"),
             BusProtection("+ 電解コンデンサ 2×1000 µF", c_bus_f=330e-6 + 2000e-6),
             BusProtection(f"+ maxon DSR 70/30 ({v_clamp:.0f} V, 8800 µF)", c_bus_f=330e-6 + 8800e-6, v_clamp=v_clamp),
             BusProtection("ESC のフリーホイール OFF", complementary_pwm=False)]
    res = [throttle_drop(dt_ref, j, pr, d0, 0.05, t_end=0.25) for pr in prots]
    ramps = np.array([0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0])
    vpk = [throttle_drop(dt_ref, j, prots[0], d0, 0.05, t_end=r_ + 0.3, ramp_s=r_).v_peak for r_ in ramps]
    save(P.fig_regen_transient(res, ref_ev.esc.v_max, (ramps, vpk),
                               title_note=f"{ref.name} / {ref_ev.esc.name} / 電源 {ref_ev.v_set:.1f} V: "
                                          f"{lim:,.0f} rpm (duty {d0:.0%}) から duty 5 % へ"), "regen_transient")
    steps = {}
    for dd in (0.05, 0.10, 0.20, 0.40):
        steps[f"{dd:.2f}"] = r(throttle_drop(dt_ref, j, prots[0], d0, d0 - dd, t_end=0.3).v_peak, 2)
    extra = {
        "+ コンデンサ 4700 µF": BusProtection("x", c_bus_f=330e-6 + 4700e-6),
        "+ バイパス抵抗 10 Ω (常時 約1.3 A)": BusProtection("x", r_bleed_ohm=1 / (1 / 35.0 + 1 / 10.0)),
        "+ 2×1000 µF + バイパス抵抗 10 Ω": BusProtection("x", c_bus_f=330e-6 + 2000e-6, r_bleed_ohm=1 / (1 / 35.0 + 1 / 10.0)),
    }
    extra_peaks = {k: r(throttle_drop(dt_ref, j, pr, d0, 0.05, t_end=0.25).v_peak, 1) for k, pr in extra.items()}
    coast = throttle_drop(dt_ref, j, prots[0], d0, 0.0, t_end=0.5, zero_throttle="coast")
    brake = throttle_drop(dt_ref, j, prots[0], d0, 0.0, t_end=0.5, zero_throttle="brake")
    values["safety"] = {
        "v_set": ref_ev.v_set, "esc_vmax": ref_ev.esc.v_max, "d0": r(d0), "v_clamp": v_clamp,
        "peaks": {**{pr.name: r(x.v_peak, 1) for pr, x in zip(prots, res)}, **extra_peaks},
        "peak_list": [r(x.v_peak, 1) for x in res],
        "clamp_i_max": r(res[2].i_clamp.max(), 2),
        "clamp_energy_j": r(float(np.trapezoid(res[2].i_clamp * res[2].v_bus, res[2].t)), 2), "i_motor_min": r(res[0].i_motor.min(), 1),
        "ramp_s": ramps.tolist(), "ramp_vpeak": [r(x, 1) for x in vpk], "step_vpeak": steps,
        "coast_vpeak": r(coast.v_peak, 2), "brake_vpeak": r(brake.v_peak, 2), "brake_i_min": r(brake.i_motor.min(), 1),
        "i_in_max": r(ref_ev.design["i_in"], 2),
    }

    # ---- numbers for the document -------------------------------------------------
    def op_summary(op):
        keys = ["rpm", "duty", "thrust_n", "torque_nm", "p_shaft", "i_motor", "v_motor", "i_in", "v_in", "p_in",
                "p_source", "p_cu", "p_noload", "p_esc", "p_lead", "eta_motor", "eta_drive"]
        return {k: r(op[k], 4) for k in keys}

    values["n_motors"] = len(motors)
    values["n_escs"] = len(escs)
    values["reference"] = {
        "motor": ref.name, "kv": ref.kv, "motor_shop": ref.meta.get("jp_shop", "") if ref.meta else "",
        "motor_price_jpy": ref.meta.get("price_jpy") if ref.meta else None,
        "esc_shop": ref_ev.esc.meta.get("jp_shop", "") if ref_ev.esc.meta else "",
        "esc_price_jpy": ref_ev.esc.meta.get("price_jpy") if ref_ev.esc.meta else None, "r_ohm": ref.r_ohm, "i0_a": ref.i0_a, "km": r(ref.km, 4),
        "kt": r(ref.kt, 5), "esc": ref_ev.esc.name, "v_set": ref_ev.v_set, "v_band": [r(x, 2) for x in ref_ev.v_band],
        "nominal": op_summary(ref_ev.nominal), "design": op_summary(ref_ev.design), "low": op_summary(ref_ev.low),
        "max_rpm_nominal": r(pm.max_rpm(dts[0]), 0), "max_rpm_design": r(pm.max_rpm(dts[1]), 0),
    }
    rows = []
    for e in evals:
        rows.append({
            "motor": e.motor.name, "esc": e.esc.name, "kv": e.motor.kv, "r_ohm": e.motor.r_ohm, "i0_a": e.motor.i0_a,
            "i_max_a": e.motor.i_max_a, "mass_g": e.motor.mass_g, "km": r(e.motor.km, 4), "v_set": e.v_set,
            "v_lo": r(e.v_band[0], 2), "v_hi": r(e.v_band[1], 2), "feasible": e.feasible,
            "duty_nominal": r(e.nominal["duty"]), "duty_design": r(e.design["duty"]),
            "i_motor": r(e.design["i_motor"], 2), "i_in": r(e.design["i_in"], 2),
            "p_motor_loss": r(e.design["p_cu"] + e.design["p_noload"], 2), "eta_motor": r(e.nominal["eta_motor"]),
            "p_in": r(e.nominal["p_in"], 1), "warnings": [c.name for c in e.warnings],
            "failed": [c.name for c in e.checks if c.hard and not c.ok], "url": e.motor.url, "price": e.motor.price,
            "esc_price": e.esc.price, "cells": e.motor.meta.get("cells", ""), "stator": e.motor.meta.get("stator", ""),
            "adapter": e.motor.meta.get("prop_adapter", ""), "mount": e.motor.mount,
            "jp_shop": e.motor.meta.get("jp_shop", ""), "price_jpy": e.motor.meta.get("price_jpy"),
            "esc_jp_shop": e.esc.meta.get("jp_shop", ""), "esc_price_jpy": e.esc.meta.get("price_jpy"),
            "esc_wiring": e.esc.meta.get("wiring", ""), "motor_wiring": e.motor.meta.get("wiring", ""),
        })
    (GEN / "candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    (GEN / "values.json").write_text(json.dumps(values, ensure_ascii=False, indent=1, default=float))
    for e in evals:
        print(e.table())
    print(f"wrote {len(list(FIG.glob('*.svg')))} figures, values.json, candidates.json ({len(rows)} rows)")


if __name__ == "__main__":
    main()
