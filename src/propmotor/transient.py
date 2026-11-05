"""Transient of a sudden throttle drop: rotor deceleration and DC-bus voltage (regeneration).

States: rotor speed omega and bus voltage V_bus (the ESC input capacitor + any added bank).
Averaged over the PWM period, with the motor inductance neglected (L/R ~ 0.2 ms << event):

    motor current, complementary PWM ("damped light", synchronous rectification):
        I_m = (d V_bus - E) / (R + R_on)            -> can be NEGATIVE (generator)
    motor current, diode freewheeling (active freewheel OFF):
        I_m = max(0, (d V_bus - E) / (R + R_on))      -> no reverse current, no regen
    rotor:  J domega/dt = K_t (I_m - I_0) - Q_prop(omega)
    ESC  :  I_esc = d I_m                            (negative = current pushed into the bus)
    bus  :  C dV/dt = I_psu - I_esc - I_bleed - I_clamp
    supply (cannot sink): I_psu = clip((V_set - V_bus)/R_s, 0, I_limit)
    bleeder (PWR-01 normal):  I_bleed ~ V_bus / R_bleed
    clamp (electronic load in CV mode): I_clamp = clip((V_bus - V_clamp)/R_clamp, 0, I_clamp_max)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .system import Drivetrain, rpm_at_duty
from .units import rpm_to_rads


@dataclass(frozen=True)
class BusProtection:
    name: str
    c_bus_f: float = 330e-6  # ESC input capacitor (+ added bank)
    complementary_pwm: bool = True  # "damped light" / active freewheeling ON
    r_bleed_ohm: float | None = 35.0  # PWR-01 bleeder ~0.35 A at 12 V
    v_clamp: float | None = None  # electronic-load CV setting
    r_clamp_ohm: float = 0.05
    i_clamp_max: float = 30.0


@dataclass
class TransientResult:
    t: np.ndarray
    rpm: np.ndarray
    v_bus: np.ndarray
    i_motor: np.ndarray
    i_esc: np.ndarray
    i_psu: np.ndarray
    i_clamp: np.ndarray
    protection: BusProtection

    @property
    def v_peak(self) -> float:
        return float(np.max(self.v_bus))


def throttle_drop(dt: Drivetrain, j_kgm2: float, prot: BusProtection, d_from: float, d_to: float,
                  t_end: float = 0.4, ramp_s: float = 0.0, zero_throttle: str = "coast") -> TransientResult:
    """Start at steady state with duty d_from, then change duty to d_to (linearly over ramp_s).

    zero_throttle: what the ESC does at duty 0 — "coast" (all switches off, hobby-ESC default)
    or "brake" (low sides on = motor shorted; energy burnt in the windings, not returned to the bus).
    """
    m, e, s = dt.motor, dt.esc, dt.source
    r_tot = m.resistance(dt.winding_temp_c) + e.r_on_ohm
    rpm0 = rpm_at_duty(dt, d_from)
    w0 = rpm_to_rads(rpm0)
    v0 = s.v_open - (d_from * float(m.current(dt.prop.torque(rpm0, dt.rho), w0)) + e.i_q_a) * s.r_series

    def duty(t):
        if t <= 0:
            return d_from
        if ramp_s <= 0 or t >= ramp_s:
            return d_to
        return d_from + (d_to - d_from) * t / ramp_s

    def currents(t, w, v):
        d = duty(t)
        i_m = (d * v - w / m.kv_si) / r_tot
        if not prot.complementary_pwm or (d <= 0.0 and zero_throttle == "coast"):
            i_m = max(i_m, 0.0)
        i_esc = d * i_m + e.i_q_a
        i_psu = min(max((s.v_open - v) / s.r_series, 0.0), s.i_limit or 1e9)
        i_bleed = v / prot.r_bleed_ohm if prot.r_bleed_ohm else 0.0
        i_cl = 0.0
        if prot.v_clamp is not None:
            i_cl = min(max((v - prot.v_clamp) / prot.r_clamp_ohm, 0.0), prot.i_clamp_max)
        return i_m, i_esc, i_psu, i_bleed, i_cl

    def rhs(t, y):
        w, v = y
        i_m, i_esc, i_psu, i_bleed, i_cl = currents(t, w, v)
        rpm = max(w, 1e-3) * 30 / np.pi
        q_prop = float(dt.prop.torque(rpm, dt.rho)) if w > 0 else 0.0
        q_m = m.kt * (i_m - float(m.i0(max(w, 0.0))) * np.sign(w))
        dw = (q_m - q_prop) / j_kgm2
        if w <= 0 and dw < 0:
            dw = 0.0
        dv = (i_psu - i_esc - i_bleed - i_cl) / prot.c_bus_f
        return [dw, dv]

    sol = solve_ivp(rhs, (0.0, t_end), [w0, v0], method="LSODA", max_step=2e-4, rtol=1e-6, atol=[1e-3, 1e-5])
    t = sol.t
    w, v = sol.y
    cur = np.array([currents(ti, wi, vi) for ti, wi, vi in zip(t, w, v)])
    return TransientResult(t=t, rpm=w * 30 / np.pi, v_bus=v, i_motor=cur[:, 0], i_esc=cur[:, 1], i_psu=cur[:, 2],
                           i_clamp=cur[:, 4], protection=prot)
