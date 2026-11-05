"""propmotor: propeller / motor / ESC / source matching for static thrust tests."""

from .atmosphere import air_density
from .esc import ESC, generic_esc
from .motor import Motor
from .propeller import (StaticPropData, apc_8x3_8sf_design, apc_8x3_8sf_measured, apc_8x3_8sf_theory,
                        apc_rpm_limit, envelope)
from .source import KIKUSUI_PWR401L, DCSource, PowerSupplySpec, lipo_pack
from .system import Drivetrain, at_duty, at_rpm, max_rpm, required_duty, rpm_at_duty, voltage_for_duty

__all__ = [
    "air_density", "ESC", "generic_esc", "Motor", "StaticPropData", "apc_8x3_8sf_design",
    "apc_8x3_8sf_measured", "apc_8x3_8sf_theory", "apc_rpm_limit", "envelope", "KIKUSUI_PWR401L",
    "DCSource", "PowerSupplySpec", "lipo_pack", "Drivetrain", "at_duty", "at_rpm", "max_rpm",
    "required_duty", "rpm_at_duty", "voltage_for_duty",
]
