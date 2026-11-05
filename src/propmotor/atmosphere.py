"""Air density for the test room."""

from __future__ import annotations

import math

R_DRY = 287.058  # J/(kg K)
R_VAPOR = 461.495  # J/(kg K)


def saturation_vapor_pressure(temp_c: float) -> float:
    """Saturation vapour pressure of water [Pa] (Magnus-Tetens, valid ~ -40..50 degC)."""
    return 610.94 * math.exp(17.625 * temp_c / (temp_c + 243.04))


def air_density(temp_c: float = 20.0, pressure_pa: float = 101_325.0, rel_humidity: float = 0.0) -> float:
    """Density of (moist) air [kg/m^3].

    rho = p_d / (R_d T) + p_v / (R_v T), with p_v = RH * p_sat(T).
    Humidity lowers the density slightly (water vapour is lighter than dry air).
    """
    t_k = temp_c + 273.15
    p_v = rel_humidity * saturation_vapor_pressure(temp_c)
    p_d = pressure_pa - p_v
    return p_d / (R_DRY * t_k) + p_v / (R_VAPOR * t_k)
