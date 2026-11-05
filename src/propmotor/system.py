"""Operating-point solver for source -> ESC -> motor -> propeller (static).

Unknowns at steady state are tied together by:
    prop      : Q = Q_prop(omega)
    motor     : I_m = Q / K_t + I_0(omega),   V_m = omega / K_v + I_m R
    ESC       : d V_in = V_m + I_m R_on,       I_in = d I_m + I_q
    source    : V_in = V_open - I_in R_s

Given a target rpm everything except d follows directly, and d solves the quadratic
    -I_m R_s d^2 + (V_open - I_q R_s) d - (V_m + I_m R_on) = 0
(take the smaller root; no real root = the source cannot deliver that power).
Given a duty, the rpm is found by inverting d(rpm), which is monotonic.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np
from scipy.optimize import brentq

from .esc import ESC
from .motor import Motor
from .propeller import StaticPropData
from .source import DCSource
from .units import rpm_to_rads


@dataclass(frozen=True)
class Drivetrain:
    prop: StaticPropData
    motor: Motor
    esc: ESC
    source: DCSource
    rho: float = 1.204
    winding_temp_c: float = 25.0

    def with_(self, **kw) -> "Drivetrain":
        from dataclasses import replace

        return replace(self, **kw)


@dataclass
class OperatingPoints:
    """Vectorised operating points (all arrays share the same shape)."""

    rpm: np.ndarray
    omega: np.ndarray
    duty: np.ndarray
    thrust_n: np.ndarray
    torque_nm: np.ndarray
    p_shaft: np.ndarray
    i_motor: np.ndarray
    v_motor: np.ndarray
    back_emf: np.ndarray
    i_in: np.ndarray
    v_in: np.ndarray
    p_in: np.ndarray  # electrical power into the ESC (what the stand measures)
    p_source: np.ndarray  # power delivered by the source (V_open * I_in)
    p_cu: np.ndarray
    p_noload: np.ndarray
    p_esc: np.ndarray
    p_lead: np.ndarray
    eta_motor: np.ndarray
    eta_esc: np.ndarray
    eta_drive: np.ndarray  # shaft / p_in
    ct: np.ndarray
    cp: np.ndarray
    fm: np.ndarray
    extrapolated: np.ndarray
    reachable: np.ndarray  # duty <= d_max and source can deliver
    cc_limited: np.ndarray  # I_in above the supply current limit

    def scalar(self, i: int = 0) -> dict:
        return {f.name: np.atleast_1d(getattr(self, f.name))[i].item() for f in fields(self)}


def _required_duty(v_open, r_s, i_q, i_m, v_req):
    a = i_m * r_s
    b = v_open - i_q * r_s
    disc = b * b - 4.0 * a * v_req
    with np.errstate(invalid="ignore", divide="ignore"):
        d_lin = v_req / b
        d_quad = (b - np.sqrt(np.maximum(disc, 0.0))) / (2.0 * np.where(a > 0, a, 1.0))
        d = np.where(a > 1e-12, d_quad, d_lin)
    return np.where(disc >= 0.0, d, np.nan)


def at_rpm(dt: Drivetrain, rpm) -> OperatingPoints:
    rpm = np.asarray(rpm, dtype=float)
    m, e, s, p = dt.motor, dt.esc, dt.source, dt.prop
    omega = rpm_to_rads(rpm)
    q = p.torque(rpm, dt.rho)
    t = p.thrust(rpm, dt.rho)
    r_m = m.resistance(dt.winding_temp_c)

    i0 = m.i0(omega)
    i_m = q / m.kt + i0
    emf = m.back_emf(omega)
    v_m = emf + i_m * r_m
    v_req = v_m + i_m * e.r_on_ohm
    d = _required_duty(s.v_open, s.r_series, e.i_q_a, i_m, v_req)
    i_in = d * i_m + e.i_q_a
    v_in = s.v_open - i_in * s.r_series

    p_shaft = q * omega
    p_cu = i_m**2 * r_m
    p_noload = i0 * emf
    p_esc = i_m**2 * e.r_on_ohm + e.i_q_a * v_in
    p_in = v_in * i_in
    p_lead = i_in**2 * s.r_series
    p_source = s.v_open * i_in
    with np.errstate(invalid="ignore", divide="ignore"):
        eta_motor = p_shaft / (v_m * i_m)
        eta_esc = (v_m * i_m) / p_in
        eta_drive = p_shaft / p_in
    ct, cp = p.coefficients(rpm)
    reachable = np.isfinite(d) & (d <= e.d_max)
    cc = np.zeros_like(rpm, dtype=bool) if s.i_limit is None else (i_in > s.i_limit)
    return OperatingPoints(
        rpm=rpm, omega=omega, duty=d, thrust_n=t, torque_nm=q, p_shaft=p_shaft, i_motor=i_m, v_motor=v_m,
        back_emf=emf, i_in=i_in, v_in=v_in, p_in=p_in, p_source=p_source, p_cu=p_cu, p_noload=p_noload,
        p_esc=p_esc, p_lead=p_lead, eta_motor=eta_motor, eta_esc=eta_esc, eta_drive=eta_drive, ct=ct, cp=cp,
        fm=p.figure_of_merit(rpm), extrapolated=p.is_extrapolated(rpm), reachable=reachable, cc_limited=cc,
    )


def required_duty(dt: Drivetrain, rpm) -> np.ndarray:
    return at_rpm(dt, rpm).duty


def rpm_at_duty(dt: Drivetrain, duty: float, rpm_hi: float = 60_000.0) -> float:
    """Steady rpm for a given ESC duty (0 if the motor cannot overcome no-load loss)."""

    def f(r):
        d = required_duty(dt, r)
        d = float(np.atleast_1d(d)[0])
        return (10.0 if not np.isfinite(d) else d) - duty

    lo = 1.0
    if f(lo) > 0:
        return 0.0
    hi = min(rpm_hi, dt.motor.kv * dt.source.v_open * 1.05 + 10.0)
    if f(hi) < 0:
        return float("nan")
    return brentq(f, lo, hi, xtol=1e-3)


def at_duty(dt: Drivetrain, duty) -> OperatingPoints:
    duty = np.atleast_1d(np.asarray(duty, dtype=float))
    rpms = np.array([rpm_at_duty(dt, d) for d in duty])
    return at_rpm(dt, rpms)


def max_rpm(dt: Drivetrain) -> float:
    """Highest steady rpm reachable at the ESC's maximum duty."""
    return rpm_at_duty(dt, dt.esc.d_max)


def voltage_for_duty(dt: Drivetrain, rpm: float, duty_target: float, v_lo: float = 1.0, v_hi: float = 60.0) -> float:
    """Source open-circuit voltage at which `rpm` needs exactly `duty_target`."""

    def f(v):
        d = float(np.atleast_1d(required_duty(dt.with_(source=_replace_v(dt.source, v)), rpm))[0])
        return (10.0 if not np.isfinite(d) else d) - duty_target

    if f(v_hi) > 0:
        return float("nan")
    return brentq(f, v_lo, v_hi, xtol=1e-4)


def _replace_v(src: DCSource, v: float) -> DCSource:
    from dataclasses import replace

    return replace(src, v_open=v)
