"""First-order brushless DC motor model (Drela, "First-Order DC Electric Motor Model", 2007).

Equivalent circuit (averaged over commutation, line-to-line quantities):

    V_m = E + I R            E = omega / K_v        (back-EMF)
    Q   = K_t (I - I_0)      K_t = 1 / K_v           (SI units: K_v in rad/s/V, K_t in N m/A)

so that
    shaft power  P_shaft = Q omega = (I - I_0) E
    copper loss  P_cu    = I^2 R
    no-load loss P_0     = I_0 E      (iron loss + bearing friction + rotor windage)
    efficiency   eta     = (1 - I_0/I) (1 - I R / V_m)

The datasheet K_v [rpm/V] is converted to SI with pi/30.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .units import COPPER_ALPHA, RPM_TO_RADS


@dataclass(frozen=True)
class Motor:
    name: str
    kv: float  # [rpm/V]
    r_ohm: float  # line-to-line winding resistance at 25 degC [ohm]
    i0_a: float  # no-load current at i0_ref_v [A]
    i0_ref_v: float = 10.0  # voltage at which i0 is specified [V]
    # I_0(omega) = I0 * ((1 - beta) + beta * omega / omega_ref). beta=0 -> constant (Drela 1st order).
    i0_speed_beta: float = 0.0
    i_max_a: float | None = None  # rated max continuous current [A]
    p_max_w: float | None = None  # rated max power [W]
    v_max: float | None = None  # max recommended supply voltage [V] (from cell count)
    mass_g: float | None = None
    poles: int | None = None  # magnet poles (e.g. 14 for 12N14P)
    shaft_mm: float | None = None
    mount: str = ""
    price: str = ""
    url: str = ""
    notes: str = ""
    meta: dict = field(default_factory=dict)

    # ---- constants -------------------------------------------------------
    @property
    def kv_si(self) -> float:
        """K_v in rad/s per volt."""
        return self.kv * RPM_TO_RADS

    @property
    def kt(self) -> float:
        """Torque constant [N m / A] = 1 / K_v(SI)."""
        return 1.0 / self.kv_si

    @property
    def km(self) -> float:
        """Motor constant K_m = K_t / sqrt(R) [N m / sqrt(W)]: torque per sqrt(copper loss)."""
        return self.kt / math.sqrt(self.r_ohm)

    @property
    def omega_i0_ref(self) -> float:
        """Approximate shaft speed of the no-load-current measurement [rad/s]."""
        return self.kv_si * (self.i0_ref_v - self.i0_a * self.r_ohm)

    def resistance(self, temp_c: float = 25.0) -> float:
        return self.r_ohm * (1.0 + COPPER_ALPHA * (temp_c - 25.0))

    def i0(self, omega) -> np.ndarray:
        omega = np.asarray(omega, dtype=float)
        b = self.i0_speed_beta
        return self.i0_a * ((1.0 - b) + b * omega / self.omega_i0_ref)

    # ---- operating relations ---------------------------------------------
    def current(self, torque_nm, omega) -> np.ndarray:
        return np.asarray(torque_nm) / self.kt + self.i0(omega)

    def back_emf(self, omega) -> np.ndarray:
        return np.asarray(omega) / self.kv_si

    def terminal_voltage(self, omega, current, temp_c: float = 25.0) -> np.ndarray:
        return self.back_emf(omega) + np.asarray(current) * self.resistance(temp_c)

    def torque_from_v_omega(self, v_m, omega, temp_c: float = 25.0) -> np.ndarray:
        """Shaft torque for a given terminal voltage and speed (torque-speed line)."""
        i = (np.asarray(v_m) - self.back_emf(omega)) / self.resistance(temp_c)
        return self.kt * (i - self.i0(omega))

    def efficiency(self, torque_nm, omega, temp_c: float = 25.0) -> np.ndarray:
        i = self.current(torque_nm, omega)
        v = self.terminal_voltage(omega, i, temp_c)
        p_in = v * i
        p_out = np.asarray(torque_nm) * np.asarray(omega)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(p_in > 0, p_out / p_in, np.nan)

    def with_kv(self, kv: float) -> "Motor":
        """Same frame (same copper volume / magnetics), different winding.

        Rewinding with turns N -> N k changes K_v -> K_v / k and R -> R k^2 (same copper
        area fill). The iron loss power at a given speed is unchanged, so I_0 at a given
        speed scales with K_v. Hence K_m and copper loss for a given torque are unchanged.
        """
        k = self.kv / kv
        return replace(self, name=f"{self.name} (Kv{kv:.0f} rewind)", kv=kv, r_ohm=self.r_ohm * k**2,
                       i0_a=self.i0_a / k, i0_ref_v=self.i0_ref_v * k,
                       i_max_a=None if self.i_max_a is None else self.i_max_a / k)
