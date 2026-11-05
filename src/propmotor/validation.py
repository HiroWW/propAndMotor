"""Check the propeller + motor models against independent manufacturer measurements."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .motor import Motor
from .propeller import StaticPropData
from .units import N_TO_GF


@dataclass
class TestPoint:
    label: str
    motor: Motor
    v_supply: float
    throttle: str
    rpm: float
    current_a: float
    power_w: float
    thrust_g: float | None
    url: str


def load_tests(path: str | Path | None = None) -> list[TestPoint]:
    path = path or Path(str(resources.files("propmotor").joinpath("data", "catalog", "manufacturer_tests.toml")))
    d = tomllib.loads(Path(path).read_text())
    out = []
    for t in d["test"]:
        m = Motor(t["label"], kv=t["kv"], r_ohm=t["r_ohm"], i0_a=t["i0_a"])
        out.append(TestPoint(t["label"], m, t["v_supply"], t["throttle"], t["rpm"], t["current_a"], t["power_w"],
                             t.get("thrust_g"), t.get("url", "")))
    return out


def predict(tp: TestPoint, prop: StaticPropData, rho: float = 1.2) -> dict:
    """Model values at the measured rpm (no assumption about the manufacturer's ESC/battery)."""
    q = float(prop.torque(tp.rpm, rho))
    i_m = q / tp.motor.kt + tp.motor.i0_a
    v_m = tp.rpm / tp.motor.kv + i_m * tp.motor.r_ohm
    return {"thrust_g": float(prop.thrust(tp.rpm, rho)) * N_TO_GF, "i_motor": i_m, "p_motor_in": v_m * i_m,
            "p_shaft": float(prop.power(tp.rpm, rho)), "duty_est": v_m / tp.v_supply}
