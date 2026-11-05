"""Regeneration (energy flowing back to the supply) when the rotor decelerates.

A lab supply normally cannot sink current. If the ESC actively brakes (complementary
PWM / "damped light", brake on stop) part of the rotor kinetic energy is pushed back
into the DC bus. With nothing to absorb it, it charges the bus capacitance:

    E = 1/2 J omega^2,        V_after = sqrt(V_0^2 + 2 eta_r E / C)

The propeller's own aerodynamic torque already decelerates the rotor quickly
(dw/dt = -Q/J); if the commanded speed is reduced more slowly than this natural
decay, the motor keeps motoring and no energy returns.
"""

from __future__ import annotations

import numpy as np

from .units import rpm_to_rads


def prop_inertia_estimate(mass_kg: float, diameter_m: float, shape_factor: float = 0.6) -> float:
    """J of a two-blade prop ~ shape_factor * (1/12) m D^2 (uniform slender rod -> shape_factor = 1).

    Real blades are thicker near the hub, so shape_factor < 1 (0.5-0.7 typical).
    """
    return shape_factor * mass_kg * diameter_m**2 / 12.0


def rotor_inertia_estimate(bell_mass_kg: float, bell_radius_m: float) -> float:
    """Outrunner bell approximated as a thin ring (upper bound)."""
    return bell_mass_kg * bell_radius_m**2


def kinetic_energy(j_kgm2: float, rpm) -> np.ndarray:
    return 0.5 * j_kgm2 * rpm_to_rads(np.asarray(rpm, dtype=float)) ** 2


def bus_voltage_after(v0: float, energy_j, capacitance_f, fraction: float = 1.0) -> np.ndarray:
    return np.sqrt(v0**2 + 2.0 * fraction * np.asarray(energy_j) / np.asarray(capacitance_f))


def natural_decel_rpm_per_s(prop, rho: float, j_kgm2: float, rpm) -> np.ndarray:
    """Coast-down rate from aerodynamic torque only: |d rpm/dt| = Q / J * 30/pi."""
    q = prop.torque(rpm, rho)
    return q / j_kgm2 * 30.0 / np.pi
