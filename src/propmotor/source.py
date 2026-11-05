"""DC power sources: lab power supply (CV/CC) and LiPo pack, both as a Thevenin source.

    V_in = V_open - I_in R_series

For a lab supply V_open is the set voltage and R_series the leads + connectors (+ the
stand's shunt). With remote sensing at the ESC input R_series -> 0. For a battery
V_open = N_s * V_cell(SoC) and R_series = N_s R_cell / N_p + leads.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DCSource:
    name: str
    v_open: float  # [V]
    r_series: float = 0.02  # [ohm]
    i_limit: float | None = None  # CC limit [A]
    p_limit: float | None = None  # [W]

    def terminal_voltage(self, i_in):
        return self.v_open - i_in * self.r_series


@dataclass(frozen=True)
class PowerSupplySpec:
    """Rating of a lab power supply (to check settings against)."""

    name: str
    v_max: float
    i_max: float
    p_max: float
    v_resolution: float = 0.01

    def at(self, v_set: float, r_leads: float = 0.02, i_limit: float | None = None) -> DCSource:
        if v_set > self.v_max:
            raise ValueError(f"{self.name}: {v_set} V exceeds {self.v_max} V")
        return DCSource(name=f"{self.name} @ {v_set:.2f} V", v_open=v_set, r_series=r_leads,
                        i_limit=self.i_max if i_limit is None else i_limit, p_limit=self.p_max)


# Kikusui PWR401L (PWR-01 series, 400 W wide-range): 0-40 V, 0-40 A, 400 W.
KIKUSUI_PWR401L = PowerSupplySpec(name="Kikusui PWR401L", v_max=40.0, i_max=40.0, p_max=400.0)


def lipo_pack(n_series: int, n_parallel: int = 1, v_cell: float = 3.8, r_cell: float = 0.006,
              r_leads: float = 0.01) -> DCSource:
    """Simple LiPo pack: nominal-ish cell voltage under load and internal resistance."""
    return DCSource(name=f"LiPo {n_series}S{n_parallel}P", v_open=n_series * v_cell,
                    r_series=n_series * r_cell / n_parallel + r_leads)
