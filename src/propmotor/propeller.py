"""Static (hover, J = 0) propeller model.

Conventions (same as APC and UIUC, n in rev/s):
    T = C_T * rho * n^2 * D^4
    P = C_P * rho * n^3 * D^5
    Q = P / omega = C_P * rho * n^2 * D^5 / (2 pi)
    FM = C_T^(3/2) / (sqrt(pi/2) * C_P)   (ideal momentum-theory power / actual power)

At J = 0 the coefficients still depend on rpm because the blade Reynolds number
(and, at high speed, tip Mach number) changes. The model therefore stores
C_T(rpm), C_P(rpm) tables and interpolates in rpm.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import numpy as np

from .units import IN_TO_M, rpm_to_rads, rpm_to_rps

SQRT_HALF_PI = math.sqrt(math.pi / 2.0)


@dataclass(frozen=True)
class StaticPropData:
    """Static thrust/power coefficients versus rpm for one propeller and one data source."""

    name: str
    label: str  # short label for plots
    kind: str  # "theory" | "measured" | "envelope"
    diameter_m: float
    rpm: np.ndarray
    ct: np.ndarray
    cp: np.ndarray
    source: str = ""
    # Number of highest-rpm points used for the linear extrapolation above the data range.
    extrap_points: int = 6
    extra: dict = field(default_factory=dict)

    # ---- coefficients -------------------------------------------------
    @property
    def rpm_range(self) -> tuple[float, float]:
        return float(self.rpm[0]), float(self.rpm[-1])

    def is_extrapolated(self, rpm) -> np.ndarray:
        rpm = np.asarray(rpm, dtype=float)
        lo, hi = self.rpm_range
        return (rpm < lo) | (rpm > hi)

    def _extrapolate_high(self, values: np.ndarray, rpm: np.ndarray) -> np.ndarray:
        k = min(self.extrap_points, len(self.rpm))
        slope, intercept = np.polyfit(self.rpm[-k:], values[-k:], 1)
        return intercept + slope * rpm

    def _coef(self, values: np.ndarray, rpm) -> np.ndarray:
        rpm = np.asarray(rpm, dtype=float)
        # Inside the table: linear interpolation. Below: hold the first value.
        out = np.interp(rpm, self.rpm, values)
        above = rpm > self.rpm[-1]
        if np.any(above):
            out = np.where(above, self._extrapolate_high(values, rpm), out)
        return out

    def ct_at(self, rpm) -> np.ndarray:
        return self._coef(self.ct, rpm)

    def cp_at(self, rpm) -> np.ndarray:
        return self._coef(self.cp, rpm)

    def coefficients(self, rpm) -> tuple[np.ndarray, np.ndarray]:
        return self.ct_at(rpm), self.cp_at(rpm)

    # ---- dimensional quantities ---------------------------------------
    def thrust(self, rpm, rho: float) -> np.ndarray:
        n = rpm_to_rps(np.asarray(rpm, dtype=float))
        return self.ct_at(rpm) * rho * n**2 * self.diameter_m**4

    def power(self, rpm, rho: float) -> np.ndarray:
        n = rpm_to_rps(np.asarray(rpm, dtype=float))
        return self.cp_at(rpm) * rho * n**3 * self.diameter_m**5

    def torque(self, rpm, rho: float) -> np.ndarray:
        n = rpm_to_rps(np.asarray(rpm, dtype=float))
        return self.cp_at(rpm) * rho * n**2 * self.diameter_m**5 / (2.0 * math.pi)

    def figure_of_merit(self, rpm) -> np.ndarray:
        ct, cp = self.coefficients(rpm)
        return ct**1.5 / (SQRT_HALF_PI * cp)

    def disk_area(self) -> float:
        return math.pi * self.diameter_m**2 / 4.0

    def ideal_power(self, thrust_n, rho: float) -> np.ndarray:
        """Momentum-theory (actuator disk) power for a given thrust: T^(3/2) / sqrt(2 rho A)."""
        t = np.asarray(thrust_n, dtype=float)
        return t**1.5 / math.sqrt(2.0 * rho * self.disk_area())

    def rpm_for_thrust(self, thrust_n: float, rho: float) -> float:
        """Invert T(rpm) (monotonic) by bisection."""
        from scipy.optimize import brentq

        return brentq(lambda r: float(self.thrust(r, rho)) - thrust_n, 10.0, 60_000.0)

    def tip_mach(self, rpm, temp_c: float = 20.0) -> np.ndarray:
        a = math.sqrt(1.4 * 287.058 * (temp_c + 273.15))
        return rpm_to_rads(np.asarray(rpm, dtype=float)) * self.diameter_m / 2.0 / a


def envelope(datasets: list[StaticPropData], rpm_grid, name: str = "envelope", label: str = "設計用包絡") -> StaticPropData:
    """Point-wise maximum of C_T and C_P over several data sources.

    Taking the max C_P (torque) and max C_T (thrust) gives a conservative load for
    sizing the motor/ESC and for checking stand limits.
    """
    rpm_grid = np.asarray(rpm_grid, dtype=float)
    d = datasets[0].diameter_m
    ct = np.max([ds.ct_at(rpm_grid) for ds in datasets], axis=0)
    cp = np.max([ds.cp_at(rpm_grid) for ds in datasets], axis=0)
    src = " / ".join(ds.label for ds in datasets)
    return StaticPropData(name=name, label=label, kind="envelope", diameter_m=d, rpm=rpm_grid, ct=ct, cp=cp,
                          source=f"max of: {src}")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

_APC_RPM_RE = re.compile(r"PROP RPM\s*=\s*(\d+)")
_APC_MODEL_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)")
_APC_COLUMNS = ["V_mph", "J", "Pe", "Ct", "Cp", "P_hp", "Q_inlbf", "T_lbf", "P_W", "Q_Nm", "T_N",
                "T_per_P_gW", "Mach", "Re75", "FOM"]


@dataclass(frozen=True)
class APCPerformance:
    """Full APC PER3 table: one array block per rpm."""

    model: str
    diameter_in: float
    pitch_in: float
    version: str
    blocks: dict[int, dict[str, np.ndarray]]

    def static(self, label: str = "APC公表値(理論)") -> StaticPropData:
        rpms = sorted(self.blocks)
        rows = [self.blocks[r] for r in rpms]
        j0 = [int(np.argmin(np.abs(b["J"]))) for b in rows]
        return StaticPropData(
            name=f"APC {self.model}",
            label=label,
            kind="theory",
            diameter_m=self.diameter_in * IN_TO_M,
            rpm=np.array(rpms, dtype=float),
            ct=np.array([b["Ct"][i] for b, i in zip(rows, j0)]),
            cp=np.array([b["Cp"][i] for b, i in zip(rows, j0)]),
            source=f"APC PER3 {self.model} ({self.version}), blade-element/vortex theory",
            extra={
                "mach_tip": np.array([b["Mach"][i] for b, i in zip(rows, j0)]),
                "re75": np.array([b["Re75"][i] for b, i in zip(rows, j0)]),
            },
        )


def load_apc_dat(path: str | Path) -> APCPerformance:
    text = Path(path).read_text(errors="replace").replace("\r", "")
    lines = text.split("\n")
    header = next(l for l in lines if l.strip())
    model = header.split("(")[0].strip()
    m = _APC_MODEL_RE.match(model)
    if not m:
        raise ValueError(f"cannot parse APC model string: {model!r}")
    version = next((l.strip() for l in lines[:5] if l.strip().startswith("v")), "")

    blocks: dict[int, dict[str, list[float]]] = {}
    rpm = None
    for line in lines:
        mm = _APC_RPM_RE.search(line)
        if mm:
            rpm = int(mm.group(1))
            blocks[rpm] = {c: [] for c in _APC_COLUMNS}
            continue
        if rpm is None:
            continue
        parts = line.split()
        if len(parts) != len(_APC_COLUMNS):
            continue
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            continue
        for c, v in zip(_APC_COLUMNS, vals):
            blocks[rpm][c].append(v)
    arr = {r: {c: np.array(v) for c, v in b.items()} for r, b in blocks.items() if b["J"]}
    return APCPerformance(model=model, diameter_in=float(m.group(1)), pitch_in=float(m.group(2)),
                          version=version, blocks=arr)


def load_uiuc_static(path: str | Path, diameter_in: float, name: str, label: str = "UIUC実測",
                     source: str = "") -> StaticPropData:
    data = np.loadtxt(path, skiprows=1)
    order = np.argsort(data[:, 0])
    data = data[order]
    return StaticPropData(name=name, label=label, kind="measured", diameter_m=diameter_in * IN_TO_M,
                          rpm=data[:, 0], ct=data[:, 1], cp=data[:, 2], source=source)


# ---------------------------------------------------------------------------
# Built-in data: APC 8x3.8SF
# ---------------------------------------------------------------------------

def _data_path(*parts: str) -> Path:
    return Path(str(resources.files("propmotor").joinpath("data", *parts)))


APC_SF_RPM_LIMIT_CONST = 65_000.0  # APC: max rpm = 65,000 / D[in] for Slow Flyer props


def apc_rpm_limit(diameter_in: float, constant: float = APC_SF_RPM_LIMIT_CONST) -> float:
    return constant / diameter_in


def apc_8x3_8sf_theory() -> StaticPropData:
    return load_apc_dat(_data_path("props", "apc", "PER3_8x38SF.dat")).static()


def apc_8x3_8sf_measured() -> StaticPropData:
    return load_uiuc_static(
        _data_path("props", "uiuc", "apcsf_8x3.8_static_2777rd.txt"),
        diameter_in=8.0,
        name="APC 8x3.8SF",
        label="UIUC実測",
        source="UIUC Propeller Data Site Vol.1, apcsf_8x3.8_static_2777rd (Brandt & Selig)",
    )


def apc_8x3_8sf_design(rpm_max: float = 10_000.0) -> StaticPropData:
    """Conservative envelope (max of APC theory and UIUC measurement) for sizing."""
    grid = np.arange(1000.0, rpm_max + 1.0, 250.0)
    return envelope([apc_8x3_8sf_theory(), apc_8x3_8sf_measured()], grid, name="APC 8x3.8SF")
