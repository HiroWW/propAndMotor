"""Unit conversions and physical constants (SI internally)."""

from __future__ import annotations

import math

G0 = 9.80665  # standard gravity [m/s^2]
IN_TO_M = 0.0254
RPM_TO_RADS = math.pi / 30.0
RADS_TO_RPM = 30.0 / math.pi
KGF_TO_N = G0
N_TO_GF = 1000.0 / G0
COPPER_ALPHA = 0.00393  # temperature coefficient of copper resistance [1/K]


def rpm_to_rads(rpm):
    return rpm * RPM_TO_RADS


def rads_to_rpm(omega):
    return omega * RADS_TO_RPM


def rpm_to_rps(rpm):
    return rpm / 60.0
