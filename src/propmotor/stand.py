"""Thrust-stand limits and measurement-uncertainty model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .units import G0


@dataclass(frozen=True)
class ThrustStand:
    name: str
    thrust_max_n: float
    torque_max_nm: float
    v_max: float
    i_max: float
    i_burst: float
    # tolerance = rel * |reading| + abs   (datasheet "0.5% -+ 0.001 kgf")
    thrust_tol_rel: float
    thrust_tol_abs_n: float
    torque_tol_rel: float
    torque_tol_abs_nm: float
    v_tol_rel: float
    i_tol_rel: float
    rpm_optical_range: tuple[float, float] = (10.0, 30_000.0)
    notes: str = ""

    def thrust_uncertainty(self, thrust_n):
        return self.thrust_tol_rel * np.abs(thrust_n) + self.thrust_tol_abs_n

    def torque_uncertainty(self, torque_nm):
        return self.torque_tol_rel * np.abs(torque_nm) + self.torque_tol_abs_nm

    def coefficient_rel_uncertainty(self, thrust_n, torque_nm, rpm_rel: float = 0.002, rho_rel: float = 0.01):
        """Worst-case-style RSS relative uncertainty of C_T and C_P from one steady sample.

        C_T = T / (rho n^2 D^4)     -> (dT/T)^2 + (2 dn/n)^2 + (drho/rho)^2
        C_P = 2 pi Q / (rho n^2 D^5) -> (dQ/Q)^2 + (2 dn/n)^2 + (drho/rho)^2
        Averaging N samples reduces only the random part; the datasheet tolerance is
        treated here as a bias-like bound, so no 1/sqrt(N) reduction is applied.
        """
        t = np.abs(thrust_n)
        q = np.abs(torque_nm)
        with np.errstate(divide="ignore", invalid="ignore"):
            ut = self.thrust_uncertainty(t) / t
            uq = self.torque_uncertainty(q) / q
        common = (2 * rpm_rel) ** 2 + rho_rel**2
        return np.sqrt(ut**2 + common), np.sqrt(uq**2 + common)


TYTO_1585 = ThrustStand(
    name="Tyto Robotics Series 1585",
    thrust_max_n=5.0 * G0,
    torque_max_nm=2.0,
    v_max=50.0,
    i_max=55.0,
    i_burst=60.0,
    thrust_tol_rel=0.005,
    thrust_tol_abs_n=0.001 * G0,
    torque_tol_rel=0.005,
    torque_tol_abs_nm=0.001,
    v_tol_rel=0.005,
    i_tol_rel=0.01,
    notes="Datasheet V2.4 (2024-08-01). Electrical RPM probe unreliable below 500 rpm or Kv<700; optical probe 10-30k rpm.",
)
