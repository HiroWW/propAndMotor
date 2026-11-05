"""Requirement checks and design-space exploration for a static thrust test.

"Selection" here means: find (supply voltage, motor, ESC) such that the whole planned
sweep 0 .. rpm_max can be produced with margin, without violating any rating of the
motor, ESC, power supply or thrust stand. Two propeller models are used:

* design model  (conservative envelope, higher torque)  -> reachability and ratings
* nominal model (best estimate, measured data)          -> predictions, "too much headroom"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .esc import ESC
from .motor import Motor
from .propeller import StaticPropData
from .source import KIKUSUI_PWR401L, DCSource, PowerSupplySpec
from .stand import TYTO_1585, ThrustStand
from .system import Drivetrain, at_rpm, voltage_for_duty


@dataclass(frozen=True)
class TestSpec:
    """What the test must be able to do, and the margins we want."""

    rpm_max: float = 8125.0  # top of the sweep (APC SF limit 65,000/8)
    rpm_min: float = 1500.0  # bottom of the sweep
    duty_design_max: float = 0.85  # design model must reach rpm_max at d <= this
    duty_target: float = 0.80  # used for the recommended voltage
    duty_nominal_min: float = 0.55  # nominal d at rpm_max below this = voltage needlessly high
    duty_low_min: float = 0.06  # d at rpm_min: below this sensorless low-speed running is marginal
    motor_i_frac: float = 0.7  # use <= 70 % of the motor's rated continuous current
    esc_i_frac: float = 0.6  # use <= 60 % of the ESC continuous rating
    esc_v_frac: float = 0.9  # keep V_set <= 90 % of ESC max (regen / ringing spikes)
    rho: float = 1.204
    winding_temp_c: float = 60.0  # hot winding for the design case
    r_leads: float = 0.03  # supply leads + connectors + stand shunt [ohm]


@dataclass
class Check:
    name: str
    ok: bool
    value: float
    limit: float
    unit: str
    hard: bool = True
    note: str = ""

    @property
    def status(self) -> str:
        if self.ok:
            return "OK"
        return "NG" if self.hard else "注意"


@dataclass
class Evaluation:
    motor: Motor
    esc: ESC
    v_set: float
    nominal: dict  # operating point at rpm_max, nominal prop model
    design: dict  # operating point at rpm_max, design prop model
    low: dict  # operating point at rpm_min, nominal prop model
    checks: list[Check] = field(default_factory=list)
    v_band: tuple[float, float] = (math.nan, math.nan)

    @property
    def feasible(self) -> bool:
        return all(c.ok for c in self.checks if c.hard)

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and not c.hard]

    def table(self) -> str:
        rows = [f"{self.motor.name} + {self.esc.name} @ {self.v_set:.2f} V  ->  {'成立' if self.feasible else '不成立'}"]
        for c in self.checks:
            rows.append(f"  [{c.status:^4}] {c.name:<28} {c.value:9.3g} / {c.limit:9.3g} {c.unit:<4} {c.note}")
        return "\n".join(rows)


def _drivetrain(prop, motor, esc, v_set, spec: TestSpec, temp_c=None) -> Drivetrain:
    src = DCSource(name=f"PSU {v_set:.2f} V", v_open=v_set, r_series=spec.r_leads)
    return Drivetrain(prop=prop, motor=motor, esc=esc, source=src, rho=spec.rho,
                      winding_temp_c=spec.winding_temp_c if temp_c is None else temp_c)


def voltage_band(motor: Motor, esc: ESC, spec: TestSpec, prop_nominal: StaticPropData,
                 prop_design: StaticPropData) -> tuple[float, float, float]:
    """(V_lo, V_rec, V_hi) for the supply setting.

    V_lo : design model reaches rpm_max exactly at duty_design_max
    V_rec: design model at duty_target
    V_hi : nominal model needs only duty_nominal_min at rpm_max (more voltage = wasted headroom)
    """
    dd = _drivetrain(prop_design, motor, esc, 12.0, spec)
    dn = _drivetrain(prop_nominal, motor, esc, 12.0, spec, temp_c=25.0)
    v_lo = voltage_for_duty(dd, spec.rpm_max, spec.duty_design_max)
    v_rec = voltage_for_duty(dd, spec.rpm_max, spec.duty_target)
    v_hi = voltage_for_duty(dn, spec.rpm_max, spec.duty_nominal_min)
    return v_lo, v_rec, v_hi


def evaluate(motor: Motor, esc: ESC, v_set: float | None, spec: TestSpec, prop_nominal: StaticPropData,
             prop_design: StaticPropData, psu: PowerSupplySpec = KIKUSUI_PWR401L,
             stand: ThrustStand = TYTO_1585) -> Evaluation:
    v_lo, v_rec, v_hi = voltage_band(motor, esc, spec, prop_nominal, prop_design)
    if v_set is None:
        v_set = math.ceil(v_rec * 10) / 10  # PSU setting rounded up to 0.1 V
    op_d = at_rpm(_drivetrain(prop_design, motor, esc, v_set, spec), spec.rpm_max).scalar()
    op_n = at_rpm(_drivetrain(prop_nominal, motor, esc, v_set, spec, temp_c=25.0), spec.rpm_max).scalar()
    op_l = at_rpm(_drivetrain(prop_nominal, motor, esc, v_set, spec, temp_c=25.0), spec.rpm_min).scalar()

    ch: list[Check] = []
    ch.append(Check("最大回転数に届く(設計モデル)", op_d["duty"] <= spec.duty_design_max, op_d["duty"],
                    spec.duty_design_max, "duty"))
    ch.append(Check("電圧が高すぎない(公称モデル)", op_n["duty"] >= spec.duty_nominal_min, op_n["duty"],
                    spec.duty_nominal_min, "duty", hard=False, note="低いと分解能・リップル・低速安定性が悪化"))
    ch.append(Check("低回転端のduty", op_l["duty"] >= spec.duty_low_min, op_l["duty"], spec.duty_low_min,
                    "duty", hard=False, note=f"{spec.rpm_min:.0f} rpm"))
    if motor.i_max_a:
        ch.append(Check("モータ電流", op_d["i_motor"] <= spec.motor_i_frac * motor.i_max_a, op_d["i_motor"],
                        spec.motor_i_frac * motor.i_max_a, "A", note=f"定格{motor.i_max_a:g} A の{spec.motor_i_frac:.0%}"))
    if motor.p_max_w:
        ch.append(Check("モータ電力", op_d["v_motor"] * op_d["i_motor"] <= motor.p_max_w,
                        op_d["v_motor"] * op_d["i_motor"], motor.p_max_w, "W"))
    if motor.v_max:
        ch.append(Check("モータ推奨電圧", v_set <= motor.v_max, v_set, motor.v_max, "V", hard=False))
    ch.append(Check("ESC 入力電圧(下限)", v_set >= esc.v_min, v_set, esc.v_min, "V"))
    ch.append(Check("ESC 入力電圧(上限×余裕)", v_set <= spec.esc_v_frac * esc.v_max, v_set,
                    spec.esc_v_frac * esc.v_max, "V", note="回生・サージ分の余裕"))
    ch.append(Check("ESC 電流", op_d["i_motor"] <= spec.esc_i_frac * esc.i_cont_a, op_d["i_motor"],
                    spec.esc_i_frac * esc.i_cont_a, "A", note=f"定格{esc.i_cont_a:g} A の{spec.esc_i_frac:.0%}"))
    ch.append(Check("ESC 回生(ブレーキ/フリーホイール)をOFF可", esc.braking_configurable is True,
                    float(esc.braking_configurable is True), 1.0, "-", hard=False,
                    note="未確認" if esc.braking_configurable is None else "PWR401L は逆電流を吸収できない"))
    mb = motor.meta.get("bullet_mm") if motor.meta else None
    solder_free = esc.motor_bullet_mm is not None and (mb is None or abs(mb - esc.motor_bullet_mm) < 0.01)
    ch.append(Check("はんだ付けなしで配線可", solder_free, float(solder_free), 1.0, "-", hard=False,
                    note=("ESC モータ側にコネクタなし" if esc.motor_bullet_mm is None else
                          ("モータ側バレット径を要確認" if mb is None else f"{mb:g} mm バレット同士"))))
    if esc.pwm_input is not None:
        ch.append(Check("ESC がサーボPWM入力対応", bool(esc.pwm_input), float(bool(esc.pwm_input)), 1.0, "-",
                        note="1585 はPWMでESCを駆動"))
    ch.append(Check("電源 電圧", v_set <= psu.v_max, v_set, psu.v_max, "V"))
    ch.append(Check("電源 電流", op_d["i_in"] <= psu.i_max, op_d["i_in"], psu.i_max, "A"))
    ch.append(Check("電源 電力", op_d["p_source"] <= psu.p_max, op_d["p_source"], psu.p_max, "W"))
    ch.append(Check("スタンド 推力", op_d["thrust_n"] <= stand.thrust_max_n, op_d["thrust_n"], stand.thrust_max_n, "N"))
    ch.append(Check("スタンド トルク", op_d["torque_nm"] <= stand.torque_max_nm, op_d["torque_nm"],
                    stand.torque_max_nm, "N·m"))
    ch.append(Check("スタンド 電流", op_d["i_in"] <= stand.i_max, op_d["i_in"], stand.i_max, "A"))
    ch.append(Check("スタンド 電圧", v_set <= stand.v_max, v_set, stand.v_max, "V"))
    return Evaluation(motor=motor, esc=esc, v_set=v_set, nominal=op_n, design=op_d, low=op_l, checks=ch,
                      v_band=(v_lo, v_hi))


# ---------------------------------------------------------------------------
# Design-space map: generic frame, Kv x V_set
# ---------------------------------------------------------------------------

@dataclass
class KvVoltageMap:
    kv: np.ndarray
    v: np.ndarray
    duty_design: np.ndarray  # [len(v), len(kv)] duty at rpm_max, design model
    duty_nominal: np.ndarray
    i_motor_design: np.ndarray  # [len(kv)] (independent of V)
    i_in_nominal: np.ndarray  # [len(v), len(kv)]
    v_lo: np.ndarray  # [len(kv)]
    v_hi: np.ndarray
    v_rec: np.ndarray


def kv_voltage_map(frame: Motor, esc: ESC, spec: TestSpec, prop_nominal: StaticPropData,
                   prop_design: StaticPropData, kv=None, v=None) -> KvVoltageMap:
    kv = np.linspace(400, 2000, 81) if kv is None else np.asarray(kv, float)
    v = np.linspace(4, 40, 145) if v is None else np.asarray(v, float)
    dd = np.full((len(v), len(kv)), np.nan)
    dn = np.full_like(dd, np.nan)
    iin = np.full_like(dd, np.nan)
    im = np.full(len(kv), np.nan)
    v_lo = np.full(len(kv), np.nan)
    v_hi = np.full(len(kv), np.nan)
    v_rec = np.full(len(kv), np.nan)
    for j, k in enumerate(kv):
        m = frame.with_kv(k)
        for i, vv in enumerate(v):
            od = at_rpm(_drivetrain(prop_design, m, esc, vv, spec), spec.rpm_max)
            on = at_rpm(_drivetrain(prop_nominal, m, esc, vv, spec, temp_c=25.0), spec.rpm_max)
            dd[i, j] = od.duty
            dn[i, j] = on.duty
            iin[i, j] = on.i_in
            im[j] = od.i_motor
        v_lo[j], v_rec[j], v_hi[j] = voltage_band(m, esc, spec, prop_nominal, prop_design)
    return KvVoltageMap(kv=kv, v=v, duty_design=dd, duty_nominal=dn, i_motor_design=im, i_in_nominal=iin,
                        v_lo=v_lo, v_hi=v_hi, v_rec=v_rec)


def best_esc(motor: Motor, escs: list[ESC], spec: TestSpec, prop_nominal: StaticPropData,
             prop_design: StaticPropData, **kw) -> Evaluation | None:
    """Pair a motor with the ESC that passes all hard checks, has the fewest warnings and the
    smallest current rating (an oversized ESC only adds cost and coarser current resolution)."""
    evs = [evaluate(motor, e, None, spec, prop_nominal, prop_design, **kw) for e in escs]
    if not evs:
        return None
    evs.sort(key=lambda ev: (not ev.feasible, len(ev.warnings), ev.esc.i_cont_a, ev.esc.v_max))
    return evs[0]


def compatibility(motors: list[Motor], escs: list[ESC], spec: TestSpec, prop_nominal: StaticPropData,
                  prop_design: StaticPropData, **kw) -> list[list[Evaluation]]:
    """evaluate() for every motor x ESC pair (rows = motors)."""
    return [[evaluate(m, e, None, spec, prop_nominal, prop_design, **kw) for e in escs] for m in motors]
